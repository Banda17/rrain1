import streamlit as st
import pandas as pd
from data_handler import DataHandler
from ai_analyzer import AIAnalyzer
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge, show_ai_insights
from database import init_db
from train_schedule import TrainSchedule
import time
from datetime import datetime
import logging

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

# Main title
st.title("🚂 Train List")

try:
    # Load data with caching
    success, status_table, cached_data, message = load_and_process_data()

    if success and cached_data is not None and not cached_data.empty:
        # Log the columns for debugging
        logger.debug(f"DataFrame columns: {cached_data.columns}")

        # Reset the index and use first row as header
        cached_data.columns = cached_data.iloc[0]
        cached_data = cached_data.iloc[1:].reset_index(drop=True)

        # Filter trains that start with numbers
        numeric_trains = cached_data[cached_data['Train Name'].str.match(r'^\d.*', na=False)]

        # Show filtering info
        st.info(f"Found {len(numeric_trains)} trains with numeric names")

        # Add Sch_Time column with debug logging
        def get_scheduled_time_with_logging(row):
            train_name = row['Train Name']
            station = row['Station']
            logger.debug(f"Getting schedule for train {train_name} at station {station}")
            scheduled_time = st.session_state['train_schedule'].get_scheduled_time(
                train_name, station
            )
            logger.debug(f"Got scheduled time: {scheduled_time}")
            return scheduled_time or ''

        numeric_trains['Sch_Time'] = numeric_trains.apply(
            get_scheduled_time_with_logging,
            axis=1
        )

        # Select only required columns including Time and Sch_Time
        selected_columns = ['Train Name', 'Station', 'Time', 'Sch_Time', 'Status']
        display_data = numeric_trains[selected_columns]

        # Display the filtered data
        st.dataframe(
            display_data,
            use_container_width=True,
            height=400
        )
    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    logger.error(f"Error occurred: {str(e)}", exc_info=True)
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("Train Tracking System")