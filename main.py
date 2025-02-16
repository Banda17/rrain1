import streamlit as st
import pandas as pd
from data_handler import DataHandler
from train_schedule import TrainSchedule
from simple_map_view import render_simple_map
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Train Tracking System",
    page_icon="🚂",
    layout="wide"
)

# Initialize session state
if 'data_handler' not in st.session_state:
    st.session_state['data_handler'] = DataHandler()
if 'train_schedule' not in st.session_state:
    st.session_state['train_schedule'] = TrainSchedule()
if 'selected_train' not in st.session_state:
    st.session_state['selected_train'] = None

# Create two columns for layout
col1, col2 = st.columns([3, 2])

with col1:
    st.title("🚂 Train List")

    try:
        # Get train data
        df = st.session_state['data_handler'].get_train_status_table()

        if not df.empty:
            # Display train list
            st.dataframe(
                df,
                use_container_width=True,
                height=400,
                column_config={
                    "train_id": "Train Number",
                    "station": "Station",
                    "time_actual": "Actual Time",
                    "time_scheduled": "Scheduled Time",
                    "status": "Status",
                    "delay": "Delay (min)"
                }
            )

            # Allow train selection
            selected_train_id = st.selectbox(
                "Select Train to Track",
                options=df['train_id'].unique(),
                format_func=lambda x: f"Train {x}"
            )

            if selected_train_id:
                train_info = df[df['train_id'] == selected_train_id].iloc[0]
                st.session_state['selected_train'] = {
                    'train': selected_train_id,
                    'station': train_info['station']
                }

        else:
            st.info("No train data available")

    except Exception as e:
        logger.error(f"Error loading train data: {str(e)}")
        st.error("Error loading train data")

with col2:
    # Render the simple map view
    render_simple_map(st.session_state.get('selected_train'))

# Footer
st.markdown("---")
st.markdown("Train Tracking System - Vijayawada Division")