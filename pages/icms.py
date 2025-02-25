import streamlit as st
import pandas as pd
from data_handler import DataHandler
import time
import numpy as np

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

                # Safe conversion of NaN values to None
                def safe_convert(value):
                    if pd.isna(value) or pd.isnull(value):
                        return None
                    return value

                # Apply safe conversion to all elements
                df = df.applymap(safe_convert)

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
                        non_null_count = df[column].notna().sum()
                        unique_count = len([x for x in df[column].unique() if x is not None])
                        st.write(f"- {column}: {unique_count} unique values, {non_null_count} non-null values")

                with col2:
                    st.write("Data Sample:")
                    if not df.empty:
                        # Convert the first row to a dictionary safely
                        sample = df.iloc[0]
                        sample_dict = {k: None if pd.isna(v) else v for k, v in sample.items()}
                        # Use write instead of json for safer display
                        st.write("Sample Record:", sample_dict)
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