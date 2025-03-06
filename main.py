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
import folium
from folium.plugins import Draw
from streamlit_folium import folium_static
from map_viewer import MapViewer

# Page configuration
st.set_page_config(page_title="Train Tracking System",
                   page_icon="🚂",
                   layout="wide",
                   initial_sidebar_state="collapsed")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add Bootstrap CSS
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        /* Bootstrap grid container for side-by-side layout */
        .bs-grid-container {
            display: flex;
            width: 100%;
            margin: 0;
            padding: 0;
        }
        .bs-grid-left {
            flex: 6;
            padding-right: 10px;
            min-width: 600px;
        }
        .bs-grid-right {
            flex: 6;
            padding-left: 10px;
            min-width: 600px;
        }
        @media (max-width: 1200px) {
            .bs-grid-container {
                flex-direction: column;
            }
            .bs-grid-left, .bs-grid-right {
                flex: 100%;
                padding: 0;
                width: 100%;
                min-width: 100%;
            }
        }
        /* Additional styling for tables and other elements */
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
    # Initialize all session state variables with proper typing
    state_configs = {
        'data_handler': {'default': DataHandler(), 'type': DataHandler},
        'visualizer': {'default': Visualizer(), 'type': Visualizer},
        'train_schedule': {'default': TrainSchedule(), 'type': TrainSchedule},
        'last_update': {'default': None, 'type': Optional[datetime]},
        'selected_train': {'default': None, 'type': Optional[Dict]},
        'selected_train_details': {'default': {}, 'type': Dict},
        'filter_status': {'default': 'Late', 'type': str},
        'last_refresh': {'default': datetime.now(), 'type': datetime},
        'is_refreshing': {'default': False, 'type': bool},
        'map_stations': {'default': [], 'type': list},
        'selected_stations': {'default': [], 'type': list},
        'map_viewer': {'default': MapViewer(), 'type': MapViewer},
        'db_initialized': {'default': False, 'type': bool}
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

# Initialize sessionstate
initialize_session_state()

# Main page title
st.title("ICMS Data - Vijayawada Division")

# Add a refresh button at the top with just an icon
col1, col2 = st.columns((10, 2))
with col2:
    if st.button("🔄", type="primary"):
        st.rerun()

try:
    data_handler = st.session_state['icms_data_handler']

    # Load data with feedback
    with st.spinner("Loading data..."):
        success, message = data_handler.load_data_from_drive()

    if success:
        # Show last update time
        if data_handler.last_update:
            # Convert last update to IST (UTC+5:30)
            last_update_ist = data_handler.last_update + timedelta(hours=5, minutes=30)
            st.info(f"Last updated: {last_update_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")

        cached_data = data_handler.get_cached_data()

        if cached_data:
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
                for column in df.columns:
                    df[column] = df[column].map(safe_convert)

                # Create a layout for train data and map side by side
                train_data_col, map_col = st.columns((3, 2))

                # Train data section
                with train_data_col:
                    st.markdown("### Train Data")
                    # Add a "Select" column for checkboxes if not present
                    if 'Select' not in df.columns:
                        df.insert(0, 'Select', False)

                    edited_df = st.data_editor(
                        df,
                        hide_index=True,
                        column_config={
                            "Select": st.column_config.CheckboxColumn("Select", default=False),
                            "Train No.": st.column_config.TextColumn("Train No."),
                            "FROM-TO": st.column_config.TextColumn("FROM-TO"),
                            "IC Entry Delay": st.column_config.TextColumn("IC Entry Delay"),
                            "Delay": st.column_config.TextColumn("Delay")
                        },
                        disabled=[col for col in df.columns if col != 'Select'],
                        use_container_width=True,
                        height=600,
                        num_rows="dynamic"
                    )

                # Map section
                with map_col:
                    st.markdown("### Interactive GPS Map")

                    # Extract station codes from selected rows
                    selected_rows = edited_df[edited_df['Select']]
                    selected_station_codes = []

                    # Define a function to extract station codes
                    def extract_station_codes(selected_stations):
                        codes = []
                        station_column = next(
                            (col for col in selected_stations.columns
                             if col in ['Station', 'station', 'STATION']), None)

                        if station_column and not selected_stations.empty:
                            for _, row in selected_stations.iterrows():
                                if pd.notna(row[station_column]):
                                    code = str(row[station_column]).strip()
                                    if code and code not in codes:
                                        codes.append(code)
                        return codes

                    # Get station coordinates using a dictionary
                    def get_station_coordinates():
                        return {
                            'BZA': {'lat': 16.5167, 'lon': 80.6167},  # Vijayawada
                            'GNT': {'lat': 16.3067, 'lon': 80.4365},  # Guntur
                            'VSKP': {'lat': 17.6868, 'lon': 83.2185},  # Visakhapatnam
                            # Add more stations as needed
                        }

                    # Extract station codes and create map
                    selected_station_codes = extract_station_codes(selected_rows)
                    station_coords = get_station_coordinates()

                    # Create the map
                    m = folium.Map(location=[16.5167, 80.6167], zoom_start=7)

                    # Add markers for selected stations
                    for code in selected_station_codes:
                        if code in station_coords:
                            coords = station_coords[code]
                            folium.Marker(
                                [coords['lat'], coords['lon']],
                                popup=f"{code}",
                                tooltip=code,
                                icon=folium.Icon(color='red', icon='train', prefix='fa')
                            ).add_to(m)

                    # Display the map
                    folium_static(m, width=650, height=600)

            else:
                st.error("No data available in the cached data frame")
        else:
            st.error("No cached data available")
    else:
        st.error(f"Failed to load data: {message}")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    logger.error(f"Error in main app: {str(e)}")

# Footer
st.markdown("---")
st.markdown('<div class="card"><div class="card-body text-center text-muted">© 2023 South Central Railway - Vijayawada Division</div></div>', unsafe_allow_html=True)