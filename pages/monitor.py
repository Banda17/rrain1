import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import io
import os
import re
import json
import logging
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp
from notifications import PushNotifier, WhatsAppNotifier, send_whatsapp_delay_notification

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration - MUST be the first Streamlit command
st.set_page_config(
    page_title="Monitor - Train Tracking System",
    page_icon="📊",
    layout="wide"
)

# URL for the Google Sheets data
MONITOR_DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=615508228&single=true&output=csv"

# Custom CSS for styling
st.markdown("""
<style>
/* Main container styling */
.main-container {
    padding: 1rem;
    background-color: #f5f5f5;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin-bottom: 1rem;
}

/* Red delay notification card styles */
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
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
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
    background-color: #ffebee;
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

/* Monitor section styling */
.monitor-container {
    margin-top: 1.5rem;
    background-color: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.monitor-title {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: #2c3e50;
    text-align: center;
    padding: 5px;
    background-color: #f8f9fa;
    border-radius: 4px;
}

.monitor-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.5rem;
    font-size: 14px;
}

.monitor-table th {
    background-color: #1E3A8A;
    color: white;
    text-align: center;
    padding: 10px;
    border: 1px solid black;
    font-weight: bold;
    text-transform: uppercase;
}

.monitor-table td {
    text-align: center;
    padding: 8px;
    border: 1px solid black;
}

/* Status indicators */
.status-normal {
    background-color: #e8f5e9;
    color: #2e7d32;
    font-weight: bold;
}

.status-warning {
    background-color: #fff9c4;
    color: #ff6f00;
    font-weight: bold;
}

.status-critical {
    background-color: #ffebee;
    color: #c62828;
    font-weight: bold;
}

/* Alert styling */
.alert {
    padding: 12px;
    border-radius: 4px;
    margin: 10px 0;
    font-size: 14px;
}

.alert-info {
    background-color: #e8f4f8;
    color: #0c5460;
    border: 1px solid #bee5eb;
}

/* Last refresh timestamp */
.refresh-timestamp {
    font-size: 12px;
    color: #666;
    text-align: right;
    margin-top: 0.5rem;
}

/* Train Details Table Styling */
.train-details-container {
    margin-top: 2rem;
    background-color: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.train-details-title {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: #2c3e50;
    text-align: center;
    padding: 5px;
    background-color: #f8f9fa;
    border-radius: 4px;
}

.train-details-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.5rem;
    font-size: 14px;
}

.train-details-table th {
    background-color: #1E3A8A;
    color: white;
    padding: 10px;
    text-align: center;
    border: 1px solid black;
    font-weight: bold;
    text-transform: uppercase;
}

.train-details-table td {
    text-align: center;
    padding: 8px;
    border: 1px solid black;
    vertical-align: middle;
}

.highlight-cell {
    background-color: #ffff00;
    font-weight: bold;
}

.train-number {
    font-weight: bold;
}

.station-code {
    font-weight: bold;
    color: #004d40;
}

.time-value {
    color: #01579b;
}

.delay-value {
    font-weight: bold;
    color: #b71c1c;
}
</style>
""", unsafe_allow_html=True)

# Page title and info
st.title("Monitor Data View")
st.write("This page displays monitoring data from Google Sheets.")

# Function to fetch data directly from a spreadsheet URL
@st.cache_data(ttl=300, show_spinner=False)
def fetch_sheet_data(url):
    try:
        # Use requests to get data with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Load into pandas
        df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
        
        # Save to cache file for offline use
        try:
            os.makedirs("temp", exist_ok=True)
            with open("temp/cached_monitor.csv", "w", newline='', encoding='utf-8') as f:
                f.write(response.content.decode('utf-8'))
        except Exception as e:
            st.warning(f"Failed to cache monitor data: {str(e)}")
            
        return df, True
    except Exception as e:
        st.error(f"Error fetching data from {url}: {str(e)}")
        
        # Try to load from cached file if available
        try:
            if os.path.exists("temp/cached_monitor.csv"):
                st.warning("Using cached data (offline mode)")
                df = pd.read_csv("temp/cached_monitor.csv")
                return df, True
        except Exception as cache_error:
            st.error(f"Failed to load cached data: {str(cache_error)}")
            
        return pd.DataFrame(), False

# Create a placeholder for the refresh animation
refresh_placeholder = st.empty()

# Set refreshing state to True and show animation
if 'is_refreshing' not in st.session_state:
    st.session_state['is_refreshing'] = True
    
create_pulsing_refresh_animation(refresh_placeholder, "Fetching monitoring data from Google Sheets...")

# Fetch monitor data
st.info("Fetching monitoring data...")
monitor_raw_data, monitor_success = fetch_sheet_data(MONITOR_DATA_URL)

# Remove the first row if the data was successfully fetched
if monitor_success and not monitor_raw_data.empty and len(monitor_raw_data) > 1:
    # Skip the first row which is typically a header/summary row
    monitor_raw_data = monitor_raw_data.iloc[1:].reset_index(drop=True)

# Clear the refresh animation when done
st.session_state['is_refreshing'] = False
refresh_placeholder.empty()

# Function to safely convert values
def safe_convert(value):
    """
    Safely convert values to strings handling NaN, None, undefined, and empty values consistently.
    
    Args:
        value: The value to convert
        
    Returns:
        String representation, dash for undefined, or empty string for null values
    """
    if pd.isna(value) or pd.isnull(value) or str(value).lower() == 'nan' or value is None:
        return ""
    
    # Convert to string and handle empty strings
    string_val = str(value).strip()
    if not string_val:
        return ""
    
    # Replace undefined values with dash wherever they appear in the string
    if 'undefined' in string_val.lower():
        return string_val.replace('undefined', '-').replace('Undefined', '-')
        
    return string_val

# Process and display monitor data
if monitor_success and not monitor_raw_data.empty:
    st.success(f"Successfully loaded monitoring data with {len(monitor_raw_data)} rows")
    
    # Apply safe conversion to all elements
    for col in monitor_raw_data.columns:
        monitor_raw_data[col] = monitor_raw_data[col].map(safe_convert)
        
    # Replace any 'undefined' values with a dash
    monitor_raw_data = monitor_raw_data.replace('undefined', '-')
    monitor_raw_data = monitor_raw_data.replace('Undefined', '-')
    
    # Notification settings section
    st.write("### Notification Settings")
    
    # Create tabs for different notification types
    browser_tab, whatsapp_tab = st.tabs(["Browser Notifications", "WhatsApp Notifications"])
    
    with browser_tab:
        # Initialize push notifier
        push_notifier = PushNotifier()
        
        # Create columns for notification controls
        col1, col2 = st.columns(2)
        
        with col1:
            # Add option to reset known trains
            if st.button("Reset Known Trains", type="primary", help="Clear the list of known trains to receive notifications for all trains again"):
                # Clear the session state and file
                if "known_trains" in st.session_state:
                    st.session_state.known_trains = set()
                try:
                    if os.path.exists('temp/known_trains.json'):
                        os.remove('temp/known_trains.json')
                    st.success("Known trains list has been reset. You will receive notifications for all trains again.")
                except Exception as e:
                    st.error(f"Error resetting known trains: {str(e)}")
            
            # Display current known trains count
            try:
                known_trains = set()
                if os.path.exists('temp/known_trains.json'):
                    with open('temp/known_trains.json', 'r') as f:
                        known_trains = set(json.load(f))
                st.info(f"Currently tracking {len(known_trains)} known trains")
            except Exception as e:
                st.warning(f"Could not read known trains: {str(e)}")
        
        with col2:
            # Add test notification button
            if st.button("Test Red Delay Card", type="secondary", help="Show a sample train delay notification card"):
                st.session_state.show_test_delay_card = True
                st.success("Test notification sent! Check for red delay card in the bottom-right corner.")
            
            # JavaScript to show test notification when button is clicked
            if st.session_state.get('show_test_delay_card', False):
                st.markdown("""
                <script>
                    // Wait for DOM to be ready
                    document.addEventListener('DOMContentLoaded', function() {
                        // Create notification container if it doesn't exist
                        if (!document.getElementById('app-notification-container')) {
                            const container = document.createElement('div');
                            container.id = 'app-notification-container';
                            document.body.appendChild(container);
                        }
                        
                        // Create and show a delay notification
                        setTimeout(function() {
                            // Create notification element
                            const notification = document.createElement('div');
                            notification.className = 'app-notification app-notification-delay';
                            
                            // Add content
                            notification.innerHTML = `
                                <span class="notification-icon">🔴</span>
                                <div class="notification-content">
                                    <h4>Train 12760 Delayed</h4>
                                    <p>Train 12760 (HYB-TBM) is currently running 45 minutes late at GDR.</p>
                                </div>
                                <button class="notification-close">&times;</button>
                            `;
                            
                            // Add to container
                            const container = document.getElementById('app-notification-container');
                            container.appendChild(notification);
                            
                            // Add close button functionality
                            const closeBtn = notification.querySelector('.notification-close');
                            closeBtn.addEventListener('click', function() {
                                notification.classList.add('closing');
                                setTimeout(function() {
                                    notification.remove();
                                }, 300);
                            });
                            
                            // Auto-remove after 10 seconds
                            setTimeout(function() {
                                notification.classList.add('closing');
                                setTimeout(function() {
                                    notification.remove();
                                }, 300);
                            }, 10000);
                        }, 1000);
                    });
                </script>
                """, unsafe_allow_html=True)
                
                # Reset the flag
                st.session_state.show_test_delay_card = False
        
        # Render the push notification UI
        push_notifier.render_notification_ui()
    
    # WhatsApp notifications tab
    with whatsapp_tab:
        # Initialize WhatsApp notifier
        whatsapp_notifier = WhatsAppNotifier()
        
        # Render WhatsApp notification settings UI
        whatsapp_notifier.render_whatsapp_settings_ui()
        
        # Add a button to test WhatsApp delay notification
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Test WhatsApp Delay Alert", type="primary"):
                if whatsapp_notifier.is_configured:
                    # Use sample data for test
                    test_train = "12760"
                    test_delay = 45
                    test_station = "VJA"
                    test_route = "HYB-TBM"
                    
                    # Send test notification
                    logger.info(f"Sending test WhatsApp delay notification for train {test_train}")
                    success = send_whatsapp_delay_notification(test_train, test_delay, test_station, test_route)
                    
                    if success:
                        st.success("Test WhatsApp delay alert sent! Check your WhatsApp.")
                    else:
                        st.error("Failed to send test WhatsApp alert. Check configuration.")
                else:
                    st.error("WhatsApp is not configured. Please set up Twilio first.")
        
        with col2:
            if st.button("Reset WhatsApp Known Trains", type="secondary"):
                try:
                    if os.path.exists('temp/known_trains_whatsapp.json'):
                        os.remove('temp/known_trains_whatsapp.json')
                    whatsapp_notifier.known_trains = set()
                    whatsapp_notifier.save_known_trains(set())
                    st.success("WhatsApp known trains list has been reset. You will receive new train notifications for all trains again.")
                except Exception as e:
                    st.error(f"Error resetting WhatsApp known trains: {str(e)}")
        
        st.divider()
        
        st.markdown("""
        ### WhatsApp Notification Features
        - Receive real-time WhatsApp messages when new trains are detected
        - Get delay alerts directly to your phone
        - No app installation required - works with any WhatsApp account
        - Messages include train details and delay information
        
        To enable WhatsApp notifications, you need a Twilio account with WhatsApp Sandbox enabled.
        """)
        
        # Add help guide
        with st.expander("How to Set Up Twilio for WhatsApp"):
            st.markdown("""
            1. Create a Twilio account at [twilio.com](https://www.twilio.com/)
            2. Navigate to the Messaging section and select "Try WhatsApp"
            3. Set up the WhatsApp Sandbox
            4. Add your phone number to the Sandbox by sending the join code to the Twilio number
            5. Copy your Account SID and Auth Token from the Twilio Console
            6. Add these values as secrets in your Replit environment:
               - TWILIO_ACCOUNT_SID
               - TWILIO_AUTH_TOKEN
               - TWILIO_PHONE_NUMBER (without the 'whatsapp:+' prefix)
               - NOTIFICATION_RECIPIENTS (comma-separated list of phone numbers with country code, e.g., 919876543210)
            """)
            
            st.warning("Important: WhatsApp messages will only be sent when new trains are detected or significant delays occur.")
    
    # Extract train numbers for push notifications
    train_numbers = []
    train_details = {}
    train_column = None
    
    # Try to find the train number column
    possible_train_columns = ['Train No.', 'Train No', 'Train Number', 'TrainNo', 'Train']
    for col in possible_train_columns:
        if col in monitor_raw_data.columns:
            train_column = col
            break
    
    # Extract train numbers if column found
    if train_column:
        train_numbers = [str(train_no).strip() for train_no in monitor_raw_data[train_column] if str(train_no).strip()]
        
        # Create train details dictionary
        for _, row in monitor_raw_data.iterrows():
            train_no = str(row[train_column]).strip()
            if train_no:
                details = {}
                for col in monitor_raw_data.columns:
                    if col != train_column and not pd.isna(row[col]):
                        details[col] = row[col]
                train_details[train_no] = ", ".join([f"{k}: {v}" for k, v in details.items() if v])
    
    # Check for new trains and send push notifications
    if train_numbers:
        # Initialize push notifier for browser notifications
        push_notifier = PushNotifier()
        
        # Initialize WhatsApp notifier
        whatsapp_notifier = WhatsAppNotifier()
        
        # Check for new trains and send browser notifications
        new_trains = push_notifier.notify_new_trains(train_numbers, train_details)
        
        # Check for new trains and send WhatsApp notifications
        new_trains_whatsapp = whatsapp_notifier.notify_new_trains(train_numbers, train_details)
        
        # Combine results for display
        all_new_trains = list(set(new_trains + new_trains_whatsapp))
        
        if all_new_trains:
            st.success(f"Detected {len(all_new_trains)} new trains: {', '.join(all_new_trains)}")
            
            # Add JavaScript to trigger browser notifications
            if new_trains:
                js_code = """
                <script>
                // Wait for notification system to initialize
                setTimeout(function() {
                    if (window.showTrainNotification) {
                """
                
                # Add code for each notification
                for train in new_trains:
                    train_detail = train_details.get(train, "New train detected")
                    js_code += f"""
                        window.showTrainNotification(
                            'New Train {train} Detected',
                            '{train_detail}',
                            'delay'
                        );
                    """
                
                js_code += """
                    }
                }, 1000);
                </script>
                """
                
                # Output JavaScript
                st.markdown(js_code, unsafe_allow_html=True)
                
                notification_methods = []
                if new_trains:
                    notification_methods.append("browser")
                if new_trains_whatsapp:
                    notification_methods.append("WhatsApp")
                
                if notification_methods:
                    st.info(f"Notifications sent via {' and '.join(notification_methods)}!")
            
            # Check for delay notifications
            delay_threshold = 30  # Minutes of delay to trigger notification
            
            # Find 'Delay' column if it exists
            delay_column = None
            for col in monitor_raw_data.columns:
                if 'delay' in col.lower():
                    delay_column = col
                    break
            
            # If we have a delay column, check for significant delays
            if delay_column and train_column:
                for _, row in monitor_raw_data.iterrows():
                    try:
                        # Extract train number and delay value
                        train_no = str(row[train_column]).strip()
                        delay_str = str(row[delay_column]).strip()
                        
                        # Parse delay value
                        delay_minutes = None
                        if delay_str and delay_str != '-':
                            # Remove non-numeric characters except minus sign
                            clean_delay = ''.join(c for c in delay_str if c.isdigit() or c == '-')
                            if clean_delay:
                                try:
                                    delay_minutes = int(clean_delay)
                                except ValueError:
                                    # Try to extract the first number
                                    import re
                                    match = re.search(r'-?\d+', delay_str)
                                    if match:
                                        delay_minutes = int(match.group())
                        
                        # Check if delay exceeds threshold
                        if delay_minutes and delay_minutes >= delay_threshold:
                            # Get station name
                            station = row.get('Station', '')
                            
                            # Check if from-to column exists
                            from_to = None
                            for col in monitor_raw_data.columns:
                                if 'from' in col.lower() and 'to' in col.lower():
                                    from_to = row.get(col, '')
                                    break
                            
                            # Log the delay notification being sent
                            logger.info(f"Sending WhatsApp delay notification for train {train_no} with delay {delay_minutes} minutes at {station}")
                            
                            # Send WhatsApp notification for significant delay
                            send_whatsapp_delay_notification(train_no, delay_minutes, station, from_to)
                    except Exception as e:
                        logger.error(f"Error checking for delay notification: {str(e)}")
        else:
            st.info("No new trains detected, no notifications sent.")
    
    # Display the data in a styled HTML table
    st.markdown('<div class="monitor-container"><div class="monitor-title">Monitoring Data</div>', unsafe_allow_html=True)
    
    # Convert DataFrame to HTML table with styling
    html_table = '<table class="monitor-table">'
    
    # Add custom header row with the specified column names inside thead
    html_table += '<thead><tr>'
    html_table += '<th>S.No</th>'  # Add serial number column
    html_table += '<th>STN</th>'
    html_table += '<th>Time Sch - Act</th>'
    html_table += '<th>Delay(Mins.)</th>'
    
    # Add any remaining columns if needed
    remaining_cols = len(monitor_raw_data.columns) - 3
    if remaining_cols > 0:
        for i in range(remaining_cols):
            col_name = monitor_raw_data.columns[i+3] if i+3 < len(monitor_raw_data.columns) else f"Column {i+4}"
            html_table += f'<th>{col_name}</th>'
    
    html_table += '</tr></thead>'
    
    # Add data rows inside tbody
    html_table += '<tbody>'
    for index, (_, row) in enumerate(monitor_raw_data.iterrows(), 1):
        html_table += '<tr>'
        
        # Add serial number cell
        html_table += f'<td style="font-weight: bold; text-align: center;">{index}</td>'
        
        # Add rest of the cells
        for col in monitor_raw_data.columns:
            cell_value = row[col]
            
            # Replace any 'undefined' values with a dash at cell level
            if 'undefined' in str(cell_value).lower():
                cell_value = str(cell_value).replace('undefined', '-').replace('Undefined', '-')
                
            # Apply status styling if the column contains status-related information
            # This is a heuristic based on column name and cell value
            if 'status' in col.lower() or 'state' in col.lower():
                if cell_value.lower() in ['normal', 'ok', 'good', 'active']:
                    html_table += f'<td class="status-normal">{cell_value}</td>'
                elif cell_value.lower() in ['warning', 'alert', 'caution']:
                    html_table += f'<td class="status-warning">{cell_value}</td>'
                elif cell_value.lower() in ['critical', 'error', 'down', 'inactive']:
                    html_table += f'<td class="status-critical">{cell_value}</td>'
                else:
                    html_table += f'<td>{cell_value}</td>'
            else:
                html_table += f'<td>{cell_value}</td>'
        html_table += '</tr>'
    
    html_table += '</tbody></table>'
    
    # Display the HTML table
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Display additional information about the data
    with st.expander("View Raw Data"):
        st.dataframe(monitor_raw_data)
    
    # Show last refresh timestamp
    refresh_time = datetime.now()
    show_refresh_timestamp(refresh_time)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Extra information section
    with st.expander("Additional Information"):
        st.write("This page monitors train data and sends notifications through multiple channels.")
        
        # Notification channels
        st.markdown("#### Multi-Channel Notification Features")
        
        # Create tabs for different notification types
        browser_info, whatsapp_info = st.tabs(["Browser Notifications", "WhatsApp Notifications"])
        
        with browser_info:
            st.markdown("""
            - Receive real-time browser notifications when new trains are detected
            - No app installation required - works in modern browsers
            - Notifications work even when the browser is in the background
            - Click on notifications to open the monitor page directly
            """)
            
            # Show usage instructions
            st.markdown("#### How to Enable Browser Notifications")
            st.markdown("""
            1. Click on the 'Enable Push Notifications' button in the notification settings section
            2. Allow notifications when prompted by your browser
            3. You will now receive notifications when new trains are detected
            """)
            
            # Technical details
            st.markdown("#### Technical Details")
            st.markdown("""
            Browser notifications use the Web Push API and Service Workers to deliver messages 
            directly to your browser. Your subscription is stored securely and no personal 
            information is collected.
            """)
            
            # Note about notification format
            st.markdown("#### Browser Notification Format Example")
            st.code("New train 12760 detected\nFROM-TO: HYB-TBM, Station: KI, Delay: -6 mins\nTime: 2023-06-15 14:30:45")
        
        with whatsapp_info:
            st.markdown("""
            - Receive WhatsApp messages for new trains and significant delays
            - Get alerts directly on your mobile phone
            - No special app required - uses your regular WhatsApp
            - Messages include detailed train information and delay status
            - Configured to send alerts only for delays of 30 minutes or more
            """)
            
            # Show usage instructions
            st.markdown("#### How to Enable WhatsApp Notifications")
            st.markdown("""
            1. Create a Twilio account with WhatsApp Sandbox
            2. Join the Sandbox by sending the join code to the Twilio WhatsApp number
            3. Add your Twilio credentials as secrets in Replit
            4. Add your phone number to the NOTIFICATION_RECIPIENTS list
            5. Test the configuration using the "Test WhatsApp Message" button
            """)
            
            # Technical details
            st.markdown("#### WhatsApp Integration")
            st.markdown("""
            WhatsApp notifications are powered by Twilio's API, which provides secure and reliable
            messaging capabilities. The system is configured to send WhatsApp alerts for:
            
            1. New trains detected in the monitoring data
            2. Significant delays (30+ minutes) for any tracked train
            
            Each notification is formatted with emojis and formatted text to clearly display the
            relevant train information.
            """)
            
            # Note about notification format
            st.markdown("#### WhatsApp Notification Format Examples")
            st.code("""🚆 *New train 12760 detected*

FROM: HYB, TO: TBM, Station: VJA
Time: 2023-06-15 14:30:45
            """)
            
            st.code("""🚨 Train is *45 minutes late* at station VJA, HYB-TBM.
Time: 2023-06-15 14:30:45
            """)
    
    # Set up auto-refresh after 5 minutes (300 seconds)
    st.markdown("""
    <div class="alert alert-info">
        Data will automatically refresh every 5 minutes. Last refreshed at: {}
    </div>
    """.format(refresh_time.strftime('%Y-%m-%d %H:%M:%S')), unsafe_allow_html=True)
    
    # Add a manual refresh button
    if st.button("Refresh Data Now"):
        st.experimental_rerun()
    
    # Set up auto-refresh with JavaScript
    st.markdown("""
    <script>
        // Auto-refresh the page every 5 minutes (300000 milliseconds)
        setTimeout(function() {
            window.location.reload();
        }, 300000);
    </script>
    """, unsafe_allow_html=True)
    
else:
    st.error("Failed to load monitoring data.")
    
    # Create a simple alert box explaining the issue
    st.markdown("""
    <div class="alert alert-info">
        <strong>Connection Issue:</strong> Unable to fetch monitoring data from Google Sheets. 
        Possible reasons:
        <ul>
            <li>Network connectivity issue</li>
            <li>Google Sheets URL is incorrect or inaccessible</li>
            <li>The sheet might be private or restricted</li>
        </ul>
        Please check your connection and try again. If the issue persists, contact the system administrator.
    </div>
    """, unsafe_allow_html=True)
    
    # Add a retry button
    if st.button("Retry Connection"):
        st.experimental_rerun()