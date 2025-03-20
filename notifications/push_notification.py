import streamlit as st
import json
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add this flag to enable/disable debug messages
DEBUG = True

class PushNotifier:
    def __init__(self):
        """Initialize the push notification manager"""
        # Create necessary directories
        os.makedirs('temp', exist_ok=True)
        
        # Track known trains to avoid duplicate notifications
        if 'known_trains' not in st.session_state:
            self.load_known_trains()
            
        # Initialize notification settings in session state
        if 'notifications_enabled' not in st.session_state:
            st.session_state.notifications_enabled = False
            
        # Keep track of notifications to display
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
    
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
        if DEBUG:
            logger.info(f"Train numbers: {sorted(list(current_trains_set))}")
        
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
    
    def get_browser_notification_js(self):
        """Get the JavaScript code for browser notifications"""
        return """
        <script>
        // Check if browser notifications are supported
        let notificationsEnabled = false;
        
        // Function to check notification permission
        function checkNotificationPermission() {
            if (!('Notification' in window)) {
                // Browser doesn't support notifications
                document.getElementById('notification-status').textContent = 
                    'Browser notifications are not supported in your browser.';
                return false;
            }
            
            if (Notification.permission === 'granted') {
                document.getElementById('notification-status').textContent = 
                    'Notifications are enabled! You will be notified when new trains are detected.';
                document.getElementById('enable-notifications-btn').style.display = 'none';
                document.getElementById('test-notification-btn').style.display = 'inline-block';
                return true;
            } else if (Notification.permission === 'denied') {
                document.getElementById('notification-status').textContent = 
                    'Notification permission was denied. Please enable notifications in your browser settings.';
                document.getElementById('enable-notifications-btn').style.display = 'inline-block';
                document.getElementById('test-notification-btn').style.display = 'none';
                return false;
            } else {
                document.getElementById('notification-status').textContent = 
                    'Click the button below to enable train notifications.';
                document.getElementById('enable-notifications-btn').style.display = 'inline-block';
                document.getElementById('test-notification-btn').style.display = 'none';
                return false;
            }
        }
        
        // Function to request notification permission
        async function requestNotificationPermission() {
            if (!('Notification' in window)) {
                alert('This browser does not support desktop notifications');
                return;
            }
            
            try {
                const permission = await Notification.requestPermission();
                if (permission === 'granted') {
                    document.getElementById('notification-status').textContent = 
                        'Notifications are now enabled! You will be notified when new trains are detected.';
                    document.getElementById('enable-notifications-btn').style.display = 'none';
                    document.getElementById('test-notification-btn').style.display = 'inline-block';
                    
                    // Send status to Streamlit
                    notificationsEnabled = true;
                    
                    // Show a welcome notification
                    showNotification(
                        'Train Notifications Enabled',
                        'You will now receive notifications when new trains are detected.',
                        'success'
                    );
                    
                    return true;
                } else {
                    document.getElementById('notification-status').textContent = 
                        'Notification permission was not granted.';
                    return false;
                }
            } catch (error) {
                console.error('Error requesting notification permission:', error);
                document.getElementById('notification-status').textContent = 
                    'Error requesting notification permission: ' + error.message;
                return false;
            }
        }
        
        // Function to show a browser notification
        function showNotification(title, body, type = 'info') {
            if (!('Notification' in window)) {
                console.warn('This browser does not support desktop notifications');
                return;
            }
            
            if (Notification.permission === 'granted') {
                // Get icon based on type
                let icon = '';
                switch(type) {
                    case 'success':
                        icon = 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Eo_circle_green_checkmark.svg/1200px-Eo_circle_green_checkmark.svg.png';
                        break;
                    case 'warning':
                        icon = 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/Eo_circle_orange_exclamation-point.svg/1200px-Eo_circle_orange_exclamation-point.svg.png';
                        break;
                    case 'error':
                        icon = 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Eo_circle_red_letter-x.svg/1200px-Eo_circle_red_letter-x.svg.png';
                        break;
                    case 'delay':
                        icon = 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Flat_cross_icon.svg/1200px-Flat_cross_icon.svg.png';
                        break;
                    default:
                        icon = 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Eo_circle_blue_letter-i.svg/1200px-Eo_circle_blue_letter-i.svg.png';
                }
                
                // Create and show the notification
                const options = {
                    body: body,
                    icon: icon,
                    silent: false
                };
                
                const notification = new Notification(title, options);
                
                // Close the notification after 5 seconds
                setTimeout(() => notification.close(), 5000);
                
                // Focus the window when clicked
                notification.onclick = function() {
                    window.focus();
                    notification.close();
                };
                
                // Also show in-app notification
                showAppNotification(title, body, type);
                
                return true;
            } else {
                console.warn('Notification permission not granted');
                
                // Still show in-app notification
                showAppNotification(title, body, type);
                
                return false;
            }
        }
        
        // Function to show in-app notification
        function showAppNotification(title, message, type = 'info') {
            // Create notification element
            const notification = document.createElement('div');
            notification.className = 'app-notification app-notification-' + type;
            
            // Add icon based on type
            let iconHtml = '';
            switch(type) {
                case 'success':
                    iconHtml = '<span class="notification-icon">✅</span>';
                    break;
                case 'warning':
                    iconHtml = '<span class="notification-icon">⚠️</span>';
                    break;
                case 'error':
                    iconHtml = '<span class="notification-icon">❌</span>';
                    break;
                case 'delay':
                    iconHtml = '<span class="notification-icon">🔴</span>';
                    break;
                default:
                    iconHtml = '<span class="notification-icon">ℹ️</span>';
            }
            
            // Create content
            notification.innerHTML = `
                ${iconHtml}
                <div class="notification-content">
                    <h4>${title}</h4>
                    <p>${message}</p>
                </div>
                <button class="notification-close">&times;</button>
            `;
            
            // Get or create notification container
            let container = document.getElementById('app-notification-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'app-notification-container';
                document.body.appendChild(container);
            }
            
            // Add notification to container
            container.appendChild(notification);
            
            // Add close button functionality
            const closeBtn = notification.querySelector('.notification-close');
            closeBtn.addEventListener('click', function() {
                notification.classList.add('closing');
                setTimeout(function() {
                    notification.remove();
                }, 300);
            });
            
            // Auto-remove after 5 seconds
            setTimeout(function() {
                notification.classList.add('closing');
                setTimeout(function() {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }, 5000);
        }
        
        // Function to send test notification
        function sendTestNotification() {
            showNotification(
                'Test Train Notification',
                'This is a test train notification. Notifications are working correctly!',
                'success'
            );
            
            showNotification(
                'Train 12760 Delayed',
                'Train 12760 (HYB-TBM) is currently running 45 minutes late at GDR.',
                'delay'
            );
        }
        
        // Initialize notification system
        document.addEventListener('DOMContentLoaded', function() {
            // Create notification container styles
            const style = document.createElement('style');
            style.textContent = `
                #app-notification-container {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 9999;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    max-width: 350px;
                }
                
                .app-notification {
                    display: flex;
                    align-items: flex-start;
                    background-color: white;
                    border-left: 4px solid #1E88E5;
                    border-radius: 4px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 12px;
                    margin-bottom: 10px;
                    animation: slide-in 0.3s ease;
                    max-width: 350px;
                    overflow: hidden;
                }
                
                .app-notification-info {
                    border-left-color: #1E88E5;
                }
                
                .app-notification-success {
                    border-left-color: #43A047;
                }
                
                .app-notification-warning {
                    border-left-color: #FB8C00;
                }
                
                .app-notification-error, .app-notification-delay {
                    border-left-color: #E53935;
                }
                
                .app-notification.closing {
                    animation: slide-out 0.3s ease forwards;
                }
                
                .notification-icon {
                    margin-right: 12px;
                    font-size: 20px;
                }
                
                .notification-content {
                    flex: 1;
                }
                
                .notification-content h4 {
                    margin: 0 0 4px 0;
                    font-size: 16px;
                    font-weight: 600;
                }
                
                .notification-content p {
                    margin: 0;
                    font-size: 14px;
                    color: #666;
                }
                
                .notification-close {
                    background: none;
                    border: none;
                    color: #999;
                    cursor: pointer;
                    font-size: 18px;
                    padding: 0;
                    margin-left: 8px;
                }
                
                @keyframes slide-in {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                @keyframes slide-out {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
            
            // Check notification permission status
            setTimeout(function() {
                // Will run after elements are created by Streamlit
                const statusElement = document.getElementById('notification-status');
                const enableButton = document.getElementById('enable-notifications-btn');
                const testButton = document.getElementById('test-notification-btn');
                
                if (statusElement && enableButton && testButton) {
                    if (checkNotificationPermission()) {
                        notificationsEnabled = true;
                    }
                }
            }, 1000);
        });
        
        // Make showNotification available globally
        window.showTrainNotification = showNotification;
        </script>
        """
    
    def render_notification_ui(self):
        """Render the notification UI component in Streamlit"""
        st.markdown("<h3>Browser Notifications</h3>", unsafe_allow_html=True)
        
        # Add notification permission status display
        st.markdown('<div id="notification-status">Checking notification permission status...</div>', unsafe_allow_html=True)
        
        # Add buttons for enabling and testing notifications
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <button id="enable-notifications-btn" class="stButton" onclick="requestNotificationPermission()" style="display:none;">
                Enable Push Notifications
            </button>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <button id="test-notification-btn" class="stButton" onclick="sendTestNotification()" style="display:none;">
                Test Notification
            </button>
            """, unsafe_allow_html=True)
        
        # Add the notification system JavaScript
        st.markdown(self.get_browser_notification_js(), unsafe_allow_html=True)
    
    def notify_new_trains(self, current_trains, train_details=None):
        """
        Check for new trains and send browser notifications if any are found
        
        Args:
            current_trains: List of current train IDs
            train_details: Optional dictionary mapping train IDs to additional info
            
        Returns:
            List of new train IDs
        """
        # Check for new trains
        new_trains = self.check_for_new_trains(current_trains)
        
        # Log notification event
        if new_trains:
            logger.info(f"Sending push notifications for {len(new_trains)} new trains")
            
            # Send browser notifications for each new train
            if st.session_state.notifications_enabled and len(new_trains) > 0:
                for train_id in new_trains:
                    # Get train details if available
                    train_info = ""
                    if train_details and train_id in train_details:
                        train_name = train_details[train_id].get('Train Name', '')
                        from_to = train_details[train_id].get('FROM-TO', '')
                        if train_name and from_to:
                            train_info = f"{train_name} ({from_to})"
                        elif train_name:
                            train_info = train_name
                        elif from_to:
                            train_info = from_to
                    
                    # Add notification to queue
                    notification = {
                        'title': f"New Train: {train_id}",
                        'message': f"New train {train_id} {train_info} detected in the system.",
                        'type': 'success',
                        'timestamp': datetime.now().isoformat()
                    }
                    st.session_state.notifications.append(notification)
            
            # If Telegram notifier is available in session state, use it for notifications
            if 'telegram_notifier' in st.session_state and st.session_state.telegram_notifier.is_configured:
                try:
                    st.session_state.telegram_notifier.notify_multiple_new_trains(new_trains, train_details)
                except Exception as e:
                    logger.error(f"Error sending Telegram notifications: {str(e)}")
        
        return new_trains