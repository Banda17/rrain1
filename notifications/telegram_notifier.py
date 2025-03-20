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
        return (self._bot is not None and 
                st.session_state.telegram_bot_token and 
                len(st.session_state.telegram_chat_ids) > 0)
    
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
        
        if not chat_ids:
            logger.warning("No chat IDs configured for Telegram notifications")
            return False
        
        # Create a new event loop for async operations - using a more robust approach
        # that handles multiple calls and prevents "Event loop is closed" errors
        try:
            async def send_all_messages():
                results = []
                for cid in chat_ids:
                    try:
                        # Check if bot is initialized
                        if self._bot is None:
                            logger.error(f"Cannot send message to {cid}: Telegram bot not initialized")
                            results.append(False)
                            continue
                            
                        await self._bot.send_message(chat_id=cid, text=message, parse_mode='HTML')
                        results.append(True)
                    except Exception as e:
                        logger.error(f"Failed to send Telegram message to {cid}: {str(e)}")
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
    
    def notify_new_train(self, train_id: str, train_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification about a new train
        
        Args:
            train_id: Train number/ID
            train_info: Optional dictionary with additional train information
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_configured:
            return False
            
        train_name = ""
        from_to = ""
        delay = None
        train_type = None
        
        if train_info:
            train_name = train_info.get('Train Name', '')
            from_to = train_info.get('FROM-TO', '')
            
            # Try to extract train type from FROM-TO field
            if from_to and len(from_to) >= 3:
                train_type = from_to[:3]  # First three characters often indicate train type
            
            # Format delay if available
            if 'Delay' in train_info:
                try:
                    delay_val = train_info['Delay']
                    if isinstance(delay_val, str) and delay_val.isdigit():
                        delay = int(delay_val)
                    elif isinstance(delay_val, (int, float)):
                        delay = int(delay_val)
                except:
                    pass
        
        # Construct message
        message = f"🚆 <b>New Train Detected:</b> #{train_id}"
        
        if train_name:
            message += f"\n<b>Name:</b> {train_name}"
        
        if from_to:
            message += f"\n<b>Route:</b> {from_to}"
            
        if delay is not None:
            message += f"\n<b>Status:</b> Delayed by {delay} minutes"
        
        message += "\n\nOpen the train tracking app for more details."
        
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
        
        # Construct message
        message = f"🚄 <b>Train #{train_id} Update</b>"
        
        if status:
            message += f"\n<b>Status:</b> {status}"
            
        if location:
            message += f"\n<b>Location:</b> {location}"
            
        if delay is not None:
            if delay > 0:
                message += f"\n<b>Delay:</b> {delay} minutes late"
            elif delay < 0:
                message += f"\n<b>Running:</b> {abs(delay)} minutes early"
            else:
                message += f"\n<b>On time</b>"
        
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
        
        # If just one train remains after filtering, use the single train notification
        if len(filtered_train_ids) == 1:
            train_id = filtered_train_ids[0]
            train_info = train_details.get(train_id, {}) if train_details else {}
            return self.notify_new_train(train_id, train_info)
            
        # For multiple trains, create a summary message
        message = f"🚆 <b>{len(filtered_train_ids)} New Trains Detected:</b>\n\n"
        
        for i, train_id in enumerate(filtered_train_ids, 1):
            # Handle different formats of train_details
            if train_details and train_id in train_details:
                train_info = train_details[train_id]
                
                # If train_info is a dictionary, extract specific fields
                if isinstance(train_info, dict):
                    train_name = train_info.get('Train Name', '')
                    from_to = train_info.get('FROM-TO', '')
                    
                    # If there's an 'info' field with generic details, use it as a fallback
                    if not (train_name or from_to) and 'info' in train_info:
                        additional_info = train_info['info']
                        message += f"{i}. <b>#{train_id}</b> - {additional_info}"
                        continue
                # If train_info is a string, use it directly
                elif isinstance(train_info, str):
                    message += f"{i}. <b>#{train_id}</b> - {train_info}"
                    continue
                else:
                    train_name = ''
                    from_to = ''
            else:
                train_name = ''
                from_to = ''
            
            message += f"{i}. <b>#{train_id}</b>"
            
            if train_name:
                message += f" - {train_name}"
                
            if from_to:
                message += f" ({from_to})"
                
            message += "\n"
            
            # Limit to 10 trains in one message to avoid hitting message length limits
            if i >= 10 and len(filtered_train_ids) > 10:
                message += f"\n...and {len(filtered_train_ids) - 10} more trains"
                break
        
        message += "\nOpen the train tracking app for more details."
        
        # Send with message type 'new_train' for consistent filtering
        return self.send_message(message, message_type='new_train')
    
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
            help="Enter comma-separated list of Telegram chat IDs"
        )
        
        # Update chat IDs if changed
        new_chat_ids = [id.strip() for id in chat_ids_str.split(',')] if chat_ids_str else []
        if new_chat_ids != st.session_state.telegram_chat_ids:
            st.session_state.telegram_chat_ids = new_chat_ids
            if new_chat_ids:
                st.success(f"Updated {len(new_chat_ids)} Telegram chat IDs")
        
        # Configuration status
        if self.is_configured:
            st.success(f"Telegram notifications are properly configured with {len(st.session_state.telegram_chat_ids)} recipients.")
        else:
            missing = []
            if not st.session_state.telegram_bot_token:
                missing.append("Bot Token")
            if not st.session_state.telegram_chat_ids:
                missing.append("Chat IDs")
            
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
                    st.error("Please configure both the bot token and at least one chat ID first.")
                    
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
                    st.error("Please configure both the bot token and at least one chat ID first.")
        
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
                    st.error("Please configure both the bot token and at least one chat ID first.")
                    
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
                    st.error("Please configure both the bot token and at least one chat ID first.")