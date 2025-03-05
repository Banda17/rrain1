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


def parse_time(time_str: str) -> Optional[datetime]:
    """Parse time string in HH:MM format to datetime object"""
    try:
        # If time string is empty, None, or "Not Available"
        if not time_str or time_str.strip().lower() == "not available":
            return None

        # Extract only the time part (HH:MM) from the string
        time_part = time_str.split()[0] if time_str else ''
        if not time_part:
            return None

        # Validate time format (HH:MM)
        if not ':' in time_part or len(time_part.split(':')) != 2:
            logger.warning(f"Invalid time format: {time_str}")
            return None

        return datetime.strptime(time_part, '%H:%M')
    except Exception as e:
        logger.debug(f"Error parsing time {time_str}: {str(e)}")
        return None


def calculate_time_difference(scheduled: str, actual: str) -> Optional[int]:
    """Calculate time difference in minutes between scheduled and actual times"""
    try:
        # Return None if either time is empty or "Not Available"
        if pd.isna(scheduled) or pd.isna(actual) or \
           scheduled.strip().lower() == "not available" or \
           actual.strip().lower() == "not available":
            return None

        sch_time = parse_time(scheduled)
        act_time = parse_time(actual)

        if sch_time and act_time:
            # Convert both times to same date for comparison
            diff = (act_time - sch_time).total_seconds() / 60
            return int(diff)
        return None
    except Exception as e:
        logger.debug(f"Error calculating time difference: {str(e)}")
        return None


def format_delay_value(delay: Optional[int]) -> str:
    """Format delay value with appropriate indicator"""
    try:
        if delay is None:
            return "N/A"
        elif delay > 5:
            return f"⚠️ +{delay}"
        elif delay < -5:
            return f"⏰ {delay}"
        else:
            return f"✅ {delay}"
    except Exception as e:
        logger.error(f"Error formatting delay value: {str(e)}")
        return "N/A"

# Create a layout for the header with logo
col1, col2 = st.columns([1, 5])

# Display the logo in the first column
with col1:
    try:
        # Try loading the new logo first
        st.image("attached_assets/scr_logo.png", width=80)
    except Exception as e:
        st.warning(f"Error loading new logo: {str(e)}")
        # Try fallback to the original logo
        try:
            st.image("scr_logo.png", width=80)
        except Exception as e2:
            st.warning(f"Error loading any logo: {str(e2)}")

# Display the title and subtitle in the second column
with col2:
    st.markdown("""
        <div class="card border-0">
            <div class="card-body p-0">
                <h1 class="card-title text-primary mb-1">South Central Railway</h1>
                <h2 class="card-subtitle text-secondary">Vijayawada Division</h2>
            </div>
        </div>
    """,
                unsafe_allow_html=True)

# Add a horizontal line to separate the header from content
st.markdown("<hr class='mt-2 mb-3'>", unsafe_allow_html=True)


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
        'selected_stations': {  # New state variable for selected stations
            'default': [],
            'type': list
        },
        'map_viewer': {  # Add MapViewer to session state
            'default': MapViewer(),
            'type': MapViewer
        },
        'db_initialized':
        {  # New state variable to track database initialization
            'default': False,
            'type': bool
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


# Cache station coordinates using Streamlit's cache_data decorator
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
        'MGM': {
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
        'IPPM': {
            'lat': 15.85281,
            'lon': 80.3814662
        },
        'SPF': {
            'lat': 15.8752985,
            'lon': 80.4140117
        },
        'BPP': {
            'lat': 15.9087804,
            'lon': 80.4652035
        },
        'APL': {
            'lat': 15.9703661,
            'lon': 80.5142194
        },
        'MCVM': {
            'lat': 16.0251057,
            'lon': 80.5391888
        },
        'NDO': {
            'lat': 16.0673498,
            'lon': 80.5553901
        },
        'MDKU': {
            'lat': 16.1233333,
            'lon': 80.5799375
        },
        'TSR': {
            'lat': 16.1567184,
            'lon': 80.5832601
        },
        'TEL': {
            'lat': 16.2435852,
            'lon': 80.6376458
        },
        'KLX': {
            'lat': 16.2946856,
            'lon': 80.6260305
        },
        'DIG': {
            'lat': 16.329159,
            'lon': 80.6232471
        },
        'CLVR': {
            'lat': 16.3802036,
            'lon': 80.6164899
        },
        'PVD': {
            'lat': 16.4150823,
            'lon': 80.6107384
        },
        'KCC': {
            'lat': 16.4778294,
            'lon': 80.600124
        },
        'NZD': {
            'lat': 16.717923,
            'lon': 80.8230084
        },
        'VAT': {
            'lat': 16.69406,
            'lon': 81.0399239
        },
        'PRH': {
            'lat': 16.7132558,
            'lon': 81.1025796
        },
        'EE': {
            'lat': 16.7132548,
            'lon': 81.0845549
        },
        'DEL': {
            'lat': 16.7818664,
            'lon': 81.1780754
        },
        'BMD': {
            'lat': 16.818151,
            'lon': 81.2627899
        },
        'PUA': {
            'lat': 16.8096519,
            'lon': 81.3207946
        },
        'CEL': {
            'lat': 16.8213153,
            'lon': 81.3900847
        },
        'BPY': {
            'lat': 16.8279598,
            'lon': 81.4719773
        },
        'TDD': {
            'lat': 16.8067368,
            'lon': 81.52052
        },
        'NBM': {
            'lat': 16.83,
            'lon': 81.5922511
        },
        'NDD': {
            'lat': 16.8959685,
            'lon': 81.6728381
        },
        'CU': {
            'lat': 16.9702728,
            'lon': 81.686414
        },
        'PSDA': {
            'lat': 16.9888598,
            'lon': 81.6959144
        },
        'KVR': {
            'lat': 17.003964,
            'lon': 81.7217881
        },
        'GVN': {
            'lat': 17.0050447,
            'lon': 81.7683895
        },
        'KYM': {
            'lat': 16.9135426,
            'lon': 81.8291201
        },
        'DWP': {
            'lat': 16.9264801,
            'lon': 81.9185066
        },
        'APT': {
            'lat': 16.9353876,
            'lon': 81.9510518
        },
        'BVL': {
            'lat': 16.967466,
            'lon': 82.0283906
        },
        'MPU': {
            'lat': 17.0050166,
            'lon': 82.0930538
        },
        'SLO': {
            'lat': 17.0473849,
            'lon': 82.1652452
        },
        'PAP': {
            'lat': 17.1127264,
            'lon': 82.2560612
        },
        'GLP': {
            'lat': 17.1544365,
            'lon': 82.2873605
        },
        'DGDG': {
            'lat': 17.2108602,
            'lon': 82.3447996
        },
        'RVD': {
            'lat': 17.2280704,
            'lon': 82.3631186
        },
        'HVM': {
            'lat': 17.3127808,
            'lon': 82.485711
        },
        'GLU': {
            'lat': 17.4098079,
            'lon': 82.6294254
        },
        'NRP': {
            'lat': 17.4511567,
            'lon': 82.7188935
        },
        'REG': {
            'lat': 17.5052679,
            'lon': 82.7880359
        },
        'YLM': {
            'lat': 17.5534876,
            'lon': 82.8428433
        },
        'NASP': {
            'lat': 17.6057255,
            'lon': 82.8899697
        },
        'BVM': {
            'lat': 17.6600783,
            'lon': 82.9259044
        },
        'KSK': {
            'lat': 17.6732113,
            'lon': 82.9564764
        },
        'AKP': {
            'lat': 17.6934772,
            'lon': 83.0049398
        },
        'THY': {
            'lat': 17.6865433,
            'lon': 83.0665228
        },
        'DVD': {
            'lat': 17.7030476,
            'lon': 83.1485371
        }
    }


@st.cache_data(ttl=300)
def extract_station_codes(selected_stations, station_column=None):
    """Extract station codes from selected DataFrame using optimized approach"""
    selected_station_codes = []

    if selected_stations.empty:
        return selected_station_codes

    # Look for station code in 'CRD' or 'Station' column
    potential_station_columns = [
        'CRD', 'Station', 'Station Code', 'station', 'STATION'
    ]

    # Try each potential column
    for col_name in potential_station_columns:
        if col_name in selected_stations.columns:
            for _, row in selected_stations.iterrows():
                if pd.notna(row[col_name]):
                    # Extract station code from text (may contain additional details)
                    text_value = str(row[col_name]).strip()

                    # Handle 'CRD' column which might have format "NZD ..."
                    if col_name == 'CRD':
                        # Extract first word which is likely the station code
                        parts = text_value.split()
                        if parts:
                            code = parts[0].strip()
                            if code and code not in selected_station_codes:
                                selected_station_codes.append(code)
                    else:
                        # For other columns, use the full value
                        if text_value and text_value not in selected_station_codes:
                            selected_station_codes.append(text_value)

    # If still no codes found, try a more generic approach with any column
    if not selected_station_codes:
        for col in selected_stations.columns:
            if any(keyword in col for keyword in
                   ['station', 'Station', 'STATION', 'Running', 'CRD']):
                for _, row in selected_stations.iterrows():
                    if pd.notna(row[col]):
                        text = str(row[col])
                        # Try to extract a station code (usually 2-5 uppercase letters)
                        words = text.split()
                        for word in words:
                            word = word.strip()
                            if 2 <= len(word) <= 5 and word.isupper():
                                if word not in selected_station_codes:
                                    selected_station_codes.append(word)

    return selected_station_codes


# Create a function to render the offline map with GPS markers
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
                    fill=(100, 100, 10, 100, 180))  # Gray with some transparency
            except:
                # Skip if conversion fails
                continue

    # Keep track of displayed stations
    displayed_stations = []

    # Draw markers for each selected station
    for code in selected_station_codes:
        normalized_code = code.upper().strip()

        # Check if we have the station in the map_viewers station locations
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
                'y': (coords['lat'] - 14.0) / 5.0  # Approximate conversion
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

# Main page title
st.title("ICMS Data - Vijayawada Division")

# Add a refresh button at the top with just an icon
col1, col2 = st.columns([10, 2])
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
            last_update_ist = data_handler.last_update + timedelta(hours=5,
                                                                  minutes=30)
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

                # Get and print all column names for debugging
                logger.debug(f"Available columns: {df.columns.tolist()}")

                # Extract stations for map
                stations = extract_stations_from_data(df)

                # Drop unwanted columns - use exact column names with proper spacing
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
                        logger.debug(f"Dropped column: {col}")

                # Create a two-column layout for the table and map
                st.markdown("""
                <style>
                .stColumn > div {
                    padding: 0px !important;
                }
                div[data-testid="column"] {
                    padding: 0px !important;
                    margin: 0px !important;
                }
                .block-container {
                    padding-left: 0.5rem !important;
                    padding-right: 0 !important;
                    max-width: 90% !important;
                }
                div[data-testid="stVerticalBlock"] {
                    gap: 0px !important;
                }
                /* Custom styling to make table wider */
                [data-testid="stDataFrame"] {
                    width: 100% !important;
                    max-width: none !important;
                }
                /* Add borders to tables */
                [data-testid="stDataFrame"] table {
                    border: 1px solid #dee2e6 !important;
                    border-collapse: collapse !important;
                }
                [data-testid="stDataFrame"] th {
                    border: 1px solid #dee2e6 !important;
                    background-color: #f8f9fa !important;
                    padding: 5px !important;
                }
                [data-testid="stDataFrame"] td {
                    border: 1px solid #dee2e6 !important;
                    padding: 5px !important;
                }
                </style>
                """,
                            unsafe_allow_html=True)

                # Create a more balanced column ratio with no gap - 60% table to 40% map
                table_col, map_col = st.columns([3.5, 2.5], gap="small")

                with table_col:
                    # Refresh animation placeholder right before displaying the table
                    refresh_table_placeholder = st.empty()
                    create_pulsing_refresh_animation(refresh_table_placeholder,
                                                     "Refreshing Table...")

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

                    # Apply styling to the dataframe
                    styled_df = filtered_df.style.apply(highlight_delay,
                                                        axis=None)

                    # Create a column layout to control table width
                    table_col1, table_col2 = st.columns([3, 1])
                    with table_col1:
                        # Put the dataframe in a card with Bootstrap styling
                        st.markdown('<div class="card shadow-sm mb-3"><div class="card-header bg-primary text-white">Train Data</div><div class="card-body p-0">', unsafe_allow_html=True)

                        # Use data_editor to make the table interactive with checkboxes
                        edited_df = st.data_editor(
                            filtered_df,
                            hide_index=True,
                            column_config={
                                "Select":
                                st.column_config.CheckboxColumn(
                                    "Select",
                                    help="Select to show on map",
                                    default=False),
                                "Train No.":
                                st.column_config.TextColumn(
                                    "Train No.", help="Train Number"),
                                "FROM-TO":
                                st.column_config.TextColumn(
                                    "FROM-TO", help="Source to Destination"),
                                "IC Entry Delay":
                                st.column_config.TextColumn(
                                    "IC Entry Delay", help="Entry Delay"),
                                "Delay":
                                st.column_config.TextColumn(
                                    "Delay", help="Delay in Minutes")
                            },
                            disabled=[
                                col for col in filtered_df.columns
                                if col != 'Select'
                            ],
                            use_container_width=True,  # Use full container width
                            height=600,  # Set appropriate height
                            num_rows=40  # Show 40 rows at a time
                        )
                        st.markdown('</div></div>', unsafe_allow_html=True)

                    with table_col2:
                        # Empty space to reduce table width
                        st.empty()

                    # Get selected stations for map
                    if station_column:
                        try:
                            # Get all selected rows
                            selected_rows = edited_df[edited_df['Select']]

                            # Debug - show all stations in selected rows (in a small text area)
                            if not selected_rows.empty and station_column in selected_rows.columns:
                                all_stations = selected_rows[station_column].tolist()
                                st.caption(f"Selected stations: {', '.join([str(s) for s in all_stations if s])}")

                        except Exception as e:
                            logger.error(f"Error processing selected stations: {str(e)}")
                            st.error(f"Error processing selected stations: {str(e)}")

                    refresh_table_placeholder.empty()  # Clear the placeholder after table display

                # Display map with reduced left margin
                with map_col:
                    # Remove extra padding/margin to bring map closer to table
                    st.markdown("""
                    <style>
                    .stColumn > div:first-child {
                        padding-left: 0 !important;
                        margin-left: 0 !important;
                    }
                    </style>
                    """,
                                unsafe_allow_html=True)

                    # Get cached station coordinates
                    station_coords = get_station_coordinates()

                    # Extract station codes from selected rows
                    selected_rows = edited_df[edited_df['Select']]
                    selected_station_codes = extract_station_codes(selected_rows, station_column)

                    # First, set a default map type value to use
                    if 'map_type' not in st.session_state:
                        st.session_state['map_type'] = "Offline Map with GPS Markers"

                    # Card container for the map
                    st.markdown("""
                    <div class="card mb-3">
                        <div class="card-header bg-secondary text-white">
                            Station Map
                        </div>
                        <div class="card-body p-0">
                    """, unsafe_allow_html=True)

                    # Display the appropriate map based on the current map type
                    if st.session_state['map_type'] == "Offline Map with GPS Markers":
                        if selected_station_codes:
                            st.caption(f"Selected stations: {', '.join(selected_station_codes)}")

                        # Render offline map with markers
                        display_image, displayed_stations = render_offline_map_with_markers(
                            selected_station_codes, station_coords)

                        if display_image is not None:
                            # Convert and resize for display if needed
                            from PIL import Image
                            display_image = display_image.convert('RGB')
                            original_width, original_height = display_image.size

                            # Calculate new dimensions maintaining aspect ratio
                            max_height = 600  # Increased height for better visibility
                            height_ratio = max_height / original_height
                            new_width = int(original_width * height_ratio * 1.2)  # Extra width factor
                            new_height = max_height

                            display_image = display_image.resize(
                                (new_width, new_height),
                                Image.Resampling.LANCZOS)

                            # Display the map
                            st.image(
                                display_image,
                                use_container_width=True,
                                caption="Vijayawada Division System Map with Selected Stations"
                            )

                            # Show station count
                            if displayed_stations:
                                st.success(f"Showing {len(displayed_stations)} selected stations with markers and all other stations as dots")
                            else:
                                st.info("No stations selected. All stations shown as dots on the map.")
                        else:
                            st.error("Unable to load the offline map. Please check the map file.")
                    else:
                        # Create the interactive map
                        m = folium.Map(
                            location=[16.5167, 80.6167],  # Centered around Vijayawada
                            zoom_start=7,
                            control_scale=True)

                        # Add a basemap with reduced opacity
                        folium.TileLayer(
                            tiles='OpenStreetMap',
                            attr='&copy; OpenStreetMap contributors',
                            opacity=0.8).add_to(m)

                        # Add markers efficiently
                        displayed_stations = []
                        valid_points = []

                        # Create a counter to alternate label positions
                        counter = 0

                        # First add all non-selected stations as dots with alternating labels
                        for code, coords in station_coords.items():
                            # Skip selected stations - they'll get bigger markers later
                            if code.upper() in selected_station_codes:
                                continue

                            # Determine offset for alternating left/right positioning
                            x_offset = -50 if counter % 2 == 0 else 50  # Pixels left or right
                            y_offset = 0  # No vertical offset

                            # Every 3rd station, use vertical offset instead to further reduce overlap
                            if counter % 3 == 0:
                                x_offset = 0
                                y_offset = -30  # Above the point

                            counter += 1

                            # Add small circle for the station with maroon border
                            folium.CircleMarker(
                                [coords['lat'], coords['lon']],
                                radius=3,
                                color='#800000',  # Maroon red border
                                fill=True,
                                fill_color='gray',
                                fill_opacity=0.6,
                                opacity=0.8,
                                tooltip=code).add_to(m)

                            # Add box around dot with label with custom positioning
                            # Make sizing consistent regardless of zoom by using absolute elements
                            html_content = f'''
                            <div style="position:absolute; width:0; height:0;">
                                <!-- Box around station location -->
                                <div style="position:absolute; width:6px; height:6px; border:1px solid #800000; left:-3px; top:-3px; border-radius:1px; background-color:rgba(255,255,255,0.5);"></div>
                                <!-- Station label -->
                                <div style="position:absolute; left:{10 if x_offset < 0 else -40}px; top:{-18 if y_offset < 0 else 0}px; background-color:rgba(255,255,255,0.8); padding:1px 3px; border:1px solid #800000; border-radius:2px; font-size:9px; white-space:nowrap;">{code}</div>
                            </div>
                            '''

                            folium.DivIcon(
                                icon_size=(0, 0),  # Using zero size to improve positioning
                                icon_anchor=(0, 0),  # Centered anchor point
                                html=html_content).add_to(
                                    folium.Marker(
                                        [coords['lat'], coords['lon']],
                                        icon=folium.DivIcon(icon_size=(0, 0))  # Invisible marker
                                    ).add_to(m))

                        # Then add larger markers for selected stations with prominent labels
                        for code in selected_station_codes:
                            normalized_code = code.upper().strip()
                            if normalized_code in station_coords:
                                lat = station_coords[normalized_code]['lat']
                                lon = station_coords[normalized_code]['lon']

                                # Determine offset for selected stations - opposite to non-selected pattern
                                x_offset = 50 if counter % 2 == 0 else -50
                                y_offset = -30 if counter % 3 == 0 else 0
                                counter += 1

                                # Add train icon marker
                                folium.Marker(
                                    [lat, lon],
                                    popup=f"<b>{normalized_code}</b><br>({lat:.4f}, {lon:.4f})",
                                    tooltip=normalized_code,
                                    icon=folium.Icon(color='red', icon='train', prefix='fa'),
                                    opacity=0.8).add_to(m)

                                # Add highlighted box and prominent label with zoom-stable positioning
                                html_content = f'''
                                <div style="position:absolute; width:0; height:0;">
                                    <!-- Larger box for selected station -->
                                    <div style="position:absolute; width:8px; height:8px; border:2px solid #800000; left:-4px; top:-4px; border-radius:2px; background-color:rgba(255,255,255,0.5);"></div>
                                    <!-- Prominent station label -->
                                    <div style="position:absolute; left:{15 if x_offset < 0 else -50}px; top:{-20 if y_offset < 0 else 0}px; background-color:rgba(255,255,255,0.9); padding:2px 4px; border:2px solid #800000; border-radius:3px; font-weight:bold; font-size:10px; color:#800000; white-space:nowrap;">{normalized_code}</div>
                                </div>
                                '''

                                folium.DivIcon(
                                    icon_size=(0, 0),  # Using zero size to improve positioning
                                    icon_anchor=(0, 0),  # Centered anchor point
                                    html=html_content).add_to(
                                        folium.Marker(
                                            [lat, lon],
                                            icon=folium.DivIcon(icon_size=(0, 0))).add_to(m))

                                displayed_stations.append(normalized_code)
                                valid_points.append([lat, lon])

                        # Add railway lines between selected stations
                        if len(valid_points) > 1:
                            folium.PolyLine(valid_points,
                                            weight=2,
                                            color='gray',
                                            opacity=0.8,
                                            dash_array='5, 10').add_to(m)

                        # Render the map with increased width
                        folium_static(m, width=900, height=650)

                    st.markdown("</div></div>", unsafe_allow_html=True)

                    # Add a separator to separate the map from the radio buttons
                    st.markdown("---")

                    # Display the map type selection radio buttons below the map
                    selected_map_type = st.radio(
                        "Map Type", [
                            "Offline Map with GPS Markers",
                            "Interactive GPS Map"
                        ],
                        index=0 if st.session_state['map_type']
                        == "Offline Map with GPS Markers" else 1,
                        horizontal=True,
                        key="map_type_selector")

                    # Update the session state when the selection changes
                    if selected_map_type != st.session_state['map_type']:
                        st.session_state['map_type'] = selected_map_type
                        st.rerun()  # Refresh to apply the new map type

                    # Add instructions in collapsible section
                    with st.expander("Map Instructions"):
                        st.markdown("""
                        <div class="card">
                            <div class="card-header bg-light">
                                Using the Map
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item">Select stations using the checkboxes in the table</li>
                                    <li class="list-group-item">Selected stations will appear with markers on the map</li>
                                    <li class="list-group-item">Use the radio buttons below to switch between map types</li>
                                    <li class="list-group-item">Railway lines connect selected stations in sequence</li>
                                </ul>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

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
st.markdown(
    '<div class="card"><div class="card-body text-center text-muted">© 2023 South Central Railway - Vijayawada Division</div></div>',
    unsafe_allow_html=True)