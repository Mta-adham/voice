"""
Notifications module for restaurant booking system.

Handles SMS and email confirmations for bookings.
"""
from notifications.sms import send_booking_sms, format_phone_number, validate_phone_number


"""

from .sms import send_sms_confirmation, SMSService, SMSError
from .email import send_email_confirmation, EmailService, EmailError

__all__ = [
    "send_sms_confirmation",
    "SMSService",
    "SMSError",
    "send_email_confirmation",
    "EmailService",
    "EmailError",
]
