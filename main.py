import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from data_handler import DataHandler
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge
import logging
from typing import Optional, Dict
import re
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp
import folium
from folium.plugins import Draw
from streamlit_folium import folium_static
from map_viewer import MapViewer
from styling import TrainStyler

# Page configuration
st.set_page_config(
    page_title="Train Tracking System",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add Bootstrap CSS
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        /* Custom styles to enhance Bootstrap */
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        /* Add bootstrap compatible styles for Streamlit elements */
        [data-testid="stDataFrame"] table {
            border: 1px solid #dee2e6 !important;
            border-collapse: collapse !important;
            width: 100% !important;
        }
        [data-testid="stDataFrame"] th {
            background-color: #f8f9fa !important;
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
            font-weight: 600 !important;
        }
        [data-testid="stDataFrame"] td {
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
        }
        [data-testid="stDataFrame"] tr:nth-of-type(odd) {
            background-color: rgba(0,0,0,.05) !important;
        }
        [data-testid="stDataFrame"] tr:hover {
            background-color: rgba(0,0,0,.075) !important;
        }
    </style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize all session state variables"""
    if 'data_handler' not in st.session_state:
        st.session_state.data_handler = DataHandler()
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = Visualizer()
    if 'styling_enabled' not in st.session_state:
        st.session_state.styling_enabled = True

def create_header():
    """Create the page header with logo"""
    header_col1, header_col2 = st.columns([1, 5])

    with header_col1:
        try:
            st.markdown("""
                <div style="padding-top: 20px; display: flex; align-items: center; height: 100%;">
                    <img src="scr_logo.svg" width="120">
                </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Error loading SVG logo: {str(e)}")
            try:
                st.markdown("""
                    <div style="padding-top: 20px; display: flex; align-items: center; height: 100%;">
                        <img src="attached_assets/scr_logo.svg" width="120">
                    </div>
                """, unsafe_allow_html=True)
            except Exception as e2:
                st.warning(f"Error loading any logo: {str(e2)}")

    with header_col2:
        st.markdown("""
            <div class="card border-0">
                <div class="card-body p-0">
                    <h1 class="card-title text-primary mb-1">South Central Railway</h1>
                    <h2 class="card-subtitle text-secondary">Vijayawada Division</h2>
                </div>
            </div>
        """, unsafe_allow_html=True)

def main():
    initialize_session_state()

    # Create header
    create_header()
    st.markdown("<hr class='mt-2 mb-3'>", unsafe_allow_html=True)

    # Main title
    st.title("ICMSData- Vijayawada Division")

    # Add refresh button and styling toggle
    col1, col2, col3 = st.columns([8, 2, 2])
    with col2:
        if st.button("🔄", type="primary"):
            st.rerun()
    with col3:
        st.session_state.styling_enabled = st.checkbox("Enable Styling", value=st.session_state.styling_enabled)

    try:
        data_handler = st.session_state.data_handler

        # Load data with feedback
        with st.spinner("Loading data..."):
            success, message = data_handler.load_data_from_drive()

        if success:
            if data_handler.last_update:
                last_update_ist = data_handler.last_update + timedelta(hours=5, minutes=30)
                st.info(f"Last updated: {last_update_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")

            cached_data = data_handler.get_cached_data()

            if cached_data:
                df = pd.DataFrame(cached_data)

                if not df.empty:
                    # Skip first two rows and reset index
                    df = df.iloc[2:].reset_index(drop=True)

                    # Safe conversion of NaN values
                    for column in df.columns:
                        df[column] = df[column].apply(lambda x: str(x) if pd.notna(x) else None)

                    # Add Select column
                    if 'Select' not in df.columns:
                        df.insert(0, 'Select', False)

                    # Apply styling if enabled
                    if st.session_state.styling_enabled:
                        display_df = TrainStyler.apply_train_styling(df)
                    else:
                        display_df = df

                    # Display the DataFrame
                    st.dataframe(display_df)

                else:
                    st.warning("No data available to display")
            else:
                st.error("No cached data available")
        else:
            st.error(f"Failed to load data: {message}")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logger.error(f"Error in main app: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()