"""
SMS notification service using Twilio.

This module provides SMS confirmation sending functionality.
This is a stub implementation that should be replaced with actual Twilio integration.
"""
from datetime import date, time
from typing import Dict, Any
from loguru import logger


class SMSError(Exception):
    """Raised when SMS sending fails."""
    pass


class SMSService:
    """
    SMS service for sending booking confirmations via Twilio.
    
    This is a placeholder implementation. The actual implementation should use
    Twilio API for sending SMS messages.
    """
    
    def __init__(self, account_sid: str = None, auth_token: str = None, from_number: str = None):
        """
        Initialize SMS service.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number to send from
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        logger.warning(
            "Using stub SMSService. "
            "Replace with actual Twilio implementation for production use."
        )
    
    def send_booking_confirmation(
        self,
        phone_number: str,
        booking_details: Dict[str, Any]
    ) -> bool:
        """
        Send SMS confirmation for a booking.
        
        Args:
            phone_number: Recipient phone number
            booking_details: Dictionary containing booking information
            
        Returns:
            True if sent successfully
            
        Raises:
            SMSError: If sending fails
        """
        logger.info(f"[STUB] Would send SMS to {phone_number}")
        logger.info(f"[STUB] Message content: {booking_details}")
        # In actual implementation, format and send via Twilio
        return True


def send_sms_confirmation(phone_number: str, booking_details: Dict[str, Any]) -> bool:
    """
    Convenience function to send SMS confirmation.
    
    Args:
        phone_number: Recipient phone number
        booking_details: Booking information
        
    Returns:
        True if sent successfully
    """
    service = SMSService()
    return service.send_booking_confirmation(phone_number, booking_details)
