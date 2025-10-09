"""
Custom exception classes for restaurant booking system error handling.

This module defines a comprehensive hierarchy of exceptions for different
error categories that can occur during the booking conversation flow.
"""
from typing import Optional, Dict, Any, List
from datetime import date, time


# ============================================================================
# Base Exception
# ============================================================================

class BookingSystemError(Exception):
    """
    Base exception for all booking system errors.
    
    Attributes:
        message: Human-readable error message
        user_message: Natural language message suitable for voice output
        context: Additional context information for debugging
        recoverable: Whether the error is recoverable
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        self.message = message
        self.user_message = user_message or message
        self.context = context or {}
        self.recoverable = recoverable
        super().__init__(message)


# ============================================================================
# Business Logic Errors
# ============================================================================

class BookingValidationError(BookingSystemError):
    """
    Exception for booking validation failures.
    
    Raised when booking request violates business rules such as:
    - Past dates
    - Dates beyond booking window
    - Party size exceeds maximum
    - Invalid time slots
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        validation_field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.validation_field = validation_field
        super().__init__(
            message=message,
            user_message=user_message,
            context=context,
            recoverable=True
        )


class NoAvailabilityError(BookingSystemError):
    """
    Exception when no availability exists for requested date/time/party_size.
    
    Should include alternative time slots when possible.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        requested_date: Optional[date] = None,
        requested_time: Optional[time] = None,
        party_size: Optional[int] = None,
        alternatives: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.requested_date = requested_date
        self.requested_time = requested_time
        self.party_size = party_size
        self.alternatives = alternatives or []
        
        ctx = context or {}
        ctx.update({
            "requested_date": str(requested_date) if requested_date else None,
            "requested_time": str(requested_time) if requested_time else None,
            "party_size": party_size,
            "alternatives_count": len(self.alternatives)
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            context=ctx,
            recoverable=True
        )


class InvalidDateError(BookingValidationError):
    """Exception for invalid dates (past dates, beyond booking window)."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        invalid_date: Optional[date] = None,
        reason: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.invalid_date = invalid_date
        self.reason = reason
        
        ctx = context or {}
        ctx.update({
            "invalid_date": str(invalid_date) if invalid_date else None,
            "reason": reason
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            validation_field="date",
            context=ctx
        )


class InvalidTimeError(BookingValidationError):
    """Exception for invalid time slots (outside operating hours)."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        invalid_time: Optional[time] = None,
        operating_hours: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.invalid_time = invalid_time
        self.operating_hours = operating_hours
        
        ctx = context or {}
        ctx.update({
            "invalid_time": str(invalid_time) if invalid_time else None,
            "operating_hours": operating_hours
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            validation_field="time",
            context=ctx
        )


class InvalidPartySizeError(BookingValidationError):
    """Exception when party size exceeds maximum or is invalid."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        party_size: Optional[int] = None,
        max_party_size: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.party_size = party_size
        self.max_party_size = max_party_size
        
        ctx = context or {}
        ctx.update({
            "party_size": party_size,
            "max_party_size": max_party_size
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            validation_field="party_size",
            context=ctx
        )


# ============================================================================
# Technical Errors - Audio Processing
# ============================================================================

class AudioProcessingError(BookingSystemError):
    """Base exception for audio-related errors."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        audio_type: Optional[str] = None,  # "recording", "playback", "processing"
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        self.audio_type = audio_type
        ctx = context or {}
        ctx["audio_type"] = audio_type
        
        super().__init__(
            message=message,
            user_message=user_message,
            context=ctx,
            recoverable=recoverable
        )


class STTError(AudioProcessingError):
    """Exception for Speech-to-Text (Whisper) failures."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        provider: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.provider = provider
        self.original_error = original_error
        
        ctx = context or {}
        ctx.update({
            "provider": provider,
            "original_error": str(original_error) if original_error else None
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            audio_type="stt",
            context=ctx,
            recoverable=True
        )


class TTSError(AudioProcessingError):
    """Exception for Text-to-Speech failures."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        provider: Optional[str] = None,
        original_error: Optional[Exception] = None,
        fallback_available: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        self.provider = provider
        self.original_error = original_error
        self.fallback_available = fallback_available
        
        ctx = context or {}
        ctx.update({
            "provider": provider,
            "original_error": str(original_error) if original_error else None,
            "fallback_available": fallback_available
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            audio_type="tts",
            context=ctx,
            recoverable=fallback_available
        )


class UnclearAudioError(AudioProcessingError):
    """Exception when audio is unclear or failed transcription."""
    
    def __init__(
        self,
        message: str = "Audio was unclear or could not be transcribed",
        user_message: Optional[str] = None,
        confidence_score: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.confidence_score = confidence_score
        
        ctx = context or {}
        ctx["confidence_score"] = confidence_score
        
        super().__init__(
            message=message,
            user_message=user_message or "I'm sorry, I couldn't quite hear that. Could you please repeat?",
            audio_type="transcription",
            context=ctx,
            recoverable=True
        )


class SilenceDetectedError(AudioProcessingError):
    """Exception when only silence is detected in audio."""
    
    def __init__(
        self,
        message: str = "No speech detected in audio",
        user_message: Optional[str] = None,
        duration: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.duration = duration
        
        ctx = context or {}
        ctx["silence_duration"] = duration
        
        super().__init__(
            message=message,
            user_message=user_message or "I didn't hear anything. Are you there?",
            audio_type="recording",
            context=ctx,
            recoverable=True
        )


# ============================================================================
# Technical Errors - LLM Provider
# ============================================================================

class LLMProviderError(BookingSystemError):
    """Exception for LLM API failures."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        provider: Optional[str] = None,
        error_type: Optional[str] = None,  # "timeout", "rate_limit", "authentication", "other"
        original_error: Optional[Exception] = None,
        retry_possible: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        self.provider = provider
        self.error_type = error_type
        self.original_error = original_error
        self.retry_possible = retry_possible
        
        ctx = context or {}
        ctx.update({
            "provider": provider,
            "error_type": error_type,
            "original_error": str(original_error) if original_error else None,
            "retry_possible": retry_possible
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            context=ctx,
            recoverable=retry_possible
        )


# ============================================================================
# Technical Errors - Database
# ============================================================================

class DatabaseError(BookingSystemError):
    """Exception for database connection and query failures."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        error_type: Optional[str] = None,  # "connection", "query", "constraint", "timeout"
        original_error: Optional[Exception] = None,
        retry_possible: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        self.error_type = error_type
        self.original_error = original_error
        self.retry_possible = retry_possible
        
        ctx = context or {}
        ctx.update({
            "error_type": error_type,
            "original_error": str(original_error) if original_error else None,
            "retry_possible": retry_possible
        })
        
        super().__init__(
            message=message,
            user_message=user_message or "I'm having trouble accessing our system right now. Please try again in a moment.",
            context=ctx,
            recoverable=retry_possible
        )


# ============================================================================
# Technical Errors - Notifications
# ============================================================================

class NotificationError(BookingSystemError):
    """Exception for SMS/email delivery failures."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        notification_type: Optional[str] = None,  # "sms", "email"
        recipient: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.notification_type = notification_type
        self.recipient = recipient
        self.original_error = original_error
        
        ctx = context or {}
        ctx.update({
            "notification_type": notification_type,
            "recipient": recipient,
            "original_error": str(original_error) if original_error else None
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            context=ctx,
            recoverable=True  # Notifications are non-critical
        )


# ============================================================================
# User Interaction Errors
# ============================================================================

class UserTimeoutError(BookingSystemError):
    """Exception when user doesn't respond after prompt."""
    
    def __init__(
        self,
        message: str = "User timeout - no response received",
        user_message: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        prompt_count: int = 1,
        context: Optional[Dict[str, Any]] = None
    ):
        self.timeout_seconds = timeout_seconds
        self.prompt_count = prompt_count
        
        ctx = context or {}
        ctx.update({
            "timeout_seconds": timeout_seconds,
            "prompt_count": prompt_count
        })
        
        super().__init__(
            message=message,
            user_message=user_message or "Are you still there? I haven't heard from you.",
            context=ctx,
            recoverable=True
        )


class AmbiguousInputError(BookingSystemError):
    """Exception when user input is ambiguous or incomplete."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        ambiguous_field: Optional[str] = None,
        possible_values: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.ambiguous_field = ambiguous_field
        self.possible_values = possible_values or []
        
        ctx = context or {}
        ctx.update({
            "ambiguous_field": ambiguous_field,
            "possible_values": possible_values
        })
        
        super().__init__(
            message=message,
            user_message=user_message,
            context=ctx,
            recoverable=True
        )


class UserInterruptionError(BookingSystemError):
    """Exception when user speaks while agent is speaking."""
    
    def __init__(
        self,
        message: str = "User interruption detected",
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            user_message=user_message or "Sorry, I think we spoke at the same time. Please go ahead.",
            context=context,
            recoverable=True
        )


# ============================================================================
# System Errors
# ============================================================================

class ConfigurationError(BookingSystemError):
    """Exception for system configuration errors."""
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.config_key = config_key
        
        ctx = context or {}
        ctx["config_key"] = config_key
        
        super().__init__(
            message=message,
            user_message=user_message or "I'm experiencing a technical issue. Please contact the restaurant directly.",
            context=ctx,
            recoverable=False
        )
