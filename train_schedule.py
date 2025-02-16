import json
from typing import Optional
import logging
from train_tree import TrainScheduleTree

logger = logging.getLogger(__name__)

class TrainSchedule:
    def __init__(self):
        """Initialize train schedule data structure"""
        try:
            self.schedule_tree = TrainScheduleTree.build_from_json('bhanu.json')

            # Create station code mapping
            self.station_mapping = {
                'CCT': 'VNEC',  # Map CCT to VNEC
                'CSMT': 'VNEC',
                'DR': 'MBD',
                'BSR': 'GWM',
                'BVI': 'PAVP'
            }
            logger.info("Train schedule initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing train schedule: {str(e)}")
            raise

    def get_scheduled_time(self, train_name: str, station: str) -> Optional[str]:
        """Get scheduled time for a train at a station using binary tree lookup."""
        try:
            logger.debug(f"Looking up schedule for train: {train_name} at station: {station}")

            # Extract train number from train name using numeric part
            train_number = ''.join(filter(str.isdigit, train_name))
            if not train_number:
                logger.debug(f"No train number found in train name: {train_name}")
                return None

            # Extract station code from the full station name
            station_parts = station.strip().split()
            original_station_code = station_parts[0] if station_parts else ""

            # Map station code using the mapping dictionary
            station_code = self.station_mapping.get(original_station_code, original_station_code)
            logger.debug(f"Original station code: {original_station_code}, Mapped to: {station_code}")

            # Look up schedule in binary tree
            schedule = self.schedule_tree.find(train_number)
            if schedule and station_code in schedule:
                station_schedule = schedule[station_code]
                # Return arrival time if available, otherwise departure time
                time = station_schedule['arrival'] or station_schedule['departure']
                if time and time.strip():
                    logger.debug(f"Found time for train {train_number} at station {station_code}: {time}")
                    return time

            logger.debug(f"No schedule found for train {train_number} at station {station_code}")
            return None

        except Exception as e:
            logger.error(f"Error getting scheduled time for train {train_name} at station {station}: {str(e)}")
            return None