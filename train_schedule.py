import json
from typing import Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

class TrainSchedule:
    def __init__(self):
        """Initialize train schedule data structure"""
        self.schedule_data = {
            "VNEC": {
                "Arr": {"times": {}},
                "DEP": {"times": {}}
            }
        }

    def set_schedule_data(self, data: Dict):
        """Set the schedule data"""
        self.schedule_data = data
        logger.info("Schedule data updated")

    def get_scheduled_time(self, train_name: str, station: str) -> Optional[str]:
        """
        Get scheduled time for a train at a station
        Returns None if no schedule is found
        """
        try:
            # Extract train number from train name using regex
            train_number_match = re.search(r'^\d+', train_name)
            if not train_number_match:
                logger.debug(f"No train number found in train name: {train_name}")
                return None

            train_number = train_number_match.group()
            logger.debug(f"Extracted train number: {train_number}")

            # Extract station code (e.g., VNEC) from the station name if needed
            station_code = station.split()[0] if station else ""
            logger.debug(f"Station code: {station_code}")

            if station_code in self.schedule_data:
                station_data = self.schedule_data[station_code]

                # Check both arrival and departure times
                for direction in ["Arr", "DEP"]:
                    if direction in station_data:
                        times = station_data[direction].get("times", {})
                        if train_number in times:
                            logger.debug(f"Found schedule time for train {train_number}")
                            return times[train_number]

            logger.debug(f"No schedule found for train {train_number} at station {station_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting scheduled time for train {train_name}: {str(e)}")
            return None