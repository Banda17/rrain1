#!/usr/bin/env python3
"""
Reset the known trains list to trigger new notifications.

This simple script can be run manually to reset the list of known trains,
which will cause all trains to be treated as new in the next check cycle.

Usage:
    python reset_trains.py
"""

import os
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("reset_trains")

# Constants
TEMP_DIR = "temp"
KNOWN_TRAINS_FILE = os.path.join(TEMP_DIR, "known_trains.json")

def reset_known_trains():
    """Reset the known trains list to trigger new notifications"""
    try:
        # Ensure temp directory exists
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # Save an empty list to reset
        with open(KNOWN_TRAINS_FILE, 'w') as f:
            json.dump([], f)
            
        logger.info(f"✅ Successfully reset known trains list at {KNOWN_TRAINS_FILE}")
        print(f"✅ Known trains list has been reset! You will get all notifications in the next check cycle.")
        
        return True
    except Exception as e:
        logger.error(f"Failed to reset known trains: {str(e)}")
        print(f"❌ Failed to reset known trains: {str(e)}")
        return False

if __name__ == "__main__":
    reset_known_trains()