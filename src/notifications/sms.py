"""
Twilio SMS integration for restaurant booking confirmations.

Handles SMS confirmations with phone number validation, E.164 formatting,
and robust error handling with retry logic.
"""
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from twilio.rest import Client
from twilio.base.exceptions import TwilioException, TwilioRestException

from config import get_settings


class PhoneValidationError(Exception):
    """Exception raised when phone number validation fails."""
    pass


def format_phone_number(phone: str) -> str:
    """
    Normalize phone number to E.164 format (+15550123456).
    
    Accepts various formats:
    - (555) 012-3456
    - 555-012-3456
    - 5550123456
    - +15550123456
    
    Args:
        phone: Phone number in various formats
        
    Returns:
        Phone number in E.164 format (+1XXXXXXXXXX)
        
    Raises:
        PhoneValidationError: If phone number cannot be formatted
        
    Examples:
        >>> format_phone_number("(555) 012-3456")
        '+15550123456'
        >>> format_phone_number("555-012-3456")
        '+15550123456'
        >>> format_phone_number("5550123456")
        '+15550123456'
    """
    # Remove all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Remove + if present for processing
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    # Remove any remaining non-digits
    digits_only = re.sub(r'\D', '', cleaned)
    
    # Handle US phone numbers
    if len(digits_only) == 10:
        # 10 digits - add US country code
        return f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # 11 digits starting with 1 - already has country code
        return f"+{digits_only}"
    else:
        raise PhoneValidationError(
            f"Invalid phone number format: {phone}. "
            "Expected 10 digits for US number (or 11 with country code 1)"
        )


def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format before sending SMS.
    
    Checks:
    - Can be normalized to E.164 format
    - Contains valid number of digits for US (10 digits)
    - No invalid characters
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
        
    Examples:
        >>> validate_phone_number("(555) 012-3456")
        (True, None)
        >>> validate_phone_number("123")
        (False, 'Invalid phone number format: ...')
    """
    try:
        formatted = format_phone_number(phone)
        
        # Verify it's a valid E.164 format
        if not re.match(r'^\+1\d{10}$', formatted):
            return False, f"Phone number {phone} does not match US format"
        
        return True, None
        
    except PhoneValidationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error validating phone number: {str(e)}"


def format_confirmation_message(booking_details: Dict) -> str:
    """
    Build formatted SMS confirmation message from booking details.
    
    Args:
        booking_details: Dictionary containing booking information:
            - restaurant_name: str (optional, uses config if not provided)
            - date: datetime.date or str
            - time_slot: datetime.time or str
            - party_size: int
            - booking_id: int or str (optional)
            - customer_name: str (optional)
            
    Returns:
        Formatted SMS message string
        
    Example:
        >>> details = {
        ...     'restaurant_name': 'The Grand Bistro',
        ...     'date': datetime.date(2024, 10, 10),
        ...     'time_slot': datetime.time(19, 0),
        ...     'party_size': 4,
        ...     'booking_id': 'BK20241010-1900-001'
        ... }
        >>> format_confirmation_message(details)
        'Your table at The Grand Bistro is confirmed!\\n\\nDate: ...'
    """
    settings = get_settings()
    
    # Get restaurant name from details or config
    restaurant_name = booking_details.get('restaurant_name', settings.restaurant_name)
    
    # Format date
    date_obj = booking_details['date']
    if isinstance(date_obj, str):
        # Parse string date if needed
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
    
    # Format as "Friday, October 10th"
    day_name = date_obj.strftime('%A')
    month_name = date_obj.strftime('%B')
    day = date_obj.day
    
    # Add ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    
    formatted_date = f"{day_name}, {month_name} {day}{suffix}"
    
    # Format time
    time_obj = booking_details['time_slot']
    if isinstance(time_obj, str):
        # Parse string time if needed
        time_obj = datetime.strptime(time_obj, '%H:%M:%S').time()
    
    # Format as "7:00 PM"
    hour = time_obj.hour
    minute = time_obj.minute
    am_pm = 'AM' if hour < 12 else 'PM'
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    
    formatted_time = f"{display_hour}:{minute:02d} {am_pm}"
    
    # Get party size
    party_size = booking_details['party_size']
    guest_text = "guest" if party_size == 1 else "guests"
    
    # Get booking ID if available
    booking_id = booking_details.get('id') or booking_details.get('booking_id')
    
    # Build message
    message = f"""Your table at {restaurant_name} is confirmed!

Date: {formatted_date}
Time: {formatted_time}
Party Size: {party_size} {guest_text}"""
    
    # Add booking ID if available
    if booking_id:
        # Format booking ID if it's a number
        if isinstance(booking_id, int):
            # Create a booking ID in the format BK20241010-1900-001
            booking_id_str = f"BK{date_obj.strftime('%Y%m%d')}-{time_obj.strftime('%H%M')}-{booking_id:03d}"
        else:
            booking_id_str = str(booking_id)
        
        message += f"\nBooking ID: #{booking_id_str}"
    
    message += "\n\nWe look forward to seeing you!"
    
    return message


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TwilioRestException, ConnectionError)),
    reraise=True,
)
def _send_sms_with_retry(
    client: Client,
    to: str,
    from_: str,
    body: str,
) -> str:
    """
    Internal function to send SMS with Twilio API (with retry decorator).
    
    Args:
        client: Twilio client instance
        to: Recipient phone number (E.164 format)
        from_: Sender phone number (E.164 format)
        body: Message body
        
    Returns:
        Message SID from Twilio
        
    Raises:
        TwilioRestException: If Twilio API call fails after retries
        ConnectionError: If network connectivity issues
    """
    try:
        message = client.messages.create(
            to=to,
            from_=from_,
            body=body
        )
        return message.sid
        
    except TwilioRestException as e:
        # Log the specific Twilio error for debugging
        logger.error(f"Twilio API error (attempt will retry): {e.code} - {e.msg}")
        raise
    except Exception as e:
        # Convert other exceptions to appropriate types for retry
        if "connection" in str(e).lower() or "timeout" in str(e).lower():
            logger.error(f"Network connectivity error (attempt will retry): {str(e)}")
            raise ConnectionError(f"Network error: {str(e)}")
        raise


def send_booking_sms(phone_number: str, booking_details: Dict) -> Dict[str, any]:
    """
    Send SMS confirmation for a booking.
    
    This is the main entry point for sending booking confirmation SMS.
    Handles phone validation, message formatting, Twilio API call,
    retry logic, and comprehensive error handling.
    
    Args:
        phone_number: Customer phone number (various formats accepted)
        booking_details: Dictionary with booking information:
            - date: datetime.date or str (required)
            - time_slot: datetime.time or str (required)
            - party_size: int (required)
            - restaurant_name: str (optional)
            - id or booking_id: int or str (optional)
            
    Returns:
        Dictionary with status information:
        {
            "success": bool,
            "message_sid": str or None (Twilio message SID if successful),
            "error": str or None (error message if failed),
            "formatted_phone": str or None (E.164 formatted phone if successful)
        }
        
    Example:
        >>> details = {
        ...     'date': datetime.date(2024, 10, 10),
        ...     'time_slot': datetime.time(19, 0),
        ...     'party_size': 4,
        ...     'id': 123
        ... }
        >>> result = send_booking_sms("(555) 012-3456", details)
        >>> print(result['success'])
        True
    """
    settings = get_settings()
    
    # Validate environment variables
    if not settings.twilio_account_sid:
        error_msg = "TWILIO_ACCOUNT_SID not configured in environment variables"
        logger.error(f"SMS send failed: {error_msg}")
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
            "formatted_phone": None,
        }
    
    if not settings.twilio_auth_token:
        error_msg = "TWILIO_AUTH_TOKEN not configured in environment variables"
        logger.error(f"SMS send failed: {error_msg}")
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
            "formatted_phone": None,
        }
    
    if not settings.twilio_phone_number:
        error_msg = "TWILIO_PHONE_NUMBER not configured in environment variables"
        logger.error(f"SMS send failed: {error_msg}")
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
            "formatted_phone": None,
        }
    
    # Validate and format phone number
    is_valid, validation_error = validate_phone_number(phone_number)
    if not is_valid:
        logger.error(
            f"SMS send failed - invalid phone number: {phone_number} - {validation_error}"
        )
        return {
            "success": False,
            "message_sid": None,
            "error": f"Invalid phone number: {validation_error}",
            "formatted_phone": None,
        }
    
    try:
        formatted_phone = format_phone_number(phone_number)
    except PhoneValidationError as e:
        logger.error(f"SMS send failed - phone formatting error: {str(e)}")
        return {
            "success": False,
            "message_sid": None,
            "error": str(e),
            "formatted_phone": None,
        }
    
    # Format confirmation message
    try:
        message_body = format_confirmation_message(booking_details)
    except Exception as e:
        error_msg = f"Failed to format confirmation message: {str(e)}"
        logger.error(f"SMS send failed: {error_msg}")
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
            "formatted_phone": formatted_phone,
        }
    
    # Initialize Twilio client
    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    except Exception as e:
        error_msg = f"Failed to initialize Twilio client: {str(e)}"
        logger.error(f"SMS send failed: {error_msg}")
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
            "formatted_phone": formatted_phone,
        }
    
    # Send SMS with retry logic
    booking_id = booking_details.get('id') or booking_details.get('booking_id', 'N/A')
    
    try:
        logger.info(
            f"Attempting to send booking confirmation SMS - "
            f"Booking ID: {booking_id}, Phone: {formatted_phone}"
        )
        
        message_sid = _send_sms_with_retry(
            client=client,
            to=formatted_phone,
            from_=settings.twilio_phone_number,
            body=message_body,
        )
        
        logger.info(
            f"SMS sent successfully - "
            f"Booking ID: {booking_id}, Phone: {formatted_phone}, "
            f"Message SID: {message_sid}"
        )
        
        return {
            "success": True,
            "message_sid": message_sid,
            "error": None,
            "formatted_phone": formatted_phone,
        }
        
    except TwilioRestException as e:
        error_msg = f"Twilio API error: {e.code} - {e.msg}"
        logger.error(
            f"SMS send failed after retries - "
            f"Booking ID: {booking_id}, Phone: {formatted_phone}, "
            f"Error: {error_msg}"
        )
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
            "formatted_phone": formatted_phone,
        }
        
    except ConnectionError as e:
        error_msg = f"Network connectivity error: {str(e)}"
        logger.error(
            f"SMS send failed after retries - "
            f"Booking ID: {booking_id}, Phone: {formatted_phone}, "
            f"Error: {error_msg}"
        )
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
            "formatted_phone": formatted_phone,
        }
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(
            f"SMS send failed - "
            f"Booking ID: {booking_id}, Phone: {formatted_phone}, "
            f"Error: {error_msg}"
        )
        return {
            "success": False,
            "message_sid": None,
            "error": error_msg,
            "formatted_phone": formatted_phone,
        }
