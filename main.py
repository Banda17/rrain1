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
import re
from animation_utils import create_pulsing_refresh_animation, show_countdown_progress, show_refresh_timestamp
import folium
from folium.plugins import Draw
from streamlit_folium import folium_static
from map_viewer import MapViewer  # Import MapViewer for offline map handling

# Page configuration - MUST be the first Streamlit command
st.set_page_config(page_title="Train Tracking System",
                    page_icon="🚂",
                    layout="wide",
                    initial_sidebar_state="collapsed")

# Configure logging
logging.basicConfig(level=logging.INFO)
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

        /* Crucial fix - remove ALL gaps in Streamlit columns */
        /* This is the key to making adjacent columns with no gap */
        div[data-testid="column"] {
            padding: 0 !important;
            margin: 0 !important;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        /* Fix the block container to make Streamlit elements appear correctly */
        .block-container {
            max-width: 100% !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            margin: 0 !important;
        }

        /* Hide streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}

        /* Add a separator between table and map */
        .with-border-right {
            border-right: 1px solid #dee2e6;
        }
    </style>
""", unsafe_allow_html=True)


# ----- Callback Functions for Handling Checkbox Selection -----

def on_station_selection_change():
    """Callback function to handle checkbox changes in data editor"""
    try:
        # Get edited dataframe from session state
        if 'dataframe' in st.session_state:
            df = st.session_state.dataframe

            # Get selected rows (where Select column is True)
            selected_rows = df[df['Select'] == True]

            # Extract station codes from selected rows
            selected_stations = []
            if not selected_rows.empty:
                # Try to get stations from 'Station' column
                if 'Station' in selected_rows.columns:
                    for station in selected_rows['Station'].dropna().unique():
                        if station:
                            selected_stations.append(str(station).strip())

                # Also try 'CRD' column if available
                if 'CRD' in selected_rows.columns:
                    for crd in selected_rows['CRD'].dropna().unique():
                        if crd:
                            # Extract first word which is likely the station code
                            code = str(crd).strip().split()[0]
                            if code and code not in selected_stations:
                                selected_stations.append(code)

            # Save to session state
            st.session_state['selected_stations'] = selected_stations
            logger.info(f"Selected stations updated: {selected_stations}")
    except Exception as e:
        logger.error(f"Error in selection callback: {str(e)}")
        st.session_state['selected_stations'] = []


def initialize_session_state():
    """Initialize all session state variables with proper typing"""
    state_configs = {
        'data_handler': {
            'default': DataHandler(),
            'type': DataHandler
        },
        'visualizer': {
            'default': Visualizer(),
            'type': Visualizer
        },
        'train_schedule': {
            'default': TrainSchedule(),
            'type': TrainSchedule
        },
        'last_update': {
            'default': None,
            'type': Optional[datetime]
        },
        'selected_train': {
            'default': None,
            'type': Optional[Dict]
        },
        'selected_train_details': {
            'default': {},
            'type': Dict
        },
        'filter_status': {
            'default': 'Late',
            'type': str
        },
        'last_refresh': {
            'default': datetime.now(),
            'type': datetime
        },
        'is_refreshing': {
            'default': False,
            'type': bool
        },
        'map_stations': {  # New state variable for map stations
            'default': [],
            'type': list
        },
        'selected_stations': {  # Store selected stations
            'default': [],
            'type': list
        },
        'map_viewer': {  # Add MapViewer to session state
            'default': MapViewer(),
            'type': MapViewer
        },
        'db_initialized': {  # New state variable to track database initialization
            'default': False,
            'type': bool
        },
        'map_type': {  # Store map type selection
            'default': "Offline Map with GPS Markers",
            'type': str
        },
        'dataframe': {  # Store the main dataframe
            'default': pd.DataFrame(),
            'type': pd.DataFrame
        }
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


def update_selected_train_details(selected):
    """Update the selected train details in session state"""
    try:
        # Clear selection if selected is None or empty DataFrame
        if selected is None or (isinstance(selected, pd.Series)
                                and selected.empty):
            st.session_state['selected_train'] = None
            st.session_state['selected_train_details'] = {}
            return

        # Extract values safely from pandas Series
        if isinstance(selected, pd.Series):
            station = selected.get('Station', '')
            train_name = selected.get('Train Name', '')
            sch_time = selected.get('Sch_Time', '')
            current_time = selected.get('Current Time', '')
            status = selected.get('Status', '')
            delay = selected.get('Delay', '')
        else:
            station = selected.get('Station', '')
            train_name = selected.get('Train Name', '')
            sch_time = selected.get('Sch_Time', '')
            current_time = selected.get('Current Time', '')
            status = selected.get('Status', '')
            delay = selected.get('Delay', '')

        st.session_state['selected_train'] = {
            'train': train_name,
            'station': station
        }
        st.session_state['selected_train_details'] = {
            'Scheduled Time': sch_time,
            'Actual Time': current_time,
            'Current Status': status,
            'Delay': delay
        }
        logger.debug(
            f"Updated selected train: {st.session_state['selected_train']}")

    except Exception as e:
        logger.error(f"Error updating selected train details: {str(e)}")
        st.session_state['selected_train'] = None
        st.session_state['selected_train_details'] = {}

def handle_timing_status_change():
    """Handle changes in timing status filter"""
    st.session_state['filter_status'] = st.session_state.get(
        'timing_status_select', 'Late')
    logger.debug(
        f"Timing status changed to: {st.session_state['filter_status']}")

def extract_stations_from_data(df):
    """Extract unique stations from the data for the map"""
    stations = []
    if df is not None and not df.empty:
        # Try different column names that might contain station information
        station_columns = [
            'Station', 'station', 'STATION', 'Station Name', 'station_name'
        ]
        for col in station_columns:
            if col in df.columns:
                # Extract unique values and convert to list
                stations = df[col].dropna().unique().tolist()
                break

    # Store in session state for use in the map
    st.session_state['map_stations'] = stations
    return stations

@st.cache_data(ttl=300)
def load_and_process_data():
    """Cache data loading and processing"""
    success, message = st.session_state[
        'icms_data_handler'].load_data_from_drive()
    if success:
        status_table = st.session_state[
            'icms_data_handler'].get_train_status_table()
        cached_data = st.session_state['icms_data_handler'].get_cached_data()
        if cached_data:
            return True, status_table, pd.DataFrame(cached_data), message
    return False, None, None, message

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_station_coordinates():
    """Cache station coordinates for faster access"""
    return {
        'BZA': {
            'lat': 16.5167,
            'lon': 80.6167
        },  # Vijayawada
        'GNT': {
            'lat': 16.3067,
            'lon': 80.4365
        },  # Guntur
        'VSKP': {
            'lat': 17.6868,
            'lon': 83.2185
        },  # Visakhapatnam
        'TUNI': {
            'lat': 17.3572,
            'lon': 82.5483
        },  # Tuni
        'RJY': {
            'lat': 17.0005,
            'lon': 81.7799
        },  # Rajahmundry
        'NLDA': {
            'lat': 17.0575,
            'lon': 79.2690
        },  # Nalgonda
        'MTM': {
            'lat': 16.4307,
            'lon': 80.5525
        },  # Mangalagiri
        'NDL': {
            'lat': 16.9107,
            'lon': 81.6717
        },  # Nidadavolu
        'ANV': {
            'lat': 17.6910,
            'lon': 83.0037
        },  # Anakapalle
        'VZM': {
            'lat': 18.1066,
            'lon': 83.4205
        },  # Vizianagaram
        'SKM': {
            'lat': 18.2949,
            'lon': 83.8935
        },  # Srikakulam
        'PLH': {
            'lat': 18.7726,
            'lon': 84.4162
        },  # Palasa
        'GDR': {
            'lat': 14.1487258,
            'lon': 79.8456503
        },
        'MBL': {
            'lat': 14.2258343,
            'lon': 79.8779689
        },
        'KMLP': {
            'lat': 14.2258344,
            'lon': 79.8779689
        },
        'VKT': {
            'lat': 14.3267653,
            'lon': 79.9270371
        },
        'VDE': {
            'lat': 14.4064058,
            'lon': 79.9553191
        },
        'NLR': {
            'lat': 14.4530742,
            'lon': 79.9868332
        },
        'PGU': {
            'lat': 14.4980222,
            'lon': 79.9901535
        },
        'KJJ': {
            'lat': 14.5640002,
            'lon': 79.9938934
        },
        'AXR': {
            'lat': 14.7101,
            'lon': 79.9893
        },
        'BTTR': {
            'lat': 14.7743359,
            'lon': 79.9667298
        },
        'SVPM': {
            'lat': 14.7949226,
            'lon': 79.9624715
        },
        'KVZ': {
            'lat': 14.9242136,
            'lon': 79.9788932
        },
        'TTU': {
            'lat': 15.0428954,
            'lon': 80.0044243
        },
        'UPD': {
            'lat': 15.1671213,
            'lon': 80.0131329
        },
        'SKM': {
            'lat': 15.252886,
            'lon': 80.026428
        },
        'OGL': {
            'lat': 15.497849,
            'lon': 80.0554939
        },
        'KRV': {
            'lat': 15.5527145,
            'lon': 80.1134587
        },
        'ANB': {
            'lat': 15.596741,
            'lon': 80.1362815
        },
        'RPRL': {
            'lat': 15.6171364,
            'lon': 80.1677164
        },
        'UGD': {
            'lat': 15.6481768,
            'lon': 80.1857879
        },
        'KVDV': {
            'lat': 15.7164922,
            'lon': 80.2369806
        },
        'KPLL': {
            'lat': 15.7482165,
            'lon': 80.2573225
        },
        'VTM': {
            'lat': 15.7797094,
            'lon': 80.2739975
        },
        'JAQ': {
            'lat': 15.8122497,
            'lon': 80.3030082
        },
        'CLX': {
            'lat': 15.830938,
            'lon': 80.3517708
        },
        'NZD': {
            'lat': 16.717923,
            'lon': 80.8230084
        },
        'VAT': {
            'lat': 16.69406,
            'lon': 81.0399239
        },
    }

@st.cache_data(ttl=60)
def render_offline_map_with_markers(selected_station_codes,
                                     station_coords,
                                     marker_opacity=0.8):
    """Render an offline map with GPS markers for selected stations"""
    # Get the map viewer from session state or create a new one
    map_viewer = st.session_state.get('map_viewer', MapViewer())

    # Temporarily increase marker size
    original_marker_size = map_viewer.base_marker_size
    map_viewer.base_marker_size = 25  # Increased from default 15 to 25

    # Load the base map
    base_map = map_viewer.load_map()
    if base_map is None:
        # Restore original marker size before returning
        map_viewer.base_marker_size = original_marker_size
        return None, []

    # Create a copy of the base map to draw on
    display_image = base_map.copy()

    # First, draw small dots for all stations
    from PIL import ImageDraw
    draw = ImageDraw.Draw(display_image)

    # Draw small dots for all stations (non-selected)
    for code, coords in station_coords.items():
        # Skip if this is a selected station (will be drawn with a marker later)
        if code in selected_station_codes:
            continue

        # Try to convert GPS coordinates to map coordinates
        if code in map_viewer.station_locations:
            # Use existing map coordinates
            x_norm = map_viewer.station_locations[code]['x']
            y_norm = map_viewer.station_locations[code]['y']

            # Convert normalized coordinates to pixel coordinates
            width, height = display_image.size
            x = int(x_norm * width)
            y = int(y_norm * height)

            # Draw a small dot (5 pixel radius)
            dot_radius = 5
            draw.ellipse(
                (x - dot_radius, y - dot_radius, x + dot_radius,
                 y + dot_radius),
                fill=(100, 100, 100, 180))  # Gray with some transparency
        else:
            # Convert GPS to approximate map coordinates
            try:
                # Approximate conversion
                x_norm = (coords['lon'] - 79.0) / 5.0
                y_norm = (coords['lat'] - 14.0) / 5.0

                # Add to map_viewer's station locations for future use
                map_viewer.station_locations[code] = {'x': x_norm, 'y': y_norm}

                # Convert normalized coordinates to pixel coordinates
                width, height = display_image.size
                x = int(x_norm * width)
                y = int(y_norm * height)

                # Draw a small dot
                dot_radius = 5
                draw.ellipse(
                    (x - dot_radius, y - dot_radius, x + dot_radius,
                     y + dot_radius),
                    fill=(100, 100, 100, 180))  # Gray with some transparency
            except:
                # Skip if conversion fails
                continue

    # Keep track of displayed stations
    displayed_stations = []

    # Draw markers for each selected station
    for code in selected_station_codes:
        normalized_code = code.upper().strip()

        # Check if we have the station in the map_viewer's station locations
        if normalized_code in map_viewer.station_locations:
            display_image = map_viewer.draw_train_marker(
                display_image, normalized_code)
            displayed_stations.append(normalized_code)
        elif normalized_code in station_coords:
            # GPS coordinates to normalized map coordinates (approximate conversion)
            # This is a simplified conversion - would need proper calibration for accuracy
            coords = station_coords[normalized_code]

            # Add to map_viewer's station locations (temporary)
            map_viewer.station_locations[normalized_code] = {
                'x': (coords['lon'] - 79.0) / 5.0,  # Approximate conversion
                'y': (coords['lat'] - 14.0) / 5.0   # Approximate conversion
            }

            # Draw the marker
            display_image = map_viewer.draw_train_marker(
                display_image, normalized_code)
            displayed_stations.append(normalized_code)

    # Restore original marker size
    map_viewer.base_marker_size = original_marker_size

    # Apply opacity to the image
    def apply_marker_opacity(img, opacity):
        """Apply opacity to the non-background pixels of an image"""
        if opacity >= 1.0:  # No change needed if fully opaque
            return img

        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        # Create a copy to work with
        result = img.copy()

        # Get pixel data
        pixdata = result.load()

        # Adjust alpha channel for pixels that are not fully transparent
        width, height = img.size
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixdata[x, y]
                if a > 0:  # Only modify non-transparent pixels
                    pixdata[x, y] = (r, g, b, int(a * opacity))

        return result

    if marker_opacity < 1.0:
        display_image = apply_marker_opacity(display_image, marker_opacity)

    return display_image, displayed_stations


# Initialize session state
initialize_session_state()

# Create header section with Bootstrap grid
st.markdown("""
<div class="container-fluid">
    <div class="row">
        <div class="col-2">
            <img src="scr_logo.svg" width="80" alt="SCR Logo">
        </div>
        <div class="col-10">
            <div class="card border-0">
                <div class="card-body p-0">
                    <h1 class="card-title text-primary mb-1">South Central Railway</h1>
                    <h2 class="card-subtitle text-secondary">Vijayawada Division</h2>
                </div>
            </div>
        </div>
    </div>
    <hr class="mt-2 mb-3">
</div>
""", unsafe_allow_html=True)

# Add a refresh button at the top
st.markdown("""
<div class="container-fluid">
    <div class="row">
        <div class="col-10"></div>
        <div class="col-2 text-end">
            <button class="btn btn-primary" id="refresh-btn" onclick="window.location.reload();">🔄 Refresh</button>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

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
            st.info(
                f"Last updated: {last_update_ist.strftime('%Y-%m-%d %H:%M:%S')} IST"
            )

        # Get cached data
        cached_data = data_handler.get_cached_data()

        if cached_data:
            # Convert to DataFrame
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

                # Extract stations for map
                stations = extract_stations_from_data(df)

                # Drop unwanted columns
                columns_to_drop = [
                    'Sr.',
                    'Exit Time for NLT Status',
                    'FROM-TO',
                    'Start date',
                    # Try different column name variations
                    'Scheduled [ Entry - Exit ]',
                    'Scheduled [Entry - Exit]',
                    'Scheduled[ Entry - Exit ]',
                    'Scheduled[Entry - Exit]',
                    'Scheduled [ Entry-Exit ]',
                    'Scheduled [Entry-Exit]',
                    'scheduled[Entry-Exit]',
                    'DivisionalActual[ Entry - Exit ]',
                    'Divisional Actual [Entry- Exit]',
                    'Divisional Actual[ Entry-Exit ]',
                    'Divisional Actual[ Entry - Exit ]',
                    'DivisionalActual[ Entry-Exit ]',
                    'Divisional Actual [Entry-Exit]'
                ]

                # Drop each column individually if it exists
                for col in columns_to_drop:
                    if col in df.columns:
                        df = df.drop(columns=[col])

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

                # Get filtered dataframe for display
                filtered_df = df.copy()

                # Define styling function with specific colors
                def highlight_delay(data):
                    styles = pd.DataFrame('', index=data.index, columns=data.columns)

                    # Apply red color only to the 'Delay' column if it exists
                    if 'Delay' in df.columns:
                        styles['Delay'] = df['Delay'].apply(
                            lambda x: 'color: red; font-weight: bold' if x and is_positive_or_plus(x) else '')

                    return styles

                # Add a "Select" column at the beginning of the DataFrame for checkboxes
                if 'Select' not in filtered_df.columns:
                    filtered_df.insert(0, 'Select', False)

                # Get station column name
                station_column = next(
                    (col for col in filtered_df.columns
                     if col in ['Station', 'station', 'STATION']), None)

                # ------[ Create Side-by-Side Layout ]------

                # Create two columns with no gap between them
                left_col, right_col = st.columns([6, 4])

                # Left column for the table - add a right border
                with left_col:
                    # Refresh animation placeholder
                    refresh_table_placeholder = st.empty()
                    create_pulsing_refresh_animation(refresh_table_placeholder, "Refreshing Table...")

                    # Card container for the table with right border
                    st.markdown('<div class="card with-border-right" style="height:100%;"><div class="card-header bg-primary text-white p-1">Train Data</div><div class="card-body p-0">', unsafe_allow_html=True)

                    # Use data_editor to make the table interactive with checkboxes
                    # Store the dataframe in session state first
                    st.session_state.dataframe = filtered_df.copy()

                    # Now use data_editor with on_change callback
                    edited_df = st.data_editor(
                        st.session_state.dataframe,
                        hide_index=True,
                        column_config={
                            "Select": st.column_config.CheckboxColumn(
                                "Select",
                                help="Select to show on map",
                                default=False),
                            "Train No.": st.column_config.TextColumn(
                                "Train No.", help="Train Number"),
                            "FROM-TO": st.column_config.TextColumn(
                                "FROM-TO", help="Source to Destination"),
                            "IC Entry Delay": st.column_config.TextColumn(
                                "IC Entry Delay", help="Entry Delay"),
                            "Delay": st.column_config.TextColumn(
                                "Delay", help="Delay in Minutes")
                        },
                        disabled=[col for col in filtered_df.columns if col != 'Select'],
                        use_container_width=True,
                        height=650,
                        key="dataframe",
                        on_change=on_station_selection_change
                    )

                    # Show selected stations for debugging
                    selected_stations = st.session_state.get('selected_stations', [])
                    if selected_stations:
                        st.caption(f"Selected stations: {', '.join(selected_stations)}")
                    else:
                        st.caption("No stations selected. Click checkboxes to select stations.")

                    st.markdown('</div></div>', unsafe_allow_html=True)
                    refresh_table_placeholder.empty()

                # Right column for the map
                with right_col:
                    # Card container for the map
                    st.markdown('<div class="card" style="height:100%;"><div class="card-header bg-secondary text-white p-1">Station Map</div><div class="card-body p-0">', unsafe_allow_html=True)

                    # Get cached station coordinates
                    station_coords = get_station_coordinates()

                    # Get selected stations
                    selected_stations = st.session_state.get('selected_stations', [])

                    # Display the appropriate map based on the current map type
                    map_type = st.session_state.get('map_type', "Offline Map with GPS Markers")

                    if map_type == "Offline Map with GPS Markers":
                        # Show selected stations
                        if selected_stations:
                            st.caption(f"Showing selected stations: {', '.join(selected_stations)}")

                        # Render offline map with markers
                        display_image, displayed_stations = render_offline_map_with_markers(
                            selected_stations, station_coords)

                        if display_image is not None:
                            # Convert and resize for display if needed
                            from PIL import Image
                            displayimage = display_image.convert('RGB')

                            # Display the map
                            st.image(
                                display_image,
                                use_container_width=True,
                                caption="Vijayawada Division System Map"
                            )

                            # Show station count
                            if displayed_stations:
                                st.success(f"Showing {len(displayed_stations)} selected stations")
                            else:
                                st.info("Select stations by checking boxes in the table")
                        else:
                            st.error("Unable to load the offline map")
                    else:
                        # Create the interactive map
                        m = folium.Map(
                            location=[16.5167, 80.6167],  # Centered around Vijayawada
                            zoom_start=7,
                            control_scale=True)

                        # Add a basemap
                        folium.TileLayer(
                            tiles='OpenStreetMap',
                            attr='&copy; OpenStreetMap contributors',
                            opacity=0.8).add_to(m)

                        # Add markers for stations
                        displayed_stations = []
                        valid_points = []

                        # Add train markers for selected stations
                        for code in selected_stations:
                            normalized_code = code.upper().strip()
                            if normalized_code in station_coords:
                                lat = station_coords[normalized_code]['lat']
                                lon = station_coords[normalized_code]['lon']

                                # Add train icon marker
                                folium.Marker(
                                    [lat, lon],
                                    popup=f"<b>{normalized_code}</b>",
                                    tooltip=normalized_code,
                                    icon=folium.Icon(color='red', icon='train', prefix='fa'),
                                    opacity=0.8).add_to(m)

                                displayed_stations.append(normalized_code)
                                valid_points.append([lat, lon])

                        # Add railway lines between selected stations
                        if len(valid_points) > 1:
                            folium.PolyLine(
                                valid_points,
                                weight=2,
                                color='gray',
                                opacity=0.8,
                                dash_array='5, 10').add_to(m)

                        # Render the map
                        folium_static(m, width=None, height=600)

                    # Map type selection callback
                    def change_map_type():
                        st.session_state.map_type = st.session_state.map_type_selector

                    # Map type selection radio buttons
                    st.radio(
                        "Map Type",
                        ["Offline Map with GPS Markers", "Interactive GPS Map"],
                        index=0 if map_type == "Offline Map with GPS Markers" else 1,
                        horizontal=True,
                        key="map_type_selector",
                        on_change=change_map_type
                    )

                    st.markdown('</div></div>', unsafe_allow_html=True)

            else:
                st.error("No data available in the cached data frame")
        else:
            st.error("No cached data available")
    else:
        st.error(f"Failed to load data: {message}")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)
    logger.error(f"Error in main app: {str(e)}")

# Footer
st.markdown("""
<div class="card mt-2">
    <div class="card-body text-center text-muted p-1">
        © 2023 South Central Railway - Vijayawada Division
    </div>
</div>
""", unsafe_allow_html=True)