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
from map_viewer import MapViewer
import folium
from streamlit_folium import folium_static

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize database
init_db()


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


# Page configuration
st.set_page_config(page_title="Train Tracking System",
                   page_icon="🚂",
                   layout="wide",
                   initial_sidebar_state="collapsed")

# Add headers
st.markdown("""
    <h1 style='text-align: center; color: #1f497d;'>South Central Railway</h1>
    <h2 style='text-align: center; color: #4f81bd;'>Vijayawada Division</h2>
    <hr>
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
        'selected_stations': {
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
def load_and_process_data():
    """Cache data loading and processing"""
    success, message = st.session_state['icms_data_handler'].load_data_from_drive()
    if success:
        status_table = st.session_state['icms_data_handler'].get_train_status_table()
        cached_data = st.session_state['icms_data_handler'].get_cached_data()
        if cached_data:
            return True, status_table, pd.DataFrame(cached_data), message
    return False, None, None, message


# Initialize session state
initialize_session_state()

# Main page title
st.title("ICMS Data - Vijayawada Division")

# Add a refresh button at the top with just an icon
col1, col2 = st.columns([10, 1])
with col2:
    if st.button("🔄", type="primary"):
        st.rerun()

try:
    data_handler = st.session_state['icms_data_handler']

    # Set refreshing state to True and show animation
    st.session_state['is_refreshing'] = True
    refresh_placeholder = st.empty()
    create_pulsing_refresh_animation(refresh_placeholder, "Loading ICMS data...")

    # Load data with feedback
    with st.spinner("Loading ICMS data..."):
        success, message = data_handler.load_data_from_drive()

    # Clear the refresh animation when done
    st.session_state['is_refreshing'] = False
    refresh_placeholder.empty()

    if success:
        # Get cached data
        cached_data = data_handler.get_cached_data()

        if cached_data:
            # Convert to DataFrame
            df = pd.DataFrame(cached_data)

            if not df.empty:
                # Skip first two rows (0 and 1) and reset index
                df = df.iloc[2:].reset_index(drop=True)

                # Add a Select column for checkboxes
                df['Select'] = False

                # Safe conversion of NaN values to None
                def safe_convert(value):
                    if pd.isna(value) or pd.isnull(value):
                        return None
                    return str(value) if value is not None else None

                # Apply safe conversion to all elements
                df = df.applymap(safe_convert)

                # Drop unwanted columns - use exact column names with proper spacing
                columns_to_drop = [
                    'Sr.',
                    'Exit Time for NLT Status',
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
                    'Divisional Actual [Entry - Exit]',
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

                # Split the display into two columns - table and map
                col_table, col_map = st.columns([2, 1])

                with col_table:
                    # Refresh animation placeholder right before displaying the table
                    refresh_table_placeholder = st.empty()
                    create_pulsing_refresh_animation(refresh_table_placeholder, "Refreshing Table...")

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
                        filtered_df = df[df['Delay'].apply(is_positive_or_plus)]
                        st.write(
                            f"Showing {len(filtered_df)} entries with positive delays"
                        )
                    else:
                        filtered_df = df
                        st.warning("Delay column not found in data")

                    # Function to highlight cells red
                    def highlight_positive_delay(val):
                        """Apply red background to positive delay values"""
                        if isinstance(val, str) and ('+' in val or is_positive_or_plus(val)):
                            return 'background-color: #ffcccc; color: #cc0000; font-weight: bold'
                        return ''

                    # Apply styling to DataFrame
                    styled_df = filtered_df.style.applymap(highlight_positive_delay, subset=['Delay'])

                    # Show the filtered data with checkbox column
                    edited_df = st.data_editor(
                        filtered_df,
                        use_container_width=True,
                        column_config={
                            "Select": st.column_config.CheckboxColumn(
                                "Select",
                                help="Select to show on map",
                                default=False
                            ),
                            "Train No.": st.column_config.TextColumn(
                                "Train No.",
                                help="Train Number"
                            ),
                            "IC Entry Delay": st.column_config.TextColumn(
                                "IC Entry Delay",
                                help="Entry Delay"
                            ),
                            "Delay": st.column_config.TextColumn(
                                "Delay",
                                help="Delay in Minutes"
                            )
                        }
                    )

                    # Get selected stations for map display
                    selected_rows = edited_df[edited_df['Select']]
                    selected_stations = []

                    if not selected_rows.empty:
                        # Extract station codes from selected rows
                        for _, row in selected_rows.iterrows():
                            if 'Station' in row and row['Station']:
                                selected_stations.append(row['Station'])

                        # Update session state
                        st.session_state['selected_stations'] = selected_stations
                    else:
                        st.session_state['selected_stations'] = []

                    refresh_table_placeholder.empty()

                with col_map:
                    st.subheader("Interactive GPS Map")

                    # Define Andhra Pradesh center coordinates
                    AP_CENTER = [16.5167, 80.6167]  # Centered around Vijayawada

                    # Define station coordinates with actual GPS locations
                    stations = {
                        'BZA': {'name': 'Vijayawada', 'lat': 16.5167, 'lon': 80.6167},
                        'GNT': {'name': 'Guntur', 'lat': 16.3067, 'lon': 80.4365},
                        'VSKP': {'name': 'Visakhapatnam', 'lat': 17.6868, 'lon': 83.2185},
                        'TUNI': {'name': 'Tuni', 'lat': 17.3572, 'lon': 82.5483},
                        'RJY': {'name': 'Rajahmundry', 'lat': 17.0005, 'lon': 81.7799},
                        'NLDA': {'name': 'Nalgonda', 'lat': 17.0575, 'lon': 79.2690},
                        'MTM': {'name': 'Mangalagiri', 'lat': 16.4307, 'lon': 80.5525},
                        'NDL': {'name': 'Nidadavolu', 'lat': 16.9107, 'lon': 81.6717},
                        'ANV': {'name': 'Anakapalle', 'lat': 17.6910, 'lon': 83.0037},
                        'VZM': {'name': 'Vizianagaram', 'lat': 18.1066, 'lon': 83.4205},
                        'SKM': {'name': 'Srikakulam', 'lat': 18.2949, 'lon': 83.8935},
                        'PLH': {'name': 'Palasa', 'lat': 18.7726, 'lon': 84.4162}
                    }

                    # Create the map centered on Vijayawada
                    m = folium.Map(
                        location=AP_CENTER,
                        zoom_start=7,
                        tiles='OpenStreetMap'
                    )

                    # Add markers for selected stations
                    selected_stations = st.session_state.get('selected_stations', [])

                    if selected_stations:
                        # Add markers for selected stations
                        for station_code in selected_stations:
                            if station_code in stations:
                                station_info = stations[station_code]

                                # Create custom popup content
                                popup_content = f"""
                                <div style='font-family: Arial; font-size: 12px;'>
                                    <b>{station_code} - {station_info['name']}</b><br>
                                    Lat: {station_info['lat']:.4f}<br>
                                    Lon: {station_info['lon']:.4f}
                                </div>
                                """

                                folium.Marker(
                                    [station_info['lat'], station_info['lon']],
                                    popup=folium.Popup(popup_content, max_width=200),
                                    tooltip=station_code,
                                    icon=folium.Icon(color='red', icon='info-sign')
                                ).add_to(m)

                        # Add railway lines between selected stations if more than one
                        if len(selected_stations) > 1:
                            station_points = []
                            for code in selected_stations:
                                if code in stations:
                                    station_points.append([stations[code]['lat'], stations[code]['lon']])

                            folium.PolyLine(
                                station_points,
                                weight=2,
                                color='gray',
                                opacity=0.8,
                                dash_array='5, 10'
                            ).add_to(m)

                    # Display the map
                    folium_static(m, width=400, height=500)

                    # Show info message if no stations selected
                    if not selected_stations:
                        st.info("Select stations from the table on the left to view them on the map")
                    else:
                        st.success(f"Showing {len(selected_stations)} selected stations on the map")

        else:
            st.warning("No data available in cache")

    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("Train Tracking System")

# Display refresh information
now = datetime.now()
# Convert to IST (UTC+5:30)
ist_time = now + timedelta(hours=5, minutes=30)
st.session_state['last_refresh'] = now
st.caption(f"Last refresh: {ist_time.strftime('%Y-%m-%d %H:%M:%S')} IST")
st.caption("Auto-refreshing every 4 minutes")

# Removed the old progress bar and replaced it with a countdown timer.
show_countdown_progress(240, 0.1)
show_refresh_timestamp()

# Refresh the page
st.rerun()