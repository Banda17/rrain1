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
        /* Custom styling for the grid */
        .bs-grid-container {
            display: flex;
            width: 100%;
        }
        .bs-grid-left {
            flex: 6;
            padding-right: 10px;
        }
        .bs-grid-right {
            flex: 6;
            padding-left: 10px;
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

# Function to check if a value is positive or contains (+)
def is_positive_or_plus(value):
    try:
        if value is None:
            return False

        if isinstance(value, str):
            # Check if the string contains a plus sign
            if '+' in value:
                return True

            # Clean the string of any non-numeric characters except minus sign and decimal point
            # First handle the case with multiple values (like "-7 \xa0-36")
            if '\xa0' in value or '  ' in value:
                # Take just the first part if there are multiple numbers
                value = value.split('\xa0')[0].split('  ')[0].strip()

            # Remove parentheses and other characters
            clean_value = value.replace('(', '').replace(')', '').strip()

            # Try to convert to float
            if clean_value:
                try:
                    return float(clean_value) > 0
                except ValueError:
                    # If conversion fails, check if it starts with a minus sign
                    return not clean_value.startswith('-')
        elif isinstance(value, (int, float)):
            return value > 0
    except Exception as e:
        logger.error(f"Error in is_positive_or_plus: {str(e)}")
        return False
    return False

# Function to get station coordinates
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_station_coordinates():
    """Cache station coordinates for faster access"""
    return {
        'BZA': {'lat': 16.5167, 'lon': 80.6167},  # Vijayawada
        'GNT': {'lat': 16.3067, 'lon': 80.4365},  # Guntur
        'VSKP': {'lat': 17.6868, 'lon': 83.2185},  # Visakhapatnam
        'TUNI': {'lat': 17.3572, 'lon': 82.5483},  # Tuni
        'RJY': {'lat': 17.0005, 'lon': 81.7799},  # Rajahmundry
        'NLDA': {'lat': 17.0575, 'lon': 79.2690},  # Nalgonda
        'MGM': {'lat': 16.4307, 'lon': 80.5525},  # Mangalagiri
        'NDL': {'lat': 16.9107, 'lon': 81.6717},  # Nidadavolu
        'ANV': {'lat': 17.6910, 'lon': 83.0037},  # Anakapalle
        'VZM': {'lat': 18.1066, 'lon': 83.4205},  # Vizianagaram
        'SKM': {'lat': 18.2949, 'lon': 83.8935},  # Srikakulam
        'PLH': {'lat': 18.7726, 'lon': 84.4162},  # Palasa
    }

# Function to extract station codes from selected rows
def extract_station_codes(selected_stations, station_column=None):
    """Extract station codes from selected DataFrame"""
    selected_station_codes = []

    if selected_stations.empty:
        return selected_station_codes

    # Look for station code in various possible column names
    potential_station_columns = [
        'CRD', 'Station', 'Station Code', 'station', 'STATION'
    ]

    # If station_column is provided and exists in the DataFrame, use it
    if station_column and station_column in selected_stations.columns:
        potential_station_columns.insert(0, station_column)

    # Try each potential column
    for col_name in potential_station_columns:
        if col_name in selected_stations.columns:
            for _, row in selected_stations.iterrows():
                if pd.notna(row[col_name]):
                    # Extract station code from text
                    text_value = str(row[col_name]).strip().upper()

                    # Add to list if not already there
                    if text_value and text_value not in selected_station_codes:
                        selected_station_codes.append(text_value)

    return selected_station_codes

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

                # Add a "Select" column at the beginning of the DataFrame for checkboxes
                if 'Select' not in df.columns:
                    df.insert(0, 'Select', False)

                # Get station column name
                station_column = next(
                    (col for col in df.columns
                     if col in ['Station', 'station', 'STATION']), None)

                # Create a layout for train data and map side by side
                st.markdown('<div class="bs-grid-container">', unsafe_allow_html=True)

                # Table container
                st.markdown('<div class="bs-grid-left">', unsafe_allow_html=True)
                st.markdown("### Train Data")
                edited_df = st.data_editor(
                    df,
                    hide_index=True,
                    column_config={
                        "Select": st.column_config.CheckboxColumn("Select", help="Select to show on map", default=False),
                        "Train No.": st.column_config.TextColumn("Train No.", help="Train Number"),
                        "FROM-TO": st.column_config.TextColumn("FROM-TO", help="Source to Destination"),
                        "IC Entry Delay": st.column_config.TextColumn("IC Entry Delay", help="Entry Delay"),
                        "Delay": st.column_config.TextColumn("Delay", help="Delay in Minutes")
                    },
                    disabled=[col for col in df.columns if col != 'Select'],
                    use_container_width=True,
                    height=600,
                    num_rows="dynamic"
                )

                # Count selected stations
                selected_count = len(edited_df[edited_df['Select']])
                st.caption(f"Total Rows: {len(df)} | Selected: {selected_count}")

                st.markdown('</div>', unsafe_allow_html=True)  # Close table container

                # Map container
                st.markdown('<div class="bs-grid-right">', unsafe_allow_html=True)
                st.markdown("### Interactive GPS Map")

                # Extract station codes from selected rows
                selected_rows = edited_df[edited_df['Select']]
                selected_station_codes = extract_station_codes(selected_rows, station_column)

                # Station coordinates
                station_coords = get_station_coordinates()

                # Create the map
                m = folium.Map(location=[16.5167, 80.6167], zoom_start=7, control_scale=True)

                # Add a basemap with reduced opacity
                folium.TileLayer(
                    tiles='OpenStreetMap',
                    attr='&copy; OpenStreetMap contributors',
                    opacity=0.8
                ).add_to(m)

                # First add all non-selected stations as small dots
                for code, coords in station_coords.items():
                    # Skip selected stations - they'll get bigger markers later
                    if code.upper() in [s.upper() for s in selected_station_codes]:
                        continue

                    # Add small circle for the station
                    folium.CircleMarker(
                        [coords['lat'], coords['lon']],
                        radius=3,
                        color='#800000',  # Maroon red border
                        fill=True,
                        fill_color='gray',
                        fill_opacity=0.6,
                        opacity=0.8,
                        tooltip=f"{code}"
                    ).add_to(m)

                # Add markers for selected stations
                valid_points = []
                for code in selected_station_codes:
                    normalized_code = code.upper().strip()
                    if normalized_code in station_coords:
                        lat = station_coords[normalized_code]['lat']
                        lon = station_coords[normalized_code]['lon']

                        # Add train icon marker for selected stations
                        folium.Marker(
                            [lat, lon],
                            popup=f"<b>{normalized_code}</b><br>({lat:.4f}, {lon:.4f})",
                            tooltip=normalized_code,
                            icon=folium.Icon(color='red', icon='train', prefix='fa'),
                            opacity=0.8
                        ).add_to(m)

                        # Store points for drawing lines
                        valid_points.append([lat, lon])

                # Add railway lines between selected stations
                if len(valid_points) > 1:
                    folium.PolyLine(
                        valid_points,
                        weight=2,
                        color='gray',
                        opacity=0.8,
                        dash_array='5, 10'
                    ).add_to(m)

                # Display the map
                folium_static(m, width=650, height=600)

                # If stations are selected, show a message
                if selected_station_codes:
                    st.success(f"Showing {len(selected_station_codes)} selected stations on the map")
                else:
                    st.info("Select stations in the table to display them on the map")

                st.markdown('</div>', unsafe_allow_html=True)  # Close map container

                st.markdown('</div>', unsafe_allow_html=True)  # Close grid container

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