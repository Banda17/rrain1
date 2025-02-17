import streamlit as st
import pandas as pd
import time
from data_handler import DataHandler
from ai_analyzer import AIAnalyzer
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge, show_ai_insights
from database import init_db
from train_schedule import TrainSchedule
from datetime import datetime
import logging
from map_viewer import MapViewer

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Page configuration
st.set_page_config(
    page_title="Train Tracking System",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'data_handler' not in st.session_state:
    st.session_state['data_handler'] = DataHandler()
if 'ai_analyzer' not in st.session_state:
    st.session_state['ai_analyzer'] = AIAnalyzer()
if 'visualizer' not in st.session_state:
    st.session_state['visualizer'] = Visualizer()
if 'train_schedule' not in st.session_state:
    st.session_state['train_schedule'] = TrainSchedule()
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None
if 'selected_train' not in st.session_state:
    st.session_state['selected_train'] = None
if 'map_viewer' not in st.session_state:
    st.session_state['map_viewer'] = MapViewer()
if 'previous_selection' not in st.session_state:
    st.session_state['previous_selection'] = None

def calculate_delay(actual_time, scheduled_time):
    """Calculate delay between actual and scheduled time in minutes"""
    try:
        # Log the input times for debugging
        logger.debug(f"Calculating delay - Actual: {actual_time}, Scheduled: {scheduled_time}")

        if not actual_time or not scheduled_time:
            logger.warning("Missing time data")
            return None

        # Get the current year
        current_year = datetime.now().year

        # Clean and standardize the time strings
        actual_time = str(actual_time).strip()
        scheduled_time = str(scheduled_time).strip()

        # Log the cleaned times
        logger.debug(f"Cleaned times - Actual: {actual_time}, Scheduled: {scheduled_time}")

        # Append the year to the time strings
        actual_time_with_year = f"{actual_time} {current_year}"
        scheduled_time_with_year = f"{scheduled_time} {current_year}"

        # Define the format
        time_format = '%H:%M %d-%m %Y'

        # Parse the times with error handling
        try:
            actual = pd.to_datetime(actual_time_with_year, format=time_format)
            logger.debug(f"Parsed actual time: {actual}")
        except ValueError as e:
            logger.error(f"Error parsing actual time: {e}")
            return None

        try:
            scheduled = pd.to_datetime(scheduled_time_with_year, format=time_format)
            logger.debug(f"Parsed scheduled time: {scheduled}")
        except ValueError as e:
            logger.error(f"Error parsing scheduled time: {e}")
            return None

        # Calculate the delay in minutes
        delay = int((actual - scheduled).total_seconds() / 60)
        logger.debug(f"Calculated delay: {delay} minutes")
        return delay

    except Exception as e:
        logger.error(f"Error calculating delay: {str(e)}")
        return None

def get_delay_color(delay):
    """Return background color based on delay"""
    if delay is None:
        return ["background-color: #e0e0e0"] * 7  # Gray for unknown delay
    if delay <= -5:  # Early
        return ["background-color: #c8e6c9"] * 7  # Light green for all columns
    elif delay > 5:  # Late
        return ["background-color: #ffcdd2"] * 7  # Light red for all columns
    else:  # On time
        return ["background-color: white"] * 7

def format_delay(delay):
    """Format delay with icon and color"""
    if delay is None:
        return "❓ Unknown Delay"
    if delay <= -5:
        return f"⏰ {abs(delay)} mins early"
    elif delay > 5:
        return f"⚠️ {delay} mins late"
    else:
        return f"✅ On time ({delay} mins)"

@st.cache_data(ttl=300)
def load_and_process_data():
    """Cache data loading and processing"""
    success, message = st.session_state['data_handler'].load_data_from_drive()
    if success:
        status_table = st.session_state['data_handler'].get_train_status_table()
        cached_data = st.session_state['data_handler'].get_cached_data()
        if cached_data:
            return True, status_table, pd.DataFrame(cached_data), message
    return False, None, None, message

# Map Section
st.title("🗺️ Division Map")
# Render the map using the MapViewer component
st.session_state['map_viewer'].render(st.session_state.get('selected_train'))

# Train List Section
st.title("🚂 Train List")

try:
    # Load data with caching
    success, status_table, cached_data, message = load_and_process_data()

    if success and cached_data is not None and not cached_data.empty:
        # Initialize DataFrame with first row as header
        df = pd.DataFrame(cached_data)
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)

        # Create mask for numeric train names
        numeric_mask = df['Train Name'].str.match(r'^\d.*', na=False)

        # Create new DataFrame with only required data
        columns_needed = ['Train Name', 'Station', 'Time', 'Status']
        filtered_df = df.loc[numeric_mask, columns_needed].copy()

        # Add scheduled time column
        def get_scheduled_time_with_logging(row):
            train_name = str(row['Train Name'])
            station = str(row['Station'])
            scheduled_time = st.session_state['train_schedule'].get_scheduled_time(
                train_name, station
            )
            return scheduled_time if scheduled_time else row['Time']  # Use actual time if scheduled not available

        # Add Sch_Time column
        filtered_df['Sch_Time'] = filtered_df.apply(
            get_scheduled_time_with_logging,
            axis=1
        )

        # Calculate delay with enhanced error handling
        filtered_df['Delay'] = filtered_df.apply(
            lambda x: calculate_delay(x['Time'], x['Sch_Time']),
            axis=1
        )

        # Format delay text, handling None values
        filtered_df['Delay_Text'] = filtered_df['Delay'].apply(
            lambda d: format_delay(d) if d is not None else "❓ Unknown Delay"
        )

        # Add checkbox column
        filtered_df['Select'] = False

        # Reorder columns to show checkbox first
        column_order = ['Select', 'Train Name', 'Station', 'Sch_Time', 'Time', 'Delay_Text', 'Status']
        filtered_df = filtered_df[column_order]

        # Show filtering info
        st.info(f"Found {len(filtered_df)} trains with numeric names")

        # Create column configuration with styling
        column_config = {
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select to highlight on map",
                default=False,
            ),
            "Train Name": st.column_config.TextColumn(
                "Train Name",
                help="Train number and name"
            ),
            "Station": st.column_config.TextColumn(
                "Station",
                help="Current station"
            ),
            "Sch_Time": st.column_config.TextColumn(
                "Scheduled Time",
                help="Working Time Table (WTT) time"
            ),
            "Time": st.column_config.TextColumn(
                "Actual Time",
                help="Actual arrival/departure time"
            ),
            "Delay_Text": st.column_config.TextColumn(
                "Delay Status",
                help="Time difference between scheduled and actual arrival"
            ),
            "Status": st.column_config.TextColumn(
                "Status",
                help="Current status"
            )
        }

        # Make the dataframe interactive with styling
        edited_df = st.data_editor(
            filtered_df,
            use_container_width=True,
            height=400,
            key="train_selector",
            column_order=column_order,
            column_config=column_config,
            disabled=["Train Name", "Station", "Sch_Time", "Time", "Delay_Text", "Status"],
            hide_index=True,
            # Apply conditional styling based on delay
            style=filtered_df.apply(lambda x: get_delay_color(x['Delay']), axis=1)
        )

        # Handle train selection
        if len(edited_df) > 0:
            # Get currently selected trains
            selected_trains = edited_df[edited_df['Select']]

            # Clear selection if no trains are selected
            if selected_trains.empty:
                st.session_state['selected_train'] = None
                st.session_state['previous_selection'] = None
            else:
                # Get the first selected train
                first_selected = selected_trains.iloc[0]

                # Get delay for the selected train
                delay = calculate_delay(first_selected['Time'], first_selected['Sch_Time'])

                # Create new selection
                new_selection = {
                    'train': first_selected['Train Name'],
                    'station': first_selected['Station']
                }

                # Only update if selection has changed
                if new_selection != st.session_state['previous_selection']:
                    st.session_state['selected_train'] = new_selection
                    st.session_state['previous_selection'] = new_selection

                    # Display detailed info for selected train with formatted delay
                    st.write("**Selected Train Details:**")
                    st.info({
                        'Train Number': first_selected['Train Name'],
                        'Station': first_selected['Station'],
                        'Scheduled Time': first_selected['Sch_Time'],
                        'Actual Time': first_selected['Time'],
                        'Delay Status': format_delay(delay),
                        'Status': first_selected['Status']
                    })

    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    logger.error(f"Error occurred: {str(e)}", exc_info=True)
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("Train Tracking System")