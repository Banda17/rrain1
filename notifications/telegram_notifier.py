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
    
    def send_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """
        Send a message to one or all configured chat IDs
        
        Args:
            message: Message text to send
            chat_id: Optional specific chat ID to send to (if None, send to all)
            
        Returns:
            True if at least one message was sent successfully
        """
        if not self.is_configured:
            logger.warning("Telegram notifications not properly configured")
            return False
            
        chat_ids = [chat_id] if chat_id else st.session_state.telegram_chat_ids
        
        if not chat_ids:
            logger.warning("No chat IDs configured for Telegram notifications")
            return False
        
        # Create a new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = []
            for cid in chat_ids:
                result = loop.run_until_complete(self._send_message_async(cid, message))
                results.append(result)
            
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
        finally:
            loop.close()
    
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
        delay = ""
        
        if train_info:
            train_name = train_info.get('Train Name', '')
            from_to = train_info.get('FROM-TO', '')
            
            # Format delay if available
            if 'Delay' in train_info:
                try:
                    delay_val = train_info['Delay']
                    if delay_val:
                        delay = f" (Delay: {delay_val} min)"
                except:
                    pass
        
        # Construct message
        message = f"🚆 <b>New Train Detected:</b> #{train_id}"
        
        if train_name:
            message += f"\n<b>Name:</b> {train_name}"
        
        if from_to:
            message += f"\n<b>Route:</b> {from_to}"
            
        if delay:
            message += f"\n<b>Status:</b>{delay}"
            
        message += "\n\nOpen the train tracking app for more details."
        
        return self.send_message(message)
    
    def notify_train_status(self, train_id: str, status: str, 
                          location: Optional[str] = None,
                          delay: Optional[int] = None) -> bool:
        """
        Send notification about train status update
        
        Args:
            train_id: Train number/ID
            status: Status text (e.g., "Running", "Arrived", "Delayed")
            location: Optional current location of the train
            delay: Optional delay in minutes
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_configured:
            return False
            
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
        
        return self.send_message(message)
    
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
            
        if len(train_ids) == 1:
            # If just one train, use the single train notification
            train_id = train_ids[0]
            train_info = train_details.get(train_id, {}) if train_details else {}
            return self.notify_new_train(train_id, train_info)
            
        # For multiple trains, create a summary message
        message = f"🚆 <b>{len(train_ids)} New Trains Detected:</b>\n\n"
        
        for i, train_id in enumerate(train_ids, 1):
            train_info = train_details.get(train_id, {}) if train_details else {}
            train_name = train_info.get('Train Name', '')
            from_to = train_info.get('FROM-TO', '')
            
            message += f"{i}. <b>#{train_id}</b>"
            
            if train_name:
                message += f" - {train_name}"
                
            if from_to:
                message += f" ({from_to})"
                
            message += "\n"
            
            # Limit to 10 trains in one message to avoid hitting message length limits
            if i >= 10 and len(train_ids) > 10:
                message += f"\n...and {len(train_ids) - 10} more trains"
                break
        
        message += "\nOpen the train tracking app for more details."
        
        return self.send_message(message)
    
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
        
        # Test notification button
        if st.button("Send Test Telegram Message"):
            if self.is_configured:
                success = self.send_message("🔔 This is a test notification from your Train Tracking application!")
                if success:
                    st.success("Test message sent successfully!")
                else:
                    st.error("Failed to send test message. Please check your bot token and chat IDs.")
            else:
                st.error("Please configure both the bot token and at least one chat ID first.")
        
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