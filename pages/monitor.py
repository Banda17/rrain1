import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import io
import os
import re
import json
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp
from whatsapp_notifier import WhatsAppNotifier

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
    st.info(f"Removed the first line from the data, now showing {len(monitor_raw_data)} entries")

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
    # Log original count
    original_row_count = len(monitor_raw_data)
    
    # Try to find the train number column
    train_column = None
    possible_train_columns = ['Train No.', 'Train No', 'Train Number', 'TrainNo', 'Train']
    for col in possible_train_columns:
        if col in monitor_raw_data.columns:
            train_column = col
            break
    
    if train_column:
        # Remove duplicates based on train number column
        monitor_raw_data = monitor_raw_data.drop_duplicates(subset=[train_column], keep='first')
        
        # Report the duplicate removal result
        removed_count = original_row_count - len(monitor_raw_data)
        if removed_count > 0:
            st.success(f"Successfully loaded monitoring data: Removed {removed_count} duplicate trains (from {original_row_count} to {len(monitor_raw_data)} rows)")
        else:
            st.success(f"Successfully loaded monitoring data with {len(monitor_raw_data)} rows (no duplicates found)")
    else:
        st.success(f"Successfully loaded monitoring data with {len(monitor_raw_data)} rows")
    
    # Apply safe conversion to all elements
    for col in monitor_raw_data.columns:
        monitor_raw_data[col] = monitor_raw_data[col].map(safe_convert)
        
    # Replace any 'undefined' values with a dash
    monitor_raw_data = monitor_raw_data.replace('undefined', '-')
    monitor_raw_data = monitor_raw_data.replace('Undefined', '-')
    
    # Show a section for WhatsApp notification settings
    with st.expander("WhatsApp Notification Settings", expanded=False):
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
            # Add option to toggle message format
            st.write("Notification Format:")
            use_new_format = st.checkbox("Use compact format", 
                                        value=st.session_state.get('use_new_format', True),
                                        help="Example: '12760 HYB-TBM, T/O - KI (-6 mins)'")
            st.session_state.use_new_format = use_new_format
            
            if use_new_format:
                st.success("Using compact WhatsApp format")
            else:
                st.info("Using standard WhatsApp format")
        
        # Add testing section
        st.markdown("---")
        st.subheader("Test WhatsApp Notification")
        
        test_col1, test_col2 = st.columns(2)
        
        with test_col1:
            # Add a test input field for train number
            test_train_number = st.text_input("Test Train Number", value="12760", help="Enter a train number to test the notification")
            test_from_to = st.text_input("Test From-To", value="HYB-TBM", help="Enter a From-To station pair")
            test_event = st.selectbox("Test Event", ["T/O", "H/O", "Arrived"], help="Select an event type")
            test_station = st.text_input("Test Station", value="KI", help="Enter a station code")
            test_delay = st.number_input("Test Delay (mins)", value=-6, help="Enter a delay value in minutes")
            
        with test_col2:
            # Add some explanation text
            st.markdown("""
            This section allows you to test the WhatsApp notification system without waiting for new trains.
            
            Simply enter the test data and click the button below to send a test notification.
            
            Note: This will not affect the known trains tracking.
            """)
            
            # Add a test button
            if st.button("Send Test WhatsApp Notification", type="primary"):
                # Create a mock train detail for testing
                test_details = {
                    "FROM-TO": test_from_to,
                    "Event": test_event,
                    "Station": test_station,
                    "Delay": f"{test_delay} mins",
                }
                
                # Initialize the notifier
                test_notifier = WhatsAppNotifier()
                
                # Create a message with the details
                if st.session_state.get('use_new_format', True):
                    test_message = f"{test_train_number} {test_from_to}, {test_event} - {test_station} ({test_delay} mins)"
                else:
                    test_message = f"{test_train_number}\nStation Pair: {test_from_to}, Events: {test_event} - {test_station} ({test_delay} mins)"
                
                # Attempt to send the test message
                success = test_notifier.send_notification(test_message)
                
                if success:
                    st.success(f"Test notification prepared successfully!")
                    st.code(test_message, language="text")
                    st.info("Check the application logs for the WhatsApp Web URL to manually send the message.")
                else:
                    st.error("Failed to prepare test notification. Check the application logs for more details.")
                    st.info("This might be due to missing WhatsApp configuration.")
    
    # Initialize WhatsApp notifier
    whatsapp_notifier = WhatsAppNotifier()
    
    # Extract train numbers for WhatsApp notifications
    train_numbers = []
    train_details = {}
    
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
    
    # Check for new trains and send notifications
    if train_numbers:
        new_trains = whatsapp_notifier.notify_new_trains(train_numbers, train_details)
        if new_trains:
            st.success(f"Detected {len(new_trains)} new trains: {', '.join(new_trains)}")
            st.info("WhatsApp notifications prepared for new trains only!")
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
        st.write("This page monitors train data and sends WhatsApp notifications for new trains only.")
        
        # Check if we have WhatsApp API key and number
        if not whatsapp_notifier.whatsapp_api_key:
            st.warning("WhatsApp credentials not found. Please add them to your secrets.toml file.")
            st.code("""
# In .streamlit/secrets.toml:
WHATSAPP_API_KEY = "your_whatsapp_api_key"  # If you're using personal WhatsApp, you can use 'personal' as the key
WHATSAPP_NUMBER = "your_whatsapp_number"  # Your personal WhatsApp number with country code
NOTIFICATION_RECIPIENTS = ["recipient_phone_number1", "recipient_phone_number2"]  # Must be WhatsApp numbers with country code
            """)
        else:
            st.success("WhatsApp configuration found. WhatsApp notifications are enabled.")
            
            # Show current notification recipients
            if whatsapp_notifier.recipients:
                st.write(f"Currently notifying {len(whatsapp_notifier.recipients)} WhatsApp recipients: {', '.join(whatsapp_notifier.recipients)}")
            else:
                st.warning("No notification recipients configured. Add them to your secrets.toml file.")
        
        # Show format examples
        st.markdown("#### WhatsApp Message Format Examples:")
        st.markdown("**Compact Format:**")
        st.code("12760 HYB-TBM, T/O - KI (-6 mins), H/O - GDR (9 mins), DELAYED BY LT 9")
        
        st.markdown("**Standard Format:**")
        st.code("12760\nStation Pair: HYB 18:00-- TBM 08:00, Intermediate Stations: KI (-6 mins), GDR (9 mins), Delays: LT 9")
    
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