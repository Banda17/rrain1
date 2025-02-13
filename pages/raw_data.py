import streamlit as st
import pandas as pd
from data_handler import DataHandler

# Page configuration
st.set_page_config(
    page_title="Raw Data - Train Tracking System",
    page_icon="🚂",
    layout="wide"
)

# Initialize data handler
if 'data_handler' not in st.session_state:
    st.session_state.data_handler = DataHandler()

# Page title
st.title("📊 Raw CSV Data")
st.markdown("This page shows the filtered train data from the CSV file.")

try:
    # Load data
    success, message = st.session_state.data_handler.load_data_from_drive()

    if success:
        # Get raw data
        raw_data = st.session_state.data_handler.data

        if raw_data is not None and not raw_data.empty:
            # Filter trains starting with numbers
            numeric_trains = raw_data[raw_data['train_id'].str.match(r'^\d')]

            # Add search functionality
            search_term = st.text_input("🔍 Search in data", "")

            # Filter data based on search term
            if search_term:
                filtered_data = numeric_trains[numeric_trains.apply(lambda x: x.astype(str).str.contains(search_term, case=False).any(), axis=1)]
            else:
                filtered_data = numeric_trains

            # Display data info
            st.info(f"Total trains with numeric IDs: {len(filtered_data)} | Total columns: {len(filtered_data.columns)}")

            # Display the data
            st.dataframe(
                filtered_data,
                use_container_width=True,
                height=500
            )

            # Download button
            st.download_button(
                label="📥 Download Filtered CSV",
                data=filtered_data.to_csv(index=False),
                file_name="filtered_train_data.csv",
                mime="text/csv"
            )
        else:
            st.warning("No data available to display")
    else:
        st.error(f"Error loading data: {message}")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)