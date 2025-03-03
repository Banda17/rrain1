import streamlit as st
import pandas as pd
import time
from data_handler import DataHandler
from database import init_db  # Import init_db function
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add responsive CSS for mobile layout
st.markdown("""
<style>
    /* Base responsive styles */
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* Header styles */
    h1 {
        font-size: 1.8rem !important;
    }

    /* Table responsiveness */
    .dataframe-container {
        overflow-x: auto;
        width: 100%;
    }

    /* Adjustments for small screens */
    @media screen and (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }

        h1 {
            font-size: 1.5rem !important;
        }

        h2 {
            font-size: 1.2rem !important;
        }

        /* Adjust button sizes */
        .stButton button {
            width: 100% !important;
            padding: 0.5rem !important;
        }

        /* Adjust download button */
        .stDownloadButton button {
            width: 100% !important;
        }
    }

    /* Make data tables horizontally scrollable */
    [data-testid="stDataFrame"] {
        width: 100% !important;
        max-width: 100% !important;
    }

    [data-testid="stDataFrame"] > div {
        overflow-x: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# Page configuration
st.set_page_config(
    page_title="Raw Data - Train Tracking System",
    page_icon="🚂",
    layout="wide"
)

# Initialize data handler
if 'data_handler' not in st.session_state:
    st.session_state['data_handler'] = DataHandler()

# Page title
st.title("📊 Raw CSV Data")
st.markdown("This page shows the raw data loaded from the CSV file.")

# Add a database initialization button
if st.button("Initialize Database"):
    with st.spinner("Initializing database connection..."):
        try:
            init_db()
            st.session_state['db_initialized'] = True
            st.success("Database initialized successfully")
            logger.info("Database initialized manually")
        except Exception as e:
            st.error(f"Database initialization error: {str(e)}")
            logger.error(f"Database initialization error: {str(e)}")

try:
    # Load data
    success, message = st.session_state['data_handler'].load_data_from_drive()

    if success:
        # Get raw data from cache
        raw_data = pd.DataFrame.from_dict(st.session_state['data_handler'].get_cached_data())

        if raw_data is not None and not raw_data.empty:
            # Reset the index and use first row as header
            raw_data.columns = raw_data.iloc[0]
            raw_data = raw_data.iloc[1:].reset_index(drop=True)

            # Add last update time
            st.info(f"Last updated: {st.session_state['data_handler'].last_update.strftime('%Y-%m-%d %H:%M:%S')}")

            # Add search functionality
            search_term = st.text_input("🔍 Search in data", "")

            # Filter data based on search term
            if search_term:
                filtered_data = raw_data[raw_data.apply(lambda x: x.astype(str).str.contains(search_term, case=False).any(), axis=1)]
            else:
                filtered_data = raw_data

            # Display data info
            st.info(f"Total rows: {len(filtered_data)} | Total columns: {len(filtered_data.columns)}")

            # Wrap dataframe in a container for horizontal scrolling on mobile
            st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)

            # Display the data
            st.dataframe(
                filtered_data,
                use_container_width=True,
                height=500
            )

            st.markdown("</div>", unsafe_allow_html=True)

            # Create a container for bottom controls to improve mobile layout
            col1, col2 = st.columns([1, 1])

            with col1:
                # Download button
                st.download_button(
                    label="📥 Download CSV",
                    data=filtered_data.to_csv(index=False),
                    file_name="train_data.csv",
                    mime="text/csv"
                )

            with col2:
                # Add a manual refresh button
                if st.button("🔄 Refresh Data"):
                    st.rerun()

            # Remove the auto-refresh timer to avoid unexpected reloads on mobile
            # Auto-refresh every 5 minutes on desktop only
            if st.session_state.get('auto_refresh', True) and not st.session_state.get('is_mobile', False):
                time.sleep(300)  # 5 minutes
                st.rerun()
        else:
            st.warning("No data available to display")
    else:
        st.error(f"Error loading data: {message}")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)