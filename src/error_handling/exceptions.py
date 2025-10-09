"""
Custom exception classes for restaurant booking voice agent.

This module defines exception hierarchies for different error categories:
- Business logic errors (booking validation, availability, etc.)
- Technical errors (audio, STT/TTS, LLM, database)
- User interaction errors (timeout, ambiguity, interruptions)

All exceptions include context information for better error handling and logging.
"""

from typing import Optional, Dict, Any
from datetime import date, time


# ============================================================================
# Base Exception
# ============================================================================

class BookingAgentError(Exception):
    """Base exception for all booking agent errors."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        """
        Initialize booking agent error.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly message for voice output (if None, uses message)
            context: Additional context information
            recoverable: Whether the error is recoverable (conversation can continue)
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.context = context or {}
        self.recoverable = recoverable


# ============================================================================
# Business Logic Errors
# ============================================================================

class BookingValidationError(BookingAgentError):
    """
    Exception raised when booking validation fails.
    
    This includes general validation errors for bookings that don't fit
    other specific categories.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "field": field,
            "value": value,
            "error_type": "validation"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.field = field
        self.value = value


class NoAvailabilityError(BookingAgentError):
    """Exception raised when no availability exists for the requested date/time/party_size."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        date: Optional[date] = None,
        time: Optional[time] = None,
        party_size: Optional[int] = None,
        available_alternatives: Optional[list] = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "date": str(date) if date else None,
            "time": str(time) if time else None,
            "party_size": party_size,
            "available_alternatives": available_alternatives,
            "error_type": "no_availability"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.date = date
        self.time = time
        self.party_size = party_size
        self.available_alternatives = available_alternatives or []


class InvalidDateError(BookingAgentError):
    """Exception raised when date is invalid (past date or beyond booking window)."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        date: Optional[date] = None,
        reason: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "date": str(date) if date else None,
            "reason": reason,
            "error_type": "invalid_date"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.date = date
        self.reason = reason


class InvalidTimeError(BookingAgentError):
    """Exception raised when time is outside operating hours."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        time: Optional[time] = None,
        operating_hours: Optional[tuple] = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "time": str(time) if time else None,
            "operating_hours": operating_hours,
            "error_type": "invalid_time"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.time = time
        self.operating_hours = operating_hours


class PartySizeTooLargeError(BookingAgentError):
    """Exception raised when party size exceeds maximum allowed."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        party_size: Optional[int] = None,
        max_party_size: int = 8,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "party_size": party_size,
            "max_party_size": max_party_size,
            "error_type": "party_too_large"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.party_size = party_size
        self.max_party_size = max_party_size


# ============================================================================
# Technical Errors - Audio Processing
# ============================================================================

class AudioProcessingError(BookingAgentError):
    """Base exception for audio processing errors."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        audio_type: Optional[str] = None,  # "recording", "playback", "device"
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "audio_type": audio_type,
            "original_error": str(original_error) if original_error else None,
            "error_type": "audio_processing"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.audio_type = audio_type
        self.original_error = original_error


class TranscriptionError(AudioProcessingError):
    """Exception raised when speech-to-text transcription fails."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        reason: Optional[str] = None,  # "unclear_audio", "api_failure", "silence"
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "reason": reason,
            "error_type": "transcription"
        })
        kwargs["audio_type"] = "transcription"
        super().__init__(message, user_message, **kwargs, context=context)
        self.reason = reason


class TextToSpeechError(AudioProcessingError):
    """Exception raised when text-to-speech generation fails."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        provider: Optional[str] = None,  # "elevenlabs", "pyttsx3", "gtts"
        can_fallback: bool = True,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "provider": provider,
            "can_fallback": can_fallback,
            "error_type": "tts"
        })
        kwargs["audio_type"] = "tts"
        super().__init__(message, user_message, **kwargs, context=context)
        self.provider = provider
        self.can_fallback = can_fallback


# ============================================================================
# Technical Errors - LLM
# ============================================================================

class LLMProviderError(BookingAgentError):
    """Exception raised when LLM provider fails."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        provider: Optional[str] = None,  # "openai", "gemini", "claude"
        error_type: Optional[str] = None,  # "rate_limit", "timeout", "auth", "api_error"
        can_retry: bool = True,
        can_fallback: bool = True,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "provider": provider,
            "llm_error_type": error_type,
            "can_retry": can_retry,
            "can_fallback": can_fallback,
            "original_error": str(original_error) if original_error else None,
            "error_type": "llm_provider"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.provider = provider
        self.llm_error_type = error_type
        self.can_retry = can_retry
        self.can_fallback = can_fallback
        self.original_error = original_error


# ============================================================================
# Technical Errors - Database
# ============================================================================

class DatabaseError(BookingAgentError):
    """Exception raised when database operations fail."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        operation: Optional[str] = None,  # "query", "insert", "update", "connection"
        can_retry: bool = True,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "operation": operation,
            "can_retry": can_retry,
            "original_error": str(original_error) if original_error else None,
            "error_type": "database"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.operation = operation
        self.can_retry = can_retry
        self.original_error = original_error


# ============================================================================
# Technical Errors - Notifications
# ============================================================================

class NotificationError(BookingAgentError):
    """Exception raised when SMS/email notifications fail."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        notification_type: Optional[str] = None,  # "sms", "email"
        provider: Optional[str] = None,  # "twilio", "sendgrid"
        blocking: bool = False,  # Whether this should block the booking flow
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "notification_type": notification_type,
            "provider": provider,
            "blocking": blocking,
            "error_type": "notification"
        })
        super().__init__(message, user_message, context, recoverable=True, **kwargs)
        self.notification_type = notification_type
        self.provider = provider
        self.blocking = blocking


# ============================================================================
# User Interaction Errors
# ============================================================================

class UserTimeoutError(BookingAgentError):
    """Exception raised when user doesn't respond within timeout period."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        retry_count: int = 0,
        max_retries: int = 2,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "timeout_seconds": timeout_seconds,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "error_type": "user_timeout"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.max_retries = max_retries


class AmbiguousInputError(BookingAgentError):
    """Exception raised when user input is ambiguous or incomplete."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        field: Optional[str] = None,
        possible_interpretations: Optional[list] = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "field": field,
            "possible_interpretations": possible_interpretations,
            "error_type": "ambiguous_input"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.field = field
        self.possible_interpretations = possible_interpretations or []


class InterruptionError(BookingAgentError):
    """Exception raised when user speaks while agent is speaking."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        agent_was_saying: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.pop("context", {})
        context.update({
            "agent_was_saying": agent_was_saying,
            "error_type": "interruption"
        })
        super().__init__(message, user_message, context, **kwargs)
        self.agent_was_saying = agent_was_saying
