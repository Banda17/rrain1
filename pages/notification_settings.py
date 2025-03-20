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
        try:
            if st.session_state.telegram_bot_token and (st.session_state.telegram_chat_ids or st.session_state.telegram_channel_id):
                # Create the .streamlit directory if it doesn't exist
                os.makedirs('.streamlit', exist_ok=True)
                
                # Check if secrets.toml already exists and read its content
                secrets_content = ""
                if os.path.exists('.streamlit/secrets.toml'):
                    with open('.streamlit/secrets.toml', 'r') as f:
                        secrets_content = f.read()
                
                # Prepare the new content to write
                bot_token_line = f'TELEGRAM_BOT_TOKEN = "{st.session_state.telegram_bot_token}"'
                chat_ids_line = f'TELEGRAM_CHAT_IDS = "{",".join(st.session_state.telegram_chat_ids)}"'
                channel_id_line = f'TELEGRAM_CHANNEL_ID = "{st.session_state.telegram_channel_id}"'
                
                # Update the content using a simple find and replace approach
                # First, check if each value exists in the file already
                if 'TELEGRAM_BOT_TOKEN' in secrets_content:
                    # Replace the existing line
                    import re
                    secrets_content = re.sub(r'TELEGRAM_BOT_TOKEN\s*=\s*"[^"]*"', 
                                           bot_token_line, secrets_content)
                else:
                    # Add a new line
                    secrets_content += f"\n{bot_token_line}"
                
                if 'TELEGRAM_CHAT_IDS' in secrets_content:
                    import re
                    secrets_content = re.sub(r'TELEGRAM_CHAT_IDS\s*=\s*"[^"]*"', 
                                           chat_ids_line, secrets_content)
                elif st.session_state.telegram_chat_ids:
                    secrets_content += f"\n{chat_ids_line}"
                
                if 'TELEGRAM_CHANNEL_ID' in secrets_content:
                    import re
                    secrets_content = re.sub(r'TELEGRAM_CHANNEL_ID\s*=\s*"[^"]*"', 
                                           channel_id_line, secrets_content)
                elif st.session_state.telegram_channel_id:
                    secrets_content += f"\n{channel_id_line}"
                
                # Write back to the secrets.toml file
                with open('.streamlit/secrets.toml', 'w') as f:
                    f.write(secrets_content)
                
                # Display the saved values
                st.code(f"""
                {bot_token_line}
                {chat_ids_line if st.session_state.telegram_chat_ids else ""}
                {channel_id_line if st.session_state.telegram_channel_id else ""}
                """)
                
                st.success("Settings saved to .streamlit/secrets.toml. These will persist between application restarts.")
                
                # Also try to set them in the current environment
                os.environ['TELEGRAM_BOT_TOKEN'] = st.session_state.telegram_bot_token
                os.environ['TELEGRAM_CHAT_IDS'] = ','.join(st.session_state.telegram_chat_ids)
                if st.session_state.telegram_channel_id:
                    os.environ['TELEGRAM_CHANNEL_ID'] = st.session_state.telegram_channel_id
                    
                st.info("Environment variables set for the current session.")
            else:
                st.error("Please configure both Bot Token and at least one Chat ID or Channel ID before saving.")
        except Exception as e:
            st.error(f"Failed to save settings: {str(e)}")
            st.info("Alternative method: Copy the settings below to your .streamlit/secrets.toml file manually:")
            
            env_vars = f"""
            TELEGRAM_BOT_TOKEN = "{st.session_state.telegram_bot_token}"
            """
            
            # Add chat IDs if configured
            if st.session_state.telegram_chat_ids:
                env_vars += f"""
            TELEGRAM_CHAT_IDS = "{','.join(st.session_state.telegram_chat_ids)}"
            """
                
            # Add channel ID if configured
            if st.session_state.telegram_channel_id:
                env_vars += f"""
            TELEGRAM_CHANNEL_ID = "{st.session_state.telegram_channel_id}"
            """
                
            st.code(env_vars)
            
# Footer
st.markdown("---")
st.markdown("ℹ️ Changes to these settings will be applied immediately but may not persist after restarting the application unless saved as environment variables.")