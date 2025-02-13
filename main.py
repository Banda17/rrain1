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
    initial_sidebar_state="collapsed"
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

# Main title
st.title("🚂 Train List")

try:
    # Load data with caching
    success, status_table, cached_data, message = load_and_process_data()

    if success and not cached_data.empty:
        # Filter only numeric train numbers
        numeric_trains = cached_data[cached_data['Train Name'].str.match(r'^\d.*', na=False)]

        if not numeric_trains.empty:
            # Create simple display table with only Train Name
            display_table = pd.DataFrame({
                'Train Name': numeric_trains['Train Name']
            })

            # Display the table
            st.dataframe(
                display_table.drop_duplicates('Train Name'),
                use_container_width=True,
                height=400
            )
        else:
            st.info("No trains found")
    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("Train Tracking System")