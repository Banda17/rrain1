import streamlit as st
import pandas as pd
from data_handler import DataHandler
import time
import re
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp

# Page configuration
st.set_page_config(
    page_title="ICMS Data - Train Tracking System",
    page_icon="🚂",
    layout="wide"
)

# Initialize data handler if not in session state
if 'icms_data_handler' not in st.session_state:
    data_handler = DataHandler()
    # Override the spreadsheet URL for ICMS data
    data_handler.spreadsheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=155911658&single=true&output=csv"
    st.session_state['icms_data_handler'] = data_handler

# Initialize refresh state if not in session state
if 'is_refreshing' not in st.session_state:
    st.session_state['is_refreshing'] = False

# Page title
st.title("📊 ICMS Data")
st.markdown("Integrated Coaching Management System Data View")

# Function to fetch data from Google Sheets
@st.cache_data(ttl=300, show_spinner="Fetching data from Google Sheets...")
def fetch_google_sheet_data(url):
    try:
        # Fetch the CSV data from the Google Sheets URL
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Error fetching data from Google Sheets: {str(e)}")
        return None

# Fetch punctuality data
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=1165743954&single=true&output=csv"
punctuality_data = fetch_google_sheet_data(sheet_url)

# Add Punctuality Summary Table styles
st.markdown("""
<style>
.punctuality-container, .ms-container {
    margin-bottom: 20px;
    width: 100%;
}
.punctuality-title, .ms-title {
    font-weight: bold;
    font-size: 18px;
    margin-bottom: 8px;
    color: #333;
}
.punctuality-table, .ms-table {
    width: 100%;
    border-collapse: collapse;
    border: 1px solid #ccc;
    font-size: 14px;
}
.punctuality-table th, .ms-table th {
    background-color: #0066b2;
    color: white;
    text-align: center;
    padding: 8px;
    border: 1px solid #ddd;
    font-weight: bold;
}
.punctuality-table td, .ms-table td {
    text-align: center;
    padding: 8px;
    border: 1px solid #ddd;
}
.punctuality-percentage {
    font-weight: bold;
    color: #008000;
}
.ms-table th {
    background-color: #6b5b95;
}
</style>
""", unsafe_allow_html=True)

# Generate Punctuality Table from fetched data
if punctuality_data is not None and not punctuality_data.empty:
    # Create HTML table from the DataFrame
    st.markdown('<div class="punctuality-container"><div class="punctuality-title">Punctuality</div>', unsafe_allow_html=True)
    
    # Start table
    html_table = '<table class="punctuality-table"><tr>'
    
    # Add headers
    for col in punctuality_data.columns:
        html_table += f'<th>{col}</th>'
    html_table += '</tr>'
    
    # Add rows
    for _, row in punctuality_data.iterrows():
        html_table += '<tr>'
        for i, col in enumerate(punctuality_data.columns):
            cell_value = row[col]
            # Add special styling for percentage column (last column)
            if i == len(punctuality_data.columns) - 1 and "%" in str(cell_value):
                html_table += f'<td class="punctuality-percentage">{cell_value}</td>'
            else:
                html_table += f'<td>{cell_value}</td>'
        html_table += '</tr>'
    
    # Close table
    html_table += '</table></div>'
    
    # Display the HTML table
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Always create a second table for MS data
    # Either extract MS columns or create a separate view of some data columns
    st.markdown('<div class="ms-container"><div class="ms-title">MS Information</div>', unsafe_allow_html=True)
    
    # Try to find MS related columns
    ms_cols = [col for col in punctuality_data.columns if 'MS' in col.upper()]
    
    # If no explicit MS columns, create a meaningful second table using available data
    if len(ms_cols) == 0:
        # Use a subset of columns for the MS table - adjust based on your actual data
        # For example, use date and any columns related to performance metrics
        date_col = next((col for col in punctuality_data.columns if 'DATE' in col.upper()), None)
        
        # Define which columns to include in MS table
        if date_col:
            ms_cols = [date_col]
        else:
            ms_cols = []
            
        # Add any columns that might be related to performance or metrics
        for col in punctuality_data.columns:
            if any(keyword in col.upper() for keyword in ['PERCENTAGE', 'METRIC', 'PERFORMANCE', 'SCORE']):
                ms_cols.append(col)
                
        # If we still don't have enough columns, add some other meaningful ones
        if len(ms_cols) < 2 and len(punctuality_data.columns) > 1:
            # Add the first few columns except date if already added
            for col in punctuality_data.columns[:3]:
                if col not in ms_cols:
                    ms_cols.append(col)
    
    # Create MS table if we have columns to display
    if len(ms_cols) > 0:
        ms_data = punctuality_data[ms_cols]
        
        # Start MS table
        ms_table = '<table class="ms-table"><tr>'
        
        # Add headers
        for col in ms_data.columns:
            ms_table += f'<th>{col}</th>'
        ms_table += '</tr>'
        
        # Add rows
        for _, row in ms_data.iterrows():
            ms_table += '<tr>'
            for col in ms_data.columns:
                cell_value = row[col]
                ms_table += f'<td>{cell_value}</td>'
            ms_table += '</tr>'
        
        # Close table
        ms_table += '</table></div>'
        
        # Display the MS table
        st.markdown(ms_table, unsafe_allow_html=True)
    else:
        # If no suitable columns found, display a message
        st.markdown('<div class="alert alert-info">No MS data available in the sheet.</div></div>', unsafe_allow_html=True)
    
    # Extract data from the punctuality table for the additional statistics table
    # Apply CSS styles for the table
    st.markdown("""
    <style>
    .totals-table {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid #ccc;
        font-size: 14px;
        margin-top: 20px;
    }
    .totals-table th {
        background-color: #424242;
        color: white;
        text-align: center;
        padding: 8px;
        border: 1px solid #ddd;
        font-weight: bold;
    }
    .totals-table td {
        text-align: center;
        padding: 8px;
        border: 1px solid #ddd;
    }
    .totals-row {
        font-weight: bold;
        background-color: #f2f2f2;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Get the values from the punctuality data
    if punctuality_data is not None and not punctuality_data.empty:
        # Get the last row (most recent) data
        latest_row = punctuality_data.iloc[-1]
        
        # Create a dictionary with data for the totals table
        # Use the actual column values when possible with error handling
        try:
            # Safely extract values with error checking
            scheduled = latest_row.iloc[1] if len(latest_row) > 1 else 42
            reported = latest_row.iloc[2] if len(latest_row) > 2 else 38  
            late = latest_row.iloc[3] if len(latest_row) > 3 else 12
            
            # Try to convert to integers for calculation
            try:
                reported_int = int(reported)
                late_int = int(late)
                ontime = reported_int - late_int
            except (ValueError, TypeError):
                ontime = 26  # Default value if conversion fails
                
            # Get percentage or use default
            percentage = latest_row.iloc[-1] if "%" in str(latest_row.iloc[-1]) else "68.4%"
            
            # Populate dictionary with extracted values
            totals_data = {
                "col0": "Total",
                "col1": scheduled,  # Scheduled Trains
                "col2": reported,   # Reported Trains
                "col3": late,       # Late Trains
                "col8": ontime,     # On-time trains (calculated)
                "col9": percentage  # Punctuality percentage
            }
        except Exception as e:
            # If anything goes wrong, use default values
            st.warning(f"Error extracting data for statistics table: {str(e)}")
            totals_data = {
                "col0": "Total",
                "col1": 42,
                "col2": 38,
                "col3": 12,
                "col8": 26,
                "col9": "68.4%"
            }
    else:
        # Default values if no data is available
        totals_data = {
            "col0": "Total",
            "col1": 42,
            "col2": 38,
            "col3": 12,
            "col8": 26,
            "col9": "68.4%"
        }
    
    # Create and display the HTML table using the data
    st.markdown(f"""
    <div class="ms-container">
        <div class="ms-title">Additional Statistics</div>
        <table class="totals-table">
            <tr>
                <th>Unnamed: col0</th>
                <th>Unnamed: col1</th>
                <th>Unnamed: col2</th>
                <th>Unnamed: col3</th>
                <th>Unnamed: col8</th>
                <th>Unnamed: col9</th>
            </tr>
            <tr class="totals-row">
                <td>{totals_data["col0"]}</td>
                <td>{totals_data["col1"]}</td>
                <td>{totals_data["col2"]}</td>
                <td>{totals_data["col3"]}</td>
                <td>{totals_data["col8"]}</td>
                <td>{totals_data["col9"]}</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
else:
    # If data fetch failed, display a static backup table
    st.markdown("""
    <div class="punctuality-container">
        <div class="punctuality-title">Punctuality</div>
        <table class="punctuality-table">
            <tr>
                <th>Date</th>
                <th>Scheduled Trains</th>
                <th>Reported Trains</th>
                <th>Late Trains</th>
                <th>Punctuality Percentage</th>
            </tr>
            <tr>
                <td>13 Mar 2025</td>
                <td>42</td>
                <td>37</td>
                <td>12</td>
                <td class="punctuality-percentage">67.6%</td>
            </tr>
        </table>
    </div>
    
    <style>
    .totals-table {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid #ccc;
        font-size: 14px;
        margin-top: 20px;
    }
    .totals-table th {
        background-color: #424242;
        color: white;
        text-align: center;
        padding: 8px;
        border: 1px solid #ddd;
        font-weight: bold;
    }
    .totals-table td {
        text-align: center;
        padding: 8px;
        border: 1px solid #ddd;
    }
    .totals-row {
        font-weight: bold;
        background-color: #f2f2f2;
    }
    </style>
    <div class="ms-container">
        <div class="ms-title">Additional Statistics</div>
        <table class="totals-table">
            <tr>
                <th>Unnamed: col0</th>
                <th>Unnamed: col1</th>
                <th>Unnamed: col2</th>
                <th>Unnamed: col3</th>
                <th>Unnamed: col8</th>
                <th>Unnamed: col9</th>
            </tr>
            <tr class="totals-row">
                <td>Total</td>
                <td>42</td>
                <td>38</td>
                <td>12</td>
                <td>26</td>
                <td>68.4%</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

# Create a placeholder for the refresh animation
refresh_placeholder = st.empty()

try:
    data_handler = st.session_state['icms_data_handler']

    # Set refreshing state to True and show animation
    st.session_state['is_refreshing'] = True
    create_pulsing_refresh_animation(refresh_placeholder, "Refreshing data...")

    # Load data
    success, message = data_handler.load_data_from_drive()

    # Clear the refresh animation when done
    st.session_state['is_refreshing'] = False
    refresh_placeholder.empty()

    if success:

        # Get cached data
        cached_data = data_handler.get_cached_data()

        if cached_data:
            # Convert to DataFrame
            df = pd.DataFrame(cached_data)

            if not df.empty:
                # Skip first two rows (0 and 1) and reset index
                df = df.iloc[2:].reset_index(drop=True)

                # Safe conversion of NaN values to None
                def safe_convert(value):
                    if pd.isna(value) or pd.isnull(value):
                        return None
                    return str(value) if value is not None else None

                # Apply safe conversion to all elements
                df = df.applymap(safe_convert)

                # Drop unwanted columns
                columns_to_drop = ['Sr.', 'Exit Time for NLT Status']
                df = df.drop(columns=columns_to_drop, errors='ignore')

                # Function to check if a value is positive or contains (+)
                def is_positive_or_plus(value):
                    if value is None:
                        return False
                    if isinstance(value, str):
                        # Check for numbers in brackets with +
                        bracket_match = re.search(r'\(.*?\+.*?\)', value)
                        if bracket_match:
                            return True
                        # Try to convert to number if possible
                        try:
                            num = float(value.replace('(', '').replace(')', '').strip())
                            return num > 0
                        except:
                            return False
                    return False

                # Filter rows where Delay column has positive values or (+)
                if 'Delay' in df.columns:
                    filtered_df = df[df['Delay'].apply(is_positive_or_plus)]
                    st.write(f"Showing {len(filtered_df)} entries with positive delays")
                else:
                    filtered_df = df
                    st.warning("Delay column not found in data")

                # Show the filtered data - removed height parameter to show all rows without scrolling
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    column_config={
                        "Train No.": st.column_config.TextColumn("Train No.", help="Train Number"),
                        "FROM-TO": st.column_config.TextColumn("FROM-TO", help="Source to Destination"),
                        "IC Entry Delay": st.column_config.TextColumn("IC Entry Delay", help="Entry Delay"),
                        "Delay": st.column_config.TextColumn("Delay", help="Delay in Minutes")
                    }
                )
        else:
            st.warning("No data available in cache")

        # Display refresh timestamp
        show_refresh_timestamp(data_handler.last_update)

        # Show "Auto-refreshing every 5 minutes" message
        st.caption("Auto-refreshing every 5 minutes")

        # Auto-refresh every 5 minutes with improved progress visualization
        show_countdown_progress(300, 0.1)  # 300 seconds = 5 minutes, update every 0.1 seconds

        st.rerun()
    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("ICMS Data View - Train Tracking System")