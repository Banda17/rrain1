import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from data_handler import DataHandler
from ai_analyzer import AIAnalyzer
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge, show_ai_insights
from database import init_db
from train_schedule import TrainSchedule
import logging
from map_viewer import MapViewer
from typing import Optional, Dict

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
st.set_page_config(
    page_title="Train Tracking System",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add headers
st.markdown("""
    <h1 style='text-align: center; color: #1f497d;'>South Central Railway</h1>
    <h2 style='text-align: center; color: #4f81bd;'>Vijayawada Division</h2>
    <hr>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize all session state variables with proper typing"""
    state_configs = {
        'data_handler': {'default': DataHandler(), 'type': DataHandler},
        'ai_analyzer': {'default': AIAnalyzer(), 'type': AIAnalyzer},
        'visualizer': {'default': Visualizer(), 'type': Visualizer},
        'train_schedule': {'default': TrainSchedule(), 'type': TrainSchedule},
        'map_viewer': {'default': MapViewer(), 'type': MapViewer},
        'last_update': {'default': None, 'type': Optional[datetime]},
        'selected_train': {'default': None, 'type': Optional[Dict]},
        'selected_train_details': {'default': {}, 'type': Dict},
        'filter_status': {'default': 'Late', 'type': str}
    }

    for key, config in state_configs.items():
        if key not in st.session_state:
            st.session_state[key] = config['default']

def update_selected_train_details(selected):
    """Update the selected train details in session state"""
    try:
        # Clear selection if selected is None or empty DataFrame
        if selected is None or (isinstance(selected, pd.Series) and selected.empty):
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

        if station and st.session_state['map_viewer'].get_station_coordinates(station):
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
            logger.debug(f"Updated selected train: {st.session_state['selected_train']}")
        else:
            logger.warning(f"Invalid station or coordinates not found for station: {station}")
            st.session_state['selected_train'] = None
            st.session_state['selected_train_details'] = {}

    except Exception as e:
        logger.error(f"Error updating selected train details: {str(e)}")
        st.session_state['selected_train'] = None
        st.session_state['selected_train_details'] = {}

def handle_timing_status_change():
    """Handle changes in timing status filter"""
    st.session_state['filter_status'] = st.session_state.get('timing_status_select', 'Late')
    logger.debug(f"Timing status changed to: {st.session_state['filter_status']}")

@st.cache_data(ttl=300)
def load_and_process_data():
    """Cache data loading and processing"""
    success, message = st.session_state['data_handler'].load_data_from_drive()
    if success:
        status_table = st.session_state['data_handler'].get_train_status_table()
        cached_data = st.session_state['data_handler'].get_cached_data()
        if cached_data:
            return True, status_table, pd.DataFrame(cached_data), message
    return False, None, None, message

# Initialize session state
initialize_session_state()

# Map Section
st.title("🗺️ Division Map")
st.session_state['map_viewer'].render(st.session_state.get('selected_train'))

# Train List Section
st.title("🚂 Train List")

try:
    # Load data with caching
    success, status_table, cached_data, message = load_and_process_data()

    if success and cached_data is not None and not cached_data.empty:
        # Initialize DataFrame with first row as header
        df = pd.DataFrame(cached_data)
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)

        # Create mask for numeric train names
        numeric_mask = df['Train Name'].str.match(r'^\d.*', na=False)

        # Create new DataFrame with only required data
        columns_needed = ['Train Name', 'Station', 'Time', 'Status']
        filtered_df = df.loc[numeric_mask, columns_needed].copy()

        # Convert Time column to show only the time part (HH:MM)
        def extract_time(time_str):
            try:
                return time_str.split()[0] if time_str else ''
            except Exception as e:
                logger.error(f"Error extracting time from {time_str}: {str(e)}")
                return time_str

        # Apply the time extraction to the Time column
        filtered_df['Time_Display'] = filtered_df['Time'].apply(extract_time)

        # Add scheduled time column
        def get_scheduled_time_with_logging(row):
            train_name = str(row['Train Name'])
            station = str(row['Station'])
            scheduled_time = st.session_state['train_schedule'].get_scheduled_time(
                train_name, station
            )
            if scheduled_time and scheduled_time.strip():
                try:
                    time_part = scheduled_time.split()[0]
                    return time_part
                except Exception as e:
                    logger.error(f"Error parsing scheduled time {scheduled_time}: {str(e)}")
                    return scheduled_time
            return 'Not Available'

        # Add Sch_Time column
        filtered_df['Sch_Time'] = filtered_df.apply(
            get_scheduled_time_with_logging,
            axis=1
        )

        # Calculate time difference
        filtered_df['Delay'] = filtered_df.apply(
            lambda row: format_delay_value(
                calculate_time_difference(
                    row['Sch_Time'], 
                    row['Time_Display']
                )
            ),
            axis=1
        )


        # Add a background color based on condition
        def style_delay(value):
            if '⚠️' in value:
                return 'background-color: #FFA07A;'  # Light Salmon
            elif '⏰' in value:
                return 'background-color: #8FBC8F;'  # Dark Sea Green
            elif '✅' in value:
                return 'background-color: #98FB98;'  # Pale Green
            return ''

        filtered_df.style.applymap(style_delay, subset=['Delay'])

        # Add checkbox column
        filtered_df['Select'] = False

        # Both Time columns will show HH:MM format
        column_order = ['Select', 'Train Name', 'Station', 'Sch_Time', 'Time_Display', 'Status', 'Delay']
        display_df = filtered_df[column_order].copy()
        display_df = display_df.rename(columns={'Time_Display': 'Current Time'})

        # Show filtering info and controls
        st.info(f"Found {len(display_df)} trains with numeric names")

        # Add timing status filter
        timing_status = st.selectbox(
            "Filter by Timing Status",
            ["All", "Late", "On Time", "Early"],
            index=1,  # Default to "Late"
            key='timing_status_select',
            on_change=handle_timing_status_change,
            help="Filter trains based on their arrival status"
        )

        # Apply timing status filter using session state
        current_filter = st.session_state['filter_status']
        if current_filter != "All":
            if current_filter == "Late":
                display_df = display_df[display_df['Delay'].str.contains('⚠️', na=False)]
            elif current_filter == "Early":
                display_df = display_df[display_df['Delay'].str.contains('⏰', na=False)]
            elif current_filter == "On Time":
                display_df = display_df[display_df['Delay'].str.contains('✅', na=False)]

            st.info(f"Showing {len(display_df)} {current_filter.lower()} trains")

        # Make the dataframe interactive
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            height=400,
            key="train_selector",
            column_order=column_order,
            disabled=["Train Name", "Station", "Sch_Time", "Current Time", "Status", "Delay"],
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select to highlight on map",
                    width="small",
                    default=False
                ),
                "Current Time": st.column_config.TextColumn(
                    "Current Time",
                    help="Current time in 24-hour format"
                ),
                "Sch_Time": st.column_config.TextColumn(
                    "Scheduled Time",
                    help="Scheduled time in 24-hour format"
                ),
                "Delay": st.column_config.TextColumn(
                    "Delay (mins)",
                    help="Time difference between scheduled and actual time in minutes"
                )
            }
        )

        if len(edited_df) > 0:
            # Get currently selected trains
            selected_trains = edited_df[edited_df['Select']]

            if selected_trains.empty:
                # Clear selection
                st.session_state['selected_train'] = None
                st.session_state['selected_train_details'] = {}
            else:
                # Get the first selected train and update details
                update_selected_train_details(selected_trains.iloc[0])

        # Display the selected train details if available
        if st.session_state['selected_train_details']:
            selected_details = st.session_state['selected_train_details']
            st.markdown(f"<p>{selected_details['Delay']}</p>", unsafe_allow_html=True)
            st.write({
                'Scheduled Time': selected_details['Scheduled Time'],
                'Actual Time': selected_details['Actual Time'],
                'Current Status': selected_details['Current Status'],
            })

    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    logger.error(f"Error occurred: {str(e)}", exc_info=True)
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("Train Tracking System")