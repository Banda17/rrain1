import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Tuple, Any
from datetime import datetime
from database import get_database_connection, TrainDetails
import logging
import time

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Move fetch_status outside class to avoid hashing self
@st.cache_data(ttl=300, show_spinner=False)
def _fetch_status(_session):
    """Fetch status with caching, using _session to prevent hashing"""
    try:
        query = _session.query(TrainDetails).order_by(TrainDetails.time_actual)
        records = query.all()

        if not records:
            return pd.DataFrame()

        return pd.DataFrame([{
            'train_id': record.train_id,
            'station': record.station,
            'time_actual': record.time_actual,
            'time_scheduled': record.time_scheduled,
            'status': record.status,
            'delay': record.delay
        } for record in records])
    except Exception as e:
        logger.error(f"Error retrieving train status: {str(e)}")
        return pd.DataFrame()

class DataHandler:
    def __init__(self):
        """Initialize data structures"""
        self.data = None
        self.data_cache = {}
        self.processed_data_cache = {}
        self.column_data = {}
        self.last_update = None
        self.update_interval = 300  # 5 minutes in seconds
        self.performance_metrics = {'load_time': 0.0, 'process_time': 0.0}
        
        # Use the existing database session from st.session_state if available
        # This prevents creating new connections on refresh
        self._db_session = None
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=0&single=true&output=csv"
    
    @property
    def db_session(self):
        """Lazy initialization of database session
        
        This ensures we only create a session when it's actually needed
        and reuse the global connection established during init_db()
        """
        if self._db_session is None:
            logger.debug("Creating new database session (lazy initialization)")
            self._db_session = get_database_connection()
        return self._db_session

    def _fetch_csv_data(self) -> pd.DataFrame:
        """Fetch CSV data with performance tracking"""
        start_time = time.time()
        try:
            @st.cache_data(ttl=300, show_spinner=False)
            def fetch_data(url):
                return pd.read_csv(url)

            df = fetch_data(self.spreadsheet_url)
            self.performance_metrics['load_time'] = time.time() - start_time
            return df
        except Exception as e:
            logger.error(f"Error fetching CSV data: {str(e)}")
            return pd.DataFrame()

    def _process_raw_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process raw data with optimized operations"""
        if df.empty:
            return df

        start_time = time.time()
        try:
            # Handle the actual data format we're seeing
            if len(df) > 0:
                logger.info(f"Raw DataFrame columns: {df.columns.tolist()}")
                logger.info(f"First row: {df.iloc[0].tolist()}")
                
                # Initialize our result DataFrame with proper columns
                result_df = pd.DataFrame(columns=['Train Name', 'Station', 'Time', 'Status'])
                
                # Check if we have the new format with "FROM-TO", "Train No.", etc.
                # This is our primary target format based on the actual data we're seeing
                if 'Sr.' in df.columns and 'Train No.' in df.columns:
                    logger.info("Detected the expected sheet format with FROM-TO and Train No.")
                    
                    # Extract train number as Train Name
                    result_df['Train Name'] = df['Train No.'].astype(str)
                    
                    # Extract station from the DivisionalActual column
                    # Format is typically "GDR(-16) - DVD" where GDR and DVD are stations
                    stations = []
                    for entry in df['DivisionalActual[ Entry - Exit ]']:
                        if isinstance(entry, str) and '-' in entry:
                            # Extract first station (entry point)
                            station = entry.split('-')[0].strip()
                            # Remove any brackets and their contents
                            if '(' in station:
                                station = station.split('(')[0].strip()
                            stations.append(station)
                        else:
                            stations.append('UNKNOWN')
                    result_df['Station'] = stations
                    
                    # Use Act. Date as Time
                    result_df['Time'] = df['Act. Date'].astype(str)
                    
                    # Use Event as Status or a default if not available
                    result_df['Status'] = df['Event'].fillna('UNKNOWN')
                    
                    logger.info(f"Successfully processed {len(result_df)} rows from the expected format")
                    
                    # At this point we have properly formatted data, return it
                    return result_df
                
                # Alternative format - check if column names are in the first row instead
                elif any('Train Name' in str(val) for val in df.iloc[0].values) and any('Station' in str(val) for val in df.iloc[0].values):
                    logger.info("Found column names in first row format")
                    # Set proper column names using the first row
                    df.columns = df.iloc[0]
                    # Remove the header row
                    df = df.iloc[1:].reset_index(drop=True)
                    
                    # Clean up column names (remove leading/trailing whitespace)
                    df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]
                    
                    # Extract required columns if present
                    if 'Train Name' in df.columns and 'Station' in df.columns and 'Time' in df.columns and 'Status' in df.columns:
                        result_df = df[['Train Name', 'Station', 'Time', 'Status']].copy()
                        logger.info(f"Successfully extracted {len(result_df)} rows from first-row format")
                        return result_df
                
                # Last resort - try to create a minimal dataset to avoid errors
                logger.warning("Using fallback dataset creation with available columns")
                
                # Try to find any column with 'train' in the name for Train Name
                train_cols = [col for col in df.columns if any(x in col.lower() for x in ['train', 'tr no', 'train no'])]
                if train_cols:
                    logger.info(f"Using {train_cols[0]} for Train Name")
                    result_df['Train Name'] = df[train_cols[0]].astype(str)
                else:
                    result_df['Train Name'] = ["UNKNOWN"] * len(df)
                
                # Try to find any column with 'station' in the name
                station_cols = [col for col in df.columns if any(x in col.lower() for x in ['station', 'div', 'actual', 'divisional'])]
                if station_cols:
                    logger.info(f"Using {station_cols[0]} for Station")
                    result_df['Station'] = df[station_cols[0]].astype(str)
                else:
                    result_df['Station'] = ["UNKNOWN"] * len(df)
                
                # Try to find any column with 'time' or 'date' in the name
                time_cols = [col for col in df.columns if any(x in col.lower() for x in ['time', 'date', 'act.', 'schedule'])]
                if time_cols:
                    logger.info(f"Using {time_cols[0]} for Time")
                    result_df['Time'] = df[time_cols[0]].astype(str)
                else:
                    result_df['Time'] = [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")] * len(df)
                
                # Try to find any column with 'status' or 'event' in the name
                status_cols = [col for col in df.columns if any(x in col.lower() for x in ['status', 'event'])]
                if status_cols:
                    logger.info(f"Using {status_cols[0]} for Status")
                    result_df['Status'] = df[status_cols[0]].astype(str)
                else:
                    result_df['Status'] = ["UNKNOWN"] * len(df)
                
                logger.info(f"Created fallback dataset with {len(result_df)} rows")
                return result_df
            else:
                logger.error("Empty dataframe")
                return pd.DataFrame(columns=['Train Name', 'Station', 'Time', 'Status'])

            self.performance_metrics['process_time'] = time.time() - start_time
            return df
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            return pd.DataFrame(columns=['Train Name', 'Station', 'Time', 'Status'])

    def get_train_status_table(self) -> pd.DataFrame:
        """Get status table from database with caching"""
        return _fetch_status(self.db_session)

    def load_data_from_drive(self) -> Tuple[bool, str]:
        """Load data from Google Sheets URL with optimized caching"""
        try:
            # Clear cache to ensure fresh data load
            st.cache_data.clear()

            # Check cache first
            if not self.should_update() and self.processed_data_cache:
                logger.debug("Using processed data cache")
                self.data = pd.DataFrame(self.processed_data_cache)
                return True, "Using cached data"

            # Fetch and process data with performance tracking
            start_time = time.time()

            raw_data = self._fetch_csv_data()
            if raw_data.empty:
                return False, "No data received from CSV"

            self.data = self._process_raw_data(raw_data)

            # Update caches efficiently
            self.data_cache = raw_data.to_dict('records')
            self.processed_data_cache = self.data.to_dict('records')
            self._update_column_data()
            self.last_update = datetime.now()

            # Store in database synchronously but efficiently
            self._store_data_in_db()

            total_time = time.time() - start_time
            logger.info(f"Total load time: {total_time:.2f}s (Load: {self.performance_metrics['load_time']:.2f}s, Process: {self.performance_metrics['process_time']:.2f}s)")

            return True, f"Data loaded in {total_time:.2f} seconds"
        except Exception as e:
            error_msg = f"Error loading data: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def should_update(self) -> bool:
        """Check if data should be updated"""
        if self.last_update is None:
            return True
        time_diff = (datetime.now() - self.last_update).total_seconds()
        return time_diff >= self.update_interval

    def _update_column_data(self):
        """Update column-wise data dictionary"""
        if self.data is None or self.data.empty:
            logger.warning("No data available to update column data")
            return

        try:
            logger.debug("Starting column data update")
            self.column_data = {
                col: {
                    'values': self.data[col].tolist(),
                    'unique_values': self.data[col].unique().tolist(),
                    'count': len(self.data[col]),
                    'last_updated': datetime.now().isoformat()
                }
                for col in self.data.columns
            }
            logger.debug(f"Updated column data with {len(self.column_data)} columns")
        except Exception as e:
            logger.error(f"Error updating column data: {str(e)}")
            raise

    def _store_data_in_db(self):
        """Store data in database with efficient batching"""
        if self.data is None or self.data.empty:
            return

        try:
            # Process in batches for better performance
            batch_size = 100
            records = []

            for _, row in self.data.iterrows():
                try:
                    # Handle the specific format we're seeing: "07 Mar 07:38"
                    time_str = str(row['Time'])
                    logger.debug(f"Processing time string: {time_str}")
                    
                    # Manually parse this specific format
                    if len(time_str) > 0 and re.match(r'\d{2} [A-Za-z]{3} \d{2}:\d{2}', time_str):
                        day = time_str[:2]
                        month = time_str[3:6]
                        time_part = time_str[7:]
                        
                        # Convert month abbreviation to month number
                        month_num = {
                            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                        }.get(month, '01')
                        
                        # Construct an ISO format date string with current year
                        current_year = datetime.now().year
                        iso_date_str = f"{current_year}-{month_num}-{day}T{time_part}:00"
                        logger.debug(f"Constructed ISO date: {iso_date_str}")
                        
                        # Create datetime object
                        time_actual = pd.Timestamp(iso_date_str)
                    else:
                        # Try standard parsing if it doesn't match our expected format
                        try:
                            time_actual = pd.to_datetime(time_str)
                        except:
                            logger.warning(f"Could not parse time: {time_str}, using current time")
                            time_actual = pd.Timestamp.now()
                    
                    time_scheduled = time_actual  # Simplified for now
                    
                    # Skip records with NaT values to prevent database errors
                    if pd.isna(time_actual) or pd.isna(time_scheduled):
                        logger.warning(f"Skipping record with NaT timestamp: Train={row.get('Train Name', 'unknown')}, Station={row.get('Station', 'unknown')}")
                        continue
                        
                    # Calculate timing status only after validating timestamps
                    status, delay = self.get_timing_status(time_actual, time_scheduled)
                        
                    # Ensure train_id is a string and not a timestamp
                    train_id = str(row.get('Train Name', ''))
                    if not train_id or pd.isna(train_id) or 'NaT' in train_id:
                        logger.warning(f"Invalid train ID: {train_id}, skipping record")
                        continue
                        
                    records.append(TrainDetails(
                        train_id=train_id,
                        station=str(row.get('Station', 'UNKNOWN')),
                        time_actual=time_actual,
                        time_scheduled=time_scheduled,
                        delay=delay,
                        status=status
                    ))
                except Exception as e:
                    logger.error(f"Error processing row: {str(e)}")
                    # Skip this row and continue with the next

                # Commit in batches
                if len(records) >= batch_size:
                    self.db_session.bulk_save_objects(records)
                    self.db_session.commit()
                    records = []

            # Commit any remaining records
            if records:
                self.db_session.bulk_save_objects(records)
                self.db_session.commit()

            logger.info("Data stored in database successfully")
        except Exception as e:
            logger.error(f"Database storage error: {str(e)}")
            self.db_session.rollback()

    def get_timing_status(self, actual_time: datetime, scheduled_time: datetime) -> Tuple[str, int]:
        """
        Calculate if train is early, late, or on time with enhanced validation
        
        Args:
            actual_time: The actual arrival/departure time
            scheduled_time: The scheduled arrival/departure time
            
        Returns:
            Tuple of (status_string, time_difference_in_minutes)
        """
        try:
            # Validate input timestamps
            if actual_time is None or scheduled_time is None:
                logger.warning("Received None timestamp in get_timing_status")
                return "UNKNOWN ❓", 0
                
            # Handle non-datetime objects
            if not isinstance(actual_time, datetime) or not isinstance(scheduled_time, datetime):
                logger.warning(f"Invalid timestamp types: actual={type(actual_time)}, scheduled={type(scheduled_time)}")
                
                # Try to convert strings to datetime if possible
                if isinstance(actual_time, str) and isinstance(scheduled_time, str):
                    try:
                        # Try standard format
                        actual_time = datetime.fromisoformat(actual_time)
                        scheduled_time = datetime.fromisoformat(scheduled_time)
                    except ValueError:
                        # Try common format with timezone info
                        try:
                            from dateutil import parser
                            actual_time = parser.parse(actual_time)
                            scheduled_time = parser.parse(scheduled_time)
                        except:
                            logger.error("Failed to parse timestamp strings")
                            return "UNKNOWN ❓", 0
                else:
                    return "UNKNOWN ❓", 0
            
            # Calculate time difference in minutes
            diff_minutes = int((actual_time - scheduled_time).total_seconds() / 60)

            # Apply business rules for status determination
            if diff_minutes <= -5:
                return "EARLY ⏰", diff_minutes
            elif diff_minutes > 5:
                return "LATE ⚠️", diff_minutes
            else:
                return "ON TIME ✅", diff_minutes
                
        except Exception as e:
            logger.error(f"Error calculating timing status: {str(e)}")
            return "UNKNOWN ❓", 0

    def get_column_data(self, column_name: str) -> Dict[str, Any]:
        """Get data for a specific column"""
        if not self.column_data:
            return {}
        return self.column_data.get(column_name, {})

    def get_all_columns(self) -> List[str]:
        """Get list of all column names"""
        return list(self.column_data.keys())

    def get_column_statistics(self, column_name: str) -> Dict[str, Any]:
        """Get statistics for a specific column"""
        column_data = self.get_column_data(column_name)
        if not column_data:
            return {}

        return {
            'unique_count': len(column_data['unique_values']),
            'total_count': column_data['count'],
            'last_updated': column_data['last_updated']
        }

    def get_cached_data(self) -> Dict:
        """Get the cached data dictionary"""
        if not self.data_cache:
            logger.warning("No data in cache")
            return {}
        logger.debug(f"Returning cached data with {len(self.data_cache)} records")
        return self.data_cache

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return self.performance_metrics