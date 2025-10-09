"""
Natural Language Error Messages for Voice Agent.

This module generates user-friendly, conversational error messages
that the voice agent can speak to users. It avoids technical jargon
and provides helpful alternatives when possible.
"""

from typing import Optional, List, Dict, Any
from datetime import date, time, datetime, timedelta
import random

from .exceptions import (
    BookingSystemError,
    BookingValidationError,
    NoAvailabilityError,
    InvalidDateError,
    InvalidTimeError,
    InvalidPartySizeError,
    AudioProcessingError,
    STTError,
    TTSError,
    LLMProviderError,
    DatabaseError,
    NotificationError,
    UserTimeoutError,
    AmbiguousInputError,
)


class ErrorMessageGenerator:
    """
    Generates natural language error messages for voice responses.
    
    Features:
    - Conversational, friendly tone
    - Avoids technical jargon
    - Includes helpful alternatives
    - Variety in phrasing (uses templates with variations)
    """
    
    # Message templates for different error types
    TEMPLATES = {
        "no_availability_date": [
            "I'm sorry, but we're fully booked on {date_str}. {alternatives}",
            "Unfortunately, we don't have any availability on {date_str}. {alternatives}",
            "That date is completely booked, I'm afraid. {alternatives}",
        ],
        "no_availability_time": [
            "I'm sorry, but we're fully booked at {time_str} on {date_str}. {alternatives}",
            "Unfortunately, that time slot is no longer available. {alternatives}",
            "We don't have any tables available at {time_str}. {alternatives}",
        ],
        "past_date": [
            "I'm sorry, but that date has already passed. Could you provide a date in the future?",
            "Unfortunately, we can't book reservations for past dates. Would you like to choose another date?",
            "That date is in the past. What future date would work for you?",
        ],
        "date_too_far": [
            "I'm sorry, but we can only accept reservations up to {max_days} days in advance. Could you choose a date within the next {max_days} days?",
            "Unfortunately, that's beyond our booking window. We accept reservations up to {max_days} days ahead. Can you pick a closer date?",
        ],
        "invalid_time": [
            "I'm sorry, but {time_str} is outside our operating hours. {hours_msg}",
            "Unfortunately, we're not open at {time_str}. {hours_msg}",
            "That time doesn't work because we're closed then. {hours_msg}",
        ],
        "closed_day": [
            "I'm sorry, but we're closed on {day_name}s. {alternatives}",
            "Unfortunately, the restaurant is closed on {day_name}s. {alternatives}",
        ],
        "party_size_too_large": [
            "I'm sorry, but we can only accommodate parties up to {max_size} people. For larger groups, please call us directly at the restaurant.",
            "Unfortunately, our maximum party size is {max_size} people. For groups larger than {max_size}, we'd need to make special arrangements. Could you call us?",
        ],
        "party_size_invalid": [
            "I'm sorry, but I didn't quite catch that. How many people will be dining with us?",
            "Could you repeat how many people will be in your party?",
        ],
        "audio_unclear": [
            "I'm sorry, I didn't quite catch that. Could you repeat that for me?",
            "I had trouble hearing you. Could you say that again?",
            "Sorry, I missed that. Could you please repeat?",
        ],
        "timeout": [
            "I haven't heard from you in a while. Are you still there?",
            "Hello? I didn't hear a response. Should we continue?",
            "Are you still there? I didn't catch your response.",
        ],
        "timeout_final": [
            "I haven't heard from you, so I'll end this call. Feel free to call back anytime to make a reservation. Have a great day!",
            "Since I haven't received a response, I'll disconnect now. Please call back when you're ready. Thank you!",
        ],
        "system_error": [
            "I apologize, but I'm experiencing some technical difficulties. Please try again in a moment, or call us directly to make your reservation.",
            "I'm sorry, something went wrong on my end. Could you try again, or would you prefer to speak with someone at the restaurant?",
        ],
        "database_error": [
            "I'm having trouble accessing our reservation system at the moment. Could you try again in a moment?",
            "I apologize, but our booking system is temporarily unavailable. Please try again shortly.",
        ],
        "notification_failed": [
            "Your reservation is confirmed, but I wasn't able to send you a confirmation {notification_type}. You may want to write down your confirmation number.",
            "I've made your reservation, but the confirmation {notification_type} failed to send. Please note your confirmation details.",
        ],
    }
    
    @staticmethod
    def _format_date(date_obj: date) -> str:
        """Format date for natural speech."""
        return date_obj.strftime("%A, %B %d")
    
    @staticmethod
    def _format_time(time_obj: time) -> str:
        """Format time for natural speech."""
        # Convert to 12-hour format
        hour = time_obj.hour
        minute = time_obj.minute
        am_pm = "AM" if hour < 12 else "PM"
        
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        
        if minute == 0:
            return f"{hour} {am_pm}"
        else:
            return f"{hour}:{minute:02d} {am_pm}"
    
    @staticmethod
    def _get_random_template(key: str) -> str:
        """Get a random message template for variety."""
        templates = ErrorMessageGenerator.TEMPLATES.get(key, [])
        if templates:
            return random.choice(templates)
        return ""
    
    @staticmethod
    def generate_no_availability_message(
        date_obj: Optional[date] = None,
        time_obj: Optional[time] = None,
        party_size: Optional[int] = None,
        alternative_slots: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate message for no availability."""
        date_str = ErrorMessageGenerator._format_date(date_obj) if date_obj else "that date"
        time_str = ErrorMessageGenerator._format_time(time_obj) if time_obj else ""
        
        # Generate alternatives suggestion
        alternatives = ""
        if alternative_slots:
            # Format first 3 alternative times
            alt_times = []
            for slot in alternative_slots[:3]:
                if isinstance(slot, dict) and "time" in slot:
                    alt_time = slot["time"]
                    if isinstance(alt_time, time):
                        alt_times.append(ErrorMessageGenerator._format_time(alt_time))
            
            if alt_times:
                if len(alt_times) == 1:
                    alternatives = f"Would {alt_times[0]} work for you instead?"
                elif len(alt_times) == 2:
                    alternatives = f"Would {alt_times[0]} or {alt_times[1]} work instead?"
                else:
                    alternatives = f"We have availability at {alt_times[0]}, {alt_times[1]}, or {alt_times[2]}. Would any of those work?"
        
        if not alternatives:
            alternatives = "Would you like to try a different date or time?"
        
        # Choose appropriate template
        if time_obj:
            template = ErrorMessageGenerator._get_random_template("no_availability_time")
            return template.format(time_str=time_str, date_str=date_str, alternatives=alternatives)
        else:
            template = ErrorMessageGenerator._get_random_template("no_availability_date")
            return template.format(date_str=date_str, alternatives=alternatives)
    
    @staticmethod
    def generate_invalid_date_message(
        date_obj: date,
        reason: str,
        max_days: Optional[int] = None,
    ) -> str:
        """Generate message for invalid date."""
        if "past" in reason.lower():
            return ErrorMessageGenerator._get_random_template("past_date")
        elif "beyond" in reason.lower() or "advance" in reason.lower():
            template = ErrorMessageGenerator._get_random_template("date_too_far")
            return template.format(max_days=max_days or 30)
        else:
            return f"I'm sorry, but {ErrorMessageGenerator._format_date(date_obj)} doesn't work. Could you choose another date?"
    
    @staticmethod
    def generate_invalid_time_message(
        time_obj: time,
        operating_hours: Optional[tuple] = None,
        day_name: Optional[str] = None,
    ) -> str:
        """Generate message for invalid time."""
        time_str = ErrorMessageGenerator._format_time(time_obj)
        
        # Check if restaurant is closed
        if operating_hours is None:
            template = ErrorMessageGenerator._get_random_template("closed_day")
            return template.format(
                day_name=day_name or "that day",
                alternatives="What other day would work for you?"
            )
        
        # Generate operating hours message
        open_time, close_time = operating_hours
        open_str = ErrorMessageGenerator._format_time(open_time)
        close_str = ErrorMessageGenerator._format_time(close_time)
        hours_msg = f"We're open from {open_str} to {close_str}. What time would you prefer?"
        
        template = ErrorMessageGenerator._get_random_template("invalid_time")
        return template.format(time_str=time_str, hours_msg=hours_msg)
    
    @staticmethod
    def generate_party_size_message(party_size: int, max_size: int = 8) -> str:
        """Generate message for invalid party size."""
        if party_size > max_size:
            template = ErrorMessageGenerator._get_random_template("party_size_too_large")
            return template.format(max_size=max_size)
        else:
            return ErrorMessageGenerator._get_random_template("party_size_invalid")
    
    @staticmethod
    def generate_audio_error_message() -> str:
        """Generate message for audio processing errors."""
        return ErrorMessageGenerator._get_random_template("audio_unclear")
    
    @staticmethod
    def generate_timeout_message(retry_count: int = 0) -> str:
        """Generate message for user timeout."""
        if retry_count >= 2:
            return ErrorMessageGenerator._get_random_template("timeout_final")
        else:
            return ErrorMessageGenerator._get_random_template("timeout")
    
    @staticmethod
    def generate_system_error_message() -> str:
        """Generate message for system errors."""
        return ErrorMessageGenerator._get_random_template("system_error")
    
    @staticmethod
    def generate_database_error_message() -> str:
        """Generate message for database errors."""
        return ErrorMessageGenerator._get_random_template("database_error")
    
    @staticmethod
    def generate_notification_error_message(notification_type: str) -> str:
        """Generate message for notification failures."""
        template = ErrorMessageGenerator._get_random_template("notification_failed")
        return template.format(notification_type=notification_type)
    
    @staticmethod
    def generate_ambiguous_input_message(missing_fields: Optional[List[str]] = None) -> str:
        """Generate message for ambiguous user input."""
        if not missing_fields:
            return "I'm sorry, I didn't quite understand that. Could you clarify?"
        
        # Map field names to friendly names
        field_map = {
            "date": "the date",
            "time": "the time",
            "party_size": "how many people",
            "name": "your name",
            "phone": "your phone number",
        }
        
        friendly_fields = [field_map.get(f, f) for f in missing_fields]
        
        if len(friendly_fields) == 1:
            return f"I didn't catch {friendly_fields[0]}. Could you repeat that?"
        else:
            fields_str = ", ".join(friendly_fields[:-1]) + f", and {friendly_fields[-1]}"
            return f"I'm missing {fields_str}. Could you provide those details?"


def get_error_message(error: Exception) -> str:
    """
    Generate user-friendly error message from exception.
    
    Args:
        error: Exception that occurred
    
    Returns:
        Natural language message suitable for voice response
    """
    generator = ErrorMessageGenerator()
    
    # BookingValidationError variants
    if isinstance(error, NoAvailabilityError):
        return generator.generate_no_availability_message(
            date_obj=error.context.get("date"),
            time_obj=error.context.get("time"),
            party_size=error.context.get("party_size"),
            alternative_slots=error.alternatives,
        )
    
    elif isinstance(error, InvalidDateError):
        return generator.generate_invalid_date_message(
            date_obj=error.value,
            reason=error.message,
            max_days=error.context.get("booking_window_days"),
        )
    
    elif isinstance(error, InvalidTimeError):
        return generator.generate_invalid_time_message(
            time_obj=error.value,
            operating_hours=error.context.get("operating_hours"),
        )
    
    elif isinstance(error, InvalidPartySizeError):
        return generator.generate_party_size_message(
            party_size=error.value,
            max_size=error.context.get("max_size", 8),
        )
    
    elif isinstance(error, BookingValidationError):
        # Generic booking validation error
        if error.user_message:
            return error.user_message
        return "I'm sorry, but that booking isn't available. Could you try different details?"
    
    # Audio errors
    elif isinstance(error, (STTError, AudioProcessingError)):
        return generator.generate_audio_error_message()
    
    # User interaction errors
    elif isinstance(error, UserTimeoutError):
        return generator.generate_timeout_message(
            retry_count=error.retry_count
        )
    
    elif isinstance(error, AmbiguousInputError):
        return generator.generate_ambiguous_input_message(
            missing_fields=error.missing_fields
        )
    
    # Technical errors
    elif isinstance(error, DatabaseError):
        return generator.generate_database_error_message()
    
    elif isinstance(error, NotificationError):
        return generator.generate_notification_error_message(
            notification_type=error.notification_type
        )
    
    elif isinstance(error, (LLMProviderError, TTSError)):
        return generator.generate_system_error_message()
    
    # Generic BookingSystemError
    elif isinstance(error, BookingSystemError):
        if error.user_message:
            return error.user_message
        return generator.generate_system_error_message()
    
    # Unknown error
    else:
        return generator.generate_system_error_message()


def get_alternative_suggestions(
    date_obj: date,
    party_size: int,
    booking_service: Any,
    num_suggestions: int = 3,
) -> List[Dict[str, Any]]:
    """
    Get alternative time slot suggestions when requested slot is unavailable.
    
    Args:
        date_obj: Requested date
        party_size: Party size
        booking_service: BookingService instance for querying availability
        num_suggestions: Number of alternative slots to return
    
    Returns:
        List of alternative slot dictionaries with date, time, and availability info
    """
    try:
        # Get available slots for the requested date
        available_slots = booking_service.get_available_slots(date_obj, party_size)
        
        if available_slots:
            return [
                {
                    "date": slot.date,
                    "time": slot.time,
                    "remaining_capacity": slot.remaining_capacity,
                }
                for slot in available_slots[:num_suggestions]
            ]
        
        # If no slots on requested date, try next 3 days
        suggestions = []
        current_date = date_obj + timedelta(days=1)
        max_date = date_obj + timedelta(days=7)
        
        while current_date <= max_date and len(suggestions) < num_suggestions:
            slots = booking_service.get_available_slots(current_date, party_size)
            if slots:
                # Take first available slot from this date
                slot = slots[0]
                suggestions.append({
                    "date": slot.date,
                    "time": slot.time,
                    "remaining_capacity": slot.remaining_capacity,
                })
            current_date += timedelta(days=1)
        
        return suggestions
        
    except Exception:
        # If we can't get alternatives, return empty list
        return []
