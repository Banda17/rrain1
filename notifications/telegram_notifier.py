import logging
import asyncio
from typing import List, Dict, Any, Optional
import os

from telegram import Bot
from telegram.error import TelegramError
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Telegram notification module for the train tracking application.
    Sends notifications about train status and delays via Telegram.
    """
    
    def __init__(self):
        """Initialize the Telegram notification manager"""
        # Check for token in session state
        if 'telegram_bot_token' not in st.session_state:
            st.session_state.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
            
        if 'telegram_chat_ids' not in st.session_state:
            chat_ids_str = os.environ.get('TELEGRAM_CHAT_IDS', '')
            st.session_state.telegram_chat_ids = [id.strip() for id in chat_ids_str.split(',')] if chat_ids_str else []
            
        if 'telegram_channel_id' not in st.session_state:
            # Use TELEGRAM_CHAT_IDS environment variable for backward compatibility
            # This allows a single chat ID to be used as a channel ID if needed
            channel_id = os.environ.get('TELEGRAM_CHANNEL_ID', '')
            if not channel_id and 'TELEGRAM_CHAT_IDS' in os.environ:
                # Try to extract the first chat ID as a potential channel ID
                chat_ids_str = os.environ.get('TELEGRAM_CHAT_IDS', '')
                if chat_ids_str:
                    chat_ids_list = [id.strip() for id in chat_ids_str.split(',')]
                    if chat_ids_list:
                        # Use the first chat ID as a channel ID if it starts with @ or -100
                        first_id = chat_ids_list[0]
                        if first_id.startswith('@') or first_id.startswith('-100'):
                            channel_id = first_id
                            logger.info(f"Using first chat ID as channel ID: {channel_id}")
            
            st.session_state.telegram_channel_id = channel_id
        
        # Initialize notification preferences with defaults
        if 'telegram_notify_preferences' not in st.session_state:
            st.session_state.telegram_notify_preferences = {
                'new_trains': True,
                'status_changes': True,
                'delays': True,
                'early_arrivals': True,
                'min_delay_threshold': 10,  # Notify only for delays >= 10 mins
                'max_notifications_per_hour': 20,
                'quiet_hours_enabled': False,
                'quiet_hours_start': "22:00",
                'quiet_hours_end': "06:00",
                'train_filters': {
                    'SUF': True,   # Superfast
                    'MEX': True,   # Express
                    'DMU': False,  # DMU
                    'MEMU': False, # MEMU
                    'PEX': False,  # Passenger Express
                    'TOD': True,   # Train on Demand
                    'VNDB': True,  # Vande Bharat
                    'RAJ': True,   # Rajdhani
                    'JSH': True,   # JANSATABDHI
                    'DNRT': True   # Duronto
                }
            }
        
        # Initialize notification counter
        if 'telegram_notification_count' not in st.session_state:
            st.session_state.telegram_notification_count = {
                'last_reset': None,
                'count': 0
            }
        
        # Initialize bot if token exists
        self._bot = None
        if st.session_state.telegram_bot_token:
            try:
                self._bot = Bot(token=st.session_state.telegram_bot_token)
                logger.info("Telegram bot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {str(e)}")
                self._bot = None
    
    @property
    def is_configured(self) -> bool:
        """Check if the Telegram bot is properly configured"""
        # Bot must have a valid token, and either chat IDs or a channel ID must be set
        return (self._bot is not None and 
                st.session_state.telegram_bot_token and 
                (len(st.session_state.telegram_chat_ids) > 0 or 
                 st.session_state.telegram_channel_id))
    
    async def _send_message_async(self, chat_id: str, message: str) -> bool:
        """
        Send a message asynchronously to a specific chat ID
        
        Args:
            chat_id: Telegram chat ID to send message to
            message: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self._bot:
            logger.warning("Telegram bot not initialized")
            return False
            
        try:
            await self._bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {str(e)}")
            return False
    
    def _is_in_quiet_hours(self) -> bool:
        """
        Check if current time is within configured quiet hours
        
        Returns:
            True if in quiet hours, False otherwise
        """
        if not st.session_state.telegram_notify_preferences.get('quiet_hours_enabled', False):
            return False
            
        try:
            from datetime import datetime, time
            
            # Get current time
            now = datetime.now().time()
            
            # Parse quiet hours start/end times
            start_str = st.session_state.telegram_notify_preferences.get('quiet_hours_start', "22:00")
            end_str = st.session_state.telegram_notify_preferences.get('quiet_hours_end', "06:00")
            
            start_hour, start_min = map(int, start_str.split(':'))
            end_hour, end_min = map(int, end_str.split(':'))
            
            start_time = time(start_hour, start_min)
            end_time = time(end_hour, end_min)
            
            # Handle overnight quiet periods (e.g., 22:00 to 06:00)
            if start_time > end_time:
                return now >= start_time or now <= end_time
            else:
                return start_time <= now <= end_time
                
        except Exception as e:
            logger.error(f"Error checking quiet hours: {str(e)}")
            return False
    
    def _check_rate_limit(self) -> bool:
        """
        Check if we've exceeded the notification rate limit
        
        Returns:
            True if under rate limit, False if rate limit exceeded
        """
        from datetime import datetime, timedelta
        
        # Get notification count from session state
        count_info = st.session_state.telegram_notification_count
        max_per_hour = st.session_state.telegram_notify_preferences.get('max_notifications_per_hour', 20)
        
        # Initialize or reset counter if needed
        now = datetime.now()
        if count_info['last_reset'] is None or (now - count_info['last_reset']) > timedelta(hours=1):
            st.session_state.telegram_notification_count = {
                'last_reset': now,
                'count': 0
            }
            return True
            
        # Check if we're under the limit
        if count_info['count'] < max_per_hour:
            # Increment counter
            st.session_state.telegram_notification_count['count'] += 1
            return True
            
        # Rate limit exceeded
        return False
    
    def send_to_channel(self, message: str, only_channel: bool = False, parse_mode: str = 'HTML') -> bool:
        """
        Send a message directly to the configured Telegram channel
        
        Args:
            message: Message text to send
            only_channel: If True, only send to channel and not to individual chat IDs
            parse_mode: Parse mode for Telegram ('HTML', 'Markdown', or None for plain text)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured:
            logger.warning("Telegram notifications not properly configured")
            return False
            
        # Check if channel ID is configured
        channel_id = st.session_state.telegram_channel_id
        if not channel_id:
            logger.warning("No channel ID configured for Telegram channel messages")
            return False
        
        # Remove any HTML span tags that might cause issues in Telegram messages
        import re
        cleaned_message = message
        # Remove <span> tags if using HTML mode
        if parse_mode == 'HTML':
            cleaned_message = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', cleaned_message)
        
        # Create a new event loop for async operations
        try:
            async def send_channel_message():
                try:
                    # Check if bot is initialized
                    if self._bot is None:
                        logger.error(f"Cannot send message to channel {channel_id}: Telegram bot not initialized")
                        return False
                    
                    # Send to channel with specified parse mode
                    await self._bot.send_message(
                        chat_id=channel_id, 
                        text=cleaned_message, 
                        parse_mode=parse_mode
                    )
                    logger.info(f"Successfully sent message to channel {channel_id}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to send Telegram message to channel {channel_id}: {str(e)}")
                    # If failed with HTML parsing, try without parse_mode
                    if parse_mode:
                        try:
                            logger.info(f"Retrying channel message without parse mode")
                            # Remove all HTML tags for plain text fallback
                            plain_message = re.sub(r'<[^>]*>', '', cleaned_message)
                            await self._bot.send_message(chat_id=channel_id, text=plain_message)
                            logger.info(f"Successfully sent plain text message to channel {channel_id}")
                            return True
                        except Exception as e2:
                            logger.error(f"Second attempt to channel also failed: {str(e2)}")
                            return False
                    return False
            
            # Check if there's a running event loop we can use
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                # No event loop found, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function in the event loop
            success = loop.run_until_complete(send_channel_message())
            
            return success
        except Exception as e:
            logger.error(f"Failed to send channel message: {str(e)}")
            return False
    
    def _should_send_notification(self, message_type: str, train_type: Optional[str] = None, delay: Optional[int] = None) -> bool:
        """
        Check if a notification should be sent based on user preferences
        
        Args:
            message_type: Type of notification ('new_train', 'status_change', 'delay', 'early')
            train_type: Optional train type code (SUF, MEX, etc.)
            delay: Optional delay in minutes (positive for delays, negative for early)
            
        Returns:
            True if notification should be sent based on preferences
        """
        prefs = st.session_state.telegram_notify_preferences
        
        # Check for quiet hours
        if self._is_in_quiet_hours():
            logger.info("Notification suppressed: quiet hours active")
            return False
            
        # Check for rate limiting
        if not self._check_rate_limit():
            logger.warning("Notification suppressed: rate limit exceeded")
            return False
            
        # Check message type preferences
        if message_type == 'new_train' and not prefs.get('new_trains', True):
            return False
            
        if message_type == 'status_change' and not prefs.get('status_changes', True):
            return False
            
        if message_type == 'delay' and not prefs.get('delays', True):
            return False
            
        if message_type == 'early' and not prefs.get('early_arrivals', True):
            return False
            
        # Check delay threshold
        if message_type == 'delay' and delay is not None:
            min_threshold = prefs.get('min_delay_threshold', 10)
            if delay < min_threshold:
                logger.info(f"Delay notification suppressed: {delay} min below threshold of {min_threshold} min")
                return False
                
        # Check train type filters
        if train_type:
            train_filters = prefs.get('train_filters', {})
            # If we have a specific filter for this train type and it's False
            if train_type in train_filters and not train_filters[train_type]:
                logger.info(f"Notification suppressed: train type {train_type} filtered out")
                return False
        
        return True

    def send_message(self, message: str, chat_id: Optional[str] = None, 
                    message_type: str = 'other', train_type: Optional[str] = None, 
                    delay: Optional[int] = None) -> bool:
        """
        Send a message to one or all configured chat IDs
        
        Args:
            message: Message text to send
            chat_id: Optional specific chat ID to send to (if None, send to all)
            message_type: Type of notification for filtering ('new_train', 'status_change', 'delay', 'early', 'other')
            train_type: Optional train type code (SUF, MEX, etc.)
            delay: Optional delay in minutes (positive for delays, negative for early)
            
        Returns:
            True if at least one message was sent successfully
        """
        if not self.is_configured:
            logger.warning("Telegram notifications not properly configured")
            return False
            
        # Check if we should send this notification based on preferences
        if message_type != 'other' and not self._should_send_notification(message_type, train_type, delay):
            return False
            
        chat_ids = [chat_id] if chat_id else st.session_state.telegram_chat_ids
        
        # Check for chat IDs and channel ID
        have_chat_ids = len(chat_ids) > 0
        have_channel_id = bool(st.session_state.telegram_channel_id)
        
        if not have_chat_ids and not have_channel_id:
            logger.warning("No chat IDs or channel ID configured for Telegram notifications")
            return False
        
        # Remove any HTML span tags that might cause issues in Telegram messages
        import re
        cleaned_message = message
        # Remove <span> tags
        cleaned_message = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', cleaned_message)
        # Remove other problematic HTML tags if needed but keep basic formatting
        # Allow only <b>, <i>, <code>, <pre> tags that are supported by Telegram
        
        # Log the message cleaning
        if cleaned_message != message:
            logger.info(f"Cleaned message by removing HTML span tags")
        
        # Create a new event loop for async operations - using a more robust approach
        # that handles multiple calls and prevents "Event loop is closed" errors
        try:
            async def send_all_messages():
                results = []
                
                # First send to all individual chat IDs
                for cid in chat_ids:
                    try:
                        # Check if bot is initialized
                        if self._bot is None:
                            logger.error(f"Cannot send message to {cid}: Telegram bot not initialized")
                            results.append(False)
                            continue
                        
                        # Use the cleaned message
                        await self._bot.send_message(chat_id=cid, text=cleaned_message, parse_mode='HTML')
                        results.append(True)
                    except Exception as e:
                        logger.error(f"Failed to send Telegram message to {cid}: {str(e)}")
                        # If failed with HTML parsing, try without parse_mode
                        try:
                            logger.info(f"Retrying without HTML parsing")
                            # Remove all HTML tags for plain text fallback
                            plain_message = re.sub(r'<[^>]*>', '', cleaned_message)
                            await self._bot.send_message(chat_id=cid, text=plain_message)
                            results.append(True)
                        except Exception as e2:
                            logger.error(f"Second attempt also failed: {str(e2)}")
                            results.append(False)
                
                # Then send to the channel if configured
                if have_channel_id and st.session_state.telegram_channel_id:
                    channel_id = st.session_state.telegram_channel_id
                    try:
                        # Check if bot is initialized
                        if self._bot is None:
                            logger.error(f"Cannot send message to channel {channel_id}: Telegram bot not initialized")
                            results.append(False)
                        else:
                            # Use the cleaned message for the channel
                            await self._bot.send_message(chat_id=channel_id, text=cleaned_message, parse_mode='HTML')
                            results.append(True)
                            logger.info(f"Successfully sent message to channel {channel_id}")
                    except Exception as e:
                        logger.error(f"Failed to send Telegram message to channel {channel_id}: {str(e)}")
                        # If failed with HTML parsing, try without parse_mode
                        try:
                            logger.info(f"Retrying channel message without HTML parsing")
                            # Remove all HTML tags for plain text fallback
                            plain_message = re.sub(r'<[^>]*>', '', cleaned_message)
                            await self._bot.send_message(chat_id=channel_id, text=plain_message)
                            results.append(True)
                            logger.info(f"Successfully sent plain text message to channel {channel_id}")
                        except Exception as e2:
                            logger.error(f"Second attempt to channel also failed: {str(e2)}")
                            results.append(False)
                
                return results
            
            # Check if there's a running event loop we can use
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Run the async function
            if loop.is_running():
                # If loop is already running (in something like Streamlit)
                # use run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(send_all_messages(), loop)
                results = future.result(timeout=10)  # 10 second timeout
            else:
                # If not running, use run_until_complete
                results = loop.run_until_complete(send_all_messages())
            
            # Process results
            success_count = sum(1 for r in results if r)
            if success_count > 0:
                logger.info(f"Successfully sent Telegram message to {success_count}/{len(results)} recipients")
                return True
            else:
                logger.error("Failed to send Telegram message to any recipient")
                return False
                
        except Exception as e:
            logger.error(f"Error in send_message: {str(e)}")
            return False
    
    def notify_new_train(self, train_id: str, train_info: Optional[Dict[str, Any]] = None, 
                          send_to_channel_only: bool = False) -> bool:
        """
        Send notification about a new train
        
        Args:
            train_id: Train number/ID
            train_info: Optional dictionary with additional train information
            send_to_channel_only: If True, only send to channel with the exact train format
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_configured:
            return False
            
        # Debug the train details we're getting
        logger.info(f"DEBUG: notify_new_train called with train_id={train_id}, train_info={train_info}")
        
        # Extract required information in the EXACT format requested
        from_to = ""
        delay_raw = ""
        delay_mins = ""
        start_date = ""
        intermediate_stations = ""
        delay = None
        train_type = None
        
        # Check if we should send directly to the channel only
        if send_to_channel_only and st.session_state.telegram_channel_id:
            # For channel-only messages, we'll format the message differently with the train emoji 🚂
            # Exact format: "🚂 #train_number | FROM-TO | T/O-H/O: stations with delay times | Delay: value | Started: date"
            
            # Extract information for the exact format
            if train_info:
                # Get FROM-TO
                from_to = train_info.get('FROM-TO', '')
                
                # Try to extract station pair if FROM-TO not found
                if not from_to and 'Station Pair' in train_info:
                    station_pair = train_info.get('Station Pair', '')
                    import re
                    pattern = r'([A-Z]+)[^-]*-([A-Z]+)'
                    match = re.search(pattern, station_pair)
                    if match:
                        from_to = f"{match.group(1)}-{match.group(2)}"
                
                # Get T/O-H/O information (Intermediate Stations in our data)
                intermediate_stations = train_info.get('Intermediate Stations', '') or train_info.get('T/O-H/O', '')
                
                # Clean up intermediate stations text
                if intermediate_stations and "Data last updated on:" in intermediate_stations:
                    import re
                    intermediate_stations = re.sub(r',?\s*Data last updated on:\s*\(\s*mins\)\s*', '', intermediate_stations)
                
                # Get delay information
                delay_value = train_info.get('Delay', 'N/A')
                
                # Get start date
                start_date = train_info.get('Start date', '') or train_info.get('Start Date', '')
                if not start_date:
                    from datetime import datetime
                    start_date = datetime.now().strftime("%d %b")
                
                # Format the message with train locomotive emoji 🚂 (not train car emoji 🚆)
                channel_message = f"🚂 #{train_id}"
                
                # Add FROM-TO
                if from_to:
                    channel_message += f" | {from_to}"
                else:
                    channel_message += f" | UNKNOWN-UNKNOWN"
                    
                # Add T/O-H/O information if available
                if intermediate_stations:
                    channel_message += f" | T/O-H/O: {intermediate_stations}"
                
                # Add Delay information
                channel_message += f" | Delay: {delay_value}"
                
                # Add Start date
                channel_message += f" | Started: {start_date}"
                
                # Log the formatted channel message
                logger.info(f"Sending direct channel message: {channel_message}")
                
                # Send directly to the channel using our new method
                return self.send_to_channel(
                    message=channel_message,
                    only_channel=True
                )
        
        if train_info:
            # Get FROM-TO
            from_to = train_info.get('FROM-TO', '')
            
            # Try to extract station pair if FROM-TO not found
            if not from_to and 'Station Pair' in train_info:
                station_pair = train_info.get('Station Pair', '')
                import re
                pattern = r'([A-Z]+)[^-]*-([A-Z]+)'
                match = re.search(pattern, station_pair)
                if match:
                    from_to = f"{match.group(1)}-{match.group(2)}"
            
            # Get Intermediate Stations information and clean it up
            intermediate_stations = train_info.get('Intermediate Stations', '')
            
            # Remove "Data last updated on: ( mins)" text if present
            if intermediate_stations and "Data last updated on:" in intermediate_stations:
                import re
                intermediate_stations = re.sub(r',?\s*Data last updated on:\s*\(\s*mins\)\s*', '', intermediate_stations)
                logger.info(f"Cleaned intermediate stations text: {intermediate_stations}")
            
            # Get delay in raw format
            delay_raw = train_info.get('Delay', '')
            
            # Get DELAY(MINS.) column value specifically - this is critical
            delay_mins = train_info.get('DELAY(MINS.)', '')
            
            # If DELAY(MINS.) contains complex station information like "KI (19 mins), COA (35 mins)"
            # Extract just the first numeric value
            if delay_mins:
                import re
                # Try to extract the first number followed by "mins"
                mins_match = re.search(r'(\d+)\s*mins', str(delay_mins))
                if mins_match:
                    delay_mins = mins_match.group(1)
                    logger.info(f"Extracted numeric value from DELAY(MINS.): {delay_mins}")
                else:
                    # Try to extract the first number in parentheses
                    parens_match = re.search(r'\((\d+)[^\)]*\)', str(delay_mins))
                    if parens_match:
                        delay_mins = parens_match.group(1)
                        logger.info(f"Extracted numeric value from parentheses in DELAY(MINS.): {delay_mins}")
                    else:
                        # Try to extract any numeric value
                        any_number = re.search(r'(\d+)', str(delay_mins))
                        if any_number:
                            delay_mins = any_number.group(1)
                            logger.info(f"Extracted any numeric value from DELAY(MINS.): {delay_mins}")
            
            # Try to extract numeric delay for filtering
            if delay_raw:
                try:
                    import re
                    match = re.search(r'-?\d+', str(delay_raw))
                    if match:
                        delay = int(match.group())
                except:
                    delay = None
            
            # Get start date
            start_date = train_info.get('Start date', '') or train_info.get('Start Date', '')
            
            # Try to extract train type for filtering
            if from_to and len(from_to) >= 3:
                train_type = from_to[:3]  # First three characters often indicate train type
        
        # Format EXACTLY as requested in the format: "#train_number | FROM-TO | T/O-H/O: value | Delay: value | Started: date"
        # Use the train emoji 🚆 as specified, but ensure it appears subdued
        message = f"🚆 #{train_id}"
        
        # Ensure FROM-TO is present
        if from_to:
            message += f" | {from_to}"
        else:
            message += f" | UNKNOWN-UNKNOWN"
            
        # Add T/O-H/O information if available (previously called Intermediate Stations)
        if intermediate_stations:
            message += f" | T/O-H/O: {intermediate_stations}"
            
        # Ensure Delay value is present
        if delay_raw:
            message += f" | Delay: {delay_raw}"
        else:
            message += f" | Delay: N/A"
            
        # Ensure Start date is present
        if start_date:
            message += f" | Started: {start_date}"
        else:
            message += f" | Started: Unknown"
        
        logger.info(f"Sending notification with message: {message}")
        
        # Send notification with filtering based on train type and notification preferences
        return self.send_message(
            message,
            message_type='new_train',
            train_type=train_type,
            delay=delay
        )
    
    def notify_train_status(self, train_id: str, status: str, 
                          location: Optional[str] = None,
                          delay: Optional[int] = None,
                          train_type: Optional[str] = None) -> bool:
        """
        Send notification about train status update
        
        Args:
            train_id: Train number/ID
            status: Status text (e.g., "Running", "Arrived", "Delayed")
            location: Optional current location of the train
            delay: Optional delay in minutes (positive for late, negative for early)
            train_type: Optional train type code (SUF, MEX, etc.)
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_configured:
            return False
            
        # Determine message type for notification filtering
        message_type = 'status_change'
        if delay is not None:
            if delay > 0:
                message_type = 'delay'
            elif delay < 0:
                message_type = 'early'
        
        # Format EXACTLY as requested in the format: "#train_number | FROM-TO | T/O-H/O: value | Delay: value | Started: date"
        from_to = location if location else "UNKNOWN-UNKNOWN"
        delay_value = f"{delay} mins late" if delay and delay > 0 else f"{abs(delay)} mins early" if delay and delay < 0 else "On time"
        
        # Create DELAY(MINS.) value with just the number
        delay_mins_value = f"{delay}" if delay is not None else "N/A"
        
        # We don't have T/O-H/O station information for status updates, but we could add them in the future
        intermediate_stations = ""
        
        # If somehow we do get intermediate stations with "Data last updated on: ( mins)", clean it up
        if intermediate_stations and "Data last updated on:" in intermediate_stations:
            import re
            intermediate_stations = re.sub(r',?\s*Data last updated on:\s*\(\s*mins\)\s*', '', intermediate_stations)
            logger.info(f"Cleaned intermediate stations text in status update: {intermediate_stations}")
        
        # If delay is a complex string (like "KI (19 mins), COA (35 mins)"), extract just the first numeric value
        if isinstance(delay_mins_value, str) and any(char.isdigit() for char in delay_mins_value):
            import re
            # Try to extract the first number followed by "mins"
            mins_match = re.search(r'(\d+)\s*mins', delay_mins_value)
            if mins_match:
                delay_mins_value = mins_match.group(1)
                logger.info(f"Extracted numeric value from complex delay string: {delay_mins_value}")
            else:
                # Try to extract the first number in parentheses
                parens_match = re.search(r'\((\d+)[^\)]*\)', delay_mins_value)
                if parens_match:
                    delay_mins_value = parens_match.group(1)
                    logger.info(f"Extracted numeric value from parentheses: {delay_mins_value}")
                else:
                    # Try to extract any numeric value
                    any_number = re.search(r'(\d+)', delay_mins_value)
                    if any_number:
                        delay_mins_value = any_number.group(1)
                        logger.info(f"Extracted any numeric value from delay string: {delay_mins_value}")
        
        # Get current date for the "Started" field if not available
        from datetime import datetime
        started_date = datetime.now().strftime("%d %b")
        
        # Format message in the exact required format with train emoji
        message = f"🚆 #{train_id} | {from_to}"
        
        # Add T/O-H/O information if available
        if intermediate_stations:
            message += f" | T/O-H/O: {intermediate_stations}"
            
        # Continue with the rest of the message (without DELAY(MINS.) as requested)
        message += f" | Delay: {delay_value} | Started: {started_date}"
        
        # Log the formatted message
        logger.info(f"Sending status notification with message: {message}")
        
        # Send message with appropriate filtering
        return self.send_message(
            message,
            message_type=message_type,
            train_type=train_type,
            delay=delay
        )
    
    def notify_multiple_new_trains(self, train_ids: List[str], 
                                  train_details: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        """
        Send notification about multiple new trains
        
        Args:
            train_ids: List of train numbers/IDs
            train_details: Optional dictionary mapping train IDs to additional info
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_configured or not train_ids:
            return False
            
        # Check if we should filter notifications based on user preferences
        prefs = st.session_state.telegram_notify_preferences
        
        # If new train notifications are disabled entirely, exit early
        if not prefs.get('new_trains', True):
            logger.info("New train notifications disabled by user preferences")
            return False
        
        # Check for quiet hours
        if self._is_in_quiet_hours():
            logger.info("Notification suppressed: quiet hours active")
            return False
            
        # Check for rate limiting
        if not self._check_rate_limit():
            logger.warning("Notification suppressed: rate limit exceeded")
            return False
            
        # Filter trains based on train type if needed
        filtered_train_ids = []
        
        for train_id in train_ids:
            train_info = train_details.get(train_id, {}) if train_details else {}
            from_to = train_info.get('FROM-TO', '')
            
            # Try to extract train type from FROM-TO field
            train_type = None
            if from_to and len(from_to) >= 3:
                train_type = from_to[:3]  # First three characters often indicate train type
                
            # Skip if this train type is filtered out
            if train_type:
                train_filters = prefs.get('train_filters', {})
                if train_type in train_filters and not train_filters[train_type]:
                    logger.info(f"Train {train_id} filtered out due to train type {train_type}")
                    continue
                    
            filtered_train_ids.append(train_id)
            
        # If all trains were filtered out, exit early
        if not filtered_train_ids:
            logger.info("All trains filtered out by user preferences")
            return False
            
        # Instead of creating a summary message for all trains, send individual notifications
        # for each train so they have the proper detailed format
        success = False
        
        # Send individual notifications for all trains, no summary needed
        max_individual_notifications = 100  # Increased to a high number to effectively never trigger summary mode
        
        # If we have too many trains, send the first few as individual notifications
        # and then send the rest as a summary
        if len(filtered_train_ids) > max_individual_notifications:
            # Send individual notifications for the first few trains
            for i, train_id in enumerate(filtered_train_ids[:max_individual_notifications]):
                train_info = train_details.get(train_id, {}) if train_details else {}
                result = self.notify_new_train(train_id, train_info)
                success = success or result
                
            # Create a summary message for the remaining trains
            remaining = len(filtered_train_ids) - max_individual_notifications
            if remaining > 0:
                summary_message = f"🚆 <b>{remaining} more new trains detected:</b>\n\n"
                
                for i, train_id in enumerate(filtered_train_ids[max_individual_notifications:], max_individual_notifications + 1):
                    summary_message += f"{i}. <b>#{train_id}</b>\n"
                    
                summary_message += "\nOpen the train tracking app for more details."
                summary_result = self.send_message(summary_message, message_type='new_train')
                success = success or summary_result
        else:
            # If we have a reasonable number, send individual notifications for all
            # If we have a channel ID configured, also send directly to channel with proper format
            have_channel = bool(st.session_state.telegram_channel_id)
            
            for train_id in filtered_train_ids:
                train_info = train_details.get(train_id, {}) if train_details else {}
                
                # Send normal notification to chat IDs
                result = self.notify_new_train(train_id, train_info)
                
                # If we have a channel ID, also send a direct channel message with the proper format
                if have_channel:
                    channel_result = self.notify_new_train(
                        train_id, 
                        train_info,
                        send_to_channel_only=True  # This flag makes it use the channel format with locomotive emoji
                    )
                    # Count success from either message
                    success = success or result or channel_result
                else:
                    success = success or result
        
        return success
    
    def render_settings_ui(self):
        """Render Telegram notification settings UI in Streamlit"""
        st.header("Telegram Notifications")
        
        # Bot token input
        token = st.text_input(
            "Telegram Bot Token",
            value=st.session_state.telegram_bot_token,
            type="password",
            help="Enter your Telegram Bot token from BotFather"
        )
        
        if token != st.session_state.telegram_bot_token:
            st.session_state.telegram_bot_token = token
            # Reinitialize bot with new token
            if token:
                try:
                    self._bot = Bot(token=token)
                    st.success("Telegram bot token updated successfully!")
                except Exception as e:
                    st.error(f"Invalid Telegram bot token: {str(e)}")
                    self._bot = None
            else:
                self._bot = None
        
        # Chat IDs input
        chat_ids_str = st.text_input(
            "Telegram Chat IDs",
            value=",".join(st.session_state.telegram_chat_ids),
            help="Enter comma-separated list of Telegram chat IDs for direct user messages"
        )
        
        # Update chat IDs if changed
        new_chat_ids = [id.strip() for id in chat_ids_str.split(',')] if chat_ids_str else []
        if new_chat_ids != st.session_state.telegram_chat_ids:
            st.session_state.telegram_chat_ids = new_chat_ids
            if new_chat_ids:
                st.success(f"Updated {len(new_chat_ids)} Telegram chat IDs")
        
        # Channel ID input
        st.markdown("### Channel Notifications")
        st.info("To send notifications to a Telegram channel, add your bot to the channel as an admin with 'Post Messages' permission, then enter the channel ID below.")
        
        channel_id = st.text_input(
            "Telegram Channel ID",
            value=st.session_state.telegram_channel_id,
            help="Enter your Telegram channel ID in the format @channelname or -100xxxxxxxxx"
        )
        
        # Update channel ID if changed
        if channel_id != st.session_state.telegram_channel_id:
            st.session_state.telegram_channel_id = channel_id
            if channel_id:
                st.success(f"Updated Telegram channel ID to {channel_id}")
        
        # Configuration status
        if self.is_configured:
            # Format a success message based on what's configured
            recipients_info = []
            
            if st.session_state.telegram_chat_ids:
                recipients_info.append(f"{len(st.session_state.telegram_chat_ids)} direct recipient(s)")
                
            if st.session_state.telegram_channel_id:
                recipients_info.append(f"channel '{st.session_state.telegram_channel_id}'")
                
            recipients_text = " and ".join(recipients_info)
            st.success(f"Telegram notifications are properly configured with {recipients_text}.")
        else:
            missing = []
            if not st.session_state.telegram_bot_token:
                missing.append("Bot Token")
            if not st.session_state.telegram_chat_ids and not st.session_state.telegram_channel_id:
                missing.append("Chat IDs or Channel ID")
            
            st.warning(f"Telegram notifications are not fully configured. Missing: {', '.join(missing)}")
        
        # Notification Preferences Section
        st.subheader("Notification Preferences")
        
        prefs = st.session_state.telegram_notify_preferences
        
        # Event Types to Notify
        st.markdown("#### Event Types")
        col1, col2 = st.columns(2)
        
        with col1:
            prefs['new_trains'] = st.checkbox(
                "New Trains", 
                value=prefs.get('new_trains', True),
                help="Receive notifications when new trains are detected"
            )
            
            prefs['status_changes'] = st.checkbox(
                "Status Changes", 
                value=prefs.get('status_changes', True),
                help="Receive notifications when train status changes (arrival, departure, etc.)"
            )
        
        with col2:
            prefs['delays'] = st.checkbox(
                "Delays", 
                value=prefs.get('delays', True),
                help="Receive notifications about delayed trains"
            )
            
            prefs['early_arrivals'] = st.checkbox(
                "Early Arrivals", 
                value=prefs.get('early_arrivals', True),
                help="Receive notifications about trains arriving ahead of schedule"
            )
        
        # Train Type Filtering
        st.markdown("#### Train Type Filters")
        st.markdown("Select which train types you want to receive notifications for:")
        
        train_filters = prefs.get('train_filters', {})
        
        # Define train types with descriptions
        train_types = {
            'SUF': 'Superfast',
            'MEX': 'Express',
            'DMU': 'DMU',
            'MEMU': 'MEMU',
            'PEX': 'Passenger Express',
            'TOD': 'Train On Demand',
            'VNDB': 'VandeBharat',
            'RAJ': 'Rajdhani',
            'JSH': 'Janshatabdhi',
            'DNRT': 'Duronto'
        }
        
        # Create columns for checkboxes
        cols = st.columns(2)
        i = 0
        
        for train_code, description in train_types.items():
            with cols[i % 2]:
                train_filters[train_code] = st.checkbox(
                    f"{description} ({train_code})", 
                    value=train_filters.get(train_code, True if train_code in ['SUF', 'MEX', 'VNDB', 'RAJ', 'JSH', 'DNRT'] else False)
                )
            i += 1
        
        # Update train filters in preferences
        prefs['train_filters'] = train_filters
        
        # Delay Threshold
        st.markdown("#### Delay Threshold")
        prefs['min_delay_threshold'] = st.slider(
            "Minimum Delay for Notification (minutes)",
            min_value=0, 
            max_value=60, 
            value=prefs.get('min_delay_threshold', 10),
            help="Only notify about delays that exceed this threshold"
        )
        
        # Rate Limiting
        st.markdown("#### Rate Limiting")
        prefs['max_notifications_per_hour'] = st.slider(
            "Maximum Notifications Per Hour",
            min_value=1, 
            max_value=100, 
            value=prefs.get('max_notifications_per_hour', 20),
            help="Limit the number of notifications to avoid overwhelming recipients"
        )
        
        # Quiet Hours
        st.markdown("#### Quiet Hours")
        
        prefs['quiet_hours_enabled'] = st.checkbox(
            "Enable Quiet Hours", 
            value=prefs.get('quiet_hours_enabled', False),
            help="Pause notifications during specified hours"
        )
        
        if prefs['quiet_hours_enabled']:
            quiet_hours_col1, quiet_hours_col2 = st.columns(2)
            
            with quiet_hours_col1:
                prefs['quiet_hours_start'] = st.text_input(
                    "Start Time (HH:MM)",
                    value=prefs.get('quiet_hours_start', "22:00"),
                    help="Quiet period starts at this time (24-hour format)"
                )
            
            with quiet_hours_col2:
                prefs['quiet_hours_end'] = st.text_input(
                    "End Time (HH:MM)",
                    value=prefs.get('quiet_hours_end', "06:00"),
                    help="Quiet period ends at this time (24-hour format)"
                )
        
        # Update preferences in session state
        st.session_state.telegram_notify_preferences = prefs
        
        # Test notification buttons with different notification types
        st.subheader("Test Notifications")
        st.markdown("You can send test messages to verify your notification settings:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Send Test - New Train"):
                if self.is_configured:
                    success = self.send_message(
                        "🚆 <b>Test Notification:</b> New Train\n\nThis is a test for new train notifications!",
                        message_type='new_train',
                        train_type='SUF'  # Test with a Superfast train
                    )
                    if success:
                        st.success("Test message sent successfully!")
                    else:
                        st.error("Failed to send test message. Please check your configuration and preferences.")
                else:
                    st.error("Please configure bot token and at least one chat ID or channel ID first.")
                    
            if st.button("Send Test - Direct Channel"):
                if self.is_configured and st.session_state.telegram_channel_id:
                    # Create a message with the proper train format and emoji
                    channel_message = (
                        "🚂 #12760 | HYB-TBM | T/O-H/O: GDR-RJY: 10 mins late | "
                        "Delay: -6 mins | Started: 2023-06-15"
                    )
                    
                    success = self.send_to_channel(
                        message=channel_message,
                        only_channel=True
                    )
                    
                    if success:
                        st.success("Direct channel message sent successfully!")
                    else:
                        st.error("Failed to send direct channel message. Check your channel ID and bot permissions.")
                else:
                    st.error("Please configure bot token and channel ID for direct channel messaging.")
                    
            if st.button("Send Test - Status Change"):
                if self.is_configured:
                    success = self.send_message(
                        "🚄 <b>Test Notification:</b> Status Change\n\nThis is a test for train status change notifications!",
                        message_type='status_change',
                        train_type='MEX'  # Test with an Express train
                    )
                    if success:
                        st.success("Test message sent successfully!")
                    else:
                        st.error("Failed to send test message. Please check your configuration and preferences.")
                else:
                    st.error("Please configure bot token and at least one chat ID or channel ID first.")
        
        with col2:
            if st.button("Send Test - Delay"):
                if self.is_configured:
                    success = self.send_message(
                        "⚠️ <b>Test Notification:</b> Train Delay\n\nThis is a test for train delay notifications!",
                        message_type='delay',
                        train_type='RAJ',  # Test with a Rajdhani train
                        delay=15  # Test with a 15-minute delay
                    )
                    if success:
                        st.success("Test message sent successfully!")
                    else:
                        st.error("Failed to send test message. Please check your configuration and preferences.")
                else:
                    st.error("Please configure bot token and at least one chat ID or channel ID first.")
                    
            if st.button("Send Test - Early Arrival"):
                if self.is_configured:
                    success = self.send_message(
                        "🕒 <b>Test Notification:</b> Early Arrival\n\nThis is a test for early arrival notifications!",
                        message_type='early',
                        train_type='VNDB',  # Test with a Vande Bharat train
                        delay=-10  # Test with a 10-minute early arrival
                    )
                    if success:
                        st.success("Test message sent successfully!")
                    else:
                        st.error("Failed to send test message. Please check your configuration and preferences.")
                else:
                    st.error("Please configure bot token and at least one chat ID or channel ID first.")