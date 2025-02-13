import streamlit as st
import pandas as pd
from data_handler import DataHandler

# Page configuration
st.set_page_config(
    page_title="Data Status - Train Tracking System",
    page_icon="🚂",
    layout="wide"
)

# Initialize data handler if not in session state
if 'data_handler' not in st.session_state:
    st.session_state['data_handler'] = DataHandler()

# Page title
st.title("📊 Data Status")
st.markdown("This page shows the current state of loaded data and cache.")

try:
    data_handler = st.session_state['data_handler']
    
    # Load data
    success, message = data_handler.load_data_from_drive()
    
    if success:
        # Show last update time
        if data_handler.last_update:
            st.info(f"Last updated: {data_handler.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get cached data
        cached_data = data_handler.get_cached_data()
        
        # Display cache status
        st.subheader("Cache Status")
        st.write(f"Number of records in cache: {len(cached_data)}")
        
        if cached_data:
            # Show sample record
            st.subheader("Sample Record")
            st.json(cached_data[0])
            
            # Show all cached data
            st.subheader("All Cached Data")
            df = pd.DataFrame(cached_data)
            st.dataframe(df)
        else:
            st.warning("No data in cache")
            
        # Show column statistics
        st.subheader("Column Statistics")
        columns = data_handler.get_all_columns()
        for column in columns:
            stats = data_handler.get_column_statistics(column)
            st.write(f"**{column}**")
            st.write(f"- Unique values: {stats['unique_count']}")
            st.write(f"- Total records: {stats['total_count']}")
            st.write(f"- Last updated: {stats['last_updated']}")
            st.write("---")
    else:
        st.error(f"Error loading data: {message}")
        
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)
