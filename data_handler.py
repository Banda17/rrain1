import streamlit as st
import pandas as pd
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
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4/export?format=csv"
        self.performance_metrics = {'load_time': 0, 'process_time': 0}

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
            # Process only required columns with optimized operations
            required_cols = ['Train Name', 'Station', 'Time', 'Status']
            df = df[required_cols].copy()

            # Vectorized string cleaning
            df = df.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)

            # Efficient datetime conversion
            df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')

            self.performance_metrics['process_time'] = time.time() - start_time
            return df
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            return pd.DataFrame()

    def get_train_status_table(self) -> pd.DataFrame:
        """Get status table from database with caching"""
        @st.cache_data(ttl=300, show_spinner=False)
        def fetch_status(session):
            try:
                query = session.query(TrainDetails).order_by(TrainDetails.time_actual)
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

        return fetch_status(self.db_session)

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

            # Store in database asynchronously
            st.runtime.async_run(self._store_data_in_db())

            total_time = time.time() - start_time
            logger.info(f"Total load time: {total_time:.2f}s (Load: {self.performance_metrics['load_time']:.2f}s, Process: {self.performance_metrics['process_time']:.2f}s)")

            return True, f"Data loaded in {total_time:.2f} seconds"
        except Exception as e:
            error_msg = f"Error loading data: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        return self.performance_metrics

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

    async def _store_data_in_db(self):
        """Asynchronously store data in database"""
        if self.data is None or self.data.empty:
            return

        try:
            for _, row in self.data.iterrows():
                time_actual = pd.to_datetime(row['Time'])
                time_scheduled = time_actual  # Simplified for now
                status, delay = self.get_timing_status(time_actual, time_scheduled)

                train_detail = TrainDetails(
                    train_id=str(row['Train Name']),
                    station=str(row['Station']),
                    time_actual=time_actual,
                    time_scheduled=time_scheduled,
                    delay=delay,
                    status=status
                )
                self.db_session.add(train_detail)

            await self.db_session.commit()
            logger.info("Data stored in database")
        except Exception as e:
            logger.error(f"Database storage error: {str(e)}")
            await self.db_session.rollback()

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