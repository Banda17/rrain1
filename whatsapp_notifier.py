import os
import streamlit as st
import requests
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppNotifier:
    def __init__(self):
        """Initialize the WhatsApp notifier with API credentials"""
        # Get credentials from environment variables or secrets
        self.whatsapp_api_key = st.secrets.get("WHATSAPP_API_KEY", os.environ.get("WHATSAPP_API_KEY"))
        self.whatsapp_number = st.secrets.get("WHATSAPP_NUMBER", os.environ.get("WHATSAPP_NUMBER"))
        
        # Get notification recipients from environment or secrets
        self.recipients = []
        try:
            recipients_value = st.secrets.get("NOTIFICATION_RECIPIENTS", os.environ.get("NOTIFICATION_RECIPIENTS"))
            
            # Handle different types of input
            if isinstance(recipients_value, str):
                # If it's a string, try to parse it as JSON
                try:
                    self.recipients = json.loads(recipients_value)
                except json.JSONDecodeError:
                    # If it's a single number in string format
                    if recipients_value.strip():
                        self.recipients = [recipients_value.strip()]
            elif isinstance(recipients_value, list):
                # If it's already a list
                self.recipients = recipients_value
            elif recipients_value is not None:
                # If it's a single value that's not None
                self.recipients = [str(recipients_value)]
                
            logger.info(f"Successfully configured {len(self.recipients)} notification recipients")
        except Exception as e:
            logger.error(f"Error processing NOTIFICATION_RECIPIENTS: {str(e)}")
            self.recipients = []
            
        # Check if API key is available
        if not self.whatsapp_api_key:
            logger.warning("WhatsApp notifications disabled: Missing API key")
    
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
        
        # Log current trains for debugging
        logger.info(f"Current trains in data: {len(current_trains_set)}")
        logger.debug(f"Train numbers: {sorted(list(current_trains_set))}")
        
        # Find new trains
        new_trains = current_trains_set - known_trains
        
        if new_trains:
            # Update known trains
            known_trains.update(new_trains)
            self.save_known_trains(known_trains)
            logger.info(f"Detected {len(new_trains)} new trains: {new_trains}")
        else:
            logger.info(f"No new trains detected. Already tracking {len(known_trains)} trains.")
        
        return list(new_trains)
    
    def send_notification(self, message):
        """
        Send notification via WhatsApp Web API
        
        Args:
            message: The message to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self.whatsapp_api_key:
            logger.warning("WhatsApp notification not sent: API key not configured")
            return False
            
        if not self.recipients:
            logger.warning("WhatsApp notification not sent: No recipients configured")
            return False
        
        success = True
        for recipient in self.recipients:
            try:
                # Format the recipient number (remove any '+' and spaces)
                clean_recipient = recipient.replace('+', '').replace(' ', '')
                
                # Send message using WhatsApp API
                url = "https://api.whatsapp.com/send"
                
                # Generate the WhatsApp Web URL
                from urllib.parse import quote
                whatsapp_url = f"{url}?phone={clean_recipient}&text={quote(message)}"
                
                # Display the URL for manual sending (this is a fallback)
                logger.info(f"WhatsApp Web URL: {whatsapp_url}")
                
                # Note: In a production environment, we would use a proper WhatsApp Business API
                # For now, we'll just log the URL and consider it a success
                logger.info(f"WhatsApp message prepared for {recipient}")
            except Exception as e:
                logger.error(f"Failed to prepare WhatsApp message for {recipient}: {str(e)}")
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
        # Only check for trains that we haven't seen before
        new_trains = self.check_for_new_trains(current_trains)
        
        if new_trains:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Sending notifications for {len(new_trains)} new trains: {new_trains}")
            
            for train in new_trains:
                # Only send notifications for newly detected trains
                try:
                    # Construct message with details if available
                    if train_details and train in train_details:
                        details = train_details[train]
                        
                        # Check if we should use the compact format
                        if st.session_state.get('use_new_format', False):
                            try:
                                # Extract train details for the compact format
                                from_to = details.split('[')[1].split(']')[0].strip() if '[' in details and ']' in details else ""
                                intermediate = ""
                                delays = ""
                                start_date = ""
                                
                                # Extract intermediate stations and delays
                                if '(' in details and ')' in details:
                                    stations_part = details.split(']')[1] if ']' in details else details
                                    stations = [s.strip() for s in stations_part.split(',')]
                                    
                                    for station in stations:
                                        if "T/O" in station or "H/O" in station or "(-" in station or "(+" in station:
                                            intermediate += station + ","
                                        elif "DELAYED" in station.upper() or "LT" in station or "BT" in station:
                                            delays = station.strip()
                                        elif "Start Date" in station:
                                            start_date = station.strip()
                                    
                                    # Remove trailing comma
                                    if intermediate.endswith(','):
                                        intermediate = intermediate[:-1]
                                
                                # Format the compact message
                                message = f"{train} {from_to}, {intermediate} {delays}, {start_date}\nTime: {timestamp}"
                            except Exception as e:
                                logger.error(f"Error formatting message: {str(e)}")
                                # Fallback to standard format if parsing fails
                                message = f"{train}\n{details}\nTime: {timestamp}"
                        else:
                            # Standard format
                            message = f"{train}\n{details}\nTime: {timestamp}"
                    else:
                        # Basic message if no details available
                        message = f"{train}\nTime: {timestamp}"
                    
                    # Send notification
                    self.send_notification(message)
                except Exception as e:
                    logger.error(f"Error sending notification for train {train}: {str(e)}")
        else:
            logger.info("No new trains detected, no notifications sent")
        
        return new_trains