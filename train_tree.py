from typing import Optional, Dict
import json
import logging

logger = logging.getLogger(__name__)

class TrainNode:
    def __init__(self, train_number: str, schedules: Dict):
        self.train_number = train_number
        self.schedules = schedules  # Contains station-wise timing data
        self.left: Optional['TrainNode'] = None
        self.right: Optional['TrainNode'] = None

class TrainScheduleTree:
    def __init__(self):
        """Initialize an empty binary tree for train schedules"""
        self.root: Optional[TrainNode] = None
        self._size = 0

    def insert(self, train_number: str, schedules: Dict):
        """Insert a new train schedule into the binary tree"""
        try:
            if not self.root:
                self.root = TrainNode(train_number, schedules)
            else:
                self._insert_recursive(self.root, train_number, schedules)
            self._size += 1
            logger.debug(f"Inserted train {train_number} into tree")
        except Exception as e:
            logger.error(f"Error inserting train {train_number}: {str(e)}")
            raise

    def _insert_recursive(self, node: TrainNode, train_number: str, schedules: Dict):
        """Recursively insert a node into the binary tree"""
        try:
            if int(train_number) < int(node.train_number):
                if node.left is None:
                    node.left = TrainNode(train_number, schedules)
                else:
                    self._insert_recursive(node.left, train_number, schedules)
            else:
                if node.right is None:
                    node.right = TrainNode(train_number, schedules)
                else:
                    self._insert_recursive(node.right, train_number, schedules)
        except ValueError as e:
            logger.error(f"Invalid train number format: {train_number} - {str(e)}")
            raise

    @staticmethod
    def build_from_json(json_file: str) -> 'TrainScheduleTree':
        """Build train schedule tree from JSON file"""
        tree = TrainScheduleTree()
        try:
            logger.info(f"Loading train schedules from {json_file}")
            with open(json_file, 'r') as f:
                data = json.load(f)
                logger.debug("Successfully parsed JSON file")

            # Process each station's data
            train_schedules: Dict = {}
            for station, station_data in data.items():
                if not isinstance(station_data, dict):
                    logger.warning(f"Invalid station data format for {station}")
                    continue

                arr_times = station_data.get('Arr', {}).get('times', {})
                dep_times = station_data.get('Dep', {}).get('times', {})

                # Combine arrival and departure times for each train
                for train_number in set(list(arr_times.keys()) + list(dep_times.keys())):
                    if train_number and train_number.strip().isdigit():
                        if train_number not in train_schedules:
                            train_schedules[train_number] = {}
                        train_schedules[train_number][station] = {
                            'arrival': arr_times.get(train_number, ''),
                            'departure': dep_times.get(train_number, '')
                        }

            # Insert each train schedule into the tree
            for train_number, schedules in train_schedules.items():
                tree.insert(train_number, schedules)

            logger.info(f"Built train schedule tree with {tree._size} trains")
            return tree

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in {json_file}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error building train schedule tree: {str(e)}")
            raise

    def find(self, train_number: str) -> Optional[Dict]:
        """Find train schedules by train number"""
        try:
            return self._find_recursive(self.root, train_number)
        except Exception as e:
            logger.error(f"Error finding train {train_number}: {str(e)}")
            return None

    def _find_recursive(self, node: Optional[TrainNode], train_number: str) -> Optional[Dict]:
        """Recursively search for a train schedule"""
        if node is None:
            return None

        try:
            if node.train_number == train_number:
                return node.schedules
            elif int(train_number) < int(node.train_number):
                return self._find_recursive(node.left, train_number)
            else:
                return self._find_recursive(node.right, train_number)
        except ValueError:
            logger.error(f"Invalid train number format during search: {train_number}")
            return None

    def get_tree_structure(self) -> Dict:
        """Get the tree structure for visualization"""
        def build_structure(node: Optional[TrainNode]) -> Optional[Dict]:
            if node is None:
                return None
            return {
                'train_number': node.train_number,
                'left': build_structure(node.left),
                'right': build_structure(node.right)
            }
        return build_structure(self.root) or {}