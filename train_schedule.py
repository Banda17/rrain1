import json
from typing import Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

class TrainSchedule:
    def __init__(self):
        """Initialize train schedule data structure"""
        try:
            # Load data from bhanu.json
            with open('bhanu.json', 'r') as f:
                self.schedule_data = json.load(f)
                logger.info("Loaded schedule data from bhanu.json")
                # Log all available stations
                self.available_stations = list(self.schedule_data.keys())
                logger.info(f"Available stations in schedule: {self.available_stations}")

                # Create station code mapping
                self.station_mapping = {
                    'CCT': 'VNEC',  # Map CCT to VNEC
                    'CSMT': 'VNEC',
                    'DR': 'MBD',
                    'BSR': 'GWM',
                    'BVI': 'PAVP'
                }
                logger.info(f"Initialized station mapping: {self.station_mapping}")
        except Exception as e:
            logger.error(f"Error loading schedule data: {str(e)}")
            self.schedule_data = {}
            self.available_stations = []
            self.station_mapping = {}

    def get_scheduled_time(self, train_name: str, station: str) -> Optional[str]:
        """Get scheduled time for a train at a station."""
        try:
            logger.debug(f"Looking up schedule for train: {train_name} at station: {station}")

            # Extract train number from train name using regex
            train_number_match = re.search(r'\d+', train_name)
            if not train_number_match:
                logger.debug(f"No train number found in train name: {train_name}")
                return None

            train_number = train_number_match.group()
            logger.debug(f"Extracted train number: {train_number}")

            # Extract station code from the full station name
            station_parts = station.strip().split()
            original_station_code = station_parts[0] if station_parts else ""

            # Map station code using the mapping dictionary
            station_code = self.station_mapping.get(original_station_code, original_station_code)
            logger.debug(f"Original station code: {original_station_code}, Mapped to: {station_code}")

            if not station_code:
                logger.debug("No station code found")
                return None

            if station_code not in self.schedule_data:
                logger.debug(f"Station code {station_code} not found in schedule data. Available stations: {self.available_stations}")
                return None

            station_data = self.schedule_data[station_code]
            logger.debug(f"Found station data for {station_code}")

            # First try to get arrival time
            arr_times = station_data.get("Arr", {}).get("times", {})
            if train_number in arr_times and arr_times[train_number].strip():
                logger.debug(f"Found arrival time for train {train_number}: {arr_times[train_number]}")
                return arr_times[train_number]

            # If no arrival time, try departure time
            dep_times = station_data.get("Dep", {}).get("times", {})
            if train_number in dep_times and dep_times[train_number].strip():
                logger.debug(f"Found departure time for train {train_number}: {dep_times[train_number]}")
                return dep_times[train_number]

            logger.debug(f"No schedule found for train {train_number} at station {station_code}")
            return None

        except Exception as e:
            logger.error(f"Error getting scheduled time for train {train_name} at station {station}: {str(e)}")
            return None