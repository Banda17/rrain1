import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime
from database import get_database_connection, TrainDetails
import logging
import time
from google.oauth2 import service_account
import gspread

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self):
        """Initialize Google Sheets connection and data structures"""
        self.data = None
        self.data_cache = {}
        self.column_data = {}  # Store column-wise data
        self.last_update = None
        self.update_interval = 300  # 5 minutes in seconds
        self.db_session = get_database_connection()
        self._initialize_google_sheets()

    def _initialize_google_sheets(self):
        """Initialize Google Sheets connection using service account."""
        try:
            logger.debug("Starting Google Sheets initialization...")

            # Verify required credentials exist
            required_fields = [
                'type', 'project_id', 'private_key_id', 'private_key',
                'client_email', 'client_id', 'auth_uri', 'token_uri',
                'auth_provider_x509_cert_url', 'client_x509_cert_url'
            ]

            credentials_info = {}
            missing_fields = []

            # Check each required field in st.secrets  - Commented out due to streamlit dependency
            #for field in required_fields:
            #    try:
            #        value = st.secrets[field]
            #        if not value:
            #            missing_fields.append(field)
            #        credentials_info[field] = value
            #    except Exception:
            #        missing_fields.append(field)

            #if missing_fields:
            #    error_msg = f"Missing required Google credentials: {', '.join(missing_fields)}"
            #    logger.error(error_msg)
            #    raise ValueError(error_msg)

            # Placeholder for credentials - Replace with your actual credentials loading
            credentials_info = {
                # Your Google Cloud service account credentials here
            }

            # Create credentials object
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
            except Exception as e:
                error_msg = f"Failed to create credentials: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Initialize gspread client
            try:
                self.client = gspread.authorize(credentials)
                logger.info("Google Sheets connection initialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize gspread client: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"Error initializing Google Sheets: {str(e)}"
            logger.error(error_msg)
            raise

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
        """Load data from Google Sheets with caching"""
        try:
            if not self.should_update() and self.data_cache:
                logger.debug("Using cached data")
                self.data = pd.DataFrame.from_dict(self.data_cache)
                return True, "Using cached data"

            logger.debug("Attempting to load data from Google Sheets")

            try:
                # Get spreadsheet ID - Commented out due to streamlit dependency
                #spreadsheet_id = st.secrets["spreadsheet_id"]
                # Placeholder for spreadsheet ID - Replace with your actual spreadsheet ID
                spreadsheet_id = "YOUR_SPREADSHEET_ID" # Replace with your actual spreadsheet ID

                worksheet = self.client.open_by_key(spreadsheet_id).sheet1
                data = worksheet.get_all_values()

                if not data:
                    return False, "No data found in spreadsheet"

                # Convert to DataFrame
                self.data = pd.DataFrame(data[1:], columns=data[0])

                # Clean the data
                for col in self.data.columns:
                    self.data[col] = self.data[col].astype(str).apply(lambda x: x.strip() if isinstance(x, str) else x)

                # Update cache and column data
                self.data_cache = self.data.to_dict('records')
                self._update_column_data()
                self.last_update = datetime.now()

                # Process and store data in database
                self._store_data_in_db()

                logger.info("Successfully loaded and processed data from Google Sheets")
                return True, "Data loaded successfully"
            except Exception as e:
                error_msg = f"Error loading data from Google Sheets: {str(e)}"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Error in data loading process: {str(e)}"
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