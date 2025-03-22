#!/usr/bin/env python3
"""
Background Telegram Notification Service for Train Tracking System

This script runs independently of the Streamlit web application and continuously
monitors train data to send notifications 24/7.

Usage:
    python background_notifier.py
"""

import os
import time
import json
import logging
import requests
import pandas as pd
import asyncio
from datetime import datetime, timedelta
import io
import re
from typing import List, Dict, Any, Optional, Tuple, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("temp/background_notifier.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("background_notifier")

# URL for the Google Sheets data
MONITOR_DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=615508228&single=true&output=csv"

# Telegram bot configuration (will be loaded from environment or secrets)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_IDS = os.environ.get('TELEGRAM_CHAT_IDS', '')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '')

# Ensure the recipient ID is included
chat_ids = [id.strip() for id in TELEGRAM_CHAT_IDS.split(',')] if TELEGRAM_CHAT_IDS else []
if chat_ids and "9985243115" not in chat_ids:
    chat_ids.append("9985243115")
    TELEGRAM_CHAT_IDS = ','.join(chat_ids)
    logger.info(f"Added recipient ID 9985243115 to chat IDs list")

# Constants
TEMP_DIR = "temp"
KNOWN_TRAINS_FILE = os.path.join(TEMP_DIR, "known_trains.json")
CACHED_MONITOR_FILE = os.path.join(TEMP_DIR, "cached_monitor.csv")
CHECK_INTERVAL_SECONDS = 300  # Check every 5 minutes


class TelegramNotifier:
    """Simplified Telegram notification manager for background service"""
    
    def __init__(self):
        """Initialize the background Telegram notifier"""
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_ids = [id.strip() for id in TELEGRAM_CHAT_IDS.split(',')] if TELEGRAM_CHAT_IDS else []
        self.channel_id = TELEGRAM_CHANNEL_ID
        
        # Add check to ensure 9985243115 is included
        if self.chat_ids and "9985243115" not in self.chat_ids:
            self.chat_ids.append("9985243115")
            logger.info(f"Added recipient ID 9985243115 to chat IDs list in notifier")
        
        # Check configuration
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not configured")
        
        if not self.chat_ids and not self.channel_id:
            logger.error("Neither TELEGRAM_CHAT_IDS nor TELEGRAM_CHANNEL_ID is configured")
        
        logger.info(f"TelegramNotifier initialized with {len(self.chat_ids)} chat IDs and channel ID: {self.channel_id}")

    @property
    def is_configured(self) -> bool:
        """Check if the notifier is properly configured"""
        return bool(self.bot_token and (self.chat_ids or self.channel_id))
    
    async def send_message_async(self, chat_id: str, message: str, parse_mode: str = 'HTML') -> bool:
        """Send a message asynchronously to a specific chat ID"""
        import telegram
        try:
            bot = telegram.Bot(token=self.bot_token)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {str(e)}")
            # Retry without parse_mode if it fails
            if parse_mode:
                try:
                    # Remove HTML tags for plain text fallback
                    plain_message = re.sub(r'<[^>]*>', '', message)
                    await bot.send_message(chat_id=chat_id, text=plain_message)
                    return True
                except Exception as e2:
                    logger.error(f"Second attempt also failed: {str(e2)}")
            return False
    
    def send_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """Send a message to one or all configured chat IDs"""
        if not self.is_configured:
            logger.warning("Telegram notifications not properly configured")
            return False
        
        # Create a new event loop for async operations
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def send_all():
                results = []
                
                # If specific chat_id is provided, send only to that one
                if chat_id:
                    return await self.send_message_async(chat_id, message)
                
                # Otherwise send to all configured chat IDs
                for cid in self.chat_ids:
                    if cid.strip():  # Skip empty IDs
                        result = await self.send_message_async(cid.strip(), message)
                        results.append(result)
                
                return any(results)  # True if at least one message was sent successfully
            
            return loop.run_until_complete(send_all())
        
        except Exception as e:
            logger.error(f"Error sending Telegram message: {str(e)}")
            return False
        finally:
            try:
                loop.close()
            except:
                pass
    
    def send_to_channel(self, message: str) -> bool:
        """Send a message to the configured Telegram channel"""
        if not self.is_configured or not self.channel_id:
            logger.warning("Telegram channel not properly configured")
            return False
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(self.send_message_async(self.channel_id, message))
        
        except Exception as e:
            logger.error(f"Error sending channel message: {str(e)}")
            return False
        finally:
            try:
                loop.close()
            except:
                pass
    
    def notify_new_train(self, train_id: str, train_info: Optional[Dict[str, Any]] = None) -> bool:
        """Send notification about a new train to both chat IDs and channel"""
        success = False
        
        # Create the formatted channel message with locomotive emoji
        # Format: 🚂 #train_number | FROM-TO | T/O-H/O: stations with delay times | Delay: value | Started: date
        try:
            from_to = ""
            delay = ""
            station = ""
            start_date = ""
            
            if train_info:
                for key, value in train_info.items():
                    if 'from' in key.lower() and 'to' in key.lower():
                        from_to = str(value)
                    elif 'delay' in key.lower():
                        delay = str(value)
                    elif 'station' in key.lower():
                        station = str(value)
                    elif 'start' in key.lower() and 'date' in key.lower():
                        start_date = str(value)
            
            # Format the message for channel
            channel_message = f"🚂 #{train_id}"
            
            if from_to:
                channel_message += f" | {from_to}"
            
            if station:
                channel_message += f" | T/O-H/O: {station}"
                if delay:
                    channel_message += f": {delay} mins late"
            
            if delay:
                channel_message += f" | Delay: {delay} mins"
            
            if start_date:
                channel_message += f" | Started: {start_date}"
            
            # Format message for direct chat IDs with more details
            chat_message = f"🚆 <b>New Train {train_id} Detected</b>\n\n"
            
            if from_to:
                chat_message += f"<b>FROM-TO:</b> {from_to}\n"
            if station:
                chat_message += f"<b>Station:</b> {station}\n"
            if delay:
                chat_message += f"<b>Delay:</b> {delay} mins\n"
            if start_date:
                chat_message += f"<b>Started:</b> {start_date}\n"
            
            chat_message += f"\n<i>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            
            # Send to channel
            if self.channel_id:
                channel_success = self.send_to_channel(channel_message)
                if channel_success:
                    logger.info(f"Successfully sent channel notification for train {train_id}")
                    success = True
            
            # Send to direct chat IDs
            if self.chat_ids:
                chat_success = self.send_message(chat_message)
                if chat_success:
                    logger.info(f"Successfully sent direct notification for train {train_id}")
                    success = True
            
            return success
        
        except Exception as e:
            logger.error(f"Error formatting and sending train notification: {str(e)}")
            
            # Fallback to simple message
            simple_message = f"🚂 New train detected: {train_id}"
            return self.send_message(simple_message)


def ensure_temp_directory():
    """Ensure the temp directory exists"""
    os.makedirs(TEMP_DIR, exist_ok=True)


def load_known_trains() -> Set[str]:
    """Load the list of known trains from file"""
    try:
        if os.path.exists(KNOWN_TRAINS_FILE):
            with open(KNOWN_TRAINS_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        logger.error(f"Failed to load known trains: {str(e)}")
        return set()


def save_known_trains(known_trains: Set[str]) -> bool:
    """Save the list of known trains to file"""
    try:
        ensure_temp_directory()
        with open(KNOWN_TRAINS_FILE, 'w') as f:
            json.dump(list(known_trains), f)
        return True
    except Exception as e:
        logger.error(f"Failed to save known trains: {str(e)}")
        return False


def fetch_monitor_data() -> Tuple[pd.DataFrame, bool]:
    """Fetch monitor data from Google Sheets with caching"""
    try:
        # Use requests to get data with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(MONITOR_DATA_URL, headers=headers)
        response.raise_for_status()
        
        # Load into pandas
        df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
        
        # Save to cache file for offline use
        try:
            ensure_temp_directory()
            with open(CACHED_MONITOR_FILE, "w", encoding='utf-8') as f:
                f.write(response.content.decode('utf-8'))
            logger.info(f"Successfully cached monitor data ({len(df)} rows)")
        except Exception as e:
            logger.warning(f"Failed to cache monitor data: {str(e)}")
            
        return df, True
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        
        # Try to load from cached file if available
        try:
            if os.path.exists(CACHED_MONITOR_FILE):
                logger.warning("Using cached data (offline mode)")
                df = pd.read_csv(CACHED_MONITOR_FILE)
                return df, True
        except Exception as cache_error:
            logger.error(f"Failed to load cached data: {str(cache_error)}")
            
        return pd.DataFrame(), False


def safe_convert(value) -> str:
    """Safely convert a value to string, handling NaN, None, etc."""
    if pd.isna(value) or pd.isnull(value) or value is None:
        return ""
    
    string_val = str(value).strip()
    if not string_val:
        return ""
    
    # Replace undefined values with dash
    if 'undefined' in string_val.lower():
        return string_val.replace('undefined', '-').replace('Undefined', '-')
    
    return string_val


def extract_train_details(df: pd.DataFrame) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    """Extract train numbers and details from the DataFrame"""
    train_numbers = []
    train_details = {}
    
    # Identify the train number column
    train_column = None
    for col in df.columns:
        if 'train' in col.lower() and 'no' in col.lower():
            train_column = col
            break
    
    if not train_column:
        logger.error("Could not find train number column in data")
        return [], {}
    
    # Extract train numbers and basic details
    for _, row in df.iterrows():
        try:
            train_no = safe_convert(row[train_column])
            
            if not train_no:
                continue
                
            # Clean up the train number (remove any non-digit characters)
            train_no = ''.join(filter(str.isdigit, train_no))
            
            if not train_no:
                continue
                
            train_numbers.append(train_no)
            
            # Gather additional details about the train
            details = {}
            
            # Extract FROM-TO information if available
            from_to_col = None
            for col in df.columns:
                if 'from' in col.lower() and 'to' in col.lower():
                    from_to_col = col
                    break
            
            if from_to_col:
                details['FROM-TO'] = safe_convert(row[from_to_col])
            
            # Extract DELAY information if available
            delay_col = None
            for col in df.columns:
                if 'delay' in col.lower():
                    delay_col = col
                    break
            
            if delay_col:
                details['Delay'] = safe_convert(row[delay_col])
            
            # Extract Station information if available
            station_col = None
            for col in df.columns:
                if col.lower() == 'station' or 'stn' in col.lower():
                    station_col = col
                    break
            
            if station_col:
                details['Station'] = safe_convert(row[station_col])
            
            # Extract Start Date if available
            date_col = None
            for col in df.columns:
                if 'date' in col.lower() and 'start' in col.lower():
                    date_col = col
                    break
            
            if date_col:
                details['Start Date'] = safe_convert(row[date_col])
            
            train_details[train_no] = details
            
        except Exception as e:
            logger.error(f"Error extracting train details: {str(e)}")
    
    return train_numbers, train_details


def reset_known_trains(notifier: Optional[TelegramNotifier] = None) -> None:
    """Reset the known trains list to trigger new notifications for all trains"""
    try:
        # Save an empty set to the known trains file
        save_known_trains(set())
        logger.info("🔄 Known trains list has been reset")
        
        # Send notification about the reset if notifier is provided
        if notifier:
            reset_message = "🔄 <b>Known Trains List Reset</b>\n\n"
            reset_message += "The known trains list has been reset as scheduled at 01:00. "
            reset_message += "You will now receive new notifications for all trains.\n\n"
            reset_message += f"<i>Reset at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            notifier.send_message(reset_message)
            
            # Also send to channel
            if notifier.channel_id:
                channel_message = "🔄 Daily train list reset complete at 01:00"
                notifier.send_to_channel(channel_message)
    except Exception as e:
        logger.error(f"Failed to reset known trains list: {str(e)}")

def check_for_new_trains(notifier: TelegramNotifier) -> None:
    """Check for new trains and send notifications if any are found"""
    logger.info("Checking for new trains...")
    
    # Check if it's time to reset the known trains list (01:00)
    current_time = datetime.now()
    if current_time.hour == 1 and current_time.minute < 5:
        logger.info("It's 01:00-01:05, resetting known trains list as scheduled")
        reset_known_trains(notifier)
    
    # Load the known trains
    known_trains = load_known_trains()
    logger.info(f"Loaded {len(known_trains)} known trains")
    
    # Fetch current train data
    df, success = fetch_monitor_data()
    
    if not success or df.empty:
        logger.error("Failed to fetch train data")
        return
    
    # Extract train numbers and details
    current_trains, train_details = extract_train_details(df)
    logger.info(f"Found {len(current_trains)} trains in current data")
    
    # Find new trains
    new_trains = []
    for train in current_trains:
        if train and train not in known_trains:
            new_trains.append(train)
            known_trains.add(train)
    
    # Send notifications for new trains
    if new_trains:
        logger.info(f"Detected {len(new_trains)} new trains: {', '.join(new_trains)}")
        
        for train_id in new_trains:
            train_info = train_details.get(train_id, {})
            success = notifier.notify_new_train(train_id, train_info)
            if success:
                logger.info(f"Successfully sent notification for train {train_id}")
            else:
                logger.error(f"Failed to send notification for train {train_id}")
        
        # Save updated known trains
        save_known_trains(known_trains)
    else:
        logger.info("No new trains detected")


def load_secrets():
    """Load secrets from .streamlit/secrets.toml if available"""
    try:
        if os.path.exists('.streamlit/secrets.toml'):
            import toml
            secrets = toml.load('.streamlit/secrets.toml')
            
            global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, TELEGRAM_CHANNEL_ID
            
            if 'TELEGRAM_BOT_TOKEN' in secrets:
                TELEGRAM_BOT_TOKEN = secrets['TELEGRAM_BOT_TOKEN']
                logger.info("Loaded TELEGRAM_BOT_TOKEN from secrets")
            
            if 'TELEGRAM_CHAT_IDS' in secrets:
                TELEGRAM_CHAT_IDS = secrets['TELEGRAM_CHAT_IDS']
                logger.info("Loaded TELEGRAM_CHAT_IDS from secrets")
            
            if 'TELEGRAM_CHANNEL_ID' in secrets:
                TELEGRAM_CHANNEL_ID = secrets['TELEGRAM_CHANNEL_ID']
                logger.info("Loaded TELEGRAM_CHANNEL_ID from secrets")
    except Exception as e:
        logger.error(f"Error loading secrets: {str(e)}")


def main():
    """Main function that runs the background notification service"""
    logger.info("Starting background notification service")
    
    # Load secrets if available
    load_secrets()
    
    # Initialize the notifier
    notifier = TelegramNotifier()
    
    if not notifier.is_configured:
        logger.error("Telegram notifier is not properly configured. Please set TELEGRAM_BOT_TOKEN and either TELEGRAM_CHAT_IDS or TELEGRAM_CHANNEL_ID.")
        return
    
    # Send startup notification
    startup_message = "🔄 <b>Background Notification Service Started</b>\n\n"
    startup_message += f"The notification service is now running and will check for new trains every {CHECK_INTERVAL_SECONDS/60:.1f} minutes.\n\n"
    startup_message += f"<i>Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    
    notifier.send_message(startup_message)
    
    # Main loop
    logger.info(f"Entering main loop with {CHECK_INTERVAL_SECONDS} second interval")
    while True:
        try:
            # Check for new trains
            check_for_new_trains(notifier)
            
            # Sleep until next check
            logger.info(f"Sleeping for {CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Service interrupted by user. Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            logger.info("Continuing after error...")
            time.sleep(60)  # Sleep for a minute after an error


if __name__ == "__main__":
    main()