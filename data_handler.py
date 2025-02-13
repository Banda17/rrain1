import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime
from database import get_database_connection, TrainDetails
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self):
        self.data = None
        self.db_session = get_database_connection()
        self.csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=0&single=true&output=csv"

    def load_data_from_drive(self, file_id: str = None) -> Tuple[bool, str]:
        """Load data from CSV URL"""
        try:
            logger.debug(f"Attempting to read CSV from URL")

            # Read CSV directly from URL with first row as headers
            self.data = pd.read_csv(self.csv_url, header=0)

            # Clean the data
            for col in self.data.columns:
                self.data[col] = self.data[col].astype(str).apply(lambda x: x.strip() if isinstance(x, str) else x)

            # Process and store data in database
            self._store_data_in_db()

            return True, "Data loaded successfully from CSV URL"
        except Exception as e:
            error_msg = f"Error loading data from CSV URL: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _store_data_in_db(self):
        """Store the loaded data in the database"""
        if self.data is None or self.data.empty:
            raise ValueError("No data available to store")

        for _, row in self.data.iterrows():
            # Convert time columns to datetime if they're not already
            time_actual = pd.to_datetime(row['time_actual']) if 'time_actual' in row else datetime.now()
            time_scheduled = pd.to_datetime(row['time_scheduled']) if 'time_scheduled' in row else datetime.now()

            # Calculate delay and status
            status, delay = self.get_timing_status(time_actual, time_scheduled)

            train_detail = TrainDetails(
                train_id=str(row.get('train_id', 'Unknown')),
                station=str(row.get('station', 'Unknown')),
                time_actual=time_actual,
                time_scheduled=time_scheduled,
                delay=delay,
                status=status
            )
            self.db_session.add(train_detail)

        self.db_session.commit()

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
        except Exception:
            return "UNKNOWN ❓", 0

    def get_train_status_table(self) -> pd.DataFrame:
        """Get status table from database"""
        query = self.db_session.query(TrainDetails).order_by(TrainDetails.time_actual)
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