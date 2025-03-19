import os
import streamlit as st
import requests
from datetime import datetime
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMSNotifier:
    def __init__(self):
        """Initialize the SMS notifier with SMS Country credentials"""
        # Get credentials from environment variables or secrets
        self.api_key = st.secrets.get("SMS_COUNTRY_API_KEY", os.environ.get("SMS_COUNTRY_API_KEY"))
        self.api_token = st.secrets.get("SMS_COUNTRY_API_TOKEN", os.environ.get("SMS_COUNTRY_API_TOKEN"))
        
        # SMS Country API endpoint
        self.api_url = "https://api.smscountry.com/v1/SMSes"
        
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
        
        # Check if credentials are available
        if self.api_key and self.api_token:
            logger.info("SMS Country credentials found, SMS notifier initialized successfully")
        else:
            logger.warning("SMS notifications disabled: Missing SMS Country credentials")
    
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
        Send SMS notification using SMS Country API
        
        Args:
            message: The message to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self.api_key or not self.api_token or not self.recipients:
            logger.warning("SMS notification not sent: Missing API credentials or no recipients")
            return False
        
        # Use SMS Country API
        success = True
        for recipient in self.recipients:
            try:
                # Prepare the SMS Country API request
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }
                
                # Basic auth with API key and token
                auth = (self.api_key, self.api_token)
                
                # Create the JSON payload for SMS Country
                payload = {
                    'Message': message,
                    'MobileNumbers': [recipient],
                    'SenderId': 'SCRVJW',  # Custom sender ID for your application
                    'Is_Unicode': False,
                    'Is_Flash': False
                }
                
                # Make the API request
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    auth=auth
                )
                
                # Check if the request was successful
                if response.status_code == 200 or response.status_code == 201:
                    try:
                        response_data = response.json()
                        if 'MessageId' in response_data:
                            logger.info(f"SMS sent to {recipient} (Message ID: {response_data.get('MessageId', 'unknown')})")
                        elif 'Message' in response_data:
                            logger.info(f"SMS Country response: {response_data.get('Message')}")
                        else:
                            logger.info(f"SMS sent successfully to {recipient}")
                    except Exception as e:
                        logger.error(f"Error parsing API response: {str(e)}")
                        if response.text:
                            logger.info(f"Raw response: {response.text}")
                        success = False
                else:
                    logger.error(f"SMS Country API request failed with status code: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    success = False
                    
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