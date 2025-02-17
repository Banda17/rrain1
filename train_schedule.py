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
            logger.info("Train schedule tree initialized successfully")

            # Create station code mapping with only exact matches
            self.station_mapping = {
                'VNEC': 'VNEC',  # Secunderabad
                'GALA': 'GALA',  # Ghatkesar
                'MBD': 'MBD',    # Malakpet
                'GWM': 'GWM',    # Gandhinagar
                'PAVP': 'PAVP',  # Pavalavagu
                'BZA': 'BZA'     # Vijayawada
            }
            logger.info(f"Station mapping initialized with {len(self.station_mapping)} entries")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in train schedule: {str(e)}")
            raise
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
                logger.debug(f"No valid train number found in train name: {train_name}")
                return None

            # Extract and map station code
            station_parts = station.strip().split()
            original_station_code = station_parts[0] if station_parts else ""
            station_code = self.station_mapping.get(original_station_code, original_station_code)

            logger.debug(f"Looking up schedule with station code: {station_code}")

            # Look up schedule in binary tree
            schedule = self.schedule_tree.find(train_number)
            if schedule and station_code in schedule:
                station_schedule = schedule[station_code]
                # Return arrival time if available, otherwise departure time
                time = station_schedule.get('arrival', '') or station_schedule.get('departure', '')
                if time and time.strip():
                    logger.debug(f"Found schedule: Train {train_number} at {station_code} -> {time}")
                    return time

            logger.debug(f"No schedule found for train {train_number} at station {station_code}")
            return None

        except Exception as e:
            logger.error(f"Error getting schedule for train {train_name} at {station}: {str(e)}")
            return None