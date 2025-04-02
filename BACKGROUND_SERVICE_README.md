# Background Notification Service

This guide explains how the background notification service works and how to manage it in different environments.

## Overview

The Train Tracking application includes a background notification service (`background_notifier.py`) that:

1. Runs continuously 24/7 to monitor train data
2. Detects new trains and sends notifications via Telegram
3. Resets known trains list daily at 01:00 hours
4. Operates independently of the web interface

## In Development Environment (Replit)

In the Replit environment, the background service can be managed through:

1. The Notification Status page in the Streamlit application
2. Manual start/stop via the provided UI elements

## In AWS Elastic Beanstalk

When deployed to AWS Elastic Beanstalk, the background service:

1. Starts automatically on deployment via the `.platform/hooks/predeploy/02_start_service.config` hook
2. Runs as a background process with output logged to `/var/log/background_notifier.log`
3. Restarts automatically when the environment is updated

## For Systemd Installations (Linux Servers)

For systemd-based servers (most modern Linux distributions), you can use the included systemd service file:

1. Copy `train_notifier.service` to `/etc/systemd/system/`:
   ```bash
   sudo cp train_notifier.service /etc/systemd/system/
   ```

2. Edit the file to update paths if necessary:
   ```bash
   sudo nano /etc/systemd/system/train_notifier.service
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable train_notifier
   sudo systemctl start train_notifier
   ```

4. Check service status:
   ```bash
   sudo systemctl status train_notifier
   ```

## Monitoring & Logs

To check logs for the background service:

- **In AWS**: `eb ssh` into the instance and check `/var/log/background_notifier.log`
- **In systemd**: Use `sudo journalctl -u train_notifier`
- **In Replit**: Look for `background_notifier.log` in your project directory

## Daily Reset Feature

The known trains list is reset daily at 01:00 hours through:

- **In AWS**: A cron job configured in `.ebextensions/03_cronjob.config`
- **In systemd**: Part of the background service functionality
- **In Replit**: Part of the background service functionality

## Troubleshooting

If the notification service isn't working:

1. Check if the process is running:
   ```bash
   ps aux | grep background_notifier.py
   ```

2. Verify log files for errors

3. Ensure the configured Telegram bot token and chat IDs are correct

4. Check network connectivity to the Telegram API

5. Verify that the required environment variables or secrets are properly set

## Manually Running the Service

To manually run the background service:

```bash
python background_notifier.py
```

For debugging or running in the foreground:

```bash
python background_notifier.py --debug
```

## Security Considerations

The background service requires access to:

1. Telegram Bot API credentials
2. Google Sheets API credentials (for data fetching)

Ensure these credentials are securely stored and properly available to the service process.