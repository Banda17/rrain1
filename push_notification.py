import streamlit as st
import json
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PushNotifier:
    def __init__(self):
        """Initialize the push notification manager"""
        # Set up storage for subscription info
        os.makedirs('temp', exist_ok=True)
        self.subscription_file = 'temp/push_subscriptions.json'
        
        # Track known trains to avoid duplicate notifications
        if 'known_trains' not in st.session_state:
            self.load_known_trains()
    
    def load_known_trains(self):
        """Load the list of known trains from the persistent store"""
        try:
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
    
    def load_subscriptions(self):
        """Load push notification subscriptions from file"""
        try:
            if os.path.exists(self.subscription_file):
                with open(self.subscription_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading subscriptions: {str(e)}")
            return []
    
    def save_subscription(self, subscription_info):
        """Save a new push notification subscription"""
        try:
            subscriptions = self.load_subscriptions()
            
            # Check if this subscription already exists
            for sub in subscriptions:
                if sub.get('endpoint') == subscription_info.get('endpoint'):
                    # Subscription already exists
                    return True
            
            # Add the new subscription
            subscriptions.append(subscription_info)
            
            # Save to file
            with open(self.subscription_file, 'w') as f:
                json.dump(subscriptions, f)
            
            logger.info(f"Saved new push subscription, total subscribers: {len(subscriptions)}")
            return True
        except Exception as e:
            logger.error(f"Error saving subscription: {str(e)}")
            return False
    
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
    
    def get_push_notification_js(self):
        """Get the JavaScript code for push notifications"""
        return """
        <script>
        // Util function for base64 URL encoding
        function urlBase64ToUint8Array(base64String) {
            const padding = '='.repeat((4 - base64String.length % 4) % 4);
            const base64 = (base64String + padding)
                .replace(/-/g, '+')
                .replace(/_/g, '/');
            
            const rawData = window.atob(base64);
            const outputArray = new Uint8Array(rawData.length);
            
            for (let i = 0; i < rawData.length; ++i) {
                outputArray[i] = rawData.charCodeAt(i);
            }
            return outputArray;
        }

        // Check if service workers are supported
        if ('serviceWorker' in navigator) {
            // When the window is loaded, register service worker
            window.addEventListener('load', async () => {
                try {
                    const registration = await navigator.serviceWorker.register('/service-worker.js');
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                    
                    // Wait for the service worker to be ready
                    const ready = await navigator.serviceWorker.ready;
                    console.log('Service worker ready');
                    
                    // Set up UI controls after service worker is ready
                    setupPushControls(ready);
                } catch (error) {
                    console.error('ServiceWorker registration failed: ', error);
                    document.getElementById('notification-status').textContent = 
                        'Push notification setup failed: ' + error.message;
                }
            });
        } else {
            console.warn('Service workers not supported');
            document.getElementById('notification-status').textContent = 
                'Sorry, push notifications are not supported in your browser.';
        }
        
        // Handle the subscribe button
        async function subscribeUser(swRegistration) {
            try {
                // Application Server Public Key from your server
                const applicationServerPublicKey = 'BLBx85QoKM1QhvmOKzBJr5m2V0o5D9m0-F50xgOVl3YoqDRZ5mitgLLm2QUcDQl3dJlZOEpPpNE3hPnCok9nbY0';
                
                const applicationServerKey = urlBase64ToUint8Array(applicationServerPublicKey);
                
                const subscription = await swRegistration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: applicationServerKey
                });
                
                console.log('User is subscribed:', subscription);
                
                // Send subscription to server
                await saveSubscription(subscription);
                
                document.getElementById('notification-status').textContent = 
                    'You are now subscribed to push notifications for new trains!';
                    
                document.getElementById('push-subscribe-button').style.display = 'none';
                document.getElementById('push-unsubscribe-button').style.display = 'inline-block';
                document.getElementById('test-push-button').style.display = 'inline-block';
                
                return subscription;
            } catch (error) {
                console.error('Failed to subscribe the user: ', error);
                document.getElementById('notification-status').textContent = 
                    'Failed to subscribe. ' + error.message;
            }
        }
        
        // Save subscription info to your server
        async function saveSubscription(subscription) {
            const response = await fetch('/save-subscription/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(subscription)
            });
            
            return response.json();
        }
        
        // Handle unsubscribe action
        async function unsubscribeUser(swRegistration) {
            try {
                const subscription = await swRegistration.pushManager.getSubscription();
                
                if (subscription) {
                    await subscription.unsubscribe();
                    console.log('User is unsubscribed');
                    
                    document.getElementById('notification-status').textContent = 
                        'You are now unsubscribed from push notifications.';
                    
                    document.getElementById('push-subscribe-button').style.display = 'inline-block';
                    document.getElementById('push-unsubscribe-button').style.display = 'none';
                    document.getElementById('test-push-button').style.display = 'none';
                }
            } catch (error) {
                console.error('Error unsubscribing', error);
                document.getElementById('notification-status').textContent = 
                    'Error unsubscribing: ' + error.message;
            }
        }
        
        // Send a test notification
        async function sendTestNotification() {
            try {
                const response = await fetch('/test-push-notification/', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    document.getElementById('notification-status').textContent = 
                        'Test notification sent!';
                } else {
                    document.getElementById('notification-status').textContent = 
                        'Failed to send test notification. Check server logs.';
                }
            } catch (error) {
                console.error('Error sending test notification', error);
                document.getElementById('notification-status').textContent = 
                    'Error sending test notification: ' + error.message;
            }
        }
        
        // Set up the subscription status and controls
        async function setupPushControls(swRegistration) {
            try {
                const subscription = await swRegistration.pushManager.getSubscription();
                
                document.getElementById('notification-status').textContent = subscription ? 
                    'You are subscribed to push notifications for new trains.' :
                    'You are not subscribed to push notifications.';
                
                document.getElementById('push-subscribe-button').style.display = 
                    subscription ? 'none' : 'inline-block';
                    
                document.getElementById('push-unsubscribe-button').style.display = 
                    subscription ? 'inline-block' : 'none';
                    
                document.getElementById('test-push-button').style.display = 
                    subscription ? 'inline-block' : 'none';
                
                // Set up click handlers
                document.getElementById('push-subscribe-button').onclick = () => {
                    subscribeUser(swRegistration);
                };
                
                document.getElementById('push-unsubscribe-button').onclick = () => {
                    unsubscribeUser(swRegistration);
                };
                
                document.getElementById('test-push-button').onclick = () => {
                    sendTestNotification();
                };
            } catch (error) {
                console.error('Error setting up push controls', error);
            }
        }
        </script>
        """
    
    def render_notification_ui(self):
        """Render the notification UI component in Streamlit"""
        st.markdown("### Push Notifications")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("Get instant browser notifications when new trains are detected.")
        
        with col2:
            # Add a test notification button in Streamlit
            if st.button("Send Test Push Notification", help="Send a test browser notification"):
                st.success("Test notification sent! Check your browser.")
        
        # Add the HTML/JS for push notification functionality
        notification_html = """
        <div class="push-notification-container">
            <p id="notification-status">Checking notification status...</p>
            <button id="push-subscribe-button" style="display:none;">
                Enable Push Notifications
            </button>
            <button id="push-unsubscribe-button" style="display:none;">
                Disable Push Notifications
            </button>
            <button id="test-push-button" style="display:none;">
                Send Test Notification
            </button>
        </div>
        
        <style>
        .push-notification-container {
            margin: 1rem 0;
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f8f9fa;
        }
        
        #push-subscribe-button, #push-unsubscribe-button, #test-push-button {
            margin-top: 0.5rem;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.25rem;
            cursor: pointer;
            font-weight: 500;
        }
        
        #push-subscribe-button {
            background-color: #4CAF50;
            color: white;
        }
        
        #push-unsubscribe-button {
            background-color: #f44336;
            color: white;
        }
        
        #test-push-button {
            background-color: #2196F3;
            color: white;
            margin-left: 0.5rem;
        }
        </style>
        """
        
        # Combine HTML and JavaScript
        st.markdown(notification_html + self.get_push_notification_js(), unsafe_allow_html=True)
    
    def notify_new_trains(self, current_trains, train_details=None):
        """
        Check for new trains and send push notifications if any are found
        
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
            logger.info(f"New trains detected: {new_trains}")
            
            # In a real implementation, you would send the push notification here
            # For now, we'll just log that we would send a notification
            
            for train in new_trains:
                # Construct message with details if available
                if train_details and train in train_details:
                    details = train_details[train]
                    message = f"New train {train} detected\n{details}\nTime: {timestamp}"
                else:
                    message = f"New train {train} detected\nTime: {timestamp}"
                
                logger.info(f"Would send push notification: {message}")
        else:
            logger.info("No new trains detected, no push notifications sent")
        
        return new_trains