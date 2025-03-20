import streamlit as st
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_known_trains():
    """Reset the known trains list to trigger new notifications"""
    try:
        # Path to the known trains file
        known_trains_file = os.path.join('temp', 'known_trains.json')
        
        # Reset to empty list
        with open(known_trains_file, 'w') as f:
            json.dump([], f)
            
        logger.info("Successfully reset known trains list")
        return True
    except Exception as e:
        logger.error(f"Error resetting known trains: {str(e)}")
        return False

st.title("Reset Train Notifications")
st.write("Use this tool to reset the known trains list and trigger new notifications for testing purposes.")

# Load notification CSS styles
try:
    with open("notification_styles.css", "r") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    
    # Show example of notification format
    st.subheader("Notification Format Example")
    st.markdown("""
    <div class="notification-message">
        <span class="train-emoji">🚆</span> <span class="train-number">#12345</span> | GHY-SMVB | Delay: 25 mins late | DELAY(MINS.): 25 | Started: 20 Mar
    </div>
    """, unsafe_allow_html=True)
except Exception as e:
    logger.error(f"Error loading notification styles: {str(e)}")

if st.button("Reset Known Trains"):
    success = reset_known_trains()
    if success:
        st.success("Successfully reset known trains list. Return to the Monitor page to see notifications for all trains.")
    else:
        st.error("Failed to reset known trains list. Check logs for details.")
        
    # Display additional instructions
    st.info("After resetting, go to the Monitor page to see new train notifications.")