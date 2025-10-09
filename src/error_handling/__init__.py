"""
Error handling package for restaurant booking voice agent.

This package provides:
- Custom exception classes for different error categories
- Natural language error message generation
- Centralized error handling utilities
- Graceful degradation strategies
"""

from .exceptions import (
    # Business Logic Errors
    BookingValidationError,
    NoAvailabilityError,
    InvalidDateError,
    InvalidTimeError,
    PartySizeTooLargeError,
    
    # Technical Errors
    AudioProcessingError,
    TranscriptionError,
    TextToSpeechError,
    LLMProviderError,
    DatabaseError,
    NotificationError,
    
    # User Interaction Errors
    UserTimeoutError,
    AmbiguousInputError,
    InterruptionError,
)

from .error_messages import (
    get_error_message,
    get_alternative_suggestions,
    ErrorMessageGenerator,
)

from .handlers import (
    handle_booking_error,
    handle_audio_error,
    handle_llm_error,
    handle_database_error,
    log_error_with_context,
    ErrorHandler,
)

__all__ = [
    # Exceptions
    "BookingValidationError",
    "NoAvailabilityError",
    "InvalidDateError",
    "InvalidTimeError",
    "PartySizeTooLargeError",
    "AudioProcessingError",
    "TranscriptionError",
    "TextToSpeechError",
    "LLMProviderError",
    "DatabaseError",
    "NotificationError",
    "UserTimeoutError",
    "AmbiguousInputError",
    "InterruptionError",
    
    # Error messages
    "get_error_message",
    "get_alternative_suggestions",
    "ErrorMessageGenerator",
    
    # Handlers
    "handle_booking_error",
    "handle_audio_error",
    "handle_llm_error",
    "handle_database_error",
    "log_error_with_context",
    "ErrorHandler",
]
