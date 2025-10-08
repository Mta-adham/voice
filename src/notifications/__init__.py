"""
Notifications module for restaurant booking system.

Handles SMS and email confirmations for bookings.
"""
from notifications.sms import send_booking_sms, format_phone_number, validate_phone_number

__all__ = [
    "send_booking_sms",
    "format_phone_number",
    "validate_phone_number",
]
