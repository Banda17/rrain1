import streamlit as st
import pandas as pd
from data_handler import DataHandler
import time

# Page configuration
st.set_page_config(
    page_title="ICMS Data - Train Tracking System",
    page_icon="🚂",
    layout="wide"
)

# Initialize data handler if not in session state
if 'icms_data_handler' not in st.session_state:
    data_handler = DataHandler()
    # Override the spreadsheet URL for ICMS data
    data_handler.spreadsheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=155911658&single=true&output=csv"
    st.session_state['icms_data_handler'] = data_handler

# Page title
st.title("📊 ICMS Data")
st.markdown("Integrated Coaching Management System Data View")

try:
    data_handler = st.session_state['icms_data_handler']
    
    # Load data
    success, message = data_handler.load_data_from_drive()
    
    if success:
        # Show last update time
        if data_handler.last_update:
            st.info(f"Last updated: {data_handler.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get cached data
        cached_data = data_handler.get_cached_data()
        
        if cached_data:
            # Convert to DataFrame and set first row as headers
            df = pd.DataFrame(cached_data)
            if not df.empty:
                # Set the first row as column headers
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
                
                # Show the data
                st.subheader("ICMS Records")
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=600
                )
                
                # Show data statistics
                st.subheader("Data Statistics")
                st.write(f"Total Records: {len(df)}")
                
                # Display column statistics
                col1, col2 = st.columns(2)
                with col1:
                    st.write("Column Information:")
                    for column in df.columns:
                        st.write(f"- {column}: {df[column].nunique()} unique values")
                
                with col2:
                    st.write("Data Sample:")
                    st.json(df.iloc[0].to_dict())
        else:
            st.warning("No data available in cache")
            
        # Auto-refresh every 5 minutes
        time.sleep(300)  # 5 minutes
        st.rerun()
    else:
        st.error(f"Error loading data: {message}")
        
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# Footer
st.markdown("---")
st.markdown("ICMS Data View - Train Tracking System")
