import streamlit as st
import pandas as pd
from data_handler import DataHandler
import time
import re

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
            # Convert to DataFrame
            df = pd.DataFrame(cached_data)

            if not df.empty:
                # Skip first two rows (0 and 1) and reset index
                df = df.iloc[2:].reset_index(drop=True)

                # Safe conversion of NaN values to None
                def safe_convert(value):
                    if pd.isna(value) or pd.isnull(value):
                        return None
                    return str(value) if value is not None else None

                # Apply safe conversion to all elements
                df = df.applymap(safe_convert)

                # Drop unwanted columns
                columns_to_drop = ['Sr.', 'Exit Time for NLT Status']
                df = df.drop(columns=columns_to_drop, errors='ignore')

                # Function to check if a value is positive or contains (+)
                def is_positive_or_plus(value):
                    if value is None:
                        return False
                    if isinstance(value, str):
                        # Check for numbers in brackets with +
                        bracket_match = re.search(r'\(.*?\+.*?\)', value)
                        if bracket_match:
                            return True
                        # Try to convert to number if possible
                        try:
                            num = float(value.replace('(', '').replace(')', '').strip())
                            return num > 0
                        except:
                            return False
                    return False

                # Filter rows where Delay column has positive values or (+)
                if 'Delay' in df.columns:
                    filtered_df = df[df['Delay'].apply(is_positive_or_plus)]
                    st.write(f"Showing {len(filtered_df)} entries with positive delays")
                else:
                    filtered_df = df
                    st.warning("Delay column not found in data")

                # Show the filtered data
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    height=600,
                    column_config={
                        "Train No.": st.column_config.TextColumn("Train No.", help="Train Number"),
                        "FROM-TO": st.column_config.TextColumn("FROM-TO", help="Source to Destination"),
                        "Delay": st.column_config.TextColumn("Delay", help="Delay in Minutes")
                    }
                )
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