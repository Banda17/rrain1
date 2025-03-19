import os
import streamlit as st
from twilio.rest import Client
from datetime import datetime
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMSNotifier:
    def __init__(self):
        """Initialize the SMS notifier with Twilio credentials"""
        # Get credentials from environment variables or secrets
        self.account_sid = st.secrets.get("TWILIO_ACCOUNT_SID", os.environ.get("TWILIO_ACCOUNT_SID"))
        self.auth_token = st.secrets.get("TWILIO_AUTH_TOKEN", os.environ.get("TWILIO_AUTH_TOKEN"))
        self.from_number = st.secrets.get("TWILIO_PHONE_NUMBER", os.environ.get("TWILIO_PHONE_NUMBER"))
        
        # Get notification recipients from environment or secrets
        recipients_str = st.secrets.get("NOTIFICATION_RECIPIENTS", os.environ.get("NOTIFICATION_RECIPIENTS", "[]"))
        try:
            self.recipients = json.loads(recipients_str)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format for NOTIFICATION_RECIPIENTS: {recipients_str}")
            self.recipients = []
        
        # Initialize client if credentials are available
        self.client = None
        if self.account_sid and self.auth_token and self.from_number:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("SMS notifier initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}")
        else:
            logger.warning("SMS notifications disabled: Missing Twilio credentials")
    
    def load_known_trains(self):
        """Load the list of known trains from the persistent store"""
        try:
            if 'known_trains' not in st.session_state:
                # Try to load from file if it exists
                try:
                    with open('temp/known_trains.json', 'r') as f:
                        st.session_state.known_trains = set(json.load(f))
                        logger.info(f"Loaded {len(st.session_state.known_trains)} known trains from file")
                except (FileNotFoundError, json.JSONDecodeError):
                    st.session_state.known_trains = set()
                    logger.info("Initialized empty known trains set")
            
            return st.session_state.known_trains
        except Exception as e:
            logger.error(f"Error loading known trains: {str(e)}")
            return set()
    
    def save_known_trains(self, known_trains):
        """Save the list of known trains to the persistent store"""
        try:
            # Create temp directory if it doesn't exist
            os.makedirs('temp', exist_ok=True)
            
            # Save to file
            with open('temp/known_trains.json', 'w') as f:
                json.dump(list(known_trains), f)
            
            # Update session state
            st.session_state.known_trains = known_trains
            logger.info(f"Saved {len(known_trains)} known trains to file")
        except Exception as e:
            logger.error(f"Error saving known trains: {str(e)}")
    
    def check_for_new_trains(self, current_trains):
        """
        Check for new trains that haven't been seen before
        
        Args:
            current_trains: List of current train IDs
            
        Returns:
            List of new train IDs
        """
        known_trains = self.load_known_trains()
        current_trains_set = set(current_trains)
        
        # Find new trains
        new_trains = current_trains_set - known_trains
        
        if new_trains:
            # Update known trains
            known_trains.update(new_trains)
            self.save_known_trains(known_trains)
            logger.info(f"Detected {len(new_trains)} new trains: {new_trains}")
        
        return list(new_trains)
    
    def send_notification(self, message):
        """
        Send SMS notification
        
        Args:
            message: The message to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self.recipients:
            logger.warning("SMS notification not sent: Client not initialized or no recipients")
            return False
        
        success = True
        for recipient in self.recipients:
            try:
                self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=recipient
                )
                logger.info(f"SMS sent to {recipient}")
            except Exception as e:
                logger.error(f"Failed to send SMS to {recipient}: {str(e)}")
                success = False
        
        return success
    
    def notify_new_trains(self, current_trains, train_details=None):
        """
        Check for new trains and send notifications if any are found
        
        Args:
            current_trains: List of current train IDs
            train_details: Optional dictionary mapping train IDs to additional info
            
        Returns:
            List of new train IDs
        """
        new_trains = self.check_for_new_trains(current_trains)
        
        if new_trains:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for train in new_trains:
                # Construct message with details if available
                if train_details and train in train_details:
                    details = train_details[train]
                    message = f"New train detected: {train}\n{details}\nTime: {timestamp}"
                else:
                    message = f"New train detected: {train}\nTime: {timestamp}"
                
                # Send notification
                self.send_notification(message)
        
        return new_trains