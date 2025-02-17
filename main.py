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

# Create two columns for layout
col1, col2 = st.columns([3, 2])

with col1:
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

            # Add scheduled time column
            def get_scheduled_time_with_logging(row):
                train_name = str(row['Train Name'])
                station = str(row['Station'])
                scheduled_time = st.session_state['train_schedule'].get_scheduled_time(
                    train_name, station
                )
                return scheduled_time if scheduled_time else 'Not Available'

            # Add Sch_Time column
            filtered_df['Sch_Time'] = filtered_df.apply(
                get_scheduled_time_with_logging,
                axis=1
            )

            # Reorder columns to show times side by side
            column_order = ['Train Name', 'Station', 'Sch_Time', 'Time', 'Status']
            filtered_df = filtered_df[column_order]

            # Show filtering info
            st.info(f"Found {len(filtered_df)} trains with numeric names")

            # Create container for train list
            train_container = st.container()

            # Add checkbox for each train
            for index, row in filtered_df.iterrows():
                train_id = f"{row['Train Name']}_{row['Station']}"
                if train_container.checkbox(
                    f"Train {row['Train Name']} at {row['Station']} - {row['Status']}",
                    key=train_id
                ):
                    st.session_state['selected_train'] = {
                        'train': row['Train Name'],
                        'station': row['Station']
                    }
                    # Display detailed info when selected
                    st.write({
                        'Scheduled Time': row['Sch_Time'],
                        'Actual Time': row['Time'],
                        'Current Status': row['Status']
                    })

        else:
            st.error(f"Error loading data: {message}")

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)

with col2:
    st.title("🗺️ Division Map")
    # Render the map using the MapViewer component
    st.session_state['map_viewer'].render(st.session_state.get('selected_train'))

# Footer
st.markdown("---")
st.markdown("Train Tracking System")