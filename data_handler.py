import pandas as pd
import json
from typing import Dict, List, Tuple

class DataHandler:
    def __init__(self):
        self.train_details = None
        self.wtt_timings = None

    def load_json_data(self, train_details_json: str, wtt_timings_json: str) -> Tuple[bool, str]:
        """Load and validate JSON data"""
        try:
            self.train_details = pd.read_json(train_details_json)
            self.wtt_timings = pd.read_json(wtt_timings_json)
            return True, "Data loaded successfully"
        except Exception as e:
            return False, f"Error loading data: {str(e)}"

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
        """Create status table with timing analysis"""
        if self.train_details is None or self.wtt_timings is None:
            return pd.DataFrame()

        merged_data = pd.merge(
            self.train_details,
            self.wtt_timings,
            on=['train_id', 'station'],
            suffixes=('_actual', '_scheduled')
        )
        
        merged_data[['status', 'delay']] = merged_data.apply(
            lambda x: self.get_timing_status(x['time_actual'], x['time_scheduled']),
            axis=1,
            result_type='expand'
        )
        
        return merged_data
