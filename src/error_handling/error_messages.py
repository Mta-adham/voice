"""
Natural language error message generation for voice assistant.

This module provides user-friendly, conversational error messages that can be
spoken by the TTS system. Messages include helpful alternatives and suggestions
when available.
"""
from datetime import date, time, datetime
from typing import Optional, List, Dict, Any
from loguru import logger

from .exceptions import (
    BookingSystemError,
    BookingValidationError,
    NoAvailabilityError,
    CapacityExceededError,
    UserTimeoutError,
    AmbiguousInputError,
)


# ============================================================================
# Message Templates
# ============================================================================

# Booking validation errors
PAST_DATE_ERROR = (
    "I'm sorry, but I can't make a booking for a date in the past. "
    "Could you please provide a future date?"
)

BOOKING_WINDOW_ERROR = (
    "I'm sorry, but we only accept bookings up to {window_days} days in advance. "
    "The date you mentioned is too far in the future. Could you choose a date within the next {window_days} days?"
)

PARTY_SIZE_TOO_SMALL = (
    "I'm sorry, but the party size must be at least one person. "
    "How many people will be dining with us?"
)

PARTY_SIZE_TOO_LARGE = (
    "I'm sorry, but our maximum party size is {max_size} people. "
    "For larger groups, please call us directly at our restaurant to discuss special arrangements."
)

OUTSIDE_OPERATING_HOURS = (
    "I'm sorry, but {time} is outside our operating hours. "
    "We're open from {open_time} to {close_time} on {day_name}s. "
    "What time would work best for you within those hours?"
)

CLOSED_ON_DAY = (
    "I'm sorry, but we're closed on {day_name}s. "
    "Would you like to book for a different day?"
)

INVALID_TIME_FORMAT = (
    "I'm sorry, but I didn't quite catch the time you mentioned. "
    "Could you please say it again? For example, you could say 'seven thirty PM' or 'nineteen thirty'."
)

INVALID_DATE_FORMAT = (
    "I'm sorry, but I didn't understand the date you mentioned. "
    "Could you please say it again? For example, 'tomorrow', 'December 25th', or 'next Friday'."
)

# Availability errors
NO_AVAILABILITY_BASE = (
    "I'm sorry, but we don't have any availability for {party_size} people "
    "at {time} on {date}."
)

NO_AVAILABILITY_WITH_ALTERNATIVES = (
    "I'm sorry, but we don't have any availability for {party_size} people "
    "at {time} on {date}. However, I do have these alternative times available: {alternatives}. "
    "Would any of these work for you?"
)

NO_AVAILABILITY_TRY_DIFFERENT_DATE = (
    "I'm sorry, but we're fully booked on {date}. "
    "Would you like to try a different date?"
)

CAPACITY_EXCEEDED = (
    "I'm sorry, but we only have {available} seats remaining at that time, "
    "which isn't quite enough for your party of {requested}. "
    "Would you like to try a different time, or perhaps split your party into smaller groups?"
)

# User interaction errors
USER_TIMEOUT_FIRST = (
    "I haven't heard from you. Are you still there?"
)

USER_TIMEOUT_SECOND = (
    "I still haven't heard from you. If you're having trouble, "
    "please feel free to call us directly, or I can try to help you again now."
)

USER_TIMEOUT_FINAL = (
    "I haven't received a response, so I'll end this conversation for now. "
    "Please feel free to call back anytime. Have a great day!"
)

AMBIGUOUS_INPUT = (
    "I'm not sure I understood that correctly. {clarification_prompt}"
)

# Technical errors
TECHNICAL_DIFFICULTY = (
    "I'm experiencing some technical difficulties at the moment. "
    "Let me try that again."
)

AUDIO_QUALITY_ISSUE = (
    "I'm sorry, I had trouble hearing that. "
    "Could you please speak a bit louder and clearer?"
)

NO_SPEECH_DETECTED = (
    "I didn't hear anything. Could you please repeat that?"
)

DATABASE_ERROR = (
    "I'm having trouble accessing our booking system right now. "
    "Please hold on while I try again."
)

DATABASE_ERROR_PERSISTENT = (
    "I'm sorry, but I'm having persistent issues connecting to our booking system. "
    "Could you please try again in a few minutes, or call us directly to make your reservation?"
)

SERVICE_UNAVAILABLE = (
    "I'm experiencing technical difficulties and cannot process your request at this time. "
    "Please try again later or call us directly to make your reservation."
)

# Success with notification warnings
BOOKING_SUCCESS_NO_SMS = (
    "Your booking is confirmed! However, I wasn't able to send you a text message confirmation. "
    "Your confirmation number is {confirmation_id}. Please write that down."
)

BOOKING_SUCCESS_NO_EMAIL = (
    "Your booking is confirmed! However, I wasn't able to send you an email confirmation. "
    "Your confirmation number is {confirmation_id}. I've sent you a text message with the details."
)

BOOKING_SUCCESS_NO_NOTIFICATIONS = (
    "Your booking is confirmed! However, I wasn't able to send confirmation messages. "
    "Your confirmation number is {confirmation_id}. Please write that down, "
    "and feel free to call us to verify your reservation."
)


# ============================================================================
# Message Generation Functions
# ============================================================================

def format_date_friendly(date_obj: date) -> str:
    """
    Format a date in a friendly, speakable way.
    
    Args:
        date_obj: Date to format
        
    Returns:
        Friendly date string (e.g., "Monday, December 25th")
    """
    day_name = date_obj.strftime("%A")
    month_name = date_obj.strftime("%B")
    day = date_obj.day
    
    # Add ordinal suffix
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    
    return f"{day_name}, {month_name} {day}{suffix}"


def format_time_friendly(time_obj: time) -> str:
    """
    Format a time in a friendly, speakable way.
    
    Args:
        time_obj: Time to format
        
    Returns:
        Friendly time string (e.g., "7:30 PM")
    """
    hour = time_obj.hour
    minute = time_obj.minute
    
    # Convert to 12-hour format
    if hour == 0:
        hour_12 = 12
        period = "AM"
    elif hour < 12:
        hour_12 = hour
        period = "AM"
    elif hour == 12:
        hour_12 = 12
        period = "PM"
    else:
        hour_12 = hour - 12
        period = "PM"
    
    if minute == 0:
        return f"{hour_12} {period}"
    else:
        return f"{hour_12}:{minute:02d} {period}"


def format_time_alternatives(time_slots: List[time], max_alternatives: int = 3) -> str:
    """
    Format alternative time slots in a friendly way.
    
    Args:
        time_slots: List of available time slots
        max_alternatives: Maximum number of alternatives to include
        
    Returns:
        Friendly formatted string of alternatives
    """
    if not time_slots:
        return ""
    
    # Limit to max_alternatives
    slots = time_slots[:max_alternatives]
    friendly_times = [format_time_friendly(t) for t in slots]
    
    if len(friendly_times) == 1:
        return friendly_times[0]
    elif len(friendly_times) == 2:
        return f"{friendly_times[0]} or {friendly_times[1]}"
    else:
        return ", ".join(friendly_times[:-1]) + f", or {friendly_times[-1]}"


def generate_booking_validation_error_message(
    error: BookingValidationError,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate user-friendly message for booking validation errors.
    
    Args:
        error: BookingValidationError instance
        context: Additional context (restaurant config, etc.)
        
    Returns:
        Natural language error message
    """
    message = error.message.lower()
    
    # Past date error
    if "past" in message:
        return PAST_DATE_ERROR
    
    # Booking window error
    if "booking" in message and "window" in message or "advance" in message:
        window_days = context.get("booking_window_days", 30) if context else 30
        return BOOKING_WINDOW_ERROR.format(window_days=window_days)
    
    # Party size errors
    if "party size" in message:
        if "at least" in message or "must be" in message:
            return PARTY_SIZE_TOO_SMALL
        elif "exceed" in message or "cannot be more" in message:
            max_size = context.get("max_party_size", 8) if context else 8
            return PARTY_SIZE_TOO_LARGE.format(max_size=max_size)
    
    # Operating hours error
    if "operating hours" in message:
        if context:
            time_str = context.get("requested_time", "that time")
            open_time = context.get("open_time", "")
            close_time = context.get("close_time", "")
            day_name = context.get("day_name", "that day")
            
            return OUTSIDE_OPERATING_HOURS.format(
                time=time_str,
                open_time=open_time,
                close_time=close_time,
                day_name=day_name
            )
        return "I'm sorry, but that time is outside our operating hours. What time would work best for you?"
    
    # Closed on day
    if "closed" in message:
        day_name = context.get("day_name", "that day") if context else "that day"
        return CLOSED_ON_DAY.format(day_name=day_name)
    
    # Invalid format errors
    if "time" in message and ("invalid" in message or "format" in message):
        return INVALID_TIME_FORMAT
    
    if "date" in message and ("invalid" in message or "format" in message):
        return INVALID_DATE_FORMAT
    
    # Default fallback
    return error.user_message or "I'm sorry, but there was an issue with that information. Could you please try again?"


def generate_no_availability_error_message(
    error: NoAvailabilityError,
    alternatives: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Generate user-friendly message for no availability errors with alternatives.
    
    Args:
        error: NoAvailabilityError instance
        alternatives: List of alternative time slots (each with 'time' key)
        
    Returns:
        Natural language error message with alternatives if available
    """
    # Extract requested information
    date_str = error.requested_date
    time_str = error.requested_time
    party_size = error.party_size
    
    # Format date and time in friendly way
    try:
        if date_str:
            if isinstance(date_str, str):
                date_obj = datetime.fromisoformat(date_str).date()
            else:
                date_obj = date_str
            friendly_date = format_date_friendly(date_obj)
        else:
            friendly_date = "that date"
    except (ValueError, AttributeError):
        friendly_date = date_str or "that date"
    
    try:
        if time_str:
            if isinstance(time_str, str):
                time_obj = datetime.strptime(time_str, "%H:%M").time()
            else:
                time_obj = time_str
            friendly_time = format_time_friendly(time_obj)
        else:
            friendly_time = "that time"
    except (ValueError, AttributeError):
        friendly_time = time_str or "that time"
    
    party_str = f"{party_size} people" if party_size else "your party"
    
    # Check if we have alternatives
    alternatives = alternatives or error.alternatives
    
    if alternatives and len(alternatives) > 0:
        # Extract time objects from alternatives
        alt_times = []
        for alt in alternatives:
            if isinstance(alt, dict) and 'time' in alt:
                alt_times.append(alt['time'])
            elif hasattr(alt, 'time'):
                alt_times.append(alt.time)
        
        if alt_times:
            alt_str = format_time_alternatives(alt_times)
            return NO_AVAILABILITY_WITH_ALTERNATIVES.format(
                party_size=party_str,
                time=friendly_time,
                date=friendly_date,
                alternatives=alt_str
            )
    
    # No alternatives available
    if date_str:
        return NO_AVAILABILITY_TRY_DIFFERENT_DATE.format(date=friendly_date)
    else:
        return NO_AVAILABILITY_BASE.format(
            party_size=party_str,
            time=friendly_time,
            date=friendly_date
        )


def generate_capacity_error_message(error: CapacityExceededError) -> str:
    """
    Generate user-friendly message for capacity exceeded errors.
    
    Args:
        error: CapacityExceededError instance
        
    Returns:
        Natural language error message
    """
    requested = error.requested_size or "your party size"
    available = error.available_capacity or 0
    
    return CAPACITY_EXCEEDED.format(
        available=available,
        requested=requested
    )


def generate_user_timeout_message(retry_count: int = 0) -> str:
    """
    Generate user-friendly message for user timeout based on retry count.
    
    Args:
        retry_count: Number of timeouts that have occurred
        
    Returns:
        Natural language timeout message
    """
    if retry_count == 0:
        return USER_TIMEOUT_FIRST
    elif retry_count == 1:
        return USER_TIMEOUT_SECOND
    else:
        return USER_TIMEOUT_FINAL


def generate_technical_error_message(
    error: BookingSystemError,
    retry_count: int = 0
) -> str:
    """
    Generate user-friendly message for technical errors.
    
    Args:
        error: BookingSystemError instance
        retry_count: Number of retries attempted
        
    Returns:
        Natural language error message
    """
    # Database errors
    if "database" in error.__class__.__name__.lower():
        if retry_count > 2:
            return DATABASE_ERROR_PERSISTENT
        return DATABASE_ERROR
    
    # Audio errors
    if "silence" in error.__class__.__name__.lower():
        return NO_SPEECH_DETECTED
    
    if "unclear" in error.__class__.__name__.lower() or "audio quality" in str(error).lower():
        return AUDIO_QUALITY_ISSUE
    
    # Service unavailable (non-recoverable)
    if not error.recoverable:
        return SERVICE_UNAVAILABLE
    
    # Generic technical difficulty
    return TECHNICAL_DIFFICULTY


def generate_error_message(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    retry_count: int = 0
) -> str:
    """
    Generate appropriate user-friendly error message for any exception.
    
    This is the main entry point for error message generation.
    
    Args:
        error: Exception instance
        context: Additional context for message generation
        retry_count: Number of retries attempted
        
    Returns:
        Natural language error message suitable for TTS
    """
    logger.debug(f"Generating error message for {error.__class__.__name__}: {str(error)}")
    
    # If error has user_message attribute, prefer that
    if hasattr(error, 'user_message') and error.user_message:
        return error.user_message
    
    # Handle specific error types
    if isinstance(error, BookingValidationError):
        return generate_booking_validation_error_message(error, context)
    
    elif isinstance(error, NoAvailabilityError):
        alternatives = context.get("alternatives") if context else None
        return generate_no_availability_error_message(error, alternatives)
    
    elif isinstance(error, CapacityExceededError):
        return generate_capacity_error_message(error)
    
    elif isinstance(error, UserTimeoutError):
        return generate_user_timeout_message(error.retry_count or retry_count)
    
    elif isinstance(error, AmbiguousInputError):
        return error.user_message or AMBIGUOUS_INPUT.format(
            clarification_prompt="Could you please clarify?"
        )
    
    elif isinstance(error, BookingSystemError):
        return generate_technical_error_message(error, retry_count)
    
    # Fallback for unknown errors
    logger.warning(f"No specific message for error type: {error.__class__.__name__}")
    return TECHNICAL_DIFFICULTY
