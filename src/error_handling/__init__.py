"""
Error handling module for restaurant booking system.

This module provides comprehensive error handling with:
- Custom exception classes for all error types
- Natural language error messages for voice output
- Graceful degradation strategies
- Timeout management
- Centralized logging
"""

from .exceptions import (
    # Base
    BookingSystemError,
    
    # Business Logic
    BookingValidationError,
    NoAvailabilityError,
    InvalidDateError,
    InvalidTimeError,
    InvalidPartySizeError,
    
    # Audio Processing
    AudioProcessingError,
    STTError,
    TTSError,
    UnclearAudioError,
    SilenceDetectedError,
    
    # Technical
    LLMProviderError,
    DatabaseError,
    NotificationError,
    
    # User Interaction
    UserTimeoutError,
    AmbiguousInputError,
    UserInterruptionError,
    
    # System
    ConfigurationError
)

from .error_messages import (
    get_error_message,
    suggest_next_action,
    format_date_friendly,
    format_time_friendly
)

from .handlers import (
    ErrorContext,
    handle_error_with_context,
    with_retry,
    with_timeout,
    graceful_degradation,
    CircuitBreaker,
    validate_and_handle_errors,
    log_function_call
)

from .timeout_manager import (
    TimeoutManager,
    SilenceDetector,
    with_user_timeout
)

from .logging_config import (
    configure_logging,
    init_logging,
    log_booking_event,
    log_conversation_event,
    log_api_call,
    log_error_with_context,
    LogContext,
    log_performance
)

__all__ = [
    # Exceptions
    'BookingSystemError',
    'BookingValidationError',
    'NoAvailabilityError',
    'InvalidDateError',
    'InvalidTimeError',
    'InvalidPartySizeError',
    'AudioProcessingError',
    'STTError',
    'TTSError',
    'UnclearAudioError',
    'SilenceDetectedError',
    'LLMProviderError',
    'DatabaseError',
    'NotificationError',
    'UserTimeoutError',
    'AmbiguousInputError',
    'UserInterruptionError',
    'ConfigurationError',
    
    # Error Messages
    'get_error_message',
    'suggest_next_action',
    'format_date_friendly',
    'format_time_friendly',
    
    # Handlers
    'ErrorContext',
    'handle_error_with_context',
    'with_retry',
    'with_timeout',
    'graceful_degradation',
    'CircuitBreaker',
    'validate_and_handle_errors',
    'log_function_call',
    
    # Timeout Management
    'TimeoutManager',
    'SilenceDetector',
    'with_user_timeout',
    
    # Logging
    'configure_logging',
    'init_logging',
    'log_booking_event',
    'log_conversation_event',
    'log_api_call',
    'log_error_with_context',
    'LogContext',
    'log_performance',
]
