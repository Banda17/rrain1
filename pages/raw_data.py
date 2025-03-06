import streamlit as st
import pandas as pd
import time
from data_handler import DataHandler
from database import init_db  # Import init_db function
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Raw Data - Train Tracking System",
    page_icon="🚂",
    layout="wide"
)

# Add Bootstrap CSS
st.markdown("""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        /* Custom styles to enhance Bootstrap */
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0 !important;
            max-width: 90% !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0px !important;
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
        /* Remove all padding and margins between columns */
        .stColumn > div {
            padding: 0px !important;
        }
        div[data-testid="column"] {
            padding: 0px !important;
            margin: 0px !important;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize data handler
if 'data_handler' not in st.session_state:
    st.session_state['data_handler'] = DataHandler()

# Page title
st.title("📊 Raw CSV Data")
st.markdown("""
<div class="card mb-3">
    <div class="card-body">
        <p class="card-text">This page shows the raw data loaded from the CSV file.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Add a database initialization button
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("Initialize Database", type="primary", help="Click to initialize the database connection"):
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

            # Add search functionality in a card
            st.markdown('<div class="card mb-3"><div class="card-header bg-light">Data Search</div><div class="card-body">', unsafe_allow_html=True)
            search_term = st.text_input("🔍 Search in data", "")
            st.markdown('</div></div>', unsafe_allow_html=True)

            # Filter data based on search term
            if search_term:
                filtered_data = raw_data[raw_data.apply(lambda x: x.astype(str).str.contains(search_term, case=False).any(), axis=1)]
            else:
                filtered_data = raw_data

            # Display data info
            #st.info(f"Total rows: {len(filtered_data)} | Total columns: {len(filtered_data.columns)}")

            # Display the data in a card with enhanced Bootstrap styling
            st.markdown('<div class="card shadow-sm mb-3"><div class="card-header bg-primary text-white d-flex justify-content-between align-items-center"><span>Raw Data</span><span class="badge bg-light text-dark rounded-pill">Showing {len(filtered_data)} records</span></div><div class="card-body p-0">', unsafe_allow_html=True)
            # Display the data
            st.dataframe(
                filtered_data,
                use_container_width=True,
                height=500
            )
            # Add a footer with data summary
            st.markdown(f'<div class="card-footer bg-light d-flex justify-content-between"><span>Total Rows: {len(filtered_data)}</span><span>Columns: {len(filtered_data.columns)}</span></div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

            # Download button in a card
            st.markdown('<div class="card mb-3"><div class="card-body text-center">', unsafe_allow_html=True)
            st.download_button(
                label="📥 Download CSV",
                data=filtered_data.to_csv(index=False),
                file_name="train_data.csv",
                mime="text/csv",
                help="Download the filtered data as a CSV file"
            )
            st.markdown('</div></div>', unsafe_allow_html=True)

            # Auto-refresh every 5 minutes
            time.sleep(300)  # 5 minutes
            st.rerun()
        else:
            st.warning("No data available to display")
    else:
        st.error(f"Error loading data: {message}")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)