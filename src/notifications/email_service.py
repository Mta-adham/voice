"""
Email notification service using SendGrid for restaurant booking system.

This module provides functionality to send booking confirmation emails with:
- Email validation and sanitization
- Professional HTML email templates
- SendGrid API integration with error handling
- Retry logic for transient failures
- Comprehensive logging
"""
import html
import re
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from email_validator import validate_email, EmailNotValidError
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from config import get_settings


@dataclass
class EmailSendResult:
    """Result of email send operation."""
    success: bool
    message: str
    error: Optional[str] = None


class EmailServiceError(Exception):
    """Base exception for email service errors."""
    pass


class EmailValidationError(EmailServiceError):
    """Exception raised when email validation fails."""
    pass


class EmailSendError(EmailServiceError):
    """Exception raised when email sending fails."""
    pass


def _validate_email_address(email: str) -> Tuple[bool, str]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, normalized_email or error_message)
    """
    try:
        # Validate and normalize email
        validated = validate_email(email, check_deliverability=False)
        normalized_email = validated.normalized
        return True, normalized_email
    except EmailNotValidError as e:
        return False, str(e)


def _sanitize_booking_details(booking_details: dict) -> dict:
    """
    Sanitize booking details to prevent injection attacks.
    
    Escapes HTML special characters in all string values.
    
    Args:
        booking_details: Dictionary containing booking information
        
    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    for key, value in booking_details.items():
        if isinstance(value, str):
            # Escape HTML special characters
            sanitized[key] = html.escape(value)
        else:
            sanitized[key] = value
    return sanitized


def _generate_confirmation_number(booking_id: int) -> str:
    """
    Generate a unique confirmation number from booking ID.
    
    Args:
        booking_id: Database booking ID
        
    Returns:
        Formatted confirmation number (e.g., BK-00123)
    """
    return f"BK-{booking_id:05d}"


def _create_email_html(booking_details: dict, restaurant_info: dict) -> str:
    """
    Create HTML email template with booking confirmation details.
    
    Args:
        booking_details: Sanitized booking information
        restaurant_info: Restaurant configuration information
        
    Returns:
        HTML email content
    """
    # Extract booking details (already sanitized)
    confirmation_number = booking_details.get('confirmation_number', 'N/A')
    customer_name = booking_details.get('customer_name', 'Guest')
    date = booking_details.get('date', 'N/A')
    time = booking_details.get('time', 'N/A')
    party_size = booking_details.get('party_size', 'N/A')
    special_requests = booking_details.get('special_requests', '')
    
    # Extract restaurant information
    restaurant_name = restaurant_info.get('name', 'Restaurant')
    restaurant_phone = restaurant_info.get('phone', '')
    restaurant_address = restaurant_info.get('address', '')
    directions_info = restaurant_info.get('directions', '')
    
    # Format date and time for display
    try:
        if isinstance(date, str):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%A, %B %d, %Y')
        else:
            formatted_date = date.strftime('%A, %B %d, %Y')
    except:
        formatted_date = str(date)
    
    try:
        if isinstance(time, str):
            time_obj = datetime.strptime(time, '%H:%M:%S')
            formatted_time = time_obj.strftime('%I:%M %p')
        else:
            formatted_time = time.strftime('%I:%M %p')
    except:
        formatted_time = str(time)
    
    # Build HTML email
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Booking Confirmation</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2c3e50;
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
            }}
            .confirmation-box {{
                background-color: #e8f5e9;
                border-left: 4px solid #4caf50;
                padding: 15px;
                margin: 20px 0;
            }}
            .confirmation-number {{
                font-size: 24px;
                font-weight: bold;
                color: #2e7d32;
                margin: 0;
            }}
            .details-table {{
                width: 100%;
                margin: 20px 0;
                border-collapse: collapse;
            }}
            .details-table td {{
                padding: 12px;
                border-bottom: 1px solid #ddd;
            }}
            .details-table td:first-child {{
                font-weight: bold;
                width: 40%;
                color: #555;
            }}
            .info-section {{
                background-color: #fff;
                padding: 20px;
                margin: 20px 0;
                border-radius: 5px;
                border: 1px solid #ddd;
            }}
            .info-section h3 {{
                margin-top: 0;
                color: #2c3e50;
            }}
            .policy {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
            }}
            .footer {{
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 0 0 5px 5px;
                font-size: 12px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #4caf50;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{restaurant_name}</h1>
            <p style="margin: 5px 0 0 0; font-size: 16px;">Reservation Confirmed</p>
        </div>
        
        <div class="content">
            <div class="confirmation-box">
                <p style="margin: 0 0 5px 0; font-size: 14px;">Confirmation Number:</p>
                <p class="confirmation-number">{confirmation_number}</p>
            </div>
            
            <p>Dear {customer_name},</p>
            
            <p>Thank you for choosing {restaurant_name}! We're delighted to confirm your reservation.</p>
            
            <table class="details-table">
                <tr>
                    <td>Date:</td>
                    <td>{formatted_date}</td>
                </tr>
                <tr>
                    <td>Time:</td>
                    <td>{formatted_time}</td>
                </tr>
                <tr>
                    <td>Party Size:</td>
                    <td>{party_size} {"guest" if str(party_size) == "1" else "guests"}</td>
                </tr>
                <tr>
                    <td>Customer Name:</td>
                    <td>{customer_name}</td>
                </tr>
            </table>
            
            {f'<div class="info-section"><h3>Special Requests</h3><p>{special_requests}</p></div>' if special_requests else ''}
            
            <div class="info-section">
                <h3>Restaurant Information</h3>
                <p><strong>Address:</strong><br>{restaurant_address}</p>
                <p><strong>Phone:</strong> {restaurant_phone}</p>
            </div>
            
            <div class="info-section">
                <h3>Directions & Parking</h3>
                <p>{directions_info}</p>
            </div>
            
            <div class="policy">
                <h3 style="margin-top: 0; color: #856404;">Cancellation Policy</h3>
                <p style="margin-bottom: 0;">As per our booking policy, we do not accept cancellations. Please ensure your party can attend at the scheduled time. If you have any questions or need to make changes, please contact us as soon as possible.</p>
            </div>
            
            <p style="text-align: center; margin-top: 30px;">
                We look forward to serving you!<br>
                <strong>See you soon at {restaurant_name}</strong>
            </p>
        </div>
        
        <div class="footer">
            <p>This is an automated confirmation email. Please save this for your records.</p>
            <p>For questions or concerns, please contact us at {restaurant_phone}</p>
            <p>&copy; {datetime.now().year} {restaurant_name}. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    return html_content


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, 'WARNING')
)
def _send_via_sendgrid(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: str,
    reply_to_email: str,
    api_key: str
) -> None:
    """
    Send email via SendGrid API with retry logic.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        from_email: Sender email address
        reply_to_email: Reply-to email address
        api_key: SendGrid API key
        
    Raises:
        EmailSendError: If email sending fails after retries
    """
    try:
        # Create SendGrid client
        sg = SendGridAPIClient(api_key=api_key)
        
        # Create email message
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        # Set reply-to
        message.reply_to = Email(reply_to_email)
        
        # Send email
        response = sg.send(message)
        
        # Check response status
        if response.status_code not in [200, 201, 202]:
            raise EmailSendError(
                f"SendGrid returned status code {response.status_code}: {response.body}"
            )
            
        logger.info(f"Email sent successfully via SendGrid. Status: {response.status_code}")
        
    except Exception as e:
        error_msg = str(e)
        
        # Handle specific SendGrid errors
        if "unauthorized" in error_msg.lower() or "api key" in error_msg.lower():
            raise EmailSendError("Invalid SendGrid API key. Please check your configuration.")
        elif "rate limit" in error_msg.lower():
            raise EmailSendError("SendGrid rate limit reached. Please try again later.")
        elif "invalid email" in error_msg.lower():
            raise EmailSendError(f"Invalid email address: {to_email}")
        else:
            raise EmailSendError(f"Failed to send email via SendGrid: {error_msg}")


def send_booking_email(email: str, booking_details: dict) -> EmailSendResult:
    """
    Send booking confirmation email to customer.
    
    This function:
    1. Validates the email address
    2. Sanitizes booking details to prevent injection
    3. Generates HTML email content
    4. Sends email via SendGrid with retry logic
    5. Logs all attempts with detailed information
    
    Args:
        email: Customer email address
        booking_details: Dictionary containing booking information with keys:
            - booking_id (int): Database booking ID (required)
            - customer_name (str): Customer name (required)
            - date (str or date): Booking date (required)
            - time (str or time): Booking time (required)
            - party_size (int): Number of guests (required)
            - special_requests (str, optional): Special requests
            
    Returns:
        EmailSendResult object with success status and message
        
    Example:
        >>> booking_details = {
        ...     'booking_id': 123,
        ...     'customer_name': 'John Doe',
        ...     'date': '2024-12-25',
        ...     'time': '19:00:00',
        ...     'party_size': 4,
        ...     'special_requests': 'Window seat please'
        ... }
        >>> result = send_booking_email('john@example.com', booking_details)
        >>> if result.success:
        ...     print(f"Email sent: {result.message}")
        ... else:
        ...     print(f"Failed: {result.error}")
    """
    # Get settings
    settings = get_settings()
    
    # Check if SendGrid is configured
    if not settings.sendgrid_api_key:
        logger.warning("SendGrid API key not configured. Email notification skipped.")
        return EmailSendResult(
            success=False,
            message="Email notification disabled",
            error="SendGrid API key not configured"
        )
    
    # Validate required booking details
    required_fields = ['booking_id', 'customer_name', 'date', 'time', 'party_size']
    missing_fields = [field for field in required_fields if field not in booking_details]
    
    if missing_fields:
        error_msg = f"Missing required booking details: {', '.join(missing_fields)}"
        logger.error(error_msg)
        return EmailSendResult(
            success=False,
            message="Invalid booking details",
            error=error_msg
        )
    
    # Extract booking ID for logging
    booking_id = booking_details.get('booking_id')
    
    # Log email attempt
    logger.info(
        f"Attempting to send booking confirmation email | "
        f"Booking ID: {booking_id} | "
        f"Recipient: {email}"
    )
    
    try:
        # Validate email address
        is_valid, result = _validate_email_address(email)
        if not is_valid:
            error_msg = f"Invalid email address: {result}"
            logger.error(
                f"Email validation failed | "
                f"Booking ID: {booking_id} | "
                f"Email: {email} | "
                f"Error: {error_msg}"
            )
            return EmailSendResult(
                success=False,
                message="Invalid email address",
                error=error_msg
            )
        
        normalized_email = result
        
        # Sanitize booking details
        sanitized_details = _sanitize_booking_details(booking_details)
        
        # Generate confirmation number
        confirmation_number = _generate_confirmation_number(booking_id)
        sanitized_details['confirmation_number'] = confirmation_number
        
        # Prepare restaurant information
        restaurant_info = {
            'name': settings.restaurant_name,
            'phone': settings.restaurant_phone,
            'address': settings.restaurant_address,
            'directions': settings.directions_info
        }
        
        # Generate HTML email content
        html_content = _create_email_html(sanitized_details, restaurant_info)
        
        # Prepare email subject
        subject = f"Booking Confirmation - {restaurant_info['name']} - {confirmation_number}"
        
        # Send email via SendGrid
        _send_via_sendgrid(
            to_email=normalized_email,
            subject=subject,
            html_content=html_content,
            from_email=settings.from_email,
            reply_to_email=settings.reply_to_email,
            api_key=settings.sendgrid_api_key
        )
        
        # Log success
        logger.info(
            f"Booking confirmation email sent successfully | "
            f"Booking ID: {booking_id} | "
            f"Recipient: {normalized_email} | "
            f"Confirmation: {confirmation_number}"
        )
        
        return EmailSendResult(
            success=True,
            message=f"Confirmation email sent to {normalized_email}"
        )
        
    except EmailSendError as e:
        # Log SendGrid-specific errors
        logger.error(
            f"Failed to send booking confirmation email | "
            f"Booking ID: {booking_id} | "
            f"Recipient: {email} | "
            f"Error: {str(e)}"
        )
        return EmailSendResult(
            success=False,
            message="Failed to send email",
            error=str(e)
        )
        
    except Exception as e:
        # Log unexpected errors
        logger.exception(
            f"Unexpected error sending booking confirmation email | "
            f"Booking ID: {booking_id} | "
            f"Recipient: {email} | "
            f"Error: {str(e)}"
        )
        return EmailSendResult(
            success=False,
            message="Unexpected error",
            error=f"An unexpected error occurred: {str(e)}"
        )
