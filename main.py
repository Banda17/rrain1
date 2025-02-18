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
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

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

# Initialize session state
if 'data_handler' not in st.session_state:
    st.session_state['data_handler'] = DataHandler()
if 'ai_analyzer' not in st.session_state:
    st.session_state['ai_analyzer'] = AIAnalyzer()
if 'visualizer' not in st.session_state:
    st.session_state['visualizer'] = Visualizer()
if 'train_schedule' not in st.session_state:
    st.session_state['train_schedule'] = TrainSchedule()
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None
if 'selected_train' not in st.session_state:
    st.session_state['selected_train'] = None
if 'selected_train_details' not in st.session_state:
    st.session_state['selected_train_details'] = {}
if 'map_viewer' not in st.session_state:
    st.session_state['map_viewer'] = MapViewer()

def update_selected_train_details(selected):
    """Update the selected train details in session state"""
    station = selected['Station']
    if st.session_state['map_viewer'].get_station_coordinates(station):
        st.session_state['selected_train'] = {
            'train': selected['Train Name'],
            'station': station
        }
        st.session_state['selected_train_details'] = {
            'Scheduled Time': selected['Sch_Time'],
            'Actual Time': selected['Current Time'],
            'Current Status': selected['Status'],
            'Delay': selected['Delay']
        }

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
            lambda row: calculate_time_difference(row['Sch_Time'], row['Time_Display']),
            axis=1
        )

        # Format delay values with indicators
        filtered_df['Delay'] = filtered_df['Delay'].apply(
            lambda x: f"⚠️ +{x}" if pd.notna(x) and x > 5 else
                     f"⏰ {x}" if pd.notna(x) and x < -5 else
                     f"✅ {x}" if pd.notna(x) else "N/A"
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
            help="Filter trains based on their arrival status"
        )

        # Apply timing status filter
        if timing_status != "All":
            if timing_status == "Late":
                display_df = display_df[display_df['Delay'].str.contains('⚠️', na=False)]
            elif timing_status == "Early":
                display_df = display_df[display_df['Delay'].str.contains('⏰', na=False)]
            elif timing_status == "On Time":
                display_df = display_df[display_df['Delay'].str.contains('✅', na=False)]

            st.info(f"Showing {len(display_df)} {timing_status.lower()} trains")

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