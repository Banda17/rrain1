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

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Page configuration must be the first Streamlit command
st.set_page_config(page_title="Train Tracking System",
                   page_icon="🚂",
                   layout="wide",
                   initial_sidebar_state="collapsed")

# Apply aggressive CSS to remove ALL gaps and padding throughout the application
st.markdown("""
<style>
/* Global reset for all elements */
* {
    margin: 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
}

/* Remove ALL padding and spacing from Streamlit containers */
.block-container, 
.stApp, 
[data-testid="stAppViewContainer"],
[data-testid="stVerticalBlock"], 
.stColumn,
.row-widget,
.stHorizontal,
[data-testid="column"] {
    padding: 0 !important;
    margin: 0 !important;
    gap: 0 !important;
}

/* Force zero spacing in all column layouts */
[data-testid="column"] > div {
    padding: 0 !important;
    margin: 0 !important;
}

/* Eliminate gaps in column layouts */
.row-widget.stHorizontal {
    gap: 0 !important;
    display: flex !important;
    flex-wrap: nowrap !important;
}

/* Reduce spacing around tables */
[data-testid="stDataFrame"] {
    padding: 0 !important;
    margin: 0 !important;
    max-width: none !important;
}

/* Compact header styling */
h1, h2, h3, h4, h5, h6 {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.2 !important;
}

/* Remove whitespace around images */
img, [data-testid="stImage"] {
    margin: 0 !important;
    padding: 0 !important;
    display: block !important;
}

/* Ensure map container has no spacing */
.stFolium, .folium-map {
    margin: 0 !important;
    padding: 0 !important;
}

/* Remove spacing from markdown elements */
.stMarkdown {
    margin: 0 !important;
    padding: 0 !important;
}

/* Add minimal spacing for readability only where absolutely necessary */
.main-content > * {
    margin-top: 0.25rem !important;
}

/* Override any streamlit-specific spacers */
.css-1kyxreq, .css-12w0qpk {
    padding: 0 !important;
    margin: 0 !important;
    gap: 0 !important;
}
</style>
""", unsafe_allow_html=True)

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
        <div>
            <h1 style='margin: 0; padding: 0; text-align: left; color: #1f497d;'>South Central Railway</h1>
            <h2 style='margin: 0; padding: 0; text-align: left; color: #4f81bd;'>Vijayawada Division</h2>
        </div>
    """, unsafe_allow_html=True)

# Add a horizontal line to separate the header from content
st.markdown("<hr style='margin-top: 0.25rem; margin-bottom: 0.25rem;'>", unsafe_allow_html=True)

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
        # If not in map_viewer, try to convert GPS coordinates to map coordinates
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
        if opacity >= 1.0:  # No change needed iffully opaque
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
st.title("Train Tracking System using ML")

# Add a refresh button at the top with just an icon
col1, col2 = st.columns([10, 2])
with col2:
    if st.button("🔄", type="primary"):
        st.rerun()


try:
    data_handler = st.session_state['icms_data_handler']

    # Set refreshing state to True and show animation
    st.session_state['is_refreshing'] = True
    refresh_placeholder = st.empty()  # Moved here
    create_pulsing_refresh_animation(refresh_placeholder,
                                     "Loading ICMS data...")

    # Load data with feedback
    with st.spinner("Loading ICMS data..."):
        success, message = data_handler.load_data_from_drive()

    # Clear the refresh animation when done
    st.session_state['is_refreshing'] = False
    refresh_placeholder.empty()

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
                # Custom styling for ultra-compact layout without any gaps
                st.markdown("""
                <style>
                /* Ultra-compact layout - no gaps or margins */
                .stColumn > div {
                    padding: 0 !important;
                    margin: 0 !important;
                }
                div[data-testid="column"] {
                    padding: 0 !important;
                    margin: 0 !important;
                }
                .block-container {
                    padding-left: 0 !important;
                    padding-right: 0 !important;
                    max-width: 100% !important;
                }
                div[data-testid="stVerticalBlock"] {
                    gap: 0 !important;
                }
                /* Custom styling to make table take available space */
                [data-testid="stDataFrame"] {
                    max-width: none !important;
                    width: 100% !important;
                }
                /* Force columns to have zero gap */
                .row-widget.stHorizontal {
                    gap: 0 !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }
                /* Force map container to be compact */
                iframe {
                    margin: 0 !important;
                    padding: 0 !important;
                    border: none !important;
                }
                </style>
                """, unsafe_allow_html=True)

                # Create a more balanced column ratio with minimum gap
                table_col, map_col = st.columns([3.5, 2.5], gap="small")

                # Apply additional styling to force columns closer together
                st.markdown("""
                <style>
                /* Force columns to have zero gap */
                .row-widget.stHorizontal {
                    gap: 0 !important;
                }
                </style>
                """, unsafe_allow_html=True)

                with table_col:
                    # Refresh animation placeholder right before displaying the table
                    refresh_table_placeholder = st.empty()
                    create_pulsing_refresh_animation(refresh_table_placeholder,
                                                     "Refreshing Table...")
                    # Function to check if a value is positive or contains (+)
                    def is_positive_or_plus(value):
                        if value is None:
                            return False
                        if isinstance(value, str):
                            # Check for numbers in brackets with +
                            bracket_match = re.search(r'\(.*?\+.*?\)', value)
                            if bracket_match:
                                return True
                            # Try to convert to number if possible
                            try:
                                num = float(
                                    value.replace('(', '').replace(')',
                                                                   '').strip())
                                return num > 0
                            except:
                                return False
                        return False

                    # Filter rows where Delay column has positive values or (+)
                    if 'Delay' in df.columns:
                        filtered_df = df[df['Delay'].apply(
                            is_positive_or_plus)]
                        st.write(
                            f"Showing {len(filtered_df)} entries with positive delays"
                        )
                    else:
                        filtered_df = df
                        st.warning("Delay column not found in data")

                    # Apply red styling only to the Delay column
                    def highlight_delay(df):
                        # Create a DataFrame of styles with same shape as the input DataFrame
                        styles = pd.DataFrame('',
                                              index=df.index,
                                              columns=df.columns)

                        # Apply red color only to the 'Delay' column if it exists
                        if 'Delay' in df.columns:
                            styles['Delay'] = 'color: red; font-weight: bold'

                        return styles

                    # Add a "Select" column at the beginning of the DataFrame for checkboxes
                    if 'Select' not in filtered_df.columns:
                        filtered_df.insert(0, 'Select', False)

                    # Display the table with selection capability
                    edited_df = st.data_editor(
                        filtered_df,
                        column_config={
                            "Select":
                            st.column_config.CheckboxColumn(
                                "Select",
                                help="Select to show on map",
                                default=False,
                            )
                        },
                        hide_index=True,
                        use_container_width=True,
                        num_rows="dynamic",
                        height=600,
                        key="train_data_editor",
                        # Apply the styling to highlight Delay column
                        styled_dataframe=filtered_df.style.apply(
                            highlight_delay, axis=None),
                    )

                    # Clear the refresh animation when done
                    refresh_table_placeholder.empty()

                with map_col:
                    # Get selected stations
                    selected_stations = edited_df[edited_df['Select']]

                    # Extract station codes from the selected DataFrame
                    selected_station_codes = extract_station_codes(
                        selected_stations)

                    # Show loading indicator while map renders
                    with st.spinner("Loading map..."):
                        # Render offline map with markers
                        display_image, displayed_stations = render_offline_map_with_markers(
                            selected_station_codes, get_station_coordinates())

                        # Display map if available
                        if display_image is not None:
                            # Resize for display - use standard size to avoid reflow
                            from PIL import Image
                            original_width, original_height = display_image.size
                            max_height = 650  # Fixed height for consistency
                            height_ratio = max_height / original_height
                            new_width = int(original_width * height_ratio * 1.0)

                            # Show map image
                            st.image(
                                display_image.resize((new_width, max_height)),
                                use_container_width=True,
                                caption="Division Map with Selected Stations")

                            # Show count of displayed stations
                            if displayed_stations:
                                st.success(
                                    f"Showing {len(displayed_stations)} selected stations"
                                )
                            else:
                                st.info(
                                    "No stations selected. Select stations from the table."
                                )
                        else:
                            # If offline map failed, show interactive map
                            st.warning(
                                "Offline map unavailable. Showing interactive map."
                            )

                            # Create the map
                            m = folium.Map(
                                location=[16.5167, 80.6167],  # Centered around Vijayawada
                                zoom_start=7,
                                control_scale=True,
                                width="100%",
                                height="100%"
                            )

                            # Add a basemap
                            folium.TileLayer(
                                tiles='OpenStreetMap',
                                attr='&copy; OpenStreetMap contributors',
                                opacity=0.8
                            ).add_to(m)

                            # Add markers for selected stations
                            if not selected_stations.empty:
                                valid_points = []
                                for _, station in selected_stations.iterrows():
                                    code = station['Station']
                                    # Extract station coordinates
                                    coords = get_station_coordinates().get(code, None)
                                    if coords:
                                        lat, lon = coords['lat'], coords['lon']
                                        folium.Marker(
                                            [lat, lon],
                                            popup=f"{code}",
                                            tooltip=f"{code}",
                                            icon=folium.Icon(color='red', icon='train')
                                        ).add_to(m)
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

                            # Render the map with reduced width
                            st.subheader("Interactive Map")
                            folium_static(m, width=800, height=650)

                    # Add a separator to separate the map from the radio buttons
                    st.markdown("---")

                    # Option to switch between map types
                    selected_map_type = st.radio(
                        "Map Type",
                        ["Offline Map", "Interactive GPS Map"],
                        horizontal=True,
                        key="map_type_selector")

                    # Simple help text about map types
                    st.markdown("""
                    **Offline Map**: Division map with train markers.<br>
                    **Interactive Map**: GPS-based OpenStreetMap.
                    """, unsafe_allow_html=True)

            else:
                st.warning(
                    "No data available from the ICMS system. Please check the data source."
                )
        else:
            st.warning("No cached data available. Please refresh data.")

    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    st.error(f"An error occurred while processing data: {str(e)}")
    logger.error(f"Main page error: {str(e)}", exc_info=True)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>© 2023 South Central Railway - Vijayawada Division</div>",
    unsafe_allow_html=True)