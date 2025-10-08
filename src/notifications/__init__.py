"""
Notifications package for restaurant booking system.

Provides email and SMS notification services.
"""
from .email_service import send_booking_email, EmailSendResult

__all__ = ['send_booking_email', 'EmailSendResult']
