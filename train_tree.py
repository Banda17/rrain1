from typing import Optional, Dict
import json
import logging

logger = logging.getLogger(__name__)

class TrainNode:
    def __init__(self, train_number: str, schedules: Dict):
        self.train_number = train_number
        self.schedules = schedules  # Contains station-wise timing data
        self.left = None
        self.right = None

class TrainScheduleTree:
    def __init__(self):
        """Initialize an empty binary tree for train schedules"""
        self.root = None
        self._size = 0
        
    def insert(self, train_number: str, schedules: Dict):
        """Insert a new train schedule into the binary tree"""
        if not self.root:
            self.root = TrainNode(train_number, schedules)
        else:
            self._insert_recursive(self.root, train_number, schedules)
        self._size += 1
            
    def _insert_recursive(self, node: TrainNode, train_number: str, schedules: Dict):
        """Recursively insert a node into the binary tree"""
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
                
    def find(self, train_number: str) -> Optional[Dict]:
        """Find train schedules by train number"""
        return self._find_recursive(self.root, train_number)
        
    def _find_recursive(self, node: TrainNode, train_number: str) -> Optional[Dict]:
        """Recursively search for a train schedule"""
        if node is None:
            return None
            
        if node.train_number == train_number:
            return node.schedules
        elif int(train_number) < int(node.train_number):
            return self._find_recursive(node.left, train_number)
        else:
            return self._find_recursive(node.right, train_number)
            
    def get_tree_structure(self) -> Dict:
        """Get the tree structure for visualization"""
        def build_structure(node):
            if node is None:
                return None
            return {
                'train_number': node.train_number,
                'left': build_structure(node.left),
                'right': build_structure(node.right)
            }
        return build_structure(self.root)
        
    @staticmethod
    def build_from_json(json_file: str) -> 'TrainScheduleTree':
        """Build train schedule tree from JSON file"""
        tree = TrainScheduleTree()
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            # Process each station's data
            train_schedules = {}
            for station, station_data in data.items():
                # Get arrival and departure times
                arr_times = station_data.get('Arr', {}).get('times', {})
                dep_times = station_data.get('Dep', {}).get('times', {})
                
                # Combine arrival and departure times for each train
                for train_number in set(list(arr_times.keys()) + list(dep_times.keys())):
                    if train_number not in train_schedules:
                        train_schedules[train_number] = {}
                    train_schedules[train_number][station] = {
                        'arrival': arr_times.get(train_number, ''),
                        'departure': dep_times.get(train_number, '')
                    }
            
            # Insert each train schedule into the tree
            for train_number, schedules in train_schedules.items():
                if train_number.isdigit():  # Only process numeric train numbers
                    tree.insert(train_number, schedules)
                    
            logger.info(f"Built train schedule tree with {tree._size} trains")
            return tree
            
        except Exception as e:
            logger.error(f"Error building train schedule tree: {str(e)}")
            raise
