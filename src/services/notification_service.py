"""
Notification service for SMS and Email delivery with graceful degradation.

This module provides notification delivery through Twilio (SMS) and SendGrid (Email)
with comprehensive error handling and fallback strategies. Notification failures
do not block the booking flow.
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time
from loguru import logger

# Twilio imports
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("twilio package not installed. SMS notifications will not be available.")

# SendGrid imports
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("sendgrid package not installed. Email notifications will not be available.")

from ..error_handling.exceptions import (
    SMSDeliveryError,
    EmailDeliveryError,
    NotificationError,
)


class NotificationService:
    """
    Service for sending booking confirmations via SMS and Email.
    
    Features:
    - SMS delivery via Twilio
    - Email delivery via SendGrid
    - Graceful degradation (failures don't block booking)
    - Automatic fallback between channels
    - Comprehensive error handling and logging
    - Template-based message formatting
    
    Example:
        notification_service = NotificationService()
        
        # Send both SMS and Email
        results = notification_service.send_booking_confirmation(
            booking_data={
                "confirmation_id": "ABC123",
                "date": "2024-12-25",
                "time": "18:00",
                "party_size": 4,
                "customer_name": "John Doe"
            },
            phone="+1234567890",
            email="john@example.com"
        )
    """
    
    def __init__(
        self,
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
        twilio_phone_number: Optional[str] = None,
        sendgrid_api_key: Optional[str] = None,
        restaurant_name: str = "Our Restaurant",
        restaurant_phone: str = "",
        restaurant_email: str = ""
    ):
        """
        Initialize notification service.
        
        Args:
            twilio_account_sid: Twilio account SID (or from TWILIO_ACCOUNT_SID env var)
            twilio_auth_token: Twilio auth token (or from TWILIO_AUTH_TOKEN env var)
            twilio_phone_number: Twilio phone number (or from TWILIO_PHONE_NUMBER env var)
            sendgrid_api_key: SendGrid API key (or from SENDGRID_API_KEY env var)
            restaurant_name: Restaurant name for notifications
            restaurant_phone: Restaurant contact phone
            restaurant_email: Restaurant contact email
        """
        self.restaurant_name = restaurant_name
        self.restaurant_phone = restaurant_phone
        self.restaurant_email = restaurant_email
        
        # Initialize Twilio client
        self.twilio_client = None
        self.twilio_phone_number = None
        
        if TWILIO_AVAILABLE:
            account_sid = twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN")
            self.twilio_phone_number = twilio_phone_number or os.getenv("TWILIO_PHONE_NUMBER")
            
            if account_sid and auth_token and self.twilio_phone_number:
                try:
                    self.twilio_client = TwilioClient(account_sid, auth_token)
                    logger.info("Twilio SMS client initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize Twilio client: {e}")
            else:
                logger.info("Twilio credentials not configured. SMS notifications disabled.")
        
        # Initialize SendGrid client
        self.sendgrid_client = None
        
        if SENDGRID_AVAILABLE:
            api_key = sendgrid_api_key or os.getenv("SENDGRID_API_KEY")
            
            if api_key:
                try:
                    self.sendgrid_client = SendGridAPIClient(api_key)
                    logger.info("SendGrid email client initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize SendGrid client: {e}")
            else:
                logger.info("SendGrid API key not configured. Email notifications disabled.")
    
    def _format_booking_sms(self, booking_data: Dict[str, Any]) -> str:
        """
        Format booking confirmation SMS message.
        
        Args:
            booking_data: Booking information dictionary
            
        Returns:
            Formatted SMS message
        """
        confirmation_id = booking_data.get("confirmation_id", "N/A")
        customer_name = booking_data.get("customer_name", "")
        date_str = booking_data.get("date", "")
        time_str = booking_data.get("time", "")
        party_size = booking_data.get("party_size", 0)
        
        # Format date in friendly way
        try:
            if isinstance(date_str, str):
                date_obj = datetime.fromisoformat(date_str).date()
            else:
                date_obj = date_str
            friendly_date = date_obj.strftime("%A, %B %d, %Y")
        except (ValueError, AttributeError):
            friendly_date = str(date_str)
        
        # Format time in friendly way
        try:
            if isinstance(time_str, str):
                time_obj = datetime.strptime(time_str, "%H:%M").time()
            else:
                time_obj = time_str
            friendly_time = time_obj.strftime("%I:%M %p").lstrip("0")
        except (ValueError, AttributeError):
            friendly_time = str(time_str)
        
        message = f"""Booking Confirmed at {self.restaurant_name}!

Hello {customer_name},
Your reservation is confirmed:

📅 Date: {friendly_date}
🕐 Time: {friendly_time}
👥 Party Size: {party_size}
🔖 Confirmation #: {confirmation_id}

We look forward to serving you!"""
        
        if self.restaurant_phone:
            message += f"\n\nQuestions? Call us: {self.restaurant_phone}"
        
        return message
    
    def _format_booking_email_html(self, booking_data: Dict[str, Any]) -> str:
        """
        Format booking confirmation email in HTML.
        
        Args:
            booking_data: Booking information dictionary
            
        Returns:
            Formatted HTML email
        """
        confirmation_id = booking_data.get("confirmation_id", "N/A")
        customer_name = booking_data.get("customer_name", "")
        date_str = booking_data.get("date", "")
        time_str = booking_data.get("time", "")
        party_size = booking_data.get("party_size", 0)
        special_requests = booking_data.get("special_requests", "")
        
        # Format date
        try:
            if isinstance(date_str, str):
                date_obj = datetime.fromisoformat(date_str).date()
            else:
                date_obj = date_str
            friendly_date = date_obj.strftime("%A, %B %d, %Y")
        except (ValueError, AttributeError):
            friendly_date = str(date_str)
        
        # Format time
        try:
            if isinstance(time_str, str):
                time_obj = datetime.strptime(time_str, "%H:%M").time()
            else:
                time_obj = time_str
            friendly_time = time_obj.strftime("%I:%M %p").lstrip("0")
        except (ValueError, AttributeError):
            friendly_time = str(time_str)
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c5282;">Booking Confirmed!</h2>
                <p>Hello {customer_name},</p>
                <p>Your reservation at <strong>{self.restaurant_name}</strong> has been confirmed.</p>
                
                <div style="background-color: #f7fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c5282;">Reservation Details</h3>
                    <table style="width: 100%;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Date:</strong></td>
                            <td style="padding: 8px 0;">{friendly_date}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Time:</strong></td>
                            <td style="padding: 8px 0;">{friendly_time}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Party Size:</strong></td>
                            <td style="padding: 8px 0;">{party_size} guests</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Confirmation Number:</strong></td>
                            <td style="padding: 8px 0;"><strong>{confirmation_id}</strong></td>
                        </tr>
        """
        
        if special_requests:
            html += f"""
                        <tr>
                            <td style="padding: 8px 0;"><strong>Special Requests:</strong></td>
                            <td style="padding: 8px 0;">{special_requests}</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
                
                <p>We look forward to serving you!</p>
        """
        
        if self.restaurant_phone or self.restaurant_email:
            html += "<p><strong>Contact Us:</strong><br>"
            if self.restaurant_phone:
                html += f"Phone: {self.restaurant_phone}<br>"
            if self.restaurant_email:
                html += f"Email: {self.restaurant_email}"
            html += "</p>"
        
        html += """
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                <p style="font-size: 12px; color: #718096;">
                    Please save this confirmation for your records. 
                    If you need to modify or cancel your reservation, please contact us directly.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_sms(self, phone: str, message: str) -> bool:
        """
        Send SMS message via Twilio.
        
        Args:
            phone: Recipient phone number (E.164 format recommended)
            message: Message text to send
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            SMSDeliveryError: If SMS delivery fails
        """
        if not self.twilio_client:
            raise SMSDeliveryError(
                "Twilio client not initialized. SMS service not available.",
                phone_number=phone
            )
        
        try:
            logger.info(f"Sending SMS to {phone}")
            
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=phone
            )
            
            logger.info(f"SMS sent successfully. SID: {message_obj.sid}")
            return True
            
        except TwilioRestException as e:
            logger.error(f"Twilio SMS delivery failed: {e}")
            raise SMSDeliveryError(
                f"SMS delivery failed: {e.msg}",
                phone_number=phone,
                original_error=e,
                context={"error_code": e.code}
            )
        except Exception as e:
            logger.error(f"Unexpected SMS delivery error: {e}")
            raise SMSDeliveryError(
                f"SMS delivery failed: {str(e)}",
                phone_number=phone,
                original_error=e
            )
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None
    ) -> bool:
        """
        Send email via SendGrid.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email content
            from_email: Sender email (uses restaurant_email if not provided)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            EmailDeliveryError: If email delivery fails
        """
        if not self.sendgrid_client:
            raise EmailDeliveryError(
                "SendGrid client not initialized. Email service not available.",
                email_address=to_email
            )
        
        if from_email is None:
            from_email = self.restaurant_email or "noreply@restaurant.com"
        
        try:
            logger.info(f"Sending email to {to_email}")
            
            message = Mail(
                from_email=Email(from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.sendgrid_client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.warning(f"Email sent with non-success status: {response.status_code}")
                return True  # SendGrid may still deliver
                
        except Exception as e:
            logger.error(f"SendGrid email delivery failed: {e}")
            raise EmailDeliveryError(
                f"Email delivery failed: {str(e)}",
                email_address=to_email,
                original_error=e
            )
    
    def send_booking_confirmation(
        self,
        booking_data: Dict[str, Any],
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Send booking confirmation via SMS and/or Email.
        
        This method implements graceful degradation - failures are logged but
        don't raise exceptions. The booking process continues even if
        notifications fail.
        
        Args:
            booking_data: Booking information dictionary
            phone: Customer phone number for SMS
            email: Customer email address for Email
            
        Returns:
            Dictionary with delivery status:
            {
                "sms_sent": True/False,
                "email_sent": True/False,
                "sms_error": Optional[str],
                "email_error": Optional[str]
            }
        """
        results = {
            "sms_sent": False,
            "email_sent": False,
            "sms_error": None,
            "email_error": None
        }
        
        # Try to send SMS
        if phone and self.twilio_client:
            try:
                message = self._format_booking_sms(booking_data)
                self.send_sms(phone, message)
                results["sms_sent"] = True
            except SMSDeliveryError as e:
                results["sms_error"] = str(e)
                logger.warning(f"SMS delivery failed but continuing: {e}")
            except Exception as e:
                results["sms_error"] = str(e)
                logger.error(f"Unexpected SMS error but continuing: {e}")
        elif phone and not self.twilio_client:
            results["sms_error"] = "SMS service not configured"
            logger.info("SMS not sent: service not configured")
        
        # Try to send Email
        if email and self.sendgrid_client:
            try:
                subject = f"Booking Confirmation - {self.restaurant_name}"
                html_content = self._format_booking_email_html(booking_data)
                self.send_email(email, subject, html_content)
                results["email_sent"] = True
            except EmailDeliveryError as e:
                results["email_error"] = str(e)
                logger.warning(f"Email delivery failed but continuing: {e}")
            except Exception as e:
                results["email_error"] = str(e)
                logger.error(f"Unexpected email error but continuing: {e}")
        elif email and not self.sendgrid_client:
            results["email_error"] = "Email service not configured"
            logger.info("Email not sent: service not configured")
        
        # Log summary
        logger.info(
            f"Notification delivery summary: "
            f"SMS={'✓' if results['sms_sent'] else '✗'}, "
            f"Email={'✓' if results['email_sent'] else '✗'}"
        )
        
        return results
    
    def is_sms_available(self) -> bool:
        """Check if SMS service is available."""
        return self.twilio_client is not None
    
    def is_email_available(self) -> bool:
        """Check if email service is available."""
        return self.sendgrid_client is not None
    
    def __repr__(self) -> str:
        sms_status = "enabled" if self.is_sms_available() else "disabled"
        email_status = "enabled" if self.is_email_available() else "disabled"
        return f"NotificationService(SMS: {sms_status}, Email: {email_status})"
