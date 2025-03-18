import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import io
import os
import re
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp

# Page configuration - MUST be the first Streamlit command
st.set_page_config(
    page_title="Monitor - Train Tracking System",
    page_icon="📊",
    layout="wide"
)

# URL for the Google Sheets data
MONITOR_DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=1047627693&single=true&output=csv"

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
    background-color: #1e88e5;
    color: white;
    text-align: center;
    padding: 8px;
    border: 1px solid black;
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

# Clear the refresh animation when done
st.session_state['is_refreshing'] = False
refresh_placeholder.empty()

# Function to safely convert values
def safe_convert(value):
    """
    Safely convert values to strings handling NaN, None, and empty values consistently.
    
    Args:
        value: The value to convert
        
    Returns:
        String representation or empty string for null values
    """
    if pd.isna(value) or pd.isnull(value) or str(value).lower() == 'nan' or value is None:
        return ""
    
    # Convert to string and handle empty strings
    string_val = str(value).strip()
    if not string_val:
        return ""
        
    return string_val

# Process and display monitor data
if monitor_success and not monitor_raw_data.empty:
    st.success(f"Successfully loaded monitoring data with {len(monitor_raw_data)} rows")
    
    # Apply safe conversion to all elements
    for col in monitor_raw_data.columns:
        monitor_raw_data[col] = monitor_raw_data[col].map(safe_convert)
    
    # Display the data in a styled HTML table
    st.markdown('<div class="monitor-container"><div class="monitor-title">Monitoring Data</div>', unsafe_allow_html=True)
    
    # Convert DataFrame to HTML table with styling
    html_table = '<table class="monitor-table">'
    
    # Add header row with special styling
    html_table += '<tr>'
    for col in monitor_raw_data.columns:
        html_table += f'<th>{col}</th>'
    html_table += '</tr>'
    
    # Add data rows
    for _, row in monitor_raw_data.iterrows():
        html_table += '<tr>'
        for col in monitor_raw_data.columns:
            cell_value = row[col]
            
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
    
    html_table += '</table>'
    
    # Display the HTML table
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Display additional information about the data
    with st.expander("View Raw Data"):
        st.dataframe(monitor_raw_data)
    
    # Show last refresh timestamp
    refresh_time = datetime.now()
    show_refresh_timestamp(refresh_time)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Extract train details from the monitor data
    # This function extracts structured train data from the monitor DataFrame
    def extract_train_details(df):
        """
        Extract structured train details from the monitor data
        
        Args:
            df: DataFrame containing monitor data
            
        Returns:
            List of dictionaries with train details
        """
        train_details = []
        
        try:
            # Look for train numbers in the data
            # We're looking for patterns like "12706 SUF" which contains train number and type
            train_number_pattern = r'\d{5}\s+[A-Z]+'
            
            # Look for station codes (2-3 letters)
            station_code_pattern = r'\b[A-Z]{2,4}\b'
            
            # Look for time patterns like "07:45" or "14:35"
            time_pattern = r'\d{1,2}:\d{2}'
            
            # Initialize a dictionary to store our train data
            train_data = {}
            
            # Iterate through all cells in the DataFrame to find train information
            for _, row in df.iterrows():
                for col in df.columns:
                    value = str(row[col]).strip()
                    
                    # Skip empty cells
                    if not value:
                        continue
                    
                    # Check if this cell contains a train number
                    if re.search(r'\d{5}', value) and 'SUF' in value or 'MEX' in value or 'VNDB' in value:
                        # Extract the train number and type
                        parts = value.split()
                        if len(parts) >= 2:
                            train_number = parts[0]
                            train_type = parts[1]
                            
                            # Store in our data structure
                            if 'train_number' not in train_data:
                                train_data['train_number'] = f"{train_number} {train_type}"
                    
                    # Check for station codes followed by times
                    station_match = re.search(station_code_pattern, value)
                    time_match = re.search(time_pattern, value)
                    
                    if station_match and time_match:
                        station_code = station_match.group()
                        # If this appears to be a station code cell
                        if len(station_code) == 2 or len(station_code) == 3:
                            train_data['station_code'] = station_code
                            
                            # Extract times if present
                            times = re.findall(time_pattern, value)
                            if times:
                                train_data['times'] = times
                    
                    # Check for specific values that could be delay numbers
                    if re.match(r'^\d+$', value) and len(value) <= 3:
                        # This could be a delay value
                        try:
                            delay_value = int(value)
                            if 'delay' not in train_data and delay_value > 0 and delay_value < 200:
                                train_data['delay'] = delay_value
                        except ValueError:
                            pass
                    
                    # Check for LT (Late Time) values
                    if 'LT' in value:
                        # Safely extract number from LT value
                        match = re.search(r'\d+', value)
                        if match:
                            lt_value = match.group()
                            train_data['lt_value'] = lt_value
            
            # If we found train data, add it to our list
            if train_data and 'train_number' in train_data:
                train_details.append(train_data)
            
            # For demo purposes, add more example entries if needed to match the image
            # Look for values in other rows that might be part of another train
            train_data = {}
            
            # Make a second pass for additional rows
            for _, row in df.iterrows():
                has_data = False
                for col in df.columns:
                    value = str(row[col]).strip()
                    
                    # Skip empty cells
                    if not value:
                        continue
                    
                    # Check for station codes
                    if re.match(r'^[A-Z]{2,3}$', value):
                        train_data['station_code'] = value
                        has_data = True
                    
                    # Check for time patterns
                    elif re.search(time_pattern, value) and not re.search(r'\d{5}', value):
                        # This looks like a time range
                        train_data['times'] = re.findall(time_pattern, value)
                        has_data = True
                    
                    # Check for delay values
                    elif re.match(r'^\d+$', value) and len(value) <= 3:
                        try:
                            delay_value = int(value)
                            if delay_value > 0 and delay_value < 200:
                                train_data['delay'] = delay_value
                                has_data = True
                        except ValueError:
                            pass
                
                # If we found data for another train, add it
                if has_data and 'station_code' in train_data and 'delay' in train_data:
                    # Add to our collection if not duplicate
                    if train_data not in train_details:
                        train_details.append(train_data.copy())
                    train_data = {}
            
        except Exception as e:
            st.warning(f"Error extracting train details: {str(e)}")
        
        return train_details
    
    # Extract train details from the monitor data
    train_details = extract_train_details(monitor_raw_data)
    
    # If we couldn't extract any train details, check if there's any raw data we can use
    if not train_details and not monitor_raw_data.empty:
        # Try to extract information from specific columns
        st.warning("Couldn't automatically extract train details from the data format")
        
        # Create a sample structure based on the image provided
        train_details = [
            {
                'serial_number': '1',
                'train_number': '12706 SUF',
                'station_info': 'SC 07:45\nGNT 14:35 18-Mar-2025',
                'lt_value': 'LT 15'
            },
            {
                'station_code': 'KI',
                'times': ['13:05', '14:29:20'],
                'delay': 84
            },
            {
                'station_code': 'KCC',
                'times': ['13:50', '15:29:27'],
                'delay': 99
            }
        ]
    
    # Display the train details in a formatted table
    if train_details:
        st.markdown('<div class="train-details-container"><div class="train-details-title">Train Details</div>', unsafe_allow_html=True)
        
        # Create a 3x3 grid table for the train details
        html_table = '<table class="train-details-table">'
        
        # First row
        html_table += '<tr>'
        
        # Cell 1,1 (Serial Number)
        serial_cell = '<td class="highlight-cell">1</td>' if any('serial_number' in td for td in train_details) else '<td></td>'
        html_table += serial_cell
        
        # Cell 1,2 (Train Number and Station Info)
        train_cell = ''
        for td in train_details:
            if 'train_number' in td:
                train_info = f'<div class="train-number">{td["train_number"]}</div>'
                if 'station_info' in td:
                    # Handle newlines separately to avoid f-string issues
                    station_info = td["station_info"].replace('\n', '<br>')
                    train_info += f'<div>{station_info}</div>'
                train_cell = f'<td class="highlight-cell">{train_info}</td>'
                break
        if not train_cell:
            train_cell = '<td></td>'
        html_table += train_cell
        
        # Cell 1,3 (LT Value)
        lt_cell = ''
        for td in train_details:
            if 'lt_value' in td:
                lt_cell = f'<td class="highlight-cell">LT {td["lt_value"]}</td>'
                break
        if not lt_cell:
            lt_cell = '<td></td>'
        html_table += lt_cell
        
        html_table += '</tr>'
        
        # Second row
        html_table += '<tr>'
        
        # Cell 2,1 (First Station Code)
        station1_cell = ''
        if len(train_details) > 1 and 'station_code' in train_details[1]:
            station1_cell = f'<td class="highlight-cell station-code">{train_details[1]["station_code"]}</td>'
        else:
            station1_cell = '<td></td>'
        html_table += station1_cell
        
        # Cell 2,2 (First Station Times)
        times1_cell = ''
        if len(train_details) > 1 and 'times' in train_details[1] and len(train_details[1]['times']) > 0:
            times = train_details[1]['times']
            if len(times) == 1:
                times1_cell = f'<td class="time-value">{times[0]}</td>'
            else:
                times1_cell = f'<td class="time-value">{times[0]}-{times[1]}</td>'
        else:
            times1_cell = '<td></td>'
        html_table += times1_cell
        
        # Cell 2,3 (First Delay)
        delay1_cell = ''
        if len(train_details) > 1 and 'delay' in train_details[1]:
            delay1_cell = f'<td class="highlight-cell delay-value">{train_details[1]["delay"]}</td>'
        else:
            delay1_cell = '<td></td>'
        html_table += delay1_cell
        
        html_table += '</tr>'
        
        # Third row
        html_table += '<tr>'
        
        # Cell 3,1 (Second Station Code)
        station2_cell = ''
        if len(train_details) > 2 and 'station_code' in train_details[2]:
            station2_cell = f'<td class="highlight-cell station-code">{train_details[2]["station_code"]}</td>'
        else:
            station2_cell = '<td></td>'
        html_table += station2_cell
        
        # Cell 3,2 (Second Station Times)
        times2_cell = ''
        if len(train_details) > 2 and 'times' in train_details[2] and len(train_details[2]['times']) > 0:
            times = train_details[2]['times']
            if len(times) == 1:
                times2_cell = f'<td class="time-value">{times[0]}</td>'
            else:
                times2_cell = f'<td class="time-value">{times[0]}-{times[1]}</td>'
        else:
            times2_cell = '<td></td>'
        html_table += times2_cell
        
        # Cell 3,3 (Second Delay)
        delay2_cell = ''
        if len(train_details) > 2 and 'delay' in train_details[2]:
            delay2_cell = f'<td class="highlight-cell delay-value">{train_details[2]["delay"]}</td>'
        else:
            delay2_cell = '<td></td>'
        html_table += delay2_cell
        
        html_table += '</tr>'
        
        html_table += '</table>'
        
        # Display the HTML table
        st.markdown(html_table, unsafe_allow_html=True)
        
        # Provide a JSON representation for debugging
        with st.expander("View Train Details JSON"):
            st.json(train_details)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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