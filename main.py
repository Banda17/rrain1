import streamlit as st
import pandas as pd
import time
from data_handler import DataHandler
from train_schedule import TrainSchedule
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize session state
if 'data_handler' not in st.session_state:
    st.session_state['data_handler'] = DataHandler()
if 'train_schedule' not in st.session_state:
    st.session_state['train_schedule'] = TrainSchedule()
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None

@st.cache_data(ttl=300)
def load_and_process_data():
    """Cache data loading and processing"""
    success, message = st.session_state['data_handler'].load_data_from_drive()
    if success:
        status_table = st.session_state['data_handler'].get_train_status_table()
        cached_data = st.session_state['data_handler'].get_cached_data()
        if cached_data:
            return True, status_table, cached_data, message
    return False, None, None, message

# Main title
st.title("🚂 Train List")

try:
    # Load data with caching
    success, status_table, cached_data, message = load_and_process_data()

    if success and cached_data:
        # Convert cached data to DataFrame
        df = pd.DataFrame(cached_data)
        logger.debug(f"Initial DataFrame shape: {df.shape}")
        logger.debug(f"DataFrame columns: {df.columns}")
        logger.debug(f"Sample data:\n{df.head()}")

        if not df.empty:
            # Create mask for numeric train names
            numeric_mask = df['Train Name'].str.match(r'^\d+', na=False)
            logger.debug(f"Number of trains with numeric names: {numeric_mask.sum()}")

            if numeric_mask.sum() > 0:
                # Filter data
                columns_needed = ['Train Name', 'Station', 'Time', 'Status']
                filtered_df = df.loc[numeric_mask, columns_needed].copy()
                logger.debug(f"Filtered DataFrame shape: {filtered_df.shape}")

                # Add scheduled time column
                filtered_df['Sch_Time'] = filtered_df.apply(
                    lambda row: st.session_state['train_schedule'].get_scheduled_time(
                        str(row['Train Name']), str(row['Station'])
                    ),
                    axis=1
                )

                # Show filtering info
                st.info(f"Found {len(filtered_df)} trains with numeric names")

                # Display the filtered data
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    height=400
                )
            else:
                st.warning("No trains with numeric names found in the data")
        else:
            st.warning("No data available to display")
    else:
        st.error(f"Error loading data: {message}")

except Exception as e:
    logger.error(f"Error occurred: {str(e)}", exc_info=True)
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("Train Tracking System")