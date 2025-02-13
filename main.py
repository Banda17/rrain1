import streamlit as st
import pandas as pd
from data_handler import DataHandler
from ai_analyzer import AIAnalyzer
from visualizer import Visualizer
from utils import format_time_difference, create_status_badge, show_ai_insights
from database import init_db
import time
from datetime import datetime

# Initialize database
init_db()

# Page configuration
st.set_page_config(
    page_title="Train Tracking System",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="collapsed"  # Optimize initial load
)

# Initialize session state
if 'data_handler' not in st.session_state:
    st.session_state['data_handler'] = DataHandler()
if 'ai_analyzer' not in st.session_state:
    st.session_state['ai_analyzer'] = AIAnalyzer()
if 'visualizer' not in st.session_state:
    st.session_state['visualizer'] = Visualizer()
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None

@st.cache_data(ttl=300)
def load_and_process_data():
    """Cache data loading and processing"""
    success, message = st.session_state['data_handler'].load_data_from_drive()
    if success:
        status_table = st.session_state['data_handler'].get_train_status_table()
        cached_data = pd.DataFrame(st.session_state['data_handler'].get_cached_data())
        return True, status_table, cached_data, message
    return False, None, None, message

# Main title and description
st.title("🚂 Train Tracking System")
st.markdown("Real-time train tracking and analysis system")

try:
    # Load data with caching
    success, status_table, cached_data, message = load_and_process_data()

    if success:
        # Update last update time
        st.session_state['last_update'] = st.session_state['data_handler'].last_update

        # Display current status
        st.header("Current Train Status")
        col1, col2 = st.columns([2, 1])

        with col1:
            # Display train position visualization
            if not status_table.empty:
                fig = st.session_state['visualizer'].create_train_position_map(status_table)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Display latest status
            if not status_table.empty:
                latest_status = status_table.iloc[-1]
                st.markdown(f"**Current Station:** {latest_status['station']}")
                st.markdown(f"**Status:** {create_status_badge(latest_status['status'])}", unsafe_allow_html=True)
                st.markdown(f"**Time Difference:** {format_time_difference(latest_status['delay'])}")
            else:
                st.warning("No status data available")

        # Process and display timing analysis
        if not cached_data.empty:
            st.header("All Train Timings")

            # Convert time column to datetime if it's not already
            if 'Time' in cached_data.columns:
                cached_data['Time'] = pd.to_datetime(cached_data['Time'])

            # Filter only numeric train numbers
            numeric_trains = cached_data[cached_data['Train Name'].str.match(r'^\d.*', na=False)]

            if not numeric_trains.empty:
                # Create display table with timestamps
                display_table = pd.DataFrame({
                    'Train Number': numeric_trains['Train Name'],
                    'Station': numeric_trains['Station'],
                    'Time': numeric_trains['Time'].dt.strftime('%Y-%m-%d %H:%M'),
                    'Running Status': numeric_trains['Status'].fillna('Unknown'),
                })

                st.dataframe(
                    display_table.sort_values('Time'),
                    use_container_width=True,
                    height=400  # Fixed height for better performance
                )

                # Show performance metrics
                metrics = st.session_state['data_handler'].get_performance_metrics()
                st.info(f"Data load time: {metrics['load_time']:.2f}s | Processing time: {metrics['process_time']:.2f}s")
            else:
                st.info("No trains with numeric IDs found")
        else:
            st.warning("No data available for analysis")
    else:
        st.error(f"Error loading data: {message}")

    # Auto-refresh every 5 minutes
    time.sleep(300)
    st.rerun()

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("Train Tracking System - Real-time Analysis")