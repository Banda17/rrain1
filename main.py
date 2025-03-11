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

# Import the custom formatter for train number styling
try:
    import color_train_formatter
except ImportError:
    st.error(
        "Could not import color_train_formatter module. Some styling features may not be available."
    )

# Page configuration - MUST be the first Streamlit command
st.set_page_config(page_title="Late Train Tracking System",
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


def get_train_number_color(train_no):
    """Get the color for a train number based on its first digit
    
    Args:
        train_no: Train number as string or number
        
    Returns:
        Dictionary with color and background-color properties
    """
    if train_no is None:
        return {"color": "#333333", "bg_color": "#ffffff"}

    train_no_str = str(train_no).strip()
    if not train_no_str or len(train_no_str) == 0:
        return {"color": "#333333", "bg_color": "#ffffff"}

    first_digit = train_no_str[0]

    # Define color mapping for each first digit
    color_map = {
        '1': {
            "color": "#d63384",
            "bg_color": "#fff0f7"
        },  # Pink
        '2': {
            "color": "#6f42c1",
            "bg_color": "#f5f0ff"
        },  # Purple
        '3': {
            "color": "#0d6efd",
            "bg_color": "#f0f7ff"
        },  # Blue
        '4': {
            "color": "#20c997",
            "bg_color": "#f0fff9"
        },  # Teal
        '5': {
            "color": "#198754",
            "bg_color": "#f0fff2"
        },  # Green
        '6': {
            "color": "#0dcaf0",
            "bg_color": "#f0fbff"
        },  # Cyan
        '7': {
            "color": "#fd7e14",
            "bg_color": "#fff6f0"
        },  # Orange 
        '8': {
            "color": "#dc3545",
            "bg_color": "#fff0f0"
        },  # Red
        '9': {
            "color": "#6610f2",
            "bg_color": "#f7f0ff"
        },  # Indigo
        '0': {
            "color": "#333333",
            "bg_color": "#f8f9fa"
        },  # Dark gray
    }

    # Get color or default to black
    return color_map.get(first_digit, {
        "color": "#333333",
        "bg_color": "#ffffff"
    })


def style_train_numbers_dataframe(df, train_column='Train No.'):
    """Apply styling to a DataFrame to color train numbers based on first digit
    
    Args:
        df: DataFrame to style
        train_column: Name of the column containing train numbers
        
    Returns:
        Styled DataFrame with colored train numbers
    """

    # Define a styling function that applies different colors to train numbers
    def style_train_numbers(val):
        if not isinstance(val, str) or not val.strip():
            return ''

        # Get the first digit (if it exists)
        first_digit = val[0] if val and val[0].isdigit() else None

        # Color mapping for train numbers based on first digit
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
            '0': '#333333'  # Dark gray
        }

        if first_digit in color_map:
            return f'color: {color_map[first_digit]}; font-weight: bold; background-color: #f0f8ff;'
        return ''

    # Apply different styling based on column content
    df_styled = df.style.applymap(style_train_numbers, subset=[train_column])

    # Apply styling for delay values
    if 'Delay' in df.columns:
        df_styled = df_styled.applymap(
            lambda x: 'color: red; font-weight: bold'
            if isinstance(x, str) and ('+' in x or 'LATE' in x) else
            ('color: green; font-weight: bold'
             if isinstance(x, str) and 'EARLY' in x else ''),
            subset=['Delay'])

    return df_styled


def color_train_number(train_no):
    """Format a train number with HTML color styling based on first digit
    
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

    # Get color style from the helper function
    colors = get_train_number_color(train_no_str)

    # Return HTML-formatted train number with styling
    return f'<span style="color: {colors["color"]}; background-color: {colors["bg_color"]}; font-weight: bold; padding: 2px 5px; border-radius: 3px;">{train_no_str}</span>'


# Create a more compact header with tighter spacing - use a single row with custom HTML
st.markdown("""
    <div style="display: flex; align-items: center; padding: 5px 0;">
        <div style="flex: 0 0 100px; text-align: right; padding-right: 10px;">
            <img src="attached_assets/scr_logo.png" width="80" alt="SCR Logo" />
        </div>
        <div style="flex: 1; padding-left: 0;">
            <h1 style="color: #0d6efd; margin: 0; padding: 0; font-size: 2.2rem;">South Central Railway</h1>
            <h2 style="color: #6c757d; margin: 0; padding: 0; font-size: 1.5rem;">Late Train Tracking - Vijayawada Division</h2>
        </div>
        <div style="flex: 0 0 100px;"></div>
    </div>
    """,
            unsafe_allow_html=True)

# Add a horizontal line to separate the header from content
st.markdown("<hr style='margin-top: 0; margin-bottom: 15px;'>",
            unsafe_allow_html=True)

# Initialize train filter variables for later use

# Initialize train_type_filters if it doesn't exist in session state
if 'train_type_filters' not in st.session_state:
    st.session_state.train_type_filters = {
        'SUF': True,  # Superfast
        'MEX': True,  # Express
        'DMU': True,  # DMU
        'MEMU': True,  # MEMU
        'PEX': True,  # Passenger Express
        'TOD': True,  # Tejas/Vande
        'VNDB': True,  # Vande Bharat
        'RAJ': True,  # Rajdhani
        'JSH': True, #JANSATABDHI
        'DNRT': True #Duronto
    }

# All train types with descriptions
train_types = {
    'SUF': 'Superfast',
    'MEX': 'Express',
    'DMU': 'DMU',
    'MEMU': 'MEMU',
    'PEX': 'Passenger Express',
    'TOD': 'Train On Demand',
    'VNDB': 'VandeBharat',
    'RAJ': 'Rajdhani',
    'JSH': 'Jansthabdhi',
    'DNRT': 'Duronto'
}

# Add custom CSS for train number styling
with open('train_number_styles.css', 'r') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Add JavaScript for dynamic styling properly inside HTML script tags
st.markdown("""
<script type="text/javascript">
// Color train numbers based on their first digit
const colorTrainNumbers = () => {
    // Define colors for each first digit
    const colors = {
        '1': '#d63384', // Pink
        '2': '#6f42c1', // Purple
        '3': '#0d6efd', // Blue
        '4': '#20c997', // Teal
        '5': '#198754', // Green
        '6': '#0dcaf0', // Cyan
        '7': '#fd7e14', // Orange
        '8': '#dc3545', // Red
        '9': '#6610f2', // Indigo
        '0': '#333333'  // Dark gray
    };
    
    // Wait for the table to be fully loaded
    setTimeout(() => {
        // Find all cells in the Train No. column (which is the 3rd column - index 2)
        const trainCells = document.querySelectorAll('div[data-testid="stDataFrame"] tbody tr td:nth-child(3)');
        
        // Apply styling to each cell
        trainCells.forEach(cell => {
            const trainNumber = cell.textContent.trim();
            if (trainNumber && trainNumber.length > 0) {
                const firstDigit = trainNumber[0];
                if (colors[firstDigit]) {
                    cell.style.color = colors[firstDigit];
                    cell.style.fontWeight = 'bold';
                }
            }
        });
    }, 1000);
};

// Run initially
document.addEventListener('DOMContentLoaded', function() {
    colorTrainNumbers();
    
    // Set up an observer for dynamic updates
    const observer = new MutationObserver(colorTrainNumbers);
    observer.observe(document.body, { childList: true, subtree: true });
});
</script>
""",
            unsafe_allow_html=True)


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
        'train_type_filters': {  # New state variable for train type filtering
            'default': {
                'SUF': True,  # Superfast
                'MEX': True,  # Express
                'TOD': True,  # Tejas, Vande Bharat
                'MEMU': True,  # MEMU
                'DMU': True,  # DMU
                'VNDB': True,  # Vande Bharat
                'PEX': True,  # Passenger Express
                'RJ': True  # Rajdhani
            },
            'type': Dict
        },
        'last_selected_codes':
        {  # Store last selected station codes for map persistence
            'default': [],
            'type': list
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


@st.cache_data(ttl=300)
def extract_stations_from_data(df):
    """Extract unique stations from the data for the map with optimized caching"""
    # Use session state if available to avoid reprocessing
    if 'map_stations' in st.session_state and st.session_state.get(
            'stations_last_updated', None) is not None:
        time_diff = (
            datetime.now() -
            st.session_state['stations_last_updated']).total_seconds()
        if time_diff < 300:  # Less than 5 minutes old
            return st.session_state['map_stations']

    stations = []
    if df is not None and not df.empty:
        # Try different column names that might contain station information
        station_columns = [
            'Station', 'station', 'STATION', 'Station Name', 'station_name',
            'CRD'
        ]

        # Vectorized approach for better performance
        for col in station_columns:
            if col in df.columns:
                # Use pandas's built-in methods for better performance
                unique_values = df[col].dropna().astype(
                    str).str.strip().unique()

                # Filter to keep only valid station codes (2-5 uppercase letters)
                if col == 'CRD':
                    # Handle special format in CRD column where first word is station code
                    stations = []
                    for val in unique_values:
                        parts = val.split()
                        if parts and len(parts[0]) >= 2 and len(
                                parts[0]) <= 5 and parts[0].isupper():
                            stations.append(parts[0])
                else:
                    # For other columns, use direct values if they look like station codes
                    stations = [
                        val for val in unique_values
                        if len(val) >= 2 and len(val) <= 5 and val.isupper()
                    ]

                if stations:
                    break

    # Store in session state for use in the map with timestamp
    st.session_state['map_stations'] = stations
    st.session_state['stations_last_updated'] = datetime.now()
    return stations


@st.cache_data(ttl=300, show_spinner="Loading data...")
def load_and_process_data():
    """Cache data loading and processing with optimized performance"""
    try:
        # Check if we have data in the session state that's recent enough
        if 'data_last_loaded' in st.session_state and 'cached_processed_data' in st.session_state:
            time_diff = (datetime.now() -
                         st.session_state['data_last_loaded']).total_seconds()
            # If data is less than 5 minutes old, use it
            if time_diff < 300:
                return (True, st.session_state.get('cached_status_table'),
                        st.session_state.get('cached_processed_data'),
                        "Using cached data")

        # Otherwise load fresh data
        success, message = st.session_state[
            'icms_data_handler'].load_data_from_drive()
        if success:
            status_table = st.session_state[
                'icms_data_handler'].get_train_status_table()
            cached_data = st.session_state[
                'icms_data_handler'].get_cached_data()

            if cached_data:
                # Store in session state for faster access
                processed_data = pd.DataFrame(cached_data)
                st.session_state['cached_status_table'] = status_table
                st.session_state['cached_processed_data'] = processed_data
                st.session_state['data_last_loaded'] = datetime.now()
                return True, status_table, processed_data, message

        return False, None, None, message
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return False, None, None, f"Error: {str(e)}"


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
        },
        'KI': {
            'lat': 16.6451902,
            'lon': 80.4689248
        },
        'RYP': {
            'lat': 16.5786346,
            'lon': 80.5589261
        },
        'VBC': {
            'lat': 16.5296738,
            'lon': 80.6219001
        },
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
        'CJM': {
            'lat': 15.688961,
            'lon': 80.2336244
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
        },
        'NS': {
            'lat': 16.7713563,
            'lon': 78.7213753
        },
        'MTM': {
            'lat': 16.5642053,
            'lon': 80.4050177
        },
        'RMV': {
            'lat': 16.5262612,
            'lon': 80.6781754
        },
        'GDV': {
            'lat': 16.4343363,
            'lon': 80.9708003
        },
        'PAVP': {
            'lat': 16.5627033,
            'lon': 80.8368158
        },
        'GWM': {
            'lat': 16.5563023,
            'lon': 80.7933824
        },
        'GALA': {
            'lat': 16.5381503,
            'lon': 80.6707216
        },
        'MBD': {
            'lat': 16.5504386,
            'lon': 80.7132015
        }
    }


@st.cache_data(ttl=300)
def extract_station_codes(selected_stations, station_column=None):
    """Extract station codes from selected DataFrame using vectorized operations for better performance"""
    if selected_stations.empty:
        return []

    # Use a set for faster lookups/deduplication
    selected_station_codes = set()

    # Look for station code in common columns, with prioritized order
    potential_station_columns = [
        'CRD', 'Station', 'Station Code', 'station', 'STATION'
    ]

    # 1. Try each potential column with vectorized operations where possible
    for col_name in potential_station_columns:
        if col_name in selected_stations.columns:
            # Get all non-null values for the column
            valid_values = selected_stations[
                selected_stations[col_name].notna()][col_name]

            if col_name == 'CRD':
                # Handle CRD column special format - get first word from each value
                for val in valid_values:
                    text = str(val).strip()
                    parts = text.split()
                    if parts:
                        code = parts[0].strip()
                        if code and 2 <= len(code) <= 5 and code.isupper():
                            selected_station_codes.add(code)
            else:
                # For other columns, filter for valid station codes (2-5 uppercase letters)
                for val in valid_values:
                    text = str(val).strip()
                    if text and 2 <= len(text) <= 5 and text.isupper():
                        selected_station_codes.add(text)

            # If we found codes, no need to check other columns
            if selected_station_codes:
                break

    # 2. If still no codes found, do a more generic search across all columns
    if not selected_station_codes:
        # Look for columns that might contain station info
        station_related_cols = [
            col for col in selected_stations.columns
            if any(keyword in col for keyword in
                   ['station', 'Station', 'STATION', 'Running', 'CRD'])
        ]

        for col in station_related_cols:
            # Extract valid values to process
            valid_values = selected_stations[
                selected_stations[col].notna()][col]

            # Process each value
            for val in valid_values:
                text = str(val)
                # Try to extract station codes (2-5 uppercase letters)
                words = text.split()
                for word in words:
                    word = word.strip()
                    if 2 <= len(word) <= 5 and word.isupper():
                        selected_station_codes.add(word)

    # Convert set back to list for return
    return list(selected_station_codes)


# Initialize sessionstate
initialize_session_state()

# Main page title
st.title("TRAIN TRACKING")

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
                    'Start date',
                    'Event',
                    'Train Class ',
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
                    styles = pd.DataFrame('',
                                          index=data.index,
                                          columns=data.columns)

                    # Apply red color only to the 'Delay' column if it exists
                    if 'Delay' in df.columns:
                        styles['Delay'] = df['Delay'].apply(
                            lambda x: 'color: red; font-weight: bold'
                            if x and is_positive_or_plus(x) else '')

                    # Style train number column based on the first digit of train number
                    train_number_cols = ['Train No.', 'Train Name']
                    for train_col in train_number_cols:
                        if train_col in df.columns:
                            # Set base styling for all train numbers
                            styles[
                                train_col] = 'background-color: #e9f7fe; font-weight: bold; border-left: 3px solid #0066cc'

                            # Apply specific color based on first digit of train number
                            for idx, train_no in df[train_col].items():
                                if pd.notna(train_no):
                                    train_no_str = str(train_no).strip()
                                    if train_no_str and len(train_no_str) > 0:
                                        first_digit = train_no_str[0]

                                        # Apply colors based on first digit
                                        if first_digit == '1':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #d63384; font-weight: bold; border-left: 3px solid #d63384'
                                        elif first_digit == '2':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #6f42c1; font-weight: bold; border-left: 3px solid #6f42c1'
                                        elif first_digit == '3':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #0d6efd; font-weight: bold; border-left: 3px solid #0d6efd'
                                        elif first_digit == '4':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #20c997; font-weight: bold; border-left: 3px solid #20c997'
                                        elif first_digit == '5':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #198754; font-weight: bold; border-left: 3px solid #198754'
                                        elif first_digit == '6':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #0dcaf0; font-weight: bold; border-left: 3px solid #0dcaf0'
                                        elif first_digit == '7':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #fd7e14; font-weight: bold; border-left: 3px solid #fd7e14'
                                        elif first_digit == '8':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #dc3545; font-weight: bold; border-left: 3px solid #dc3545'
                                        elif first_digit == '9':
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #6610f2; font-weight: bold; border-left: 3px solid #6610f2'
                                        else:
                                            styles.loc[
                                                idx,
                                                train_col] = 'background-color: #e9f7fe; color: #333333; font-weight: bold; border-left: 3px solid #333333'

                    # Hidden column name
                    from_to_col = 'FROM-TO'

                    # Check if the hidden column exists in the DataFrame
                    if from_to_col in df.columns:
                        for idx, value in df[from_to_col].items():
                            if pd.notna(value):
                                logger.info(
                                    f"Processing row {idx} with value: {value}"
                                )

                                extracted_value = str(value).split(
                                    ' ')[0].upper()
                                logger.debug(
                                    f"FROM-TO value: {value}, extracted value: {extracted_value}"
                                )

                                font_styles = {
                                    'DMU': 'color: blue; font-weight: bold; ',
                                    'MEM': 'color: blue; font-weight: bold; ',
                                    'SUF':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'MEX':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'VND':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'RJ':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'PEX':
                                    'color: #e83e8c; font-weight: bold; ',
                                    'TOD':
                                    'color: #fd7e14; font-weight: bold; '
                                }

                                # Apply train type styling
                                for col in styles.columns:
                                    style_to_apply = font_styles.get(
                                        extracted_value, '')
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

                # Train type filters have been moved to the card header

                # Process the FROM-TO column to extract train types before filtering
                train_types_column = 'FROM-TO'
                has_train_types = train_types_column in df.columns

                # Create a copy of the DataFrame to avoid SettingWithCopyWarning
                df_with_types = df.copy()

                if has_train_types:
                    # Function to extract train type
                    def extract_train_type_for_filter(value):
                        if pd.notna(value) and isinstance(value, str):
                            # Get the first part before any brackets or spaces
                            return value.split('[')[0].split(' ')[0].strip()
                        return ''

                    # Add a column with just the train type for filtering
                    df_with_types['__train_type'] = df_with_types[
                        train_types_column].apply(
                            extract_train_type_for_filter)

                # Define a cached function to process filters to improve performance
                @st.cache_data(ttl=5, show_spinner="Applying filters...")
                def filter_dataframe(df, train_type_filters, has_train_types):
                    """
                    Filter the dataframe based on train types and plus sign criteria
                    Returns the filtered dataframe and active filters
                    """
                    # Make a copy to avoid warnings
                    df_filtered = df.copy()

                    # Filter 1: Filter rows containing plus sign in brackets like "(+5)"
                    def contains_plus_in_brackets(row):
                        # Use regex to find values with plus sign inside brackets like "(+5)"
                        row_as_str = row.astype(str).str.contains('\(\+\d+\)',
                                                                  regex=True)
                        return row_as_str.any()

                    # Apply the plus sign filter - vectorized for better performance when possible
                    filtered_by_plus = df_filtered[df_filtered.apply(
                        contains_plus_in_brackets, axis=1)]

                    # Filter 2: Apply train type filter if we have train types
                    active_filters = []

                    if has_train_types:
                        # Extract active filters for display
                        active_filters = [
                            k for k, v in train_type_filters.items() if v
                        ]

                        # Fast path: if all filters are active, we don't need to filter
                        if len(active_filters) == len(train_type_filters):
                            final_df = filtered_by_plus
                        else:
                            # Handle special cases for MEMU which might be "MEM" and VND which might be "VNDB"
                            def is_train_type_selected(train_type):
                                if pd.isna(train_type):
                                    return True

                                # Handle MEM as MEMU
                                if train_type.startswith('MEM'):
                                    return train_type_filters.get('MEMU', True)

                                # Handle VND including VNDB
                                if train_type.startswith('VND'):
                                    return train_type_filters.get('VND', True)

                                # Direct match for other types
                                return train_type_filters.get(train_type, True)

                            # Apply train type filter using vectorized operations where possible
                            mask = filtered_by_plus['__train_type'].apply(
                                is_train_type_selected)
                            final_df = filtered_by_plus[mask]
                    else:
                        final_df = filtered_by_plus

                    # Remove the temporary column before returning
                    if '__train_type' in final_df.columns:
                        final_df = final_df.drop(columns=['__train_type'])

                    return final_df, active_filters

                # Apply the cached filter function
                filtered_df, active_filters = filter_dataframe(
                    df_with_types, st.session_state.train_type_filters,
                    has_train_types)

                # If filtered dataframe is empty, show a message and use original dataframe
                if filtered_df.empty:
                    st.warning(
                        "No matching trains found with current filters. Showing all data."
                    )
                    display_df = df
                else:
                    # Show filter information
                    if active_filters:
                        st.success(
                            f"Showing {len(filtered_df)} trains with filter types: {', '.join(active_filters)}"
                        )
                    else:
                        st.success(
                            f"Showing {len(filtered_df)} trains with no type filters"
                        )

                    display_df = filtered_df

                # Process the FROM-TO column to extract only the first part (MEX, SUF, etc.)
                if 'FROM-TO' in display_df.columns:
                    # Make a clean copy to avoid SettingWithCopyWarning
                    display_df = display_df.copy()

                    # Create a function to extract just the train type
                    def extract_train_type(value):
                        if pd.notna(value) and isinstance(value, str):
                            # Get the first part before any brackets or spaces
                            return value.split('[')[0].split(' ')[0].strip()
                        return value

                    # Apply the function to the entire column at once (more efficient)
                    display_df['FROM-TO'] = display_df['FROM-TO'].apply(
                        extract_train_type)

                    # Log for debugging
                    logger.info(f"Found column: FROM-TO")
                    for idx, value in enumerate(display_df['FROM-TO']):
                        if pd.notna(value):
                            logger.info(
                                f"Train {idx} - FROM-TO: '{value}', First three chars: '{str(value)[:3]}'"
                            )

                # Reset index and add a sequential serial number column
                display_df = display_df.reset_index(drop=True)

                # Add a sequential S.No. column at the beginning (before Select)
                display_df.insert(0, '#', range(1, len(display_df) + 1))

                # Create style info for train numbers
                if 'Train No.' in display_df.columns:
                    # Add a column with train number class for styling
                    def get_train_class(train_no):
                        if train_no is None or str(train_no).strip() == '':
                            return ''
                        train_no_str = str(train_no).strip()
                        if not train_no_str or len(train_no_str) == 0:
                            return ''
                        try:
                            first_digit = train_no_str[0]
                            return f'train-{first_digit}'
                        except:
                            return ''

                    # Set the train class attribute that will be used for styling
                    # This column will be used temporarily and removed before displaying the table
                    display_df['Train Class'] = display_df['Train No.'].apply(
                        get_train_class)

                    # Custom styler to add data attributes to cells
                    def apply_train_class_styler(df):
                        # Style the Train No column based on first digit
                        styles = []
                        for i, row in df.iterrows():
                            train_class = row.get('Train Class', '')
                            if train_class:
                                styles.append({
                                    'selector':
                                    f'td:nth-child(3)',
                                    'props':
                                    [('data-train-class', train_class)]
                                })
                        return styles

                    # Apply the styler function to add data attributes
                    # (Note: This may not be supported in all Streamlit versions)

                # Log FROM-TO values for debugging
                def log_from_to_values(df):
                    """Print FROM-TO values for each train to help with debugging"""

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
                    # Add a card for the table content with filter UI in the header
                    st.markdown(
                        '<div class="card shadow-sm mb-3"><div class="card-header bg-primary text-white d-flex justify-content-between align-items-center"><span>Train Data</span><span class="badge bg-light text-dark rounded-pill">Select stations to display on map</span></div>',
                        unsafe_allow_html=True)
                    
                    # Add the train filter UI right after the header but before the table
                    st.markdown("""
                    <style>
                    .filter-container {
                        background-color: #f8f9fa;
                        border-bottom: 1px solid #dee2e6;
                        padding: 10px 15px;
                        display: flex;
                        align-items: center;
                    }
                    .filter-title {
                        font-weight: bold;
                        color: #495057;
                        margin-right: 10px;
                        white-space: nowrap;
                    }
                    .filter-dropdown {
                        flex-grow: 1;
                        max-width: 600px;
                    }
                    </style>
                    <div class="filter-container">
                        <div class="filter-title">🔍 Train Type Filters:</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Create a dropdown for train type filters
                    filter_col1, filter_col2 = st.columns([3, 1])
                    
                    with filter_col1:
                        # Create options for the multiselect dropdown
                        options = []
                        for code, desc in train_types.items():
                            options.append(f"{code} - {desc}")
                        
                        # Track which train types are currently selected
                        selected_train_types = []
                        for code, is_selected in st.session_state.train_type_filters.items():
                            if is_selected:
                                selected_train_types.append(f"{code} - {train_types.get(code, '')}")
                        
                        # If none are selected, show a message
                        if len(selected_train_types) == 0:
                            selected_train_types = ["No filters selected - showing all trains"]
                            
                        # Create a multi-select dropdown for train types
                        new_selected = st.multiselect(
                            "Select train types to display:",
                            options=options,
                            default=selected_train_types,
                            key="train_type_dropdown"
                        )
                        
                        # Update session state based on the multiselect
                        for code in train_types.keys():
                            code_with_desc = f"{code} - {train_types.get(code, '')}"
                            is_selected = code_with_desc in new_selected
                            st.session_state.train_type_filters[code] = is_selected
                    
                    with filter_col2:
                        # Add a "Select All" button
                        all_selected = all(st.session_state.train_type_filters.values())
                        if st.button("Select All" if not all_selected else "Deselect All", key="select_all_button"):
                            new_state = not all_selected
                            for train_type in train_types.keys():
                                st.session_state.train_type_filters[train_type] = new_state
                            # Force a rerun to update the multiselect
                            st.experimental_rerun()
                    
                    # Continue with the card body
                    st.markdown('<div class="card-body p-0">', unsafe_allow_html=True)

                    # Use combination approach: Standard data_editor for selection + styled display

                    # Check if Select column already exists
                    if 'Select' not in display_df.columns:
                        display_df.insert(0, 'Select',
                                          False)  # Add selection column

                    # Fill any NaN values in the Select column with False to prevent filtering errors
                    display_df['Select'] = display_df['Select'].fillna(False)

                    # Display the main data table with integrated selection checkboxes
                    # Apply cell styling function to color the train numbers
                    styled_df = display_df.copy()

                    # Remove the "Train Class" column if it exists before displaying
                    if 'Train Class' in styled_df.columns:
                        styled_df = styled_df.drop(columns=['Train Class'])

                    # Import the styling function from color_train_formatter
                    from color_train_formatter import style_train_dataframe

                    # Use Streamlit's built-in dataframe with styling from our formatter
                    edited_df = st.data_editor(
                        style_train_dataframe(styled_df,
                                              train_column='Train No.'),
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
                                                        help="Train Number"),
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
                    # Fill NaN values in the Select column to prevent filtering errors
                    edited_df['Select'] = edited_df['Select'].fillna(False)
                    selected_count = len(
                        edited_df[edited_df['Select'] == True])
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
                    # Check if we need to rebuild the map from scratch or can use session state

                    # Extract station codes from selected rows
                    # Ensure we're using boolean indexing with no NaN values
                    selected_rows = edited_df[edited_df['Select'] == True]
                    # Determine which column contains station codes
                    station_column = 'Station' if 'Station' in edited_df.columns else 'CRD'
                    selected_station_codes = extract_station_codes(
                        selected_rows, station_column)

                    # Store the selected codes for comparison
                    if 'last_selected_codes' not in st.session_state:
                        st.session_state['last_selected_codes'] = []

                    # Convert to frozenset for comparison (order doesn't matter)
                    current_selected = frozenset(selected_station_codes)
                    last_selected = frozenset(
                        st.session_state['last_selected_codes'])

                    # Update the stored codes
                    st.session_state[
                        'last_selected_codes'] = selected_station_codes

                    # Create a cached map function for better performance
                    @st.cache_data(ttl=60, show_spinner=False)
                    def create_optimized_map(selected_codes_frozenset,
                                             center_lat=16.5167,
                                             center_lon=80.6167):
                        """Create an optimized map with selected stations highlighted"""
                        # Convert frozenset back to list
                        selected_station_codes_list = list(
                            selected_codes_frozenset)

                        # Create a folium map with fewer features for better performance
                        m = folium.Map(
                            location=[center_lat, center_lon
                                      ],  # Centered around Vijayawada
                            zoom_start=7,
                            control_scale=True,
                            prefer_canvas=True  # Use canvas renderer for speed
                        )

                        # Use a lightweight tile layer
                        folium.TileLayer(
                            tiles='CartoDB positron',  # Lighter map style
                            attr='&copy; OpenStreetMap contributors',
                            opacity=0.7).add_to(m)

                        # Get cached station coordinates
                        station_coords = get_station_coordinates()

                        # Process stations more efficiently
                        regular_stations = []
                        selected_stations = []
                        valid_points = []

                        # First classification pass - separate regular and selected stations
                        for code, coords in station_coords.items():
                            if code in selected_station_codes_list:
                                selected_stations.append((code, coords))
                            else:
                                regular_stations.append((code, coords))

                        # Add regular stations with optimized rendering
                        for code, coords in regular_stations:
                            # Add small circle markers for all stations
                            folium.CircleMarker([coords['lat'], coords['lon']],
                                                radius=3,
                                                color='#800000',
                                                fill=True,
                                                fill_color='gray',
                                                fill_opacity=0.6,
                                                tooltip=f"{code}").add_to(m)

                            # Add permanent text label for station with dynamic width
                            label_width = max(
                                len(code) * 7, 20
                            )  # Adjust width based on station code length
                            folium.Marker(
                                [coords['lat'], coords['lon'] + 0.005],
                                icon=folium.DivIcon(
                                    icon_size=(0, 0),
                                    icon_anchor=(0, 0),
                                    html=
                                    f'<div style="display:inline-block; min-width:{label_width}px; font-size:10px; background-color:rgba(255,255,255,0.7); padding:1px 3px; border-radius:2px; border:1px solid #800000; text-align:center;">{code}</div>'
                                )).add_to(m)

                        # Add selected stations with train icons
                        for code, coords in selected_stations:
                            normalized_code = code.strip().upper()
                            lat = coords['lat']
                            lon = coords['lon']

                            # Add a large train icon marker for selected stations
                            folium.Marker(
                                [lat, lon],
                                popup=f"<b>{normalized_code}</b>",
                                tooltip=normalized_code,
                                icon=folium.Icon(color='red',
                                                 icon='train',
                                                 prefix='fa'),
                            ).add_to(m)

                            # Add a prominent label with bolder styling and dynamic width
                            label_width = max(
                                len(normalized_code) * 10,
                                30)  # Larger width for selected stations
                            folium.Marker(
                                [lat, lon + 0.01],
                                icon=folium.DivIcon(
                                    icon_size=(0, 0),
                                    icon_anchor=(0, 0),
                                    html=
                                    f'<div style="display:inline-block; min-width:{label_width}px; font-size:14px; font-weight:bold; background-color:rgba(255,255,255,0.9); padding:3px 5px; border-radius:3px; border:2px solid red; text-align:center;">{normalized_code}</div>'
                                )).add_to(m)

                            valid_points.append([lat, lon])

                        # Add railway lines between selected stations if more than one
                        if len(valid_points) > 1:
                            folium.PolyLine(valid_points,
                                            weight=2,
                                            color='gray',
                                            opacity=0.8,
                                            dash_array='5, 10').add_to(m)

                        return m, valid_points

                    # Call the cached map function
                    with st.spinner("Rendering map..."):
                        m, valid_points = create_optimized_map(
                            current_selected)

                    # Use a feature that allows map to remember its state (zoom, pan position)
                    st_folium(m, width=None, height=600, key="persistent_map")

                    st.markdown('</div></div>', unsafe_allow_html=True)

                    # Show success message if stations are selected
                    if len(selected_station_codes) > 0:
                        st.success(
                            f"Showing {len(selected_station_codes)} selected stations on the map"
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


# Note: Custom formatter is already imported at the top of the file

# Footer
st.markdown("---")
st.markdown(
    '<div class="card"><div class="card-body text-center text-muted">© 2023 South Central Railway - Vijayawada Division</div></div>',
    unsafe_allow_html=True)
