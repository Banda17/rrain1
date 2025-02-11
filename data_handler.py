import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime
from database import get_database_connection, TrainDetails
from google_drive_handler import GoogleDriveHandler

class DataHandler:
    def __init__(self):
        self.data = None
        self.db_session = get_database_connection()
        self.drive_handler = GoogleDriveHandler()

    def load_data_from_drive(self, file_id: str) -> Tuple[bool, str]:
        """Load data from Google Drive Excel file"""
        try:
            # Get data from Google Drive
            self.data = self.drive_handler.get_file_content(file_id)

            # Process and store data in database
            self._store_data_in_db()

            return True, "Data loaded successfully from Google Drive"
        except Exception as e:
            return False, f"Error loading data from Google Drive: {str(e)}"

    def _store_data_in_db(self):
        """Store the loaded data in the database"""
        if self.data is None or self.data.empty:
            raise ValueError("No data available to store")

        for _, row in self.data.iterrows():
            # Convert time columns to datetime if they're not already
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