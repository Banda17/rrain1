#!/usr/bin/env python3
"""
Test script for the background notification service.
This will send a test message to verify the configuration.
"""

import os
import asyncio
import logging
from background_notifier import TelegramNotifier, load_secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_notifier")

async def test_notification():
    # Load secrets from .streamlit/secrets.toml if available
    load_secrets()
    
    # Initialize the notifier
    notifier = TelegramNotifier()
    
    if not notifier.is_configured:
        logger.error("Telegram notifier is not properly configured!")
        logger.error("Please set TELEGRAM_BOT_TOKEN and either TELEGRAM_CHAT_IDS or TELEGRAM_CHANNEL_ID.")
        return False
    
    # Send test message
    logger.info("Sending test direct message...")
    direct_success = notifier.send_message("🔔 <b>Test Notification</b>\n\nThis is a test from the background service.\nIf you're seeing this, the direct messaging is working correctly!")
    
    if direct_success:
        logger.info("✅ Direct message sent successfully!")
    else:
        logger.error("❌ Failed to send direct message!")
    
    # Test channel message if configured
    if notifier.channel_id:
        logger.info("Sending test channel message...")
        channel_message = "🚂 #TEST123 | TEST-SERVICE | T/O-H/O: BZA-GDR: 0 mins late | Delay: 0 mins | Started: Today"
        channel_success = notifier.send_to_channel(channel_message)
        
        if channel_success:
            logger.info("✅ Channel message sent successfully!")
        else:
            logger.error("❌ Failed to send channel message!")
    else:
        logger.warning("⚠️ No channel ID configured, skipping channel test")
    
    return direct_success

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    success = loop.run_until_complete(test_notification())
    
    if success:
        print("\n✅ Test completed successfully! Your configuration is working.")
    else:
        print("\n❌ Test failed. Please check the error messages above.")