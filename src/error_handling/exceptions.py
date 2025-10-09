"""
Custom exception classes for restaurant booking system error handling.

This module provides a comprehensive exception hierarchy for handling various
error scenarios including business logic errors, technical errors, and user
interaction errors.
"""
from typing import Optional, Any, Dict


# ============================================================================
# Base Exception Classes
# ============================================================================

class BookingSystemError(Exception):
    """
    Base exception class for all booking system errors.
    
    Attributes:
        message: Human-readable error message
        user_message: User-friendly message suitable for TTS
        context: Additional context information for logging
        recoverable: Whether the error is recoverable
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.context = context or {}
        self.recoverable = recoverable
    
    def __str__(self) -> str:
        return self.message


# ============================================================================
# Business Logic Errors
# ============================================================================

class BookingValidationError(BookingSystemError):
    """
    Exception raised when booking validation fails.
    
    Used for:
    - Invalid dates (past dates, dates beyond booking window)
    - Invalid party sizes (> max_party_size or < 1)
    - Invalid time slots (outside operating hours)
    - Invalid data formats
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)
        self.field = field
        self.value = value


class NoAvailabilityError(BookingSystemError):
    """
    Exception raised when there is no availability for requested date/time/party_size.
    
    This error should include alternative suggestions when possible.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        requested_date: Optional[str] = None,
        requested_time: Optional[str] = None,
        party_size: Optional[int] = None,
        alternatives: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)
        self.requested_date = requested_date
        self.requested_time = requested_time
        self.party_size = party_size
        self.alternatives = alternatives or []


class CapacityExceededError(BookingSystemError):
    """
    Exception raised when requested party size exceeds available capacity.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        requested_size: Optional[int] = None,
        available_capacity: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)
        self.requested_size = requested_size
        self.available_capacity = available_capacity


# ============================================================================
# Technical Errors - Audio Processing
# ============================================================================

class AudioProcessingError(BookingSystemError):
    """
    Base exception for audio processing errors.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        super().__init__(message, user_message, context, recoverable)


class AudioDeviceError(AudioProcessingError):
    """
    Exception raised when audio device is not available or lacks permissions.
    """
    pass


class AudioRecordingError(AudioProcessingError):
    """
    Exception raised when audio recording fails.
    """
    pass


class AudioPlaybackError(AudioProcessingError):
    """
    Exception raised when audio playback fails.
    """
    pass


class SilenceDetectedError(AudioProcessingError):
    """
    Exception raised when only silence is detected in audio input.
    """
    
    def __init__(
        self,
        message: str = "No speech detected",
        user_message: str = "I didn't hear anything. Could you please repeat that?",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)


class UnclearAudioError(AudioProcessingError):
    """
    Exception raised when audio quality is too poor for transcription.
    """
    
    def __init__(
        self,
        message: str = "Audio quality too poor",
        user_message: str = "I'm sorry, I had trouble hearing that. Could you please speak a bit louder and clearer?",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)


# ============================================================================
# Technical Errors - Speech Services (STT/TTS)
# ============================================================================

class SpeechServiceError(BookingSystemError):
    """
    Base exception for speech service errors (STT/TTS).
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        service: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        super().__init__(message, user_message, context, recoverable)
        self.service = service


class STTError(SpeechServiceError):
    """
    Exception raised when Speech-to-Text (Whisper) fails.
    """
    
    def __init__(
        self,
        message: str,
        user_message: str = "I'm having trouble understanding. Let me try again.",
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, user_message, service="whisper", context=context, recoverable=True)
        self.original_error = original_error


class TTSError(SpeechServiceError):
    """
    Exception raised when Text-to-Speech fails.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        service: Optional[str] = "elevenlabs",
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        use_fallback: bool = True
    ):
        super().__init__(message, user_message, service=service, context=context, recoverable=use_fallback)
        self.original_error = original_error
        self.use_fallback = use_fallback


class APIKeyError(SpeechServiceError):
    """
    Exception raised when API key is invalid or missing.
    """
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            user_message="I'm experiencing technical difficulties. Please try again later.",
            service=service,
            context=context,
            recoverable=False
        )


class QuotaExceededError(SpeechServiceError):
    """
    Exception raised when API quota is exceeded.
    """
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            user_message="I'm experiencing technical difficulties due to high demand. Please try again later.",
            service=service,
            context=context,
            recoverable=False
        )


class RateLimitError(SpeechServiceError):
    """
    Exception raised when API rate limit is hit.
    """
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            user_message="I need to slow down for a moment. Please hold on.",
            service=service,
            context=context,
            recoverable=True
        )
        self.retry_after = retry_after


# ============================================================================
# Technical Errors - LLM Provider
# ============================================================================

class LLMProviderError(BookingSystemError):
    """
    Exception raised when LLM provider fails.
    """
    
    def __init__(
        self,
        message: str,
        user_message: str = "I'm having trouble processing that. Let me try again.",
        provider: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        super().__init__(message, user_message, context, recoverable)
        self.provider = provider
        self.original_error = original_error


class LLMTimeoutError(LLMProviderError):
    """
    Exception raised when LLM request times out.
    """
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            user_message="I'm taking a bit longer than expected. Let me try again.",
            provider=provider,
            context=context,
            recoverable=True
        )
        self.timeout = timeout


class AllLLMProvidersFailed(LLMProviderError):
    """
    Exception raised when all configured LLM providers have failed.
    """
    
    def __init__(
        self,
        message: str = "All LLM providers failed",
        failed_providers: Optional[Dict[str, Exception]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            user_message="I'm experiencing technical difficulties and cannot process your request at this time. Please try again later or call us directly.",
            context=context,
            recoverable=False
        )
        self.failed_providers = failed_providers or {}


# ============================================================================
# Technical Errors - Database
# ============================================================================

class DatabaseError(BookingSystemError):
    """
    Exception raised when database operations fail.
    """
    
    def __init__(
        self,
        message: str,
        user_message: str = "I'm having trouble accessing our booking system. Please try again in a moment.",
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        super().__init__(message, user_message, context, recoverable)
        self.operation = operation
        self.original_error = original_error


class DatabaseConnectionError(DatabaseError):
    """
    Exception raised when database connection fails.
    """
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            user_message="I'm unable to connect to our booking system at the moment. Please try again shortly.",
            operation="connect",
            original_error=original_error,
            context=context,
            recoverable=True
        )


class DatabaseQueryError(DatabaseError):
    """
    Exception raised when database query fails.
    """
    pass


# ============================================================================
# Technical Errors - Notifications
# ============================================================================

class NotificationError(BookingSystemError):
    """
    Base exception for notification delivery errors.
    
    These are non-blocking - booking should succeed even if notification fails.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        channel: Optional[str] = None,
        recipient: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        # Notification errors should not block the booking flow
        super().__init__(message, user_message, context, recoverable=True)
        self.channel = channel
        self.recipient = recipient
        self.original_error = original_error


class SMSDeliveryError(NotificationError):
    """
    Exception raised when SMS delivery fails.
    """
    
    def __init__(
        self,
        message: str,
        phone_number: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            user_message=None,  # SMS failures are logged but not announced
            channel="sms",
            recipient=phone_number,
            original_error=original_error,
            context=context
        )


class EmailDeliveryError(NotificationError):
    """
    Exception raised when email delivery fails.
    """
    
    def __init__(
        self,
        message: str,
        email_address: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            user_message=None,  # Email failures are logged but not announced
            channel="email",
            recipient=email_address,
            original_error=original_error,
            context=context
        )


# ============================================================================
# User Interaction Errors
# ============================================================================

class UserInteractionError(BookingSystemError):
    """
    Base exception for user interaction errors.
    """
    pass


class UserTimeoutError(UserInteractionError):
    """
    Exception raised when user does not respond after prompt.
    """
    
    def __init__(
        self,
        message: str = "User timeout - no response",
        user_message: str = "I haven't heard from you. Are you still there?",
        timeout_duration: Optional[float] = None,
        retry_count: int = 0,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)
        self.timeout_duration = timeout_duration
        self.retry_count = retry_count


class AmbiguousInputError(UserInteractionError):
    """
    Exception raised when user provides ambiguous or incomplete information.
    """
    
    def __init__(
        self,
        message: str,
        user_message: str,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)
        self.field = field


class UserInterruptionError(UserInteractionError):
    """
    Exception raised when user speaks while agent is speaking.
    """
    
    def __init__(
        self,
        message: str = "User interrupted agent",
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)


# ============================================================================
# State Management Errors
# ============================================================================

class StateTransitionError(BookingSystemError):
    """
    Exception raised when an invalid state transition is attempted.
    """
    
    def __init__(
        self,
        message: str,
        user_message: str = "Something went wrong with the booking flow. Let's start over.",
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, user_message, context, recoverable=True)
        self.from_state = from_state
        self.to_state = to_state
