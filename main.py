import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from data_handler import DataHandler
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge
from database import init_db
from train_schedule import TrainSchedule
import logging
from typing import Optional, Dict
import re
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp
from map_component import render_gps_map

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize database
init_db()


def parse_time(time_str: str) -> Optional[datetime]:
    """Parse time string in HH:MM format to datetime object"""
    try:
        # If time string is empty, None, or "Not Available"
        if not time_str or time_str.strip().lower() == "not available":
            return None

        # Extract only the time part (HH:MM) from the string
        time_part = time_str.split()[0] if time_str else ''
        if not time_part:
            return None

        # Validate time format (HH:MM)
        if not ':' in time_part or len(time_part.split(':')) != 2:
            logger.warning(f"Invalid time format: {time_str}")
            return None

        return datetime.strptime(time_part, '%H:%M')
    except Exception as e:
        logger.debug(f"Error parsing time {time_str}: {str(e)}")
        return None


def calculate_time_difference(scheduled: str, actual: str) -> Optional[int]:
    """Calculate time difference in minutes between scheduled and actual times"""
    try:
        # Return None if either time is empty or "Not Available"
        if pd.isna(scheduled) or pd.isna(actual) or \
           scheduled.strip().lower() == "not available" or \
           actual.strip().lower() == "not available":
            return None

        sch_time = parse_time(scheduled)
        act_time = parse_time(actual)

        if sch_time and act_time:
            # Convert both times to same date for comparison
            diff = (act_time - sch_time).total_seconds() / 60
            return int(diff)
        return None
    except Exception as e:
        logger.debug(f"Error calculating time difference: {str(e)}")
        return None


def format_delay_value(delay: Optional[int]) -> str:
    """Format delay value with appropriate indicator"""
    try:
        if delay is None:
            return "N/A"
        elif delay > 5:
            return f"⚠️ +{delay}"
        elif delay < -5:
            return f"⏰ {delay}"
        else:
            return f"✅ {delay}"
    except Exception as e:
        logger.error(f"Error formatting delay value: {str(e)}")
        return "N/A"


# Page configuration
st.set_page_config(page_title="Train Tracking System",
                   page_icon="🚂",
                   layout="wide",
                   initial_sidebar_state="collapsed")

# Add headers
st.markdown("""
    <h1 style='text-align: center; color: #1f497d;'>South Central Railway</h1>
    <h2 style='text-align: center; color: #4f81bd;'>Vijayawada Division</h2>
    <hr>
""",
            unsafe_allow_html=True)


def initialize_session_state():
    """Initialize all session state variables with proper typing"""
    state_configs = {
        'data_handler': {
            'default': DataHandler(),
            'type': DataHandler
        },
        'visualizer': {
            'default': Visualizer(),
            'type': Visualizer
        },
        'train_schedule': {
            'default': TrainSchedule(),
            'type': TrainSchedule
        },
        'last_update': {
            'default': None,
            'type': Optional[datetime]
        },
        'selected_train': {
            'default': None,
            'type': Optional[Dict]
        },
        'selected_train_details': {
            'default': {},
            'type': Dict
        },
        'filter_status': {
            'default': 'Late',
            'type': str
        },
        'last_refresh': {
            'default': datetime.now(),
            'type': datetime
        },
        'is_refreshing': {
            'default': False,
            'type': bool
        },
        'map_stations': {  # New state variable for map stations
            'default': [],
            'type': list
        },
        'selected_stations': {  # New state variable for selected stations
            'default': [],
            'type': list
        }
    }

    for key, config in state_configs.items():
        if key not in st.session_state:
            st.session_state[key] = config['default']

    # Initialize ICMS data handler if not in session state
    if 'icms_data_handler' not in st.session_state:
        data_handler = DataHandler()
        # Override the spreadsheet URL for ICMS data
        data_handler.spreadsheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=155911658&single=true&output=csv"
        st.session_state['icms_data_handler'] = data_handler


def update_selected_train_details(selected):
    """Update the selected train details in session state"""
    try:
        # Clear selection if selected is None or empty DataFrame
        if selected is None or (isinstance(selected, pd.Series)
                                and selected.empty):
            st.session_state['selected_train'] = None
            st.session_state['selected_train_details'] = {}
            return

        # Extract values safely from pandas Series
        if isinstance(selected, pd.Series):
            station = selected.get('Station', '')
            train_name = selected.get('Train Name', '')
            sch_time = selected.get('Sch_Time', '')
            current_time = selected.get('Current Time', '')
            status = selected.get('Status', '')
            delay = selected.get('Delay', '')
        else:
            station = selected.get('Station', '')
            train_name = selected.get('Train Name', '')
            sch_time = selected.get('Sch_Time', '')
            current_time = selected.get('Current Time', '')
            status = selected.get('Status', '')
            delay = selected.get('Delay', '')

        st.session_state['selected_train'] = {
            'train': train_name,
            'station': station
        }
        st.session_state['selected_train_details'] = {
            'Scheduled Time': sch_time,
            'Actual Time': current_time,
            'Current Status': status,
            'Delay': delay
        }
        logger.debug(
            f"Updated selected train: {st.session_state['selected_train']}")

    except Exception as e:
        logger.error(f"Error updating selected train details: {str(e)}")
        st.session_state['selected_train'] = None
        st.session_state['selected_train_details'] = {}


def handle_timing_status_change():
    """Handle changes in timing status filter"""
    st.session_state['filter_status'] = st.session_state.get(
        'timing_status_select', 'Late')
    logger.debug(
        f"Timing status changed to: {st.session_state['filter_status']}")


def extract_stations_from_data(df):
    """Extract unique stations from the data for the map"""
    stations = []
    if df is not None and not df.empty:
        # Try different column names that might contain station information
        station_columns = ['Station', 'station', 'STATION', 'Station Name', 'station_name']
        for col in station_columns:
            if col in df.columns:
                # Extract unique values and convert to list
                stations = df[col].dropna().unique().tolist()
                break

    # Store in session state for use in the map
    st.session_state['map_stations'] = stations
    return stations


@st.cache_data(ttl=300)
def load_and_process_data():
    """Cache data loading and processing"""
    success, message = st.session_state['icms_data_handler'].load_data_from_drive()
    if success:
        status_table = st.session_state['icms_data_handler'].get_train_status_table()
        cached_data = st.session_state['icms_data_handler'].get_cached_data()
        if cached_data:
            return True, status_table, pd.DataFrame(cached_data), message
    return False, None, None, message

# Initialize session state
initialize_session_state()

# Main page title
st.title("ICMS Data - Vijayawada Division")

# Add a refresh button at the top with just an icon
col1, col2 = st.columns([10, 1])
with col2:
    if st.button("🔄", type="primary"):
        st.rerun()

try:
    data_handler = st.session_state['icms_data_handler']

    # Set refreshing state to True and show animation
    st.session_state['is_refreshing'] = True
    refresh_placeholder = st.empty() # Moved here
    create_pulsing_refresh_animation(refresh_placeholder, "Loading ICMS data...")

    # Load data with feedback
    with st.spinner("Loading ICMS data..."):
        success, message = data_handler.load_data_from_drive()

    # Clear the refresh animation when done
    st.session_state['is_refreshing'] = False
    refresh_placeholder.empty()

    if success:
        # Show last update time
        if data_handler.last_update:
            # Convert last update to IST (UTC+5:30)
            last_update_ist = data_handler.last_update + timedelta(hours=5,
                                                                   minutes=30)
            st.info(
                f"Last updated: {last_update_ist.strftime('%Y-%m-%d %H:%M:%S')} IST"
            )

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

                # Get and print all column names for debugging
                logger.debug(f"Available columns: {df.columns.tolist()}")

                # Extract stations for map
                stations = extract_stations_from_data(df)

                # Drop unwanted columns - use exact column names with proper spacing
                columns_to_drop = [
                    'Sr.',
                    'Exit Time for NLT Status',
                    'FROM-TO',
                    'Start date',
                    # Try different column name variations
                    'Scheduled [ Entry - Exit ]',
                    'Scheduled [Entry - Exit]',
                    'Scheduled[ Entry - Exit ]',
                    'Scheduled[Entry - Exit]',
                    'Scheduled [ Entry-Exit ]',
                    'Scheduled [Entry-Exit]',
                    'scheduled[Entry-Exit]',
                    'DivisionalActual[ Entry - Exit ]',
                    'Divisional Actual [Entry - Exit]', 
                    'Divisional Actual[ Entry-Exit ]',
                    'Divisional Actual[ Entry - Exit ]',
                    'DivisionalActual[ Entry-Exit ]',
                    'Divisional Actual [Entry-Exit]'
                ]

                # Drop each column individually if it exists
                for col in columns_to_drop:
                    if col in df.columns:
                        df = df.drop(columns=[col])
                        logger.debug(f"Dropped column: {col}")

                # Create a two-column layout for the table and map
                table_col, map_col = st.columns([3, 2])

                with table_col:
                    # Refresh animation placeholder right before displaying the table
                    refresh_table_placeholder = st.empty()
                    create_pulsing_refresh_animation(refresh_table_placeholder, "Refreshing Table...")

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
                                num = float(
                                    value.replace('(', '').replace(')',
                                                                    '').strip())
                                return num > 0
                            except:
                                return False
                        return False

                    # Filter rows where Delay column has positive values or (+)
                    if 'Delay' in df.columns:
                        filtered_df = df[df['Delay'].apply(is_positive_or_plus)]
                        st.write(
                            f"Showing {len(filtered_df)} entries with positive delays"
                        )
                    else:
                        filtered_df = df
                        st.warning("Delay column not found in data")

                    # Apply red styling only to the Delay column
                    def highlight_delay(df):
                        # Create a DataFrame of styles with same shape as the input DataFrame
                        styles = pd.DataFrame('', index=df.index, columns=df.columns)

                        # Apply red color only to the 'Delay' column if it exists
                        if 'Delay' in df.columns:
                            styles['Delay'] = 'color: red; font-weight: bold'

                        return styles

                    # Add a "Select" column at the beginning of the DataFrame for checkboxes
                    if 'Select' not in filtered_df.columns:
                        filtered_df.insert(0, 'Select', False)

                    # Get station column name
                    station_column = next((col for col in filtered_df.columns if col in ['Station', 'station', 'STATION']), None)

                    # Apply styling to the dataframe
                    styled_df = filtered_df.style.apply(highlight_delay, axis=None)

                    # Use data_editor to make the table interactive with checkboxes
                    edited_df = st.data_editor(
                        filtered_df,
                        hide_index=True,
                        column_config={
                            "Select": st.column_config.CheckboxColumn(
                                "Select",
                                help="Select to show on map",
                                default=False
                            ),
                            "Train No.": st.column_config.TextColumn("Train No.", help="Train Number"),
                            "FROM-TO": st.column_config.TextColumn("FROM-TO", help="Source to Destination"),
                            "IC Entry Delay": st.column_config.TextColumn("IC Entry Delay", help="Entry Delay"),
                            "Delay": st.column_config.TextColumn("Delay", help="Delay in Minutes")
                        },
                        disabled=[col for col in filtered_df.columns if col != 'Select'],
                        use_container_width=True
                    )

                    # Get selected stations for map
                    if station_column:
                        selected_rows = edited_df[edited_df['Select']]
                        selected_stations = selected_rows[station_column].dropna().tolist()
                        st.session_state['selected_stations'] = selected_stations

                        if selected_stations:
                            st.success(f"Selected {len(selected_stations)} stations for map view")

                    refresh_table_placeholder.empty() # Clear the placeholder after table display

                # Render map in the right column
                with map_col:
                    # Only show selected stations
                    display_stations = st.session_state['selected_stations']

                    # Render the map with only selected stations
                    render_gps_map(
                        selected_stations=display_stations,
                        map_title="Division GPS Map",
                        height=550
                    )
        else:
            st.warning("No data available in cache")

    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("Train Tracking System")

# Display refresh information
now = datetime.now()
# Convert to IST (UTC+5:30)
ist_time = now + timedelta(hours=5, minutes=30)
st.session_state['last_refresh'] = now
st.caption(f"Last refresh: {ist_time.strftime('%Y-%m-%d %H:%M:%S')} IST")
st.caption("Auto-refreshing every 4 minutes")


# Removed the old progress bar and replaced it with a countdown timer.
show_countdown_progress(240, 0.1) #Countdown for 4 minutes
show_refresh_timestamp() #Shows refresh timestamp


# Refresh the page
st.rerun()