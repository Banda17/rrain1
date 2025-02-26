import streamlit as st
import time
from datetime import datetime, timedelta

def create_refresh_animation(placeholder):
    """
    Create an animated refresh indicator in the given placeholder
    """
    placeholder.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 15px;">
        <div style="border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 25px; height: 25px; margin-right: 10px; animation: spin 2s linear infinite;"></div>
        <span style="color: #3498db; font-weight: bold;">Refreshing data...</span>
    </div>
    <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """, unsafe_allow_html=True)

def create_pulsing_refresh_animation(placeholder, message="Refreshing data..."):
    """
    Create a pulsing animation with customizable message
    """
    placeholder.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 15px; animation: pulse 1.5s infinite;">
        <div style="border: 4px solid rgba(52, 152, 219, 0.5); border-top: 4px solid #3498db; border-radius: 50%; width: 30px; height: 30px; margin-right: 15px; animation: spin 2s linear infinite;"></div>
        <div>
            <span style="color: #3498db; font-weight: bold; font-size: 1.1rem;">{message}</span>
            <div style="height: 2px; background: linear-gradient(to right, #3498db, rgba(52, 152, 219, 0.2)); animation: progress 2s infinite;"></div>
        </div>
    </div>
    <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        @keyframes pulse {{
            0% {{ opacity: 0.8; }}
            50% {{ opacity: 1; }}
            100% {{ opacity: 0.8; }}
        }}
        @keyframes progress {{
            0% {{ width: 0%; }}
            50% {{ width: 100%; }}
            100% {{ width: 0%; }}
        }}
    </style>
    """, unsafe_allow_html=True)

def show_countdown_progress(seconds, step=0.1):
    """
    Show a countdown progress bar that updates more frequently

    Args:
        seconds: Total seconds for countdown
        step: Update interval in seconds

    Returns:
        None
    """
    # Create a progress bar
    progress_bar = st.progress(0)

    # Create a text display for the countdown
    countdown_text = st.empty()

    steps = int(seconds / step)
    for i in range(steps):
        # Update progress bar
        progress = i / steps
        progress_bar.progress(progress)

        # Calculate remaining time
        remaining_seconds = seconds - (i * step)
        minutes, secs = divmod(remaining_seconds, 60)

        # Update countdown text
        countdown_text.markdown(f"""
        <div style="text-align: center; font-size: 0.9rem; color: #555;">
            Next refresh in: {int(minutes):02d}:{int(secs):02d}
        </div>
        """, unsafe_allow_html=True)

        # Wait for the step duration
        time.sleep(step)

    # Complete the progress bar
    progress_bar.progress(1.0)

    # Clear the text
    countdown_text.empty()

    # Return the objects so they can be cleared if needed
    return progress_bar, countdown_text

def show_refresh_timestamp(refresh_time=None):
    """
    Show a formatted timestamp of the last refresh in IST

    Args:
        refresh_time: Datetime object of refresh time, if None use current time

    Returns:
        Streamlit container with timestamp
    """
    if refresh_time is None:
        refresh_time = datetime.now()

    # Convert to IST (UTC+5:30)
    ist_time = refresh_time + timedelta(hours=5, minutes=30)

    # Create text display
    timestamp_container = st.container()
    with timestamp_container:
        st.markdown(f"""
        <div style="text-align: right; font-size: 0.8rem; color: #666; margin-top: 10px;">
            Last refreshed: <span style="font-weight: bold;">{ist_time.strftime('%Y-%m-%d %H:%M:%S')}</span> IST
        </div>
        """, unsafe_allow_html=True)

    return timestamp_container