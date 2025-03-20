"""
Notification system for train tracking application.

This package provides notification capabilities for the train tracking system:
- Browser notifications - for real-time in-browser alerts
- Telegram notifications - for mobile/desktop notifications via Telegram bot
"""

from notifications.push_notification import PushNotifier
from notifications.telegram_notifier import TelegramNotifier

__all__ = ['PushNotifier', 'TelegramNotifier']