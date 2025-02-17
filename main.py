import streamlit as st
import pandas as pd
import time
from data_handler import DataHandler
from ai_analyzer import AIAnalyzer
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge, show_ai_insights
from database import init_db
from train_schedule import TrainSchedule
from datetime import datetime
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
# Render the map using the MapViewer component
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

        # Convert Time column to datetime and format to show only time
        filtered_df['Time'] = pd.to_datetime(filtered_df['Time'])
        filtered_df['Time_Display'] = filtered_df['Time'].dt.strftime('%H:%M')

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

        # Add checkbox column
        filtered_df['Select'] = False

        # Reorder columns to show checkbox first, use Time_Display instead of Time
        column_order = ['Select', 'Train Name', 'Station', 'Sch_Time', 'Time_Display', 'Status']
        display_df = filtered_df[column_order].copy()
        display_df = display_df.rename(columns={'Time_Display': 'Time'})

        # Show filtering info
        st.info(f"Found {len(display_df)} trains with numeric names")

        # Make the dataframe interactive
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            height=400,
            key="train_selector",
            column_order=column_order,
            disabled=["Train Name", "Station", "Sch_Time", "Time", "Status"],
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select to highlight on map",
                    default=False,
                ),
                "Time": st.column_config.TextColumn(
                    "Time",
                    help="Current time in 24-hour format"
                ),
                "Sch_Time": st.column_config.TextColumn(
                    "Scheduled Time",
                    help="Scheduled time in 24-hour format"
                )
            }
        )

        # Handle train selection
        if len(edited_df) > 0:
            # Get currently selected trains
            selected_trains = edited_df[edited_df['Select']]

            # Clear selection if no trains are selected
            if selected_trains.empty:
                st.session_state['selected_train'] = None
                st.session_state['previous_selection'] = None
            else:
                # Get the first selected train
                first_selected = selected_trains.iloc[0]

                # Create new selection
                new_selection = {
                    'train': first_selected['Train Name'],
                    'station': first_selected['Station']
                }

                # Only update if selection has changed
                if new_selection != st.session_state['previous_selection']:
                    st.session_state['selected_train'] = new_selection
                    st.session_state['previous_selection'] = new_selection

                    # Display detailed info for selected train
                    st.write({
                        'Scheduled Time': first_selected['Sch_Time'],
                        'Actual Time': first_selected['Time'],
                        'Current Status': first_selected['Status']
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