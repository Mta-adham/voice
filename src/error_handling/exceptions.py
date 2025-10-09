"""
Custom Exception Classes for Restaurant Booking Voice Agent.

This module defines exception classes for different error categories:
- Business Logic Errors (booking validation)
- Technical Errors (STT/TTS, LLM, database)
- User Interaction Errors (timeouts, ambiguous input)

Each exception includes context for error recovery and logging.
"""

from typing import Optional, Any, Dict
from datetime import date, time


class BookingSystemError(Exception):
    """Base exception for all booking system errors."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        """
        Initialize booking system error.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly message for voice response
            context: Additional context for error recovery
            recoverable: Whether the error is recoverable
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.context = context or {}
        self.recoverable = recoverable


# ============================================================================
# Business Logic Errors
# ============================================================================

class BookingValidationError(BookingSystemError):
    """
    Raised when booking validation fails.
    
    Examples:
    - Invalid dates (past dates, beyond booking window)
    - Party size exceeds maximum
    - Invalid time slot (outside operating hours)
    - No availability for requested date/time/party_size
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        alternatives: Optional[list] = None,
        **kwargs
    ):
        """
        Initialize booking validation error.
        
        Args:
            message: Technical error message
            user_message: User-friendly message
            field: Field that failed validation (date, time, party_size)
            value: Invalid value
            alternatives: List of alternative valid options
            **kwargs: Additional context
        """
        context = {
            "field": field,
            "value": value,
            "alternatives": alternatives or [],
            **kwargs
        }
        super().__init__(message, user_message, context, recoverable=True)
        self.field = field
        self.value = value
        self.alternatives = alternatives or []


class NoAvailabilityError(BookingValidationError):
    """Raised when no availability exists for the requested slot."""
    
    def __init__(
        self,
        date: date,
        time: Optional[time] = None,
        party_size: Optional[int] = None,
        alternative_slots: Optional[list] = None,
        **kwargs
    ):
        """
        Initialize no availability error.
        
        Args:
            date: Requested date
            time: Requested time (if specified)
            party_size: Requested party size
            alternative_slots: List of alternative available slots
            **kwargs: Additional context
        """
        message = f"No availability for date={date}, time={time}, party_size={party_size}"
        context = {
            "date": date,
            "time": time,
            "party_size": party_size,
            "alternative_slots": alternative_slots or [],
            **kwargs
        }
        super().__init__(
            message=message,
            field="availability",
            alternatives=alternative_slots,
            **context
        )


class InvalidDateError(BookingValidationError):
    """Raised when date is invalid (past date or beyond booking window)."""
    
    def __init__(self, date: date, reason: str, **kwargs):
        message = f"Invalid date {date}: {reason}"
        super().__init__(
            message=message,
            field="date",
            value=date,
            **kwargs
        )


class InvalidTimeError(BookingValidationError):
    """Raised when time is outside operating hours."""
    
    def __init__(
        self,
        time: time,
        operating_hours: Optional[tuple] = None,
        **kwargs
    ):
        message = f"Invalid time {time}"
        if operating_hours:
            message += f". Operating hours: {operating_hours[0]} - {operating_hours[1]}"
        super().__init__(
            message=message,
            field="time",
            value=time,
            operating_hours=operating_hours,
            **kwargs
        )


class InvalidPartySizeError(BookingValidationError):
    """Raised when party size is invalid or exceeds maximum."""
    
    def __init__(self, party_size: int, max_size: int = 8, **kwargs):
        message = f"Invalid party size {party_size}. Maximum is {max_size}."
        super().__init__(
            message=message,
            field="party_size",
            value=party_size,
            max_size=max_size,
            **kwargs
        )


# ============================================================================
# Technical Errors - Audio Processing
# ============================================================================

class AudioProcessingError(BookingSystemError):
    """
    Raised when audio processing fails.
    
    Examples:
    - Microphone not accessible
    - Recording failure
    - Playback failure
    - Audio device errors
    """
    
    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        """
        Initialize audio processing error.
        
        Args:
            message: Error message
            error_type: Type of audio error (device, recording, playback)
            original_error: Original exception if any
            **kwargs: Additional context
        """
        context = {
            "error_type": error_type,
            "original_error": str(original_error) if original_error else None,
            **kwargs
        }
        super().__init__(message, context=context, recoverable=True)
        self.error_type = error_type
        self.original_error = original_error


class STTError(AudioProcessingError):
    """
    Raised when Speech-to-Text fails.
    
    Examples:
    - Unclear audio
    - Failed transcription
    - Whisper API errors
    """
    
    def __init__(
        self,
        message: str,
        audio_quality: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_type="stt",
            audio_quality=audio_quality,
            **kwargs
        )


class TTSError(AudioProcessingError):
    """
    Raised when Text-to-Speech fails.
    
    Examples:
    - ElevenLabs API failure
    - Rate limit exceeded
    - Audio generation error
    """
    
    def __init__(
        self,
        message: str,
        provider: str = "elevenlabs",
        **kwargs
    ):
        super().__init__(
            message=message,
            error_type="tts",
            provider=provider,
            **kwargs
        )


# ============================================================================
# Technical Errors - LLM Provider
# ============================================================================

class LLMProviderError(BookingSystemError):
    """
    Raised when LLM provider fails.
    
    Examples:
    - OpenAI, Gemini, Claude timeouts
    - Rate limits
    - Authentication errors
    - API connection failures
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        error_type: str = "unknown",
        original_error: Optional[Exception] = None,
        retry_possible: bool = True,
        **kwargs
    ):
        """
        Initialize LLM provider error.
        
        Args:
            message: Error message
            provider: LLM provider name (openai, gemini, claude)
            error_type: Type of error (timeout, rate_limit, auth, connection)
            original_error: Original exception
            retry_possible: Whether retry is possible
            **kwargs: Additional context
        """
        context = {
            "provider": provider,
            "error_type": error_type,
            "original_error": str(original_error) if original_error else None,
            "retry_possible": retry_possible,
            **kwargs
        }
        super().__init__(message, context=context, recoverable=retry_possible)
        self.provider = provider
        self.error_type = error_type
        self.original_error = original_error
        self.retry_possible = retry_possible


class LLMTimeoutError(LLMProviderError):
    """Raised when LLM provider times out."""
    
    def __init__(self, provider: str, **kwargs):
        super().__init__(
            message=f"{provider} API timeout",
            provider=provider,
            error_type="timeout",
            retry_possible=True,
            **kwargs
        )


class LLMRateLimitError(LLMProviderError):
    """Raised when LLM provider rate limit is exceeded."""
    
    def __init__(self, provider: str, **kwargs):
        super().__init__(
            message=f"{provider} rate limit exceeded",
            provider=provider,
            error_type="rate_limit",
            retry_possible=True,
            **kwargs
        )


class LLMAuthenticationError(LLMProviderError):
    """Raised when LLM provider authentication fails."""
    
    def __init__(self, provider: str, **kwargs):
        super().__init__(
            message=f"{provider} authentication failed",
            provider=provider,
            error_type="authentication",
            retry_possible=False,
            **kwargs
        )


# ============================================================================
# Technical Errors - Database
# ============================================================================

class DatabaseError(BookingSystemError):
    """
    Raised when database operations fail.
    
    Examples:
    - Connection errors
    - Query failures
    - Transaction errors
    - Constraint violations
    """
    
    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        original_error: Optional[Exception] = None,
        retry_possible: bool = True,
        **kwargs
    ):
        """
        Initialize database error.
        
        Args:
            message: Error message
            error_type: Type of error (connection, query, constraint)
            original_error: Original exception
            retry_possible: Whether retry is possible
            **kwargs: Additional context
        """
        context = {
            "error_type": error_type,
            "original_error": str(original_error) if original_error else None,
            "retry_possible": retry_possible,
            **kwargs
        }
        super().__init__(message, context=context, recoverable=retry_possible)
        self.error_type = error_type
        self.original_error = original_error
        self.retry_possible = retry_possible


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    
    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(
            message=message,
            error_type="connection",
            retry_possible=True,
            **kwargs
        )


class DatabaseQueryError(DatabaseError):
    """Raised when database query fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_type="query",
            retry_possible=True,
            **kwargs
        )


# ============================================================================
# Technical Errors - Notifications
# ============================================================================

class NotificationError(BookingSystemError):
    """
    Raised when notification delivery fails.
    
    Examples:
    - SMS delivery failure (Twilio)
    - Email delivery failure (SendGrid)
    """
    
    def __init__(
        self,
        message: str,
        notification_type: str,
        recipient: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        """
        Initialize notification error.
        
        Args:
            message: Error message
            notification_type: Type of notification (sms, email)
            recipient: Recipient address/phone
            original_error: Original exception
            **kwargs: Additional context
        """
        context = {
            "notification_type": notification_type,
            "recipient": recipient,
            "original_error": str(original_error) if original_error else None,
            **kwargs
        }
        # Notifications are non-critical - booking should continue
        super().__init__(message, context=context, recoverable=True)
        self.notification_type = notification_type
        self.recipient = recipient
        self.original_error = original_error


class SMSDeliveryError(NotificationError):
    """Raised when SMS delivery fails."""
    
    def __init__(self, phone: str, **kwargs):
        super().__init__(
            message=f"Failed to send SMS to {phone}",
            notification_type="sms",
            recipient=phone,
            **kwargs
        )


class EmailDeliveryError(NotificationError):
    """Raised when email delivery fails."""
    
    def __init__(self, email: str, **kwargs):
        super().__init__(
            message=f"Failed to send email to {email}",
            notification_type="email",
            recipient=email,
            **kwargs
        )


# ============================================================================
# User Interaction Errors
# ============================================================================

class UserTimeoutError(BookingSystemError):
    """
    Raised when user doesn't respond within timeout period.
    
    Examples:
    - No response after prompt
    - Extended silence during conversation
    """
    
    def __init__(
        self,
        timeout_seconds: int,
        prompt: Optional[str] = None,
        retry_count: int = 0,
        **kwargs
    ):
        """
        Initialize user timeout error.
        
        Args:
            timeout_seconds: Timeout duration in seconds
            prompt: Last prompt that timed out
            retry_count: Number of retry attempts made
            **kwargs: Additional context
        """
        message = f"User timeout after {timeout_seconds} seconds"
        context = {
            "timeout_seconds": timeout_seconds,
            "prompt": prompt,
            "retry_count": retry_count,
            **kwargs
        }
        super().__init__(message, context=context, recoverable=True)
        self.timeout_seconds = timeout_seconds
        self.prompt = prompt
        self.retry_count = retry_count


class AmbiguousInputError(BookingSystemError):
    """Raised when user input is ambiguous or incomplete."""
    
    def __init__(
        self,
        user_input: str,
        missing_fields: Optional[list] = None,
        **kwargs
    ):
        """
        Initialize ambiguous input error.
        
        Args:
            user_input: User's unclear input
            missing_fields: Fields that couldn't be extracted
            **kwargs: Additional context
        """
        message = f"Ambiguous input: {user_input}"
        context = {
            "user_input": user_input,
            "missing_fields": missing_fields or [],
            **kwargs
        }
        super().__init__(message, context=context, recoverable=True)
        self.user_input = user_input
        self.missing_fields = missing_fields or []


class UserCorrectionError(BookingSystemError):
    """Raised when user wants to correct previously provided information."""
    
    def __init__(
        self,
        field: str,
        old_value: Any,
        new_value: Any,
        **kwargs
    ):
        """
        Initialize user correction error.
        
        Args:
            field: Field being corrected
            old_value: Previous value
            new_value: New value
            **kwargs: Additional context
        """
        message = f"User correction: {field} from {old_value} to {new_value}"
        context = {
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            **kwargs
        }
        super().__init__(message, context=context, recoverable=True)
        self.field = field
        self.old_value = old_value
        self.new_value = new_value


# ============================================================================
# System Errors
# ============================================================================

class SystemError(BookingSystemError):
    """
    Raised for general system errors.
    
    Used for unexpected errors that don't fit other categories.
    """
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        """
        Initialize system error.
        
        Args:
            message: Error message
            original_error: Original exception
            **kwargs: Additional context
        """
        context = {
            "original_error": str(original_error) if original_error else None,
            **kwargs
        }
        super().__init__(message, context=context, recoverable=False)
        self.original_error = original_error
