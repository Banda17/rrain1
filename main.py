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
if 'map_viewer' not in st.session_state:
    st.session_state['map_viewer'] = MapViewer()
if 'previous_selection' not in st.session_state:
    st.session_state['previous_selection'] = None

def parse_time(time_str: str) -> datetime:
    """Parse time string in HH:MM format to datetime object"""
    try:
        # Extract only the time part (HH:MM) from the string
        time_part = time_str.split()[0] if time_str else ''
        if not time_part:
            return None
        return datetime.strptime(time_part, '%H:%M')
    except Exception as e:
        logger.error(f"Error parsing time {time_str}: {str(e)}")
        return None

def calculate_time_difference(scheduled: str, actual: str) -> int:
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
        logger.error(f"Error calculating time difference: {str(e)}")
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
                # Extract just the time part (HH:MM) from "HH:MM DD-MM" format
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
            # Format scheduled time to show only time part if available
            if scheduled_time and scheduled_time.strip():
                try:
                    # Split the time string and take only the time part before the space
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

        # Add checkbox column
        filtered_df['Select'] = False

        # Both Time columns will show HH:MM format
        column_order = ['Select', 'Train Name', 'Station', 'Sch_Time', 'Time_Display', 'Time', 'Status', 'Delay']
        display_df = filtered_df[column_order].copy()
        display_df['Time'] = display_df['Time'].apply(extract_time)  # Format Time column to show only HH:MM
        display_df = display_df.rename(columns={'Time_Display': 'Current Time'})

        # Show filtering info
        st.info(f"Found {len(display_df)} trains with numeric names")

        # Make the dataframe interactive
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            height=400,
            key="train_selector",
            column_order=column_order,
            disabled=["Train Name", "Station", "Sch_Time", "Current Time", "Time", "Status", "Delay"],
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select to highlight on map",
                    default=False,
                ),
                "Current Time": st.column_config.TextColumn(
                    "Current Time",
                    help="Current time in 24-hour format"
                ),
                "Time": st.column_config.TextColumn(
                    "Time",
                    help="Time in HH:MM format"
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

        # Simplified selection logic
        if len(edited_df) > 0:
            # Get currently selected train
            selected_trains = edited_df[edited_df['Select']]

            if selected_trains.empty:
                # No selection, clear the map
                st.session_state['selected_train'] = None
            else:
                # Get the first (and only) selected train
                selected = selected_trains.iloc[0]

                # Update the selection state directly
                st.session_state['selected_train'] = {
                    'train': selected['Train Name'],
                    'station': selected['Station']
                }

                # Show train details
                delay_text = selected['Delay']
                st.markdown(f"<p>{delay_text}</p>", unsafe_allow_html=True)
                st.write({
                    'Scheduled Time': selected['Sch_Time'],
                    'Actual Time': selected['Current Time'],
                    'Current Status': selected['Status'],
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