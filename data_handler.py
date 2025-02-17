import streamlit as st
import pandas as pd
import requests
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
        self.db_session = get_database_connection()
        # Sample data for testing
        self.sample_data = pd.DataFrame({
            'Train Name': ['12345', '67890'],
            'Station': ['VNEC', 'GALA'],
            'Time': ['10:30', '11:45'],
            'Status': ['On Time', 'Delayed']
        })
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4/export?format=csv&gid=0"
        self.performance_metrics = {'load_time': 0, 'process_time': 0}

    def _fetch_csv_data(self) -> pd.DataFrame:
        """Fetch CSV data with improved error handling and logging"""
        start_time = time.time()
        try:
            logger.info(f"Attempting to fetch data from {self.spreadsheet_url}")

            @st.cache_data(ttl=300, show_spinner=False)
            def fetch_data(url):
                try:
                    response = requests.get(url)
                    response.raise_for_status()

                    df = pd.read_csv(url)
                    logger.info(f"Successfully loaded CSV with shape {df.shape}")

                    if df.empty:
                        logger.warning("Using sample data as CSV was empty")
                        return self.sample_data.copy()

                    return df

                except Exception as e:
                    logger.warning(f"Failed to fetch CSV, using sample data: {str(e)}")
                    return self.sample_data.copy()

            df = fetch_data(self.spreadsheet_url)

            # Map columns if needed
            required_cols = ['Train Name', 'Station', 'Time', 'Status']
            column_mappings = {
                'Train Name': ['Train_Name', 'TrainName', 'Train_ID', 'Train'],
                'Station': ['Station_Name', 'StationName', 'Stop'],
                'Time': ['Arrival_Time', 'Departure_Time', 'Schedule_Time'],
                'Status': ['Train_Status', 'CurrentStatus', 'State']
            }

            # Try to map columns
            for required_col, variants in column_mappings.items():
                if required_col not in df.columns:
                    for variant in variants:
                        if variant in df.columns:
                            df = df.rename(columns={variant: required_col})
                            break

            # Create any missing columns
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 'Not Available'

            # Clean and format data
            for col in required_cols:
                if col in df.columns:
                    df[col] = df[col].fillna('Not Available')
                    df[col] = df[col].astype(str).str.strip()

            # Ensure time format is consistent (HH:MM)
            def format_time(time_str):
                try:
                    # Handle empty or invalid values
                    if pd.isna(time_str) or time_str == 'Not Available':
                        return 'Not Available'
                    # Extract time part if datetime is present
                    if ' ' in time_str:
                        time_str = time_str.split()[1]
                    # Ensure HH:MM format
                    if ':' in time_str:
                        hours, minutes = map(int, time_str.split(':')[:2])
                        return f"{hours:02d}:{minutes:02d}"
                    return 'Not Available'
                except Exception:
                    return 'Not Available'

            df['Time'] = df['Time'].apply(format_time)

            self.performance_metrics['load_time'] = time.time() - start_time
            return df[required_cols]

        except Exception as e:
            logger.error(f"Error in _fetch_csv_data: {str(e)}", exc_info=True)
            return self.sample_data.copy()

    def _process_raw_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process raw data with optimized operations"""
        if df.empty:
            logger.warning("Received empty DataFrame for processing")
            return self.sample_data.copy()

        start_time = time.time()
        try:
            required_cols = ['Train Name', 'Station', 'Time', 'Status']
            processed_df = df[required_cols].copy()

            # Clean string columns
            for col in processed_df.columns:
                if col != 'Time':  # Skip time column as it's handled separately
                    processed_df[col] = processed_df[col].fillna('Not Available')
                    processed_df[col] = processed_df[col].astype(str).str.strip()

            self.performance_metrics['process_time'] = time.time() - start_time
            return processed_df

        except Exception as e:
            logger.error(f"Error processing data: {str(e)}", exc_info=True)
            return self.sample_data.copy()

    def get_train_status_table(self) -> pd.DataFrame:
        """Get status table from database with caching"""
        return _fetch_status(self.db_session)

    def load_data_from_drive(self) -> Tuple[bool, str]:
        """Load data from Google Sheets URL with optimized caching"""
        try:
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
                time_actual = pd.to_datetime(row['Time'], format='%H:%M', errors='coerce')
                time_scheduled = time_actual  # Simplified for now
                status, delay = self.get_timing_status(time_actual, time_scheduled)

                records.append(TrainDetails(
                    train_id=str(row['Train Name']),
                    station=str(row['Station']),
                    time_actual=time_actual,
                    time_scheduled=time_scheduled,
                    delay=delay,
                    status=status
                ))

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
        """Calculate if train is early, late, or on time"""
        try:
            diff_minutes = int((actual_time - scheduled_time).total_seconds() / 60)

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

    def get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        return self.performance_metrics