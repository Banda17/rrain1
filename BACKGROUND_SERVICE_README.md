# 24/7 Background Notification Service

This guide explains how to set up a background service for continuous 24/7 Telegram notifications from your train tracking system, even when the web application is not open.

## What You'll Need

- A server or computer that can run continuously (VPS, Raspberry Pi, desktop PC, etc.)
- Python 3.7+ installed
- Required Python packages: `requests`, `pandas`, `python-telegram-bot`
- Your Telegram bot token and chat IDs

## Quick Start

1. Install the required packages if not already installed:
   ```bash
   pip install requests pandas python-telegram-bot
   ```

2. Test if the background service works with your Telegram configuration:
   ```bash
   python test_background_notifier.py
   ```

3. If the test is successful, you can now run the background service:
   ```bash
   python background_notifier.py
   ```

4. You should receive a startup notification on your Telegram, and the service will start checking for new trains every 5 minutes.

## Setting Up as a System Service (For Linux Users)

1. Edit the `train_notifier.service` file and replace:
   - `YOUR_USERNAME` with your actual username
   - `/path/to/your/application` with the actual path
   - Telegram environment variables with your actual values

2. Copy the service file to the systemd directory:
   ```bash
   sudo cp train_notifier.service /etc/systemd/system/
   ```

3. Reload systemd:
   ```bash
   sudo systemctl daemon-reload
   ```

4. Enable and start the service:
   ```bash
   sudo systemctl enable train_notifier.service
   sudo systemctl start train_notifier.service
   ```

5. Check the status:
   ```bash
   sudo systemctl status train_notifier.service
   ```

## Running on Windows

1. Create a batch file `start_notifier.bat` with the following content:
   ```batch
   @echo off
   echo Starting Train Notification Service...
   python background_notifier.py
   pause
   ```

2. To run at startup:
   - Press `Win + R` and type `shell:startup`
   - Create a shortcut to the batch file in this folder

## Checking Logs

The background service creates logs in the `temp/background_notifier.log` file. You can view them with:

```bash
tail -f temp/background_notifier.log
```

## Troubleshooting

1. **Telegram Bot Issues**
   - Make sure your bot token is correct
   - Check that you've started a conversation with your bot
   - Verify that you've added your bot to any channels with admin rights

2. **Service Not Starting**
   - Check logs with `sudo journalctl -u train_notifier.service`
   - Verify that Python and all dependencies are installed
   - Make sure file paths are correct in the service file

3. **No Notifications**
   - Check the log file for any errors
   - Verify that your Telegram chat IDs are correct
   - Make sure the Google Sheets URL is accessible

## How It Works

The background service:
1. Regularly fetches train data from the Google Sheets URL
2. Compares the current trains with the list of previously known trains
3. Sends notifications for any new trains it discovers
4. Updates the known trains list for future checks
5. **Automatically resets the known trains list at 01:00 every day** so you get fresh notifications for all trains each day
6. Sends a notification when the daily reset happens

This happens completely independently of the Streamlit web application, ensuring you get notifications 24/7.

## Manual Reset

If you want to manually reset the known trains list (to receive notifications for all trains again), you can run:

```bash
python reset_trains.py
```

This will clear the list of known trains, and all trains will trigger notifications on the next check cycle.