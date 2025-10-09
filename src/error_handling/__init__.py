"""
Error Handling Module for Restaurant Booking Voice Agent.

This module provides comprehensive error handling including:
- Custom exception classes for different error categories
- Natural language error messages for voice responses
- Centralized error handling utilities
- Graceful degradation strategies
"""

from .exceptions import (
    BookingValidationError,
    AudioProcessingError,
    LLMProviderError,
    DatabaseError,
    NotificationError,
    UserTimeoutError,
    SystemError,
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
    handle_notification_error,
    handle_timeout_error,
)

__all__ = [
    # Exceptions
    "BookingValidationError",
    "AudioProcessingError",
    "LLMProviderError",
    "DatabaseError",
    "NotificationError",
    "UserTimeoutError",
    "SystemError",
    # Message generation
    "get_error_message",
    "get_alternative_suggestions",
    "ErrorMessageGenerator",
    # Handlers
    "handle_booking_error",
    "handle_audio_error",
    "handle_llm_error",
    "handle_database_error",
    "handle_notification_error",
    "handle_timeout_error",
]
