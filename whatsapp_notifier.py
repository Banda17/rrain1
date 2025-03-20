import os
import streamlit as st
import logging
from twilio.rest import Client
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppNotifier:
    def __init__(self):
        """Initialize the WhatsApp notification manager"""
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
        self.notification_recipients = os.environ.get('NOTIFICATION_RECIPIENTS', '').split(',')
        
        # Store known trains to avoid duplicate notifications
        self.known_trains_file = 'temp/known_trains_whatsapp.json'
        self.known_trains = self.load_known_trains()
        
        # Check if required environment variables are set
        self.is_configured = self._check_configuration()
        
    def _check_configuration(self):
        """Check if Twilio is properly configured"""
        if not self.account_sid or not self.auth_token or not self.twilio_phone_number:
            logger.warning("Twilio WhatsApp notifications not configured. Missing required environment variables.")
            return False
        
        if not self.notification_recipients or self.notification_recipients == ['']:
            logger.warning("No WhatsApp recipients configured.")
            return False
            
        return True
    
    def load_known_trains(self):
        """Load the list of known trains from the persistent store"""
        try:
            if os.path.exists(self.known_trains_file):
                with open(self.known_trains_file, 'r') as f:
                    known_trains = set(json.load(f))
                    logger.info(f"Loaded {len(known_trains)} known trains for WhatsApp notifications")
                    return known_trains
        except Exception as e:
            logger.warning(f"Could not load known trains for WhatsApp: {str(e)}")
        
        logger.info("Initialized empty known trains set for WhatsApp")
        return set()
    
    def save_known_trains(self, known_trains):
        """Save the list of known trains to the persistent store"""
        try:
            os.makedirs('temp', exist_ok=True)
            with open(self.known_trains_file, 'w') as f:
                json.dump(list(known_trains), f)
            logger.info(f"Saved {len(known_trains)} known trains to file for WhatsApp")
        except Exception as e:
            logger.error(f"Error saving known trains for WhatsApp: {str(e)}")
    
    def check_for_new_trains(self, current_trains):
        """
        Check for new trains that haven't been seen before
        
        Args:
            current_trains: List of current train IDs
            
        Returns:
            List of new train IDs
        """
        if not current_trains:
            return []
        
        # Convert to set for fast lookups
        current_train_set = set(current_trains)
        
        # Find trains that are in current set but not in known set
        new_trains = current_train_set - self.known_trains
        
        # Update known trains with the current set
        if new_trains:
            self.known_trains.update(new_trains)
            self.save_known_trains(self.known_trains)
            logger.info(f"New trains detected for WhatsApp: {new_trains}")
        
        return list(new_trains)
    
    def notify_new_trains(self, current_trains, train_details=None):
        """
        Check for new trains and send WhatsApp notifications if any are found
        
        Args:
            current_trains: List of current train IDs
            train_details: Optional dictionary mapping train IDs to additional info
            
        Returns:
            List of new train IDs
        """
        if not self.is_configured:
            logger.warning("WhatsApp notifications not configured, skipping...")
            return []
        
        if not current_trains:
            logger.info("No train data available for WhatsApp notifications")
            return []
        
        logger.info(f"Current trains in data for WhatsApp: {len(current_trains)}")
        logger.info(f"Train numbers for WhatsApp: {current_trains}")
        
        # Check for new trains
        new_trains = self.check_for_new_trains(current_trains)
        
        if not new_trains:
            logger.info(f"No new trains detected for WhatsApp. Already tracking {len(self.known_trains)} trains.")
            return []
        
        # Send notifications for new trains
        logger.info(f"Detected {len(new_trains)} new trains for WhatsApp: {new_trains}")
        
        # Send WhatsApp notifications
        for train in new_trains:
            detail = train_details.get(train, "New train detected") if train_details else "New train detected"
            self._send_whatsapp_message(train, detail)
        
        return new_trains
    
    def _send_whatsapp_message(self, train_id, details):
        """
        Send a WhatsApp message using Twilio
        
        Args:
            train_id: The train ID
            details: Additional details about the train
        """
        if not self.is_configured:
            logger.warning("WhatsApp notifications not configured, skipping...")
            return
        
        try:
            # Initialize Twilio client
            client = Client(self.account_sid, self.auth_token)
            
            # Format the message
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message_body = f"🚆 *New train {train_id} detected*\n\n{details}\n\nTime: {timestamp}"
            
            # Send to each recipient
            for recipient in self.notification_recipients:
                recipient = recipient.strip()
                if not recipient:
                    continue
                
                # Format recipient number if needed
                if not recipient.startswith('whatsapp:+'):
                    recipient = f"whatsapp:+{recipient}"
                
                try:
                    # Send message via Twilio
                    message = client.messages.create(
                        from_=f"whatsapp:{self.twilio_phone_number}",
                        body=message_body,
                        to=recipient
                    )
                    logger.info(f"Sent WhatsApp notification for train {train_id} to {recipient}, SID: {message.sid}")
                except Exception as e:
                    logger.error(f"Error sending WhatsApp message to {recipient}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in WhatsApp notification system: {str(e)}")
    
    def render_whatsapp_settings_ui(self):
        """Render WhatsApp notification settings UI in Streamlit"""
        st.subheader("WhatsApp Notifications")
        
        # Show configuration status
        if self.is_configured:
            st.success("WhatsApp notifications are configured")
            
            # Show recipient count
            recipients = [r for r in self.notification_recipients if r.strip()]
            if recipients:
                st.info(f"WhatsApp notifications will be sent to {len(recipients)} number(s)")
            else:
                st.warning("No WhatsApp recipients configured")
            
            # Test notification button
            if st.button("Send Test WhatsApp Message"):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._send_whatsapp_message("TEST", f"This is a test notification from the Train Tracking System.\nTime: {timestamp}")
                st.success("Test WhatsApp message sent! Check your WhatsApp.")
                
            # Known trains count
            st.write(f"Currently tracking {len(self.known_trains)} trains for WhatsApp notifications")
            
            # Reset button
            if st.button("Reset Known Trains for WhatsApp"):
                self.known_trains = set()
                self.save_known_trains(self.known_trains)
                st.success("Reset successful. You will receive notifications for all trains again.")
        else:
            missing = []
            if not self.account_sid:
                missing.append("TWILIO_ACCOUNT_SID")
            if not self.auth_token:
                missing.append("TWILIO_AUTH_TOKEN")
            if not self.twilio_phone_number:
                missing.append("TWILIO_PHONE_NUMBER")
            if not self.notification_recipients or self.notification_recipients == ['']:
                missing.append("NOTIFICATION_RECIPIENTS")
                
            st.warning("WhatsApp notifications are not fully configured")
            st.write("Missing environment variables: " + ", ".join(missing))
            
            # Show configuration help
            with st.expander("Configuration Help"):
                st.markdown("""
                To enable WhatsApp notifications:
                
                1. Create a Twilio account at https://www.twilio.com/
                2. Set up the Twilio WhatsApp Sandbox: https://www.twilio.com/docs/whatsapp/sandbox
                3. Add the following environment variables to your Replit Secrets:
                   - `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
                   - `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token
                   - `TWILIO_PHONE_NUMBER` - Your Twilio phone number (without the 'whatsapp:+' prefix)
                   - `NOTIFICATION_RECIPIENTS` - Comma-separated list of recipient phone numbers (with country code, e.g., 919876543210)
                4. Make sure recipients have joined your Twilio WhatsApp Sandbox by sending the join code to the Twilio number
                """)

def send_whatsapp_delay_notification(train_id, delay_minutes, station, from_to=None):
    """
    Send a WhatsApp notification for a train delay
    
    Args:
        train_id: The train ID
        delay_minutes: The delay in minutes
        station: The current station
        from_to: Optional from-to information
    """
    notifier = WhatsAppNotifier()
    if not notifier.is_configured:
        return False
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    from_to_info = f", {from_to}" if from_to else ""
    details = f"🚨 Train is *{delay_minutes} minutes late* at station {station}{from_to_info}.\nTime: {timestamp}"
    
    try:
        notifier._send_whatsapp_message(train_id, details)
        return True
    except Exception as e:
        logger.error(f"Error sending WhatsApp delay notification: {str(e)}")
        return False