"""
Notification system for train tracking application.

This package provides browser notification capabilities for the train tracking system.
Browser notifications - for real-time in-browser alerts
"""

from notifications.push_notification import PushNotifier

__all__ = ['PushNotifier']