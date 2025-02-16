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
from PIL import Image
import numpy as np

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
if 'zoom_level' not in st.session_state:
    st.session_state['zoom_level'] = 1.0

# Station coordinates (normalized to image coordinates)
STATION_LOCATIONS = {
    'VNEC': {'x': 0.7, 'y': 0.3},  # Secunderabad
    'GALA': {'x': 0.65, 'y': 0.35}, # Gala
    'MBD': {'x': 0.68, 'y': 0.32},  # Malakpet
    'GWM': {'x': 0.72, 'y': 0.28},  # Gandhigram
    'PAVP': {'x': 0.75, 'y': 0.25}, # Pavalavagu
    'BZA': {'x': 0.5, 'y': 0.5},    # Vijayawada
}

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
    # Main title
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

            # Make the dataframe interactive
            selected_row = st.data_editor(
                filtered_df,
                use_container_width=True,
                height=400,
                key="train_selector"
            )

            # Update selected train in session state when a row is clicked
            if len(selected_row) > 0:
                selected_index = selected_row.index[0]
                st.session_state['selected_train'] = {
                    'train': selected_row.iloc[selected_index]['Train Name'],
                    'station': selected_row.iloc[selected_index]['Station']
                }

        else:
            st.error(f"Error loading data: {message}")

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)

with col2:
    st.title("🗺️ Division Map")

    try:
        # Add zoom control
        zoom_level = st.slider("Zoom Level", min_value=1.0, max_value=3.0, value=st.session_state['zoom_level'], step=0.1)
        st.session_state['zoom_level'] = zoom_level

        # Load the map image
        map_image = Image.open('Vijayawada_Division_System_map_page-0001 (2).jpg')

        # Create a copy of the image for modification
        display_image = map_image.copy()

        # If a train is selected, highlight its station
        if st.session_state['selected_train']:
            station_code = st.session_state['selected_train']['station']
            if station_code in STATION_LOCATIONS:
                # Get image dimensions
                width, height = display_image.size

                # Calculate station position
                station_pos = STATION_LOCATIONS[station_code]
                x = int(station_pos['x'] * width)
                y = int(station_pos['y'] * height)

                # Draw highlight circle
                from PIL import ImageDraw
                draw = ImageDraw.Draw(display_image)
                circle_radius = 20
                draw.ellipse([x-circle_radius, y-circle_radius, x+circle_radius, y+circle_radius], 
                           outline='red', width=3)

                # Add station label
                st.caption(f"Currently showing: {station_code}")

        # Apply zoom
        if zoom_level != 1.0:
            new_size = tuple(int(dim * zoom_level) for dim in display_image.size)
            display_image = display_image.resize(new_size, Image.Resampling.LANCZOS)

        # Display the image
        st.image(display_image, use_container_width=True, caption="Vijayawada Division System Map")

    except Exception as e:
        logger.error(f"Error loading map: {str(e)}")
        st.error("Error loading division map")

# Footer
st.markdown("---")
st.markdown("Train Tracking System")