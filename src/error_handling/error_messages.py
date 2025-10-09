"""
 Natural language error message generation for voice-based booking system.

This module provides user-friendly, conversational error messages that can be
spoken by the TTS system. It includes logic for suggesting alternatives and
maintaining a friendly tone even during errors.
"""
from datetime import date, time, datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger

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
    UnclearAudioError,
    SilenceDetectedError, 
    BookingAgentError,
    NoAvailabilityError,
    InvalidDateError,
    InvalidTimeError,
    PartySizeTooLargeError,
    AudioProcessingError,
    TranscriptionError,
    TextToSpeechError, 
    LLMProviderError,
    DatabaseError,
    NotificationError,
    UserTimeoutError,
    AmbiguousInputError,
    UserInterruptionError,
    ConfigurationError
)


def format_date_friendly(date_obj: date) -> str:
    """
    Format date in a friendly, speakable format.
    
    Args:
        date_obj: Date to format
        
    Returns:
        Friendly date string (e.g., "tomorrow", "next Monday", "December 25th")
    """
    today = datetime.now().date()
    delta = (date_obj - today).days
    
    if delta == 0:
        return "today"
    elif delta == 1:
        return "tomorrow"
    elif delta == 2:
        return "the day after tomorrow"
    elif 3 <= delta <= 7:
        return f"this {date_obj.strftime('%A')}"
    elif 8 <= delta <= 14:
        return f"next {date_obj.strftime('%A')}"
    else:
        # Format as "December 25th"
        day = date_obj.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return date_obj.strftime(f"%B {day}{suffix}")


def format_time_friendly(time_obj: time) -> str:
    """
    Format time in a friendly, speakable format.
    
    Args:
        time_obj: Time to format
        
    Returns:
        Friendly time string (e.g., "6:30 PM", "noon", "midnight")
    """
    hour = time_obj.hour
    minute = time_obj.minute
    
    # Special cases
    if hour == 12 and minute == 0:
        return "noon"
    elif hour == 0 and minute == 0:
        return "midnight"
    
    # Standard formatting
    period = "PM" if hour >= 12 else "AM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    
    if minute == 0:
        return f"{display_hour} {period}"
    else:
        return f"{display_hour}:{minute:02d} {period}"


def format_alternatives(alternatives: List[Dict[str, Any]], max_count: int = 3) -> str:
    """
    Format alternative time slots in a speakable format.
    
    Args:
        alternatives: List of alternative time slots
        max_count: Maximum number of alternatives to mention
        
    Returns:
        Formatted alternatives string
    """
    if not alternatives:
        return ""
    
    alternatives = alternatives[:max_count]
    time_strings = []
    
    for alt in alternatives:
        if "time" in alt:
            time_obj = alt["time"]
            if isinstance(time_obj, str):
                # Parse if string
                try:
                    time_obj = datetime.strptime(time_obj, "%H:%M").time()
                except ValueError:
                    continue
            time_strings.append(format_time_friendly(time_obj))
    
    if not time_strings:
        return ""
    
    if len(time_strings) == 1:
        return f"I have availability at {time_strings[0]}."
    elif len(time_strings) == 2:
        return f"I have availability at {time_strings[0]} or {time_strings[1]}."
    else:
        return f"I have availability at {', '.join(time_strings[:-1])}, or {time_strings[-1]}."


# ============================================================================
# Business Logic Error Messages
# ============================================================================

def get_no_availability_message(error: NoAvailabilityError) -> str:
    """Generate message for no availability errors with alternatives."""
    base_msg = "I'm sorry, but we don't have any tables available"
    
    if error.requested_date and error.requested_time:
        date_str = format_date_friendly(error.requested_date)
        time_str = format_time_friendly(error.requested_time)
        base_msg = f"I'm sorry, but we don't have a table available for {error.party_size} people at {time_str} on {date_str}."
    elif error.requested_date:
        date_str = format_date_friendly(error.requested_date)
        base_msg = f"I'm sorry, but we don't have any tables available for {error.party_size} people on {date_str}."
    elif error.requested_time:
        time_str = format_time_friendly(error.requested_time)
        base_msg = f"I'm sorry, but we don't have a table available at {time_str}."
    else:
        base_msg = f"I'm sorry, but we don't have any tables available for {error.party_size} people at that time."
    
    # Add alternatives if available
    if error.alternatives:
        alternatives_msg = format_alternatives(error.alternatives)
        if alternatives_msg:
            return f"{base_msg} However, {alternatives_msg} Would any of those work for you?"
    
    return f"{base_msg} Would you like to try a different date or time?"


def get_invalid_date_message(error: InvalidDateError) -> str:
    """Generate message for invalid date errors."""
    if error.reason == "past":
        return "I'm sorry, but that date has already passed. We can only book reservations for today or future dates. What date would work for you?"
    elif error.reason == "too_far":
        return "I'm sorry, but we can only take reservations up to 30 days in advance. Could you choose a date within the next month?"
    elif error.reason == "closed":
        day_name = error.invalid_date.strftime("%A") if error.invalid_date else "that day"
        return f"I'm sorry, but we're closed on {day_name}s. Would you like to book for a different day?"
    else:
        return "I'm sorry, but that date doesn't work for us. Could you try a different date?"


def get_invalid_time_message(error: InvalidTimeError) -> str:
    """Generate message for invalid time errors."""
    if error.operating_hours:
        open_time = error.operating_hours.get("open", "")
        close_time = error.operating_hours.get("close", "")
        
        if open_time and close_time:
            try:
                open_obj = datetime.strptime(open_time, "%H:%M").time()
                close_obj = datetime.strptime(close_time, "%H:%M").time()
                open_str = format_time_friendly(open_obj)
                close_str = format_time_friendly(close_obj)
                return f"I'm sorry, but we're only open from {open_str} to {close_str}. What time would work for you within our operating hours?"
            except ValueError:
                pass
    
    return "I'm sorry, but that time is outside our operating hours. Could you choose a different time?"


def get_invalid_party_size_message(error: InvalidPartySizeError) -> str:
    """Generate message for invalid party size errors."""
    if error.party_size and error.party_size > error.max_party_size:
        return f"I'm sorry, but we can only accommodate parties of up to {error.max_party_size} people. For larger groups, please call us directly at the restaurant so we can make special arrangements."
    elif error.party_size and error.party_size < 1:
        return "I need at least one person for the reservation. How many people will be dining?"
    else:
        return "I'm sorry, but that party size doesn't work. How many people will be dining?"


def get_validation_error_message(error: BookingValidationError) -> str:
    """Generate message for general validation errors."""
    # Check for specific validation error types first
    if isinstance(error, InvalidDateError):
        return get_invalid_date_message(error)
    elif isinstance(error, InvalidTimeError):
        return get_invalid_time_message(error)
    elif isinstance(error, InvalidPartySizeError):
        return get_invalid_party_size_message(error)
    
    # Generic validation error
    field = error.validation_field
    if field:
        return f"I'm sorry, but there's an issue with the {field} you provided. Could you try again?"
    
    return "I'm sorry, but there's an issue with the information you provided. Could you clarify that for me?"


# ============================================================================
# Audio Processing Error Messages
# ============================================================================

def get_unclear_audio_message(error: UnclearAudioError) -> str:
    """Generate message for unclear audio errors."""
    return "I'm sorry, I couldn't quite hear that. Could you please repeat?"


def get_silence_detected_message(error: SilenceDetectedError) -> str:
    """Generate message for silence detection errors."""
    return "I didn't hear anything. Are you still there?"


def get_stt_error_message(error: STTError) -> str:
    """Generate message for speech-to-text errors."""
    return "I'm having trouble understanding what you said. Could you please repeat that a bit more clearly?"


def get_tts_error_message(error: TTSError) -> str:
    """Generate message for text-to-speech errors."""
    # This is typically not spoken (since TTS is failing)
    # But we log it and may try fallback TTS
    logger.error(f"TTS error: {error.message}")
    return error.message


def get_audio_processing_error_message(error: AudioProcessingError) -> str:
    """Generate message for general audio processing errors."""
    if isinstance(error, UnclearAudioError):
        return get_unclear_audio_message(error)
    elif isinstance(error, SilenceDetectedError):
        return get_silence_detected_message(error)
    elif isinstance(error, STTError):
        return get_stt_error_message(error)
    elif isinstance(error, TTSError):
        return get_tts_error_message(error)
    
    return "I'm having some audio difficulties. Let me try that again."


# ============================================================================
# Technical Error Messages
# ============================================================================

def get_llm_provider_error_message(error: LLMProviderError) -> str:
    """Generate message for LLM provider errors."""
    if error.error_type == "timeout":
        return "I'm sorry, I'm experiencing a slight delay. Please give me just a moment."
    elif error.error_type == "rate_limit":
        return "I'm sorry, I'm handling a lot of requests right now. Please give me just a moment to process that."
    else:
        return "I'm having a bit of trouble processing that right now. Could you please repeat?"


def get_database_error_message(error: DatabaseError) -> str:
    """Generate message for database errors."""
    if error.error_type == "connection":
        return "I'm having trouble connecting to our reservation system right now. Please try again in a moment, or call us directly to make your reservation."
    elif error.error_type == "timeout":
        return "Our system is running a bit slow right now. Please give me just a moment."
    else:
        return "I'm experiencing a technical issue with our system. Please try again in a moment."


def get_notification_error_message(error: NotificationError) -> str:
    """Generate message for notification errors."""
    if error.notification_type == "sms":
        return "Your reservation is confirmed, but I'm having trouble sending the confirmation text. You should receive an email confirmation instead."
    elif error.notification_type == "email":
        return "Your reservation is confirmed, but I'm having trouble sending the confirmation email. You should receive a text message confirmation instead."
    else:
        return "Your reservation is confirmed, but I'm having trouble sending the confirmation. Please note your confirmation number."


# ============================================================================
# User Interaction Error Messages
# ============================================================================

def get_user_timeout_message(error: UserTimeoutError) -> str:
    """Generate message for user timeout errors."""
    if error.prompt_count == 1:
        return "Are you still there? I haven't heard from you."
    elif error.prompt_count == 2:
        return "I'm still here when you're ready. Just let me know if you'd like to continue."
    else:
        return "I haven't heard from you in a while. I'll end this call now, but feel free to call back anytime to make your reservation. Goodbye!"


def get_ambiguous_input_message(error: AmbiguousInputError) -> str:
    """Generate message for ambiguous input errors."""
    field = error.ambiguous_field
    if field == "date":
        return "I'm not sure which date you meant. Could you be more specific? For example, you can say 'tomorrow' or 'next Friday'."
    elif field == "time":
        return "I'm not sure which time you meant. Could you tell me the time you'd like, like '7 PM' or '6:30'?"
    elif field == "party_size":
        return "I'm not sure how many people will be dining. Could you tell me the number of guests?"
    else:
        return "I'm not quite sure what you meant. Could you clarify that for me?"


def get_user_interruption_message(error: UserInterruptionError) -> str:
    """Generate message for user interruption errors."""
    return "Sorry, I think we spoke at the same time. Please go ahead."


# ============================================================================
# Main Error Message Router
# ============================================================================

def get_error_message(error: Exception) -> str:
    """
    Get natural language error message for any exception.
    
    This is the main entry point for converting exceptions into speakable
    error messages for the voice interface.
    
    Args:
        error: Exception that occurred
        
    Returns:
        Natural language error message suitable for TTS output
    """
    # Handle custom booking system errors
    if isinstance(error, NoAvailabilityError):
        return get_no_availability_message(error)
    elif isinstance(error, InvalidDateError):
        return get_invalid_date_message(error)
    elif isinstance(error, InvalidTimeError):
        return get_invalid_time_message(error)
    elif isinstance(error, InvalidPartySizeError):
        return get_invalid_party_size_message(error)
    elif isinstance(error, BookingValidationError):
        return get_validation_error_message(error)
    elif isinstance(error, UnclearAudioError):
        return get_unclear_audio_message(error)
    elif isinstance(error, SilenceDetectedError):
        return get_silence_detected_message(error)
    elif isinstance(error, STTError):
        return get_stt_error_message(error)
    elif isinstance(error, TTSError):
        return get_tts_error_message(error)
    elif isinstance(error, AudioProcessingError):
        return get_audio_processing_error_message(error)
    elif isinstance(error, LLMProviderError):
        return get_llm_provider_error_message(error)
    elif isinstance(error, DatabaseError):
        return get_database_error_message(error)
    elif isinstance(error, NotificationError):
        return get_notification_error_message(error)
    elif isinstance(error, UserTimeoutError):
        return get_user_timeout_message(error)
    elif isinstance(error, AmbiguousInputError):
        return get_ambiguous_input_message(error)
    elif isinstance(error, UserInterruptionError):
        return get_user_interruption_message(error)
    elif isinstance(error, ConfigurationError):
        return error.user_message
    elif isinstance(error, BookingSystemError):
        # Generic booking system error
        return error.user_message if error.user_message else "I'm sorry, something went wrong. Could you try that again?"
    else:
        # Unknown error type
        logger.error(f"Unhandled error type: {type(error).__name__}: {str(error)}")
        return "I'm sorry, something unexpected happened. Could you try that again?"


def suggest_next_action(error: Exception) -> Optional[str]:
    """
    Suggest what the user should do next after an error.
    
    Args:
        error: Exception that occurred
        
    Returns:
        Suggestion message or None
    """
    if isinstance(error, NoAvailabilityError) and error.alternatives:
        return None  # Alternatives already included in main message
    elif isinstance(error, InvalidDateError):
        return "What date works for you?"
    elif isinstance(error, InvalidTimeError):
        return "What time would you prefer?"
    elif isinstance(error, InvalidPartySizeError):
        if error.party_size and error.party_size > error.max_party_size:
            return "For special arrangements, please call us directly."
        else:
            return "How many people will be dining?"
    elif isinstance(error, UserTimeoutError) and error.prompt_count >= 3:
        return None  # Already saying goodbye
    elif isinstance(error, DatabaseError):
        return "Please try again in a moment."
    elif isinstance(error, ConfigurationError):
        return "Please contact the restaurant directly to make your reservation."
    else:
        return None
=======
)


class ErrorMessageGenerator:
    """
    Generates natural, conversational error messages for voice output.
    
    This class provides context-aware error messages that:
    - Are friendly and professional
    - Avoid technical jargon
    - Suggest alternatives when possible
    - Maintain conversation flow
    """
    
    # Variation templates for natural speech
    GREETING_VARIATIONS = [
        "I'm sorry, but ",
        "Unfortunately, ",
        "I apologize, but ",
        "I'm afraid ",
    ]
    
    TRANSITION_PHRASES = [
        "However, ",
        "But ",
        "On the bright side, ",
        "Alternatively, ",
    ]
    
    def __init__(self, agent_name: str = "Alex"):
        """
        Initialize error message generator.
        
        Args:
            agent_name: Name of the voice agent for personalization
        """
        self.agent_name = agent_name
    
    def _add_natural_variation(self, base_message: str, add_greeting: bool = True) -> str:
        """Add natural variation to message for less robotic speech."""
        if add_greeting:
            greeting = random.choice(self.GREETING_VARIATIONS)
            return f"{greeting}{base_message}"
        return base_message
    
    # ========================================================================
    # Business Logic Error Messages
    # ========================================================================
    
    def no_availability_message(
        self,
        error: NoAvailabilityError,
        alternatives: Optional[List[Any]] = None
    ) -> str:
        """Generate message for no availability."""
        date_str = ""
        if error.date:
            date_str = error.date.strftime("%A, %B %d")
        
        time_str = ""
        if error.time:
            time_str = f" at {error.time.strftime('%I:%M %p').lstrip('0')}"
        
        party_str = ""
        if error.party_size:
            party_str = f" for {error.party_size} {'person' if error.party_size == 1 else 'people'}"
        
        base_message = f"we don't have availability{time_str}{party_str}"
        if date_str:
            base_message += f" on {date_str}"
        base_message += "."
        
        # Add alternatives if available
        if alternatives and len(alternatives) > 0:
            transition = random.choice(self.TRANSITION_PHRASES)
            alt_list = self._format_time_alternatives(alternatives[:3])
            base_message += f" {transition}I do have openings at {alt_list}. Would any of those work for you?"
        else:
            base_message += " Would you like to try a different date or time?"
        
        return self._add_natural_variation(base_message)
    
    def invalid_date_message(self, error: InvalidDateError) -> str:
        """Generate message for invalid date."""
        if error.reason == "past":
            return self._add_natural_variation(
                "that date has already passed. Could you choose a date in the future?"
            )
        elif error.reason == "too_far":
            return self._add_natural_variation(
                "that date is beyond our booking window. We can take reservations up to 30 days in advance. "
                "Would you like to choose a date within the next month?"
            )
        elif error.reason == "closed":
            day_name = error.date.strftime("%A") if error.date else "that day"
            return self._add_natural_variation(
                f"we're closed on {day_name}s. Could you choose another day?"
            )
        else:
            return self._add_natural_variation(
                "I didn't catch that date correctly. Could you tell me the date again?"
            )
    
    def invalid_time_message(self, error: InvalidTimeError) -> str:
        """Generate message for invalid time."""
        if error.operating_hours:
            open_time, close_time = error.operating_hours
            hours_str = f"{open_time.strftime('%I:%M %p').lstrip('0')} to {close_time.strftime('%I:%M %p').lstrip('0')}"
            return self._add_natural_variation(
                f"that time is outside our operating hours. We're open from {hours_str}. "
                "What time would work for you within those hours?"
            )
        else:
            return self._add_natural_variation(
                "that time doesn't work with our schedule. Could you choose a different time?"
            )
    
    def party_too_large_message(self, error: PartySizeTooLargeError) -> str:
        """Generate message for party size too large."""
        party_size = error.party_size or "that many"
        max_size = error.max_party_size
        
        return self._add_natural_variation(
            f"our maximum party size is {max_size} people, and you mentioned {party_size}. "
            f"For larger parties, I'd recommend calling us directly at the restaurant so we can make special arrangements for you. "
            f"Would you like to book for {max_size} people instead, or shall I give you our phone number?"
        )
    
    # ========================================================================
    # Technical Error Messages
    # ========================================================================
    
    def audio_processing_message(self, error: AudioProcessingError) -> str:
        """Generate message for audio processing errors."""
        if error.audio_type == "recording":
            return self._add_natural_variation(
                "I'm having trouble with my microphone. Could you repeat that?"
            )
        elif error.audio_type == "playback":
            return self._add_natural_variation(
                "I'm having a technical issue with the speaker. Let me try again."
            )
        else:
            return self._add_natural_variation(
                "I'm having an audio issue. Could you say that again?"
            )
    
    def transcription_message(self, error: TranscriptionError) -> str:
        """Generate message for transcription errors."""
        if error.reason == "unclear_audio":
            return self._add_natural_variation(
                "I didn't catch that clearly. Could you repeat that a bit louder or more slowly?"
            )
        elif error.reason == "silence":
            return "I didn't hear anything. Are you still there?"
        else:
            return self._add_natural_variation(
                "I'm having trouble understanding. Could you say that again?"
            )
    
    def tts_message(self, error: TextToSpeechError) -> str:
        """Generate message for TTS errors (usually not spoken, but logged)."""
        # This is primarily for logging as TTS errors prevent speaking
        return f"Text-to-speech error with {error.provider}: {error.message}"
    
    def llm_provider_message(self, error: LLMProviderError) -> str:
        """Generate message for LLM provider errors."""
        if error.llm_error_type == "rate_limit":
            return self._add_natural_variation(
                "I'm experiencing high demand right now. Let me try that again in just a moment."
            )
        elif error.llm_error_type == "timeout":
            return self._add_natural_variation(
                "that's taking longer than expected. Let me try again."
            )
        else:
            return self._add_natural_variation(
                "I'm having a momentary technical issue. Could you repeat that?"
            )
    
    def database_message(self, error: DatabaseError) -> str:
        """Generate message for database errors."""
        if error.operation == "connection":
            return self._add_natural_variation(
                "I'm having trouble accessing our booking system. Could you try again in a moment?"
            )
        else:
            return self._add_natural_variation(
                "I'm experiencing a technical issue with our booking system. Let me try that again."
            )
    
    def notification_message(self, error: NotificationError) -> str:
        """Generate message for notification errors."""
        if error.notification_type == "sms":
            return "I wasn't able to send a text confirmation, but your booking is confirmed. " \
                   "You should receive an email confirmation shortly."
        elif error.notification_type == "email":
            return "I wasn't able to send an email confirmation, but your booking is confirmed. " \
                   "You should receive a text message shortly."
        else:
            return "I had trouble sending the confirmation, but your booking is confirmed. " \
                   "Please check your phone or email for confirmation."
    
    # ========================================================================
    # User Interaction Error Messages
    # ========================================================================
    
    def user_timeout_message(self, error: UserTimeoutError) -> str:
        """Generate message for user timeout."""
        if error.retry_count == 0:
            return "I didn't hear anything. Are you still there?"
        elif error.retry_count < error.max_retries:
            return "Hello? I'm still here if you'd like to continue with your reservation."
        else:
            return "I haven't heard from you, so I'll end this call. Feel free to call back anytime to make a reservation. Thank you!"
    
    def ambiguous_input_message(self, error: AmbiguousInputError) -> str:
        """Generate message for ambiguous input."""
        field_name = error.field or "information"
        
        if error.possible_interpretations and len(error.possible_interpretations) > 1:
            options = " or ".join(error.possible_interpretations)
            return f"Just to clarify, did you mean {options}?"
        else:
            return f"I'm not quite sure I understood the {field_name}. Could you say that again more clearly?"
    
    def interruption_message(self) -> str:
        """Generate message for interruption handling."""
        return "Oh, sorry! Go ahead."
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _format_time_alternatives(self, times: List[Any]) -> str:
        """Format list of time slots for natural speech."""
        formatted = []
        for t in times:
            if isinstance(t, time):
                formatted.append(t.strftime('%I:%M %p').lstrip('0'))
            elif isinstance(t, dict) and 'time' in t:
                formatted.append(t['time'].strftime('%I:%M %p').lstrip('0'))
            elif hasattr(t, 'time'):
                formatted.append(t.time.strftime('%I:%M %p').lstrip('0'))
            else:
                formatted.append(str(t))
        
        if len(formatted) == 1:
            return formatted[0]
        elif len(formatted) == 2:
            return f"{formatted[0]} or {formatted[1]}"
        else:
            return f"{', '.join(formatted[:-1])}, or {formatted[-1]}"
    
    def generate_message(self, error: Exception, **kwargs) -> str:
        """
        Generate appropriate error message for any error type.
        
        Args:
            error: Exception instance
            **kwargs: Additional context for message generation
            
        Returns:
            Natural language error message suitable for voice output
        """
        # Handle specific error types
        if isinstance(error, NoAvailabilityError):
            alternatives = kwargs.get('alternatives', error.available_alternatives)
            return self.no_availability_message(error, alternatives)
        
        elif isinstance(error, InvalidDateError):
            return self.invalid_date_message(error)
        
        elif isinstance(error, InvalidTimeError):
            return self.invalid_time_message(error)
        
        elif isinstance(error, PartySizeTooLargeError):
            return self.party_too_large_message(error)
        
        elif isinstance(error, TranscriptionError):
            return self.transcription_message(error)
        
        elif isinstance(error, AudioProcessingError):
            return self.audio_processing_message(error)
        
        elif isinstance(error, TextToSpeechError):
            return self.tts_message(error)
        
        elif isinstance(error, LLMProviderError):
            return self.llm_provider_message(error)
        
        elif isinstance(error, DatabaseError):
            return self.database_message(error)
        
        elif isinstance(error, NotificationError):
            return self.notification_message(error)
        
        elif isinstance(error, UserTimeoutError):
            return self.user_timeout_message(error)
        
        elif isinstance(error, AmbiguousInputError):
            return self.ambiguous_input_message(error)
        
        elif isinstance(error, BookingAgentError):
            # Generic booking agent error
            return error.user_message
        
        else:
            # Unknown error type
            return self._add_natural_variation(
                "I'm experiencing a technical issue. Could you try that again?"
            )


# ============================================================================
# Convenience Functions
# ============================================================================

# Global message generator instance
_message_generator = ErrorMessageGenerator()


def get_error_message(error: Exception, **kwargs) -> str:
    """
    Get user-friendly error message for any error.
    
    Args:
        error: Exception instance
        **kwargs: Additional context for message generation
        
    Returns:
        Natural language error message
        
    Examples:
        >>> error = InvalidDateError("Date in past", date=date(2020, 1, 1), reason="past")
        >>> message = get_error_message(error)
        >>> print(message)
        "I'm sorry, but that date has already passed. Could you choose a date in the future?"
    """
    return _message_generator.generate_message(error, **kwargs)


def get_alternative_suggestions(
    error: NoAvailabilityError,
    booking_service: Any = None
) -> List[Any]:
    """
    Get alternative time slot suggestions when availability is lacking.
    
    Args:
        error: NoAvailabilityError with context
        booking_service: Optional BookingService instance to query alternatives
        
    Returns:
        List of alternative time slots
    """
    alternatives = error.available_alternatives
    
    # If booking service provided and no alternatives in error, try to fetch them
    if not alternatives and booking_service and error.date and error.party_size:
        try:
            # Try same date, different times
            all_slots = booking_service.get_available_slots(error.date, error.party_size)
            alternatives = all_slots[:5]  # Return up to 5 alternatives
            
            # If no slots on same date, try next day
            if not alternatives:
                next_date = error.date + timedelta(days=1)
                all_slots = booking_service.get_available_slots(next_date, error.party_size)
                alternatives = all_slots[:3]
        except Exception:
            # If fetching alternatives fails, return empty list
            alternatives = []
    
    return alternatives or [] 
