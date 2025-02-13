import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime
from database import get_database_connection, TrainDetails
import logging

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
        self.column_data = {}  # Store column-wise data
        self.last_update = None
        self.update_interval = 300  # 5 minutes in seconds
        self.db_session = get_database_connection()
        # Format URL for direct CSV download
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4/export?format=csv"

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
            # Get all columns and their data
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

    def load_data_from_drive(self, file_id: str = None) -> Tuple[bool, str]:
        """Load data from Google Sheets URL with caching"""
        try:
            if not self.should_update() and self.data_cache:
                logger.debug("Using cached data")
                self.data = pd.DataFrame.from_dict(self.data_cache)
                return True, "Using cached data"

            logger.debug("Attempting to read CSV from URL")

            # Read CSV directly from URL
            self.data = pd.read_csv(self.spreadsheet_url)

            # Clean the data
            for col in self.data.columns:
                self.data[col] = self.data[col].astype(str).apply(lambda x: x.strip() if isinstance(x, str) else x)

            # Update cache and column data
            self.data_cache = self.data.to_dict('records')
            self._update_column_data()
            self.last_update = datetime.now()

            # Process and store data in database
            self._store_data_in_db()

            return True, "Data loaded successfully from CSV URL"
        except Exception as e:
            error_msg = f"Error loading data from CSV URL: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

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

    def _store_data_in_db(self):
        """Store the loaded data in the database"""
        if self.data is None or self.data.empty:
            logger.warning("No data available to store in database")
            return

        try:
            for _, row in self.data.iterrows():
                # Convert time columns to datetime
                time_actual = pd.to_datetime(row['time_actual'])
                time_scheduled = pd.to_datetime(row['time_scheduled'])

                # Calculate delay and status
                status, delay = self.get_timing_status(time_actual, time_scheduled)

                train_detail = TrainDetails(
                    train_id=str(row['train_id']),
                    station=str(row['station']),
                    time_actual=time_actual,
                    time_scheduled=time_scheduled,
                    delay=delay,
                    status=status
                )
                self.db_session.add(train_detail)

            self.db_session.commit()
            logger.info("Successfully stored data in database")
        except Exception as e:
            logger.error(f"Error storing data in database: {str(e)}")
            self.db_session.rollback()
            raise

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

    def get_train_status_table(self) -> pd.DataFrame:
        """Get status table from database"""
        try:
            query = self.db_session.query(TrainDetails).order_by(TrainDetails.time_actual)
            records = query.all()

            if not records:
                logger.warning("No records found in database")
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
            logger.error(f"Error retrieving train status table: {str(e)}")
            return pd.DataFrame()

    def get_cached_data(self) -> Dict:
        """Get the cached data dictionary"""
        return self.data_cache