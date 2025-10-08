"""
Notifications package for restaurant booking system.

Provides email and SMS notification services.
"""
from .email_service import send_booking_email, EmailSendResult
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
