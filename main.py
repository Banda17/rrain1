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
from streamlit_folium import folium_static, st_folium
from map_viewer import MapViewer  # Import MapViewer for offline map handling

# Page configuration - MUST be the first Streamlit command
st.set_page_config(page_title="Train Tracking System",
                   page_icon="🚂",
                   layout="wide",
                   initial_sidebar_state="collapsed")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add Bootstrap CSS - Update the style section to ensure grid layout works correctly
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
        /* Styling train number columns */
        [data-testid="stDataFrame"] td:nth-child(3) {
            background-color: #e9f7fe !important;
            font-weight: bold !important;
            color: #0066cc !important;
            border-left: 3px solid #0066cc !important;
        }
        [data-testid="stDataFrame"] tr:nth-of-type(odd) {
            background-color: rgba(0,0,0,.05) !important;
        }
        [data-testid="stDataFrame"] tr:hover {
            background-color: rgba(0,0,0,.075) !important;
        }
        .stColumn > div {
            padding: 0px !important;
        }
        div[data-testid="column"] {
            padding: 0px !important;
            margin: 0px !important;
        }
        /* Style for checkboxes */
        [data-testid="stDataFrame"] input[type="checkbox"] {
            width: 18px !important;
            height: 18px !important;
            cursor: pointer !important;
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
        /* Enhance Bootstrap table styles */
        [data-testid="stDataFrame"] table {
            border: 1px solid #dee2e6 !important;
            border-collapse: collapse !important;
            width: 100% !important;
            margin-bottom: 0 !important;
        }
        [data-testid="stDataFrame"] th {
            border: 1px solid #dee2e6 !important;
            background-color: #f8f9fa !important;
            padding: 8px !important;
            font-weight: 600 !important;
            position: sticky !important;
            top: 0 !important;
            z-index: 1 !important;
        }
        [data-testid="stDataFrame"] td {
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
            vertical-align: middle !important;
        }
        [data-testid="stDataFrame"] tr:nth-of-type(odd) {
            background-color: rgba(0,0,0,.05) !important;
        }
        [data-testid="stDataFrame"] tr:hover {
            background-color: rgba(0,0,0,.075) !important;
            transition: background-color 0.3s ease !important;
        }
    </style>
""",
    unsafe_allow_html=True)



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

# Add the missing helper function above the format_delay_value function
def is_positive_or_plus(value):
    """Check if a value is positive or contains a plus sign."""
    if value is None:
        return False
    value_str = str(value).strip()
    # Check if the value contains a plus sign or has a numerical value > 0
    if '+' in value_str:
        return True
    try:
        # Try to convert to float and check if positive
        return float(value_str) > 0
    except (ValueError, TypeError):
        return False

def color_train_number(train_no):
    """Apply color formatting to train numbers based on first digit
    
    Args:
        train_no: Train number as string or number
        
    Returns:
        HTML formatted string with appropriate color
    """
    if train_no is None:
        return train_no
        
    train_no_str = str(train_no).strip()
    if not train_no_str or len(train_no_str) == 0:
        return train_no
        
    first_digit = train_no_str[0]
    
    # Define color mapping for each first digit
    color_map = {
        '1': '#d63384',  # Pink
        '2': '#6f42c1',  # Purple
        '3': '#0d6efd',  # Blue
        '4': '#20c997',  # Teal
        '5': '#198754',  # Green
        '6': '#0dcaf0',  # Cyan
        '7': '#fd7e14',  # Orange 
        '8': '#dc3545',  # Red
        '9': '#6610f2',  # Indigo
        '0': '#333333',  # Dark gray
    }
    
    # Get color or default to black
    color = color_map.get(first_digit, '#000000')
    
    # Return HTML formatted string with both inline style and class
    return f'<span class="train-{first_digit}" style="color: {color}; font-weight: bold; background-color: #f0f8ff; padding: 2px 6px; border-radius: 3px; border-left: 3px solid {color};">{train_no_str}</span>'

# Create a layout for the header with logo
header_col1, header_col2 = st.columns([1, 5])

# Display the logo in the first column
with header_col1:
    try:
        # Add a container with custom padding to lower the logo
        st.markdown("""
            <div style="padding-top: 20px; display: flex; align-items: center; height: 100%;">
                <img src="scr_logo.svg" width="120">
            </div>
        """,
                    unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Error loading SVG logo: {str(e)}")
        try:
            st.markdown("""
                <div style="padding-top: 20px; display: flex; align-items: center; height: 100%;">
                    <img src="attached_assets/scr_logo.svg" width="120">
                </div>
            """,
                        unsafe_allow_html=True)
        except Exception as e2:
            st.warning(f"Error loading any logo: {str(e2)}")

# Display the title and subtitle in the second column
with header_col2:
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

# Add custom CSS for train number styling
with open('train_number_styles.css', 'r') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


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


# Initialize sessionstate
initialize_session_state()

# Main page title
st.title("ICMSData- Vijayawada Division")

# Add a refresh button atthe top with just an icon
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
        ## Show last update time
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
                    'Event',
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

                # Define styling function with specific colors for train types
                def highlight_delay(data):
                    styles = pd.DataFrame('', index=data.index, columns=data.columns)

                    # Apply red color only to the 'Delay' column if it exists
                    if 'Delay' in df.columns:
                        styles['Delay'] = df['Delay'].apply(
                            lambda x: 'color: red; font-weight: bold' if x and is_positive_or_plus(x) else '')
                    
                    # Style train number column based on the first digit of train number
                    train_number_cols = ['Train No.', 'Train Name']
                    for train_col in train_number_cols:
                        if train_col in df.columns:
                            # Set base styling for all train numbers
                            styles[train_col] = 'background-color: #e9f7fe; font-weight: bold; border-left: 3px solid #0066cc'
                            
                            # Apply specific color based on first digit of train number
                            for idx, train_no in df[train_col].items():
                                if pd.notna(train_no):
                                    train_no_str = str(train_no).strip()
                                    if train_no_str and len(train_no_str) > 0:
                                        first_digit = train_no_str[0]
                                        
                                        # Apply colors based on first digit
                                        if first_digit == '1':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #d63384; font-weight: bold; border-left: 3px solid #d63384'
                                        elif first_digit == '2':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #6f42c1; font-weight: bold; border-left: 3px solid #6f42c1'
                                        elif first_digit == '3':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #0d6efd; font-weight: bold; border-left: 3px solid #0d6efd'
                                        elif first_digit == '4':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #20c997; font-weight: bold; border-left: 3px solid #20c997'
                                        elif first_digit == '5':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #198754; font-weight: bold; border-left: 3px solid #198754'
                                        elif first_digit == '6':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #0dcaf0; font-weight: bold; border-left: 3px solid #0dcaf0'
                                        elif first_digit == '7':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #fd7e14; font-weight: bold; border-left: 3px solid #fd7e14'
                                        elif first_digit == '8':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #dc3545; font-weight: bold; border-left: 3px solid #dc3545'
                                        elif first_digit == '9':
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #6610f2; font-weight: bold; border-left: 3px solid #6610f2'
                                        else:
                                            styles.loc[idx, train_col] = 'background-color: #e9f7fe; color: #333333; font-weight: bold; border-left: 3px solid #333333'

                    # Hidden column name
                    from_to_col = 'FROM-TO'

                    # Check if the hidden column exists in the DataFrame
                    if from_to_col in df.columns:
                        for idx, value in df[from_to_col].items():
                            if pd.notna(value):
                                logger.info(f"Processing row {idx} with value: {value}")

                                extracted_value = str(value).split(' ')[0].upper()
                                logger.debug(f"FROM-TO value: {value}, extracted value: {extracted_value}")

                                font_styles = {
                                    'DMU': 'color: blue; font-weight: bold; ',
                                    'MEM': 'color: blue; font-weight: bold; ',
                                    'SUF': 'color: #e83e8c; font-weight: bold; ',
                                    'MEX': 'color: #e83e8c; font-weight: bold; ',
                                    'VND': 'color: #e83e8c; font-weight: bold; ',
                                    'RJ': 'color: #e83e8c; font-weight: bold; ',
                                    'PEX': 'color: #e83e8c; font-weight: bold; ',
                                    'TOD': 'color: #fd7e14; font-weight: bold; '
                                }

                                # Apply train type styling
                                for col in styles.columns:
                                    style_to_apply = font_styles.get(extracted_value, '')
                                    if style_to_apply:
                                        styles.loc[idx, col] += style_to_apply

                    # Train number styling is now handled in the earlier section

                    return styles

                # Add a "Select" column at the beginning of the DataFrame for checkboxes
                if 'Select' not in df.columns:
                    df.insert(0, 'Select', False)

                # Get station column name
                station_column = next(
                    (col for col in df.columns
                     if col in ['Station', 'station', 'STATION']), None)

                # Refresh animation placeholder
                refresh_table_placeholder = st.empty()
                create_pulsing_refresh_animation(refresh_table_placeholder,
                                                 "Refreshing data...")

                # Apply styling to the dataframe
                styled_df = df.style.apply(highlight_delay, axis=None)

                # Replacing just the filter implementation to look for "(+X)" pattern:

                # Filter rows containing plus sign in brackets like "(+5)"
                def contains_plus_in_brackets(row):
                    # Use regex to find values with plus sign inside brackets like "(+5)"
                    row_as_str = row.astype(str).str.contains('\(\+\d+\)',
                                                              regex=True)
                    return row_as_str.any()

                # Apply filter to dataframe
                filtered_df = df[df.apply(contains_plus_in_brackets, axis=1)]

                # If filtered dataframe is empty, show a message and use original dataframe
                if filtered_df.empty:
                    st.warning(
                        "No rows found containing values with plus sign in brackets. Showing all data."
                    )
                    display_df = df
                else:
                    st.success(
                        f"Showing {len(filtered_df)} rows containing values with plus sign in brackets like '(+5)'"
                    )
                    display_df = filtered_df

                # Reset index and add a sequential serial number column
                display_df = display_df.reset_index(drop=True)

                # Add a sequential S.No. column at the beginning (before Select)
                display_df.insert(0, '#', range(1, len(display_df) + 1))
                
                # Add a CSS class based on the first digit of train numbers
                if 'Train No.' in display_df.columns:
                    # Create a CSS class column for train numbers
                    def get_train_class(train_no):
                        if train_no is None or str(train_no).strip() == '':
                            return ''
                        first_digit = str(train_no).strip()[0]
                        return f'train-{first_digit}'
                        
                    display_df['Train Class'] = display_df['Train No.'].apply(get_train_class)

                # Log FROM-TO values for debugging
                def log_from_to_values(df):
                    """Print FROM-TO values for each train to help with debugging"""
                    st.write("Logging FROM-TO values to console...")
                    from_to_columns = ['FROM-TO', 'FROM_TO']
                    for col_name in from_to_columns:
                        if col_name in df.columns:
                            logger.info(f"Found column: {col_name}")
                            for idx, value in df[col_name].items():
                                if pd.notna(value):
                                    first_three = str(value).upper()[:3]
                                    logger.info(
                                        f"Train {idx} - {col_name}: '{value}', First three chars: '{first_three}'"
                                    )

                # Call the logging function
                log_from_to_values(display_df)

                # Create a layout for train data and map side by side
                train_data_col, map_col = st.columns((2.4, 2.6))

                # Train data section
                with train_data_col:
                    # Add a card for the table content
                    st.markdown(
                        '<div class="card shadow-sm mb-3"><div class="card-header bg-primary text-white d-flex justify-content-between align-items-center"><span>Train Data</span><span class="badge bg-light text-dark rounded-pill">Select stations to display on map</span></div><div class="card-body p-0">',
                        unsafe_allow_html=True)

                    # Use data_editor to make the table interactive with checkboxes
                    edited_df = st.data_editor(
                        display_df,
                        hide_index=True,
                        column_config={
                            "#":
                            st.column_config.NumberColumn("#",
                                                          help="Serial Number",
                                                          format="%d"),
                            "Select":
                            st.column_config.CheckboxColumn(
                                "Select",
                                help="Select to show on map",
                                default=False),
                            "Train No.":
                            st.column_config.TextColumn("Train No.",
                                                      help="Train Number",
                                                      format=color_train_number),
                            "FROM-TO":
                            st.column_config.TextColumn(
                                "FROM-TO", help="Source to Destination"),
                            "IC Entry Delay":
                            st.column_config.TextColumn("IC Entry Delay",
                                                        help="Entry Delay"),
                            "Delay":
                            st.column_config.TextColumn(
                                "Delay", help="Delay in Minutes")
                        },
                        disabled=[
                            col for col in display_df.columns
                            if col != 'Select'
                        ],
                        use_container_width=True,
                        height=600,
                        num_rows="dynamic")

                    # Add a footer to the card with information about the data
                    selected_count = len(edited_df[edited_df['Select']])
                    st.markdown(
                        f'<div class="card-footer bg-light d-flex justify-content-between align-items-center"><span>Total Rows: {len(display_df)}</span><span>Selected: {selected_count}</span></div>',
                        unsafe_allow_html=True)
                    st.markdown('</div></div>', unsafe_allow_html=True)

                # Map section
                with map_col:
                    # Add a card for the map content
                    st.markdown(
                        '<div class="card mb-3"><div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center"><span>Interactive GPS Map</span><span class="badge bg-light text-dark rounded-pill">Showing selected stations</span></div><div class="card-body p-0">',
                        unsafe_allow_html=True)

                    # Create the interactive map
                    m = folium.Map(
                        location=[16.5167,
                                  80.6167],  # Centered around Vijayawada
                        zoom_start=7,
                        control_scale=True)

                    # Add a basemap with reduced opacity
                    folium.TileLayer(tiles='OpenStreetMap',
                                     attr='&copy; OpenStreetMap contributors',
                                     opacity=0.8).add_to(m)

                    # Get cached station coordinates
                    station_coords = get_station_coordinates()

                    # Extract station codes from selected rows
                    selected_rows = edited_df[edited_df['Select']]
                    selected_station_codes = extract_station_codes(
                        selected_rows, station_column)

                    # Add markers efficiently
                    displayed_stations = []
                    valid_points = []

                    # First add all non-selected stations as dots with alternating labels
                    for code, coords in station_coords.items():
                        # Skip selected stations - they'll get bigger markers later
                        if code in selected_station_codes:
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
                            tooltip=f"{code}").add_to(m)

                        # Add permanent text label for station with slight offset
                        folium.Marker(
                            [coords['lat'], coords['lon'] + 0.005
                             ],  # Smaller offset to the right
                            icon=folium.DivIcon(
                                icon_size=(
                                    0, 0),  # Dynamic sizing based on content
                                icon_anchor=(0, 0),
                                html=
                                f'<div style="display: inline-block; font-size:10px; background-color:rgba(255,255,255,0.7); padding:2px; border-radius:3px; border:1px solid #800000; white-space: nowrap;">{code}</div>'
                            )).add_to(m)

                    # Then add larger markers for selected stations
                    for code in selected_station_codes:
                        # First normalize the station code to match our coordinate dictionary
                        # Some codes might have spaces or different casing
                        normalized_code = code.strip().upper()

                        # Check if we have coordinates for this station
                        if normalized_code in station_coords:
                            lat = station_coords[normalized_code]['lat']
                            lon = station_coords[normalized_code]['lon']

                            # Add train icon marker
                            folium.Marker(
                                [lat, lon],
                                popup=
                                f"<b>{normalized_code}</b><br>({lat:.4f}, {lon:.4f})",
                                tooltip=normalized_code,
                                icon=folium.Icon(color='red',
                                                 icon='train',
                                                 prefix='fa'),
                                opacity=0.8).add_to(m)

                            # Add prominent text label for selected station with slight offset
                            folium.Marker(
                                [lat, lon + 0.008
                                 ],  # Smaller offset for selected stations
                                icon=folium.DivIcon(
                                    icon_size=(
                                        0,
                                        0),  # Dynamic sizing based on content
                                    icon_anchor=(0, 0),
                                    html=
                                    f'<div style="display: inline-block; font-size:12px; font-weight:bold; background-color:rgba(255,255,255,0.8); padding:3px; border-radius:3px; border:2px solid red; white-space: nowrap;">{normalized_code}</div>'
                                )).add_to(m)

                            displayed_stations.append(normalized_code)
                            valid_points.append([lat, lon])

                    # Add railway lines between selected stations
                    if len(valid_points) > 1:
                        folium.PolyLine(valid_points,
                                        weight=2,
                                        color='gray',
                                        opacity=0.8,
                                        dash_array='5, 10').add_to(m)

                    # Render the map using st_folium instead of deprecated folium_static
                    st_folium(m, width=None, height=600)

                    st.markdown('</div></div>', unsafe_allow_html=True)

                    # Show success message if stations are selected
                    if displayed_stations:
                        st.success(
                            f"Showing {len(displayed_stations)} selected stations on the map"
                        )
                    else:
                        st.info(
                            "Select stations in the table to display them on the map"
                        )

                # Add instructions in collapsible section
                with st.expander("Map Instructions"):
                    st.markdown("""
                    <div class="card">
                        <div class="card-header bg-light">
                            Using the Interactive Map
                        </div>
                        <div class="card-body">
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item">Select stations using the checkboxes in the table</li>
                                <li class="list-group-item">Selected stations will appear with red train markers on the map</li>
                                <li class="list-group-item">All other stations are shown as small gray dots</li>
                                <li class="list-group-item">Railway lines automatically connect selected stations in sequence</li>
                                <li class="list-group-item">Zoom and pan the map to explore different areas</li>
                            </ul>
                        </div>
                    </div>
                    """,
                                unsafe_allow_html=True)

                refresh_table_placeholder.empty(
                )  # Clear the placeholder after table display

            else:
                st.error("No data available in the cached data frame")
        else:
            st.error(f"Error: No cached data available. {message}")
    else:
        st.error(f"Error loading data: {message}")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    logger.exception("Exception in main app")


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

# Footer
st.markdown("---")
st.markdown(
    '<div class="card"><div class="card-body text-center text-muted">© 2023 South Central Railway - Vijayawada Division</div></div>',
    unsafe_allow_html=True)