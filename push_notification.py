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
            
            // Create notification container
            const container = document.createElement('div');
            container.id = 'app-notification-container';
            document.body.appendChild(container);
            
            // Check notification permission
            checkNotificationPermission();
            
            // Set up event handlers
            const enableBtn = document.getElementById('enable-notifications-btn');
            if (enableBtn) {
                enableBtn.addEventListener('click', requestNotificationPermission);
            }
            
            const testBtn = document.getElementById('test-notification-btn');
            if (testBtn) {
                testBtn.addEventListener('click', sendTestNotification);
            }
        });
        
        // Expose function to global scope
        window.showTrainNotification = showNotification;
        </script>
        """
    
    def render_notification_ui(self):
        """Render the notification UI component in Streamlit"""
        st.markdown("### Push Notifications")
        
        notification_container = st.container()
        
        with notification_container:
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("Get instant browser notifications when new trains are detected.")
            
            with col2:
                # Add a test notification button in Streamlit
                if st.button("Send Test Notification", help="Send a test browser notification"):
                    # This will trigger the JavaScript notification
                    st.session_state.show_test_notification = True
                    st.success("Test notification sent! Check the bottom-right corner of your screen.")
        
        # Add the HTML/JS for browser notification functionality
        notification_html = """
        <div class="browser-notification-container">
            <p id="notification-status">Checking notification status...</p>
            <button id="enable-notifications-btn" style="display:none;">
                Enable Notifications
            </button>
            <button id="test-notification-btn" style="display:none;">
                Send Test Notification
            </button>
        </div>
        
        <style>
        .browser-notification-container {
            margin: 1rem 0;
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f8f9fa;
        }
        
        #enable-notifications-btn, #test-notification-btn {
            margin-top: 0.5rem;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.25rem;
            cursor: pointer;
            font-weight: 500;
        }
        
        #enable-notifications-btn {
            background-color: #4CAF50;
            color: white;
        }
        
        #test-notification-btn {
            background-color: #2196F3;
            color: white;
        }
        </style>
        """
        
        # Add JavaScript to trigger test notification if button was clicked
        trigger_js = ""
        if st.session_state.get('show_test_notification', False):
            trigger_js = """
            <script>
                // Wait for notification functions to be loaded
                setTimeout(function() {
                    if (window.showTrainNotification) {
                        window.showTrainNotification(
                            'Test Train Notification',
                            'This is a test train notification. Notifications are working correctly!',
                            'success'
                        );
                        
                        // Show a delay notification example
                        setTimeout(function() {
                            window.showTrainNotification(
                                'Train 12760 Delayed',
                                'Train 12760 (HYB-TBM) is currently running 45 minutes late at GDR.',
                                'delay'
                            );
                        }, 1000);
                    }
                }, 1000);
            </script>
            """
            # Reset the flag
            st.session_state.show_test_notification = False
        
        # Combine HTML and JavaScript
        st.markdown(notification_html + self.get_browser_notification_js() + trigger_js, unsafe_allow_html=True)
    
    def notify_new_trains(self, current_trains, train_details=None):
        """
        Check for new trains and send browser notifications if any are found
        
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
            
            # Store notifications to be shown
            notifications = []
            
            for train in new_trains:
                # Construct message with details if available
                if train_details and train in train_details:
                    details = train_details[train]
                    message = f"New train {train} detected\n{details}\nTime: {timestamp}"
                else:
                    message = f"New train {train} detected\nTime: {timestamp}"
                
                logger.info(f"Would send push notification: {message}")
                
                # Add to notifications list (will be shown via JavaScript)
                notifications.append({
                    'title': f'New Train {train} Detected',
                    'message': details if (train_details and train in train_details) else f"New train at {timestamp}",
                    'type': 'info'
                })
            
            # Store in session state to be shown
            st.session_state.new_train_notifications = notifications
        else:
            logger.info("No new trains detected, no push notifications sent")
        
        return new_trains