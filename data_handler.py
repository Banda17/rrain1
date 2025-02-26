import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime
from database import get_database_connection, TrainDetails
import logging
import time
import requests

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
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=377625640&single=true&output=csv"
        self.performance_metrics = {'load_time': 0, 'process_time': 0}
        self.last_error = None

    def _fetch_csv_data(self) -> pd.DataFrame:
        """Fetch CSV data with enhanced error handling and performance tracking"""
        start_time = time.time()
        try:
            # First, try to make a HEAD request to check if the URL is accessible
            try:
                head_response = requests.head(self.spreadsheet_url, timeout=5, allow_redirects=True)
                status_code = head_response.status_code

                # Log redirect information if present
                if head_response.history:
                    redirect_chain = " -> ".join([str(r.status_code) for r in head_response.history])
                    logger.info(f"Redirect chain: {redirect_chain}")
                    logger.info(f"Final URL after redirects: {head_response.url}")

                if status_code != 200:
                    error_msg = f"Error accessing spreadsheet: HTTP {status_code}"
                    logger.error(error_msg)
                    self.last_error = error_msg
                    return pd.DataFrame()

            except requests.exceptions.RequestException as e:
                error_msg = f"Connection error checking spreadsheet URL: {str(e)}"
                logger.error(error_msg)
                self.last_error = error_msg
                return pd.DataFrame()

            @st.cache_data(ttl=300, show_spinner=False)
            def fetch_data(url):
                try:
                    # Use a session to handle redirects properly
                    session = requests.Session()

                    # Configure session to follow redirects
                    session.max_redirects = 5

                    # Make the request with the session
                    response = session.get(url, timeout=10)

                    # Log redirect information
                    if response.history:
                        redirect_chain = " -> ".join([str(r.status_code) for r in response.history])
                        logger.info(f"GET request redirect chain: {redirect_chain}")
                        logger.info(f"Final URL after GET redirects: {response.url}")

                    status_code = response.status_code
                    if status_code != 200:
                        error_msg = f"Error downloading CSV: HTTP {status_code}"
                        logger.error(error_msg)
                        self.last_error = error_msg
                        return pd.DataFrame()

                    # Try to parse the CSV data directly from the response content
                    try:
                        # Convert the response content to a string with UTF-8 encoding
                        csv_content = response.content.decode('utf-8')

                        # Use pandas to read the CSV from the string content
                        return pd.read_csv(pd.io.common.StringIO(csv_content))
                    except Exception as e:
                        error_msg = f"Error parsing CSV data: {str(e)}"
                        logger.error(error_msg)
                        self.last_error = error_msg
                        return pd.DataFrame()
                except requests.exceptions.RequestException as e:
                    error_msg = f"Error downloading CSV: {str(e)}"
                    logger.error(error_msg)
                    self.last_error = error_msg
                    return pd.DataFrame()

            df = fetch_data(self.spreadsheet_url)
            if df.empty:
                logger.error("Received empty dataframe from CSV source")
                return pd.DataFrame()

            self.performance_metrics['load_time'] = time.time() - start_time
            return df
        except Exception as e:
            error_msg = f"Error fetching CSV data: {str(e)}"
            logger.error(error_msg)
            self.last_error = error_msg
            return pd.DataFrame()

    def _process_raw_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process raw data with optimized operations"""
        if df.empty:
            return df

        start_time = time.time()
        try:
            # Ensure we have the required columns in the first row
            if not all(col in df.iloc[0].values for col in ['Train Name', 'Station', 'Time', 'Status']):
                error_msg = "Required columns not found in data"
                logger.error(error_msg)
                self.last_error = error_msg
                return pd.DataFrame(columns=['Train Name', 'Station', 'Time', 'Status'])

            # Set the first row as headers and reset index
            df.columns = df.iloc[0]
            df = df.iloc[1:].reset_index(drop=True)

            # Process only required columns with optimized operations
            required_cols = ['Train Name', 'Station', 'Time', 'Status']
            try:
                df = df[required_cols].copy()
            except KeyError as e:
                error_msg = f"Missing required columns: {str(e)}"
                logger.error(error_msg)
                self.last_error = error_msg
                return pd.DataFrame(columns=required_cols)

            # Vectorized string cleaning
            df = df.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)

            # Efficient datetime conversion
            df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')

            self.performance_metrics['process_time'] = time.time() - start_time
            return df
        except Exception as e:
            error_msg = f"Error processing data: {str(e)}"
            logger.error(error_msg)
            self.last_error = error_msg
            return pd.DataFrame(columns=['Train Name', 'Station', 'Time', 'Status'])

    def get_train_status_table(self) -> pd.DataFrame:
        """Get status table from database with caching"""
        return _fetch_status(self.db_session)

    def load_data_from_drive(self) -> Tuple[bool, str]:
        """Load data from Google Sheets URL with improved error handling and caching"""
        try:
            # Reset last error
            self.last_error = None

            # Clear cache to ensure fresh data load
            st.cache_data.clear()

            # Fetch and process data with performance tracking
            start_time = time.time()

            raw_data = self._fetch_csv_data()
            if raw_data.empty:
                error_msg = self.last_error or "No data received from CSV - the source may be unavailable"
                logger.warning(error_msg)
                # Keep using existing cache if we already have data
                if not self.data_cache:
                    return False, error_msg
                logger.info("Using existing cache since new data fetch failed")
                return True, f"Warning: Using cached data. Data source error: {error_msg}"

            self.data = self._process_raw_data(raw_data)
            if self.data.empty:
                error_msg = self.last_error or "Failed to process data"
                logger.warning(error_msg)
                if not self.data_cache:
                    return False, error_msg
                logger.info("Using existing cache since data processing failed")
                return True, f"Warning: Using cached data. Processing error: {error_msg}"

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
            self.last_error = error_msg

            # If we have cached data, continue using it rather than failing completely
            if self.data_cache:
                logger.info("Using existing cache due to error in data loading")
                return True, f"Warning: Using cached data. Error: {error_msg}"

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
                time_actual = pd.to_datetime(row['Time'])
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

    def get_last_error(self) -> str:
        """Get the last error message"""
        return self.last_error or ""