import pandas as pd
import json
from typing import Dict, List, Tuple
from datetime import datetime
from database import get_database_connection, TrainDetails
from google_drive_handler import GoogleDriveHandler

class DataHandler:
    def __init__(self):
        self.train_details = None
        self.wtt_timings = None
        self.db_session = get_database_connection()
        self.drive_handler = GoogleDriveHandler()

    def load_data_from_drive(self, train_details_file_id: str, wtt_timings_file_id: str) -> Tuple[bool, str]:
        """Load data from Google Drive files"""
        try:
            # Get data from Google Drive
            train_details_data = self.drive_handler.get_file_content(train_details_file_id)
            wtt_timings_data = self.drive_handler.get_file_content(wtt_timings_file_id)

            # Convert to DataFrames
            self.train_details = pd.DataFrame(train_details_data)
            self.wtt_timings = pd.DataFrame(wtt_timings_data)

            # Store data in database
            self._store_data_in_db()

            return True, "Data loaded successfully from Google Drive"
        except Exception as e:
            return False, f"Error loading data from Google Drive: {str(e)}"

    def load_json_data(self, train_details_json: str, wtt_timings_json: str) -> Tuple[bool, str]:
        """Load and validate JSON data from uploaded files"""
        try:
            self.train_details = pd.read_json(train_details_json)
            self.wtt_timings = pd.read_json(wtt_timings_json)

            # Store data in database
            self._store_data_in_db()

            return True, "Data loaded successfully"
        except Exception as e:
            return False, f"Error loading data: {str(e)}"

    def _store_data_in_db(self):
        """Store the loaded data in the database"""
        merged_data = pd.merge(
            self.train_details,
            self.wtt_timings,
            on=['train_id', 'station'],
            suffixes=('_actual', '_scheduled')
        )

        for _, row in merged_data.iterrows():
            status, delay = self.get_timing_status(row['time_actual'], row['time_scheduled'])
            train_detail = TrainDetails(
                train_id=row['train_id'],
                station=row['station'],
                time_actual=pd.to_datetime(row['time_actual']),
                time_scheduled=pd.to_datetime(row['time_scheduled']),
                delay=delay,
                status=status
            )
            self.db_session.add(train_detail)

        self.db_session.commit()

    def get_timing_status(self, actual_time: str, scheduled_time: str) -> Tuple[str, int]:
        """Calculate if train is early, late, or on time"""
        try:
            actual = pd.to_datetime(actual_time)
            scheduled = pd.to_datetime(scheduled_time)
            diff_minutes = int((actual - scheduled).total_seconds() / 60)

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