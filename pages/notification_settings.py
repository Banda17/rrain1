import streamlit as st
import os
from notifications import PushNotifier, TelegramNotifier

# Set page config
st.set_page_config(
    page_title="Notification Settings | Train Monitor",
    page_icon="🚆",
    layout="wide"
)

# Initialize session state
if 'telegram_notifier' not in st.session_state:
    st.session_state.telegram_notifier = TelegramNotifier()

# Load bot token, chat IDs, and channel ID from environment variables if available
if 'TELEGRAM_BOT_TOKEN' in os.environ and not st.session_state.telegram_bot_token:
    st.session_state.telegram_bot_token = os.environ['TELEGRAM_BOT_TOKEN']
    
if 'TELEGRAM_CHAT_IDS' in os.environ and not st.session_state.telegram_chat_ids:
    chat_ids_str = os.environ['TELEGRAM_CHAT_IDS']
    st.session_state.telegram_chat_ids = [id.strip() for id in chat_ids_str.split(',')] if chat_ids_str else []

if 'TELEGRAM_CHANNEL_ID' in os.environ and not st.session_state.telegram_channel_id:
    st.session_state.telegram_channel_id = os.environ['TELEGRAM_CHANNEL_ID']

# Page header
st.title("🔔 Notification Settings")
st.markdown("""
Configure how you want to receive notifications about train updates and alerts.
""")

# Create tabs for different notification types
tabs = st.tabs(["Browser Notifications", "Telegram Notifications"])

with tabs[0]:
    # Browser notifications
    st.header("Browser Notifications")
    st.markdown("""
    Browser notifications appear on your desktop when new trains are detected or when
    train status changes. These notifications work only when the browser is open.
    """)
    
    # Initialize push notifier
    push_notifier = PushNotifier()
    
    # Render browser notification UI
    push_notifier.render_notification_ui()

with tabs[1]:
    # Telegram notifications
    telegram_notifier = st.session_state.telegram_notifier
    
    st.markdown("""
    Telegram notifications let you receive train updates on your phone or desktop even when 
    you're not using the browser. You'll need to create a Telegram bot and add its token below.
    
    To create a Telegram bot:
    1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
    2. Send the command `/newbot` and follow the instructions
    3. Copy the bot token provided and paste it below
    4. Start a chat with your new bot
    5. Get your chat ID by using [@userinfobot](https://t.me/userinfobot)
    
    For channel notifications:
    1. Create a channel in Telegram (public or private)
    2. Add your bot as an administrator to the channel with "Post Messages" permission
    3. For public channels, use the channel username in the format: @channelname
    4. For private channels, get the channel ID by forwarding a message from the channel to [@getidsbot](https://t.me/getidsbot)
       and use the ID in the format: -100xxxxxxxxxx
    """)
    
    # Render Telegram settings UI
    telegram_notifier.render_settings_ui()
    
    # Save button for environment variables
    st.subheader("Save as Environment Variables")
    if st.button("Save Telegram Settings as Environment Variables"):
        # This would typically save to .env or similar
        # Here we're just displaying what would be saved
        if st.session_state.telegram_bot_token and (st.session_state.telegram_chat_ids or st.session_state.telegram_channel_id):
            env_vars = f"""
            TELEGRAM_BOT_TOKEN={st.session_state.telegram_bot_token}
            """
            
            # Add chat IDs if configured
            if st.session_state.telegram_chat_ids:
                env_vars += f"""
            TELEGRAM_CHAT_IDS={','.join(st.session_state.telegram_chat_ids)}
            """
                
            # Add channel ID if configured
            if st.session_state.telegram_channel_id:
                env_vars += f"""
            TELEGRAM_CHANNEL_ID={st.session_state.telegram_channel_id}
            """
                
            st.code(env_vars)
            st.success("These values should be added to your environment variables or .streamlit/secrets.toml file.")
        else:
            st.error("Please configure both Bot Token and at least one Chat ID or Channel ID before saving.")
            
# Footer
st.markdown("---")
st.markdown("ℹ️ Changes to these settings will be applied immediately but may not persist after restarting the application unless saved as environment variables.")