"""
Notification Status Page

This page displays the status of the background notification service
and allows users to check if it's running properly.
"""

import os
import streamlit as st
import subprocess
import psutil
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="Notification Status", page_icon="🔔")

st.title("🔔 Background Notification Status")

def is_process_running(process_name="background_notifier.py"):
    """Check if the background notifier process is running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and any(process_name in cmd for cmd in proc.info['cmdline']):
                return True, proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False, None

def get_log_file_info():
    """Get information about the log file"""
    log_file = "temp/background_notifier.log"
    
    if not os.path.exists(log_file):
        return None, None, None
    
    file_size = os.path.getsize(log_file) / 1024  # in KB
    last_modified = datetime.fromtimestamp(os.path.getmtime(log_file))
    
    # Read the last 5 lines of the log file
    last_lines = []
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            last_lines = lines[-5:] if lines else []
    except:
        last_lines = ["Error reading log file"]
    
    return file_size, last_modified, last_lines

def check_known_trains_file():
    """Check the known trains file"""
    known_trains_file = "temp/known_trains.json"
    
    if not os.path.exists(known_trains_file):
        return None, None, 0
    
    file_size = os.path.getsize(known_trains_file) / 1024  # in KB
    last_modified = datetime.fromtimestamp(os.path.getmtime(known_trains_file))
    
    # Count the number of trains in the file
    try:
        import json
        with open(known_trains_file, "r") as f:
            known_trains = json.load(f)
            train_count = len(known_trains)
    except:
        train_count = -1  # Error reading file
    
    return file_size, last_modified, train_count

# Create status section
st.subheader("Service Status")

# Check if the background service is running
running, pid = is_process_running()

# Status indicator columns
col1, col2 = st.columns([1, 3])

if running:
    with col1:
        st.markdown(
            """
            <div style="background-color: #01B636; padding: 15px; border-radius: 50%; width: 30px; height: 30px; text-align: center;">
                <span style="color: white; font-size: 16px;">✓</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(f"**Service is RUNNING**<br>Process ID: {pid}", unsafe_allow_html=True)
        st.markdown("The background notification service is active and monitoring for new trains.")
else:
    with col1:
        st.markdown(
            """
            <div style="background-color: #FF4B4B; padding: 15px; border-radius: 50%; width: 30px; height: 30px; text-align: center;">
                <span style="color: white; font-size: 16px;">✕</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
    with col2:
        st.markdown("**Service is NOT RUNNING**", unsafe_allow_html=True)
        st.markdown("The background notification service is currently inactive.")
        
        # Add a button to start the service
        if st.button("Start Background Service"):
            try:
                # Try to start the service in the background
                subprocess.Popen(
                    ["python", "background_notifier.py"],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    close_fds=True
                )
                st.success("Service started! Refreshing page in 3 seconds...")
                time.sleep(3)
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to start service: {str(e)}")

# Display log information
st.subheader("Log Information")

file_size, last_modified, last_lines = get_log_file_info()

if file_size is not None:
    st.markdown(f"**Log File Size:** {file_size:.2f} KB")
    st.markdown(f"**Last Updated:** {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Calculate time since last update
    time_diff = datetime.now() - last_modified
    if time_diff < timedelta(minutes=10):
        status = "✅ Recent activity"
    elif time_diff < timedelta(hours=1):
        status = "⚠️ No recent activity"
    else:
        status = "❌ Service may be stalled"
    
    st.markdown(f"**Status:** {status} (Last update was {time_diff.seconds//60} minutes ago)")
    
    # Show the last few log entries
    st.markdown("**Recent Log Entries:**")
    log_text = "".join(last_lines)
    st.text_area("Log", log_text, height=150)
else:
    st.warning("No log file found. The service may not have been started yet.")

# Display known trains information
st.subheader("Known Trains Information")

file_size, last_modified, train_count = check_known_trains_file()

if file_size is not None:
    st.markdown(f"**File Size:** {file_size:.2f} KB")
    st.markdown(f"**Last Updated:** {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown(f"**Known Trains Count:** {train_count}")
    
    # Add a button to reset known trains
    if st.button("Reset Known Trains"):
        try:
            subprocess.run(["python", "reset_trains.py"], check=True)
            st.success("Known trains reset successfully! You'll get notifications for all trains in the next check cycle.")
            time.sleep(2)
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Failed to reset known trains: {str(e)}")
else:
    st.warning("No known trains file found. The service may not have processed any trains yet.")

# Add note about scheduled reset
st.info("ℹ️ The known trains list is automatically reset daily at 01:00 hours.")

# Add note about deploying to a server
st.subheader("Running as a System Service")
st.markdown("""
To run this service continuously on a server:
1. Set up the systemd service as described in `BACKGROUND_SERVICE_README.md`
2. Install required Python packages: `requests`, `pandas`, `python-telegram-bot`, `psutil`
3. Configure your Telegram credentials in the service file

The service will then run 24/7 and send notifications even when this web interface is closed.
""")