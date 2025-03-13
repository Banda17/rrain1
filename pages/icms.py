import streamlit as st
import pandas as pd
import re
import time
import requests
from datetime import datetime
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp
import numpy as np
import io

# Page Configuration
st.set_page_config(
    page_title="ICMS Data Tracker",
    page_icon="🚆",
    layout="wide"
)

# URLs for the data
MAIN_DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=0&single=true&output=csv"
PUNCTUALITY_DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=1136087799&single=true&output=csv"

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

/* Punctuality section styling */
.punctuality-container {
    margin-top: 1.5rem;
    background-color: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.punctuality-title {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: #2c3e50;
    text-align: center;
    padding: 5px;
    background-color: #f8f9fa;
    border-radius: 4px;
}

.punctuality-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.5rem;
    font-size: 14px;
}

.punctuality-table th {
    background-color: #424242;
    color: white;
    text-align: center;
    padding: 8px;
    border: 1px solid #ddd;
}

.punctuality-table td {
    text-align: center;
    padding: 8px;
    border: 1px solid #ddd;
}

.punctuality-percentage {
    font-weight: bold;
    color: #ffffff;
    background-color: #4CAF50;
    padding: 2px 8px;
    border-radius: 4px;
}

.punctuality-header {
    background-color: #1e88e5;
    color: white;
    text-align: center;
    padding: 12px;
    border-radius: 4px;
    font-weight: bold;
}

.punctuality-schedule {
    background-color: #e3f2fd;
    color: #0d47a1;
    font-weight: bold;
}

.punctuality-reported {
    background-color: #fff9c4;
    color: #ff6f00;
    font-weight: bold;
}

.punctuality-late {
    background-color: #ffebee;
    color: #c62828;
    font-weight: bold;
}

/* MS section styling */
.ms-container {
    margin-top: 1.5rem;
    background-color: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.ms-title {
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: #2c3e50;
    text-align: center;
    padding: 5px;
    background-color: #f8f9fa;
    border-radius: 4px;
}

.ms-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.5rem;
    font-size: 14px;
}

.ms-table th {
    background-color: #424242;
    color: white;
    text-align: center;
    padding: 8px;
    border: 1px solid #ddd;
}

.ms-table td {
    text-align: center;
    padding: 8px;
    border: 1px solid #ddd;
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

/* Totals table styling */
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

# Page title and info
st.title("ICMS Data View")
st.write("This page displays data from the ICMS system with punctuality statistics.")

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
        return df, True
    except Exception as e:
        st.error(f"Error fetching data from {url}: {str(e)}")
        return pd.DataFrame(), False

# Create a placeholder for the refresh animation
refresh_placeholder = st.empty()

# Set refreshing state to True and show animation
st.session_state['is_refreshing'] = True
create_pulsing_refresh_animation(refresh_placeholder, "Fetching data from Google Sheets...")

# Fetch both datasets
st.info("Fetching punctuality data and train details...")

# Fetch punctuality data first
punctuality_raw_data, punctuality_success = fetch_sheet_data(PUNCTUALITY_DATA_URL)

# Fetch main data
main_raw_data, main_success = fetch_sheet_data(MAIN_DATA_URL)

# Clear the refresh animation when done
st.session_state['is_refreshing'] = False
refresh_placeholder.empty()

success = main_success or punctuality_success  # We'll proceed if at least one succeeded

if success:
    # First process and display the punctuality data
    if punctuality_success and not punctuality_raw_data.empty:
        st.success(f"Successfully loaded punctuality data with {len(punctuality_raw_data)} rows")
        
        # Display the punctuality data in a styled HTML table
        st.markdown('<div class="punctuality-container"><div class="punctuality-title">Punctuality</div>', unsafe_allow_html=True)
        
        # Convert DataFrame to HTML table with styling
        html_table = '<table class="punctuality-table">'
        
        # Add header row with special styling
        html_table += '<tr class="punctuality-header">'
        for col in punctuality_raw_data.columns:
            html_table += f'<th>{col}</th>'
        html_table += '</tr>'
        
        # Add data rows
        for _, row in punctuality_raw_data.iterrows():
            html_table += '<tr>'
            for i, col in enumerate(punctuality_raw_data.columns):
                cell_value = row[col]
                
                # Replace NaN values with empty strings
                if pd.isna(cell_value) or pd.isnull(cell_value) or str(cell_value).lower() == 'nan':
                    display_value = ""
                else:
                    display_value = cell_value
                    
                # Apply appropriate styling based on the column
                if col == 'Punctuality %' or (isinstance(display_value, str) and '%' in str(display_value)):
                    html_table += f'<td class="punctuality-percentage">{display_value}</td>'
                elif col == 'Scheduled':
                    html_table += f'<td class="punctuality-schedule">{display_value}</td>'
                elif col == 'Reported':
                    html_table += f'<td class="punctuality-reported">{display_value}</td>'
                elif col == 'Late':
                    html_table += f'<td class="punctuality-late">{display_value}</td>'
                else:
                    html_table += f'<td>{display_value}</td>'
            html_table += '</tr>'
        
        html_table += '</table>'
        
        # Display the HTML table
        st.markdown(html_table, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Additional space after the punctuality table
        st.write("")
    else:
        st.warning("Failed to load punctuality data. Using default values.")
        # Create a default punctuality table
        punctuality_data = pd.DataFrame({
            'Date': [datetime.now().strftime('%d %b %Y')],
            'Scheduled': [42],
            'Reported': [38],
            'Late': [12],
            'Punctuality %': ["68.4%"],
        })
        
        # Display the punctuality data in a styled HTML table
        st.markdown('<div class="punctuality-container"><div class="punctuality-title">Punctuality</div>', unsafe_allow_html=True)
        
        # Convert DataFrame to HTML table with styling
        html_table = '<table class="punctuality-table">'
        
        # Add header row with special styling
        html_table += '<tr class="punctuality-header">'
        for col in punctuality_data.columns:
            html_table += f'<th>{col}</th>'
        html_table += '</tr>'
        
        # Add data rows
        for _, row in punctuality_data.iterrows():
            html_table += '<tr>'
            for i, col in enumerate(punctuality_data.columns):
                cell_value = row[col]
                
                # Replace NaN values with empty strings
                if pd.isna(cell_value) or pd.isnull(cell_value) or str(cell_value).lower() == 'nan':
                    display_value = ""
                else:
                    display_value = cell_value
                
                # Apply appropriate styling based on the column
                if col == 'Punctuality %' or (isinstance(display_value, str) and '%' in str(display_value)):
                    html_table += f'<td class="punctuality-percentage">{display_value}</td>'
                elif col == 'Scheduled':
                    html_table += f'<td class="punctuality-schedule">{display_value}</td>'
                elif col == 'Reported':
                    html_table += f'<td class="punctuality-reported">{display_value}</td>'
                elif col == 'Late':
                    html_table += f'<td class="punctuality-late">{display_value}</td>'
                else:
                    html_table += f'<td>{display_value}</td>'
            html_table += '</tr>'
        
        html_table += '</table>'
        
        # Display the HTML table
        st.markdown(html_table, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Additional space after the punctuality table
        st.write("")
    
    # Then process and display the main train data
    if main_success and not main_raw_data.empty:
        try:
            # Skip first two rows (0 and 1) and reset index
            if len(main_raw_data) > 2:
                df = main_raw_data.iloc[2:].reset_index(drop=True)
            else:
                df = main_raw_data.copy()
                
            # Safe conversion of NaN values to empty string
            def safe_convert(value):
                if pd.isna(value) or pd.isnull(value) or str(value).lower() == 'nan':
                    return ""
                return str(value) if value is not None else ""

            # Apply safe conversion to all elements
            df = df.applymap(safe_convert)
            
            # Extract the necessary columns for our tables
            st.subheader("Data Processing")
            st.write("Processing train data for display...")
            
            # Check for expected columns
            expected_cols = ['Sr.', 'Train No.', 'FROM-TO', 'Delay']
            missing_cols = [col for col in expected_cols if col not in df.columns]
            
            if missing_cols:
                st.warning(f"Missing expected columns: {', '.join(missing_cols)}")
                st.write("Available columns:", ', '.join(df.columns))
            
            # Display the raw data table first (just top rows)
            with st.expander("View Raw Data Sample"):
                st.dataframe(df.head(5))
            
            # Function to check if a value is positive or contains (+)
            def is_positive_or_plus(value):
                if value is None or value == "":
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
            
            # Filter and display the main data table
            if 'Delay' in df.columns:
                filtered_df = df[df['Delay'].apply(is_positive_or_plus)]
                st.write(f"Showing {len(filtered_df)} entries with positive delays")
            else:
                filtered_df = df
                st.warning("Delay column not found in data")
            
            # Show the filtered data
            st.subheader("Train Delay Details")
            st.dataframe(
                filtered_df,
                use_container_width=True,
                column_config={
                    "Train No.": st.column_config.TextColumn("Train No.", help="Train Number"),
                    "FROM-TO": st.column_config.TextColumn("FROM-TO", help="Source to Destination"),
                    "IC EntryDelay": st.column_config.TextColumn("IC Entry Delay", help="Entry Delay"),
                    "Delay": st.column_config.TextColumn("Delay", help="Delay in Minutes")
                }
            )
        except Exception as e:
            st.error(f"An error occurred while processing train data: {str(e)}")
            st.exception(e)
        
    # Display refresh timestamp
    now = datetime.now()
    st.markdown(f"<p style='text-align: right; color: gray; font-size: 12px;'>Last refreshed: {now.strftime('%d %b %Y %H:%M:%S')} IST</p>", unsafe_allow_html=True)
    
    # Show "Auto-refreshing every 5 minutes" message
    st.caption("Auto-refreshing every 5 minutes")
    
    # Auto-refresh every 5 minutes with improved progress visualization
    show_countdown_progress(300, 0.1)  # 300 seconds = 5 minutes, update every 0.1 seconds
    
    st.rerun()

else:
    # Display error message if data fetch failed
    st.error("Failed to load data from Google Sheets. Displaying backup information.")
    
    # Show a backup table with minimal information
    st.markdown("""
    <div class="punctuality-container">
        <div class="punctuality-title">Punctuality</div>
        <table class="punctuality-table">
            <tr class="punctuality-header">
                <th>Date</th>
                <th>Scheduled</th>
                <th>Reported</th>
                <th>Late</th>
                <th>Punctuality %</th>
            </tr>
            <tr>
                <td>13 Mar 2025</td>
                <td class="punctuality-schedule">42</td>
                <td class="punctuality-reported">37</td>
                <td class="punctuality-late">12</td>
                <td class="punctuality-percentage">67.6%</td>
            </tr>
        </table>
    </div>
    

    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("ICMS Data View - Train Tracking System")