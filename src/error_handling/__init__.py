"""
Error handling module for restaurant booking system.

This module provides comprehensive error handling infrastructure including:
- Custom exception hierarchy for all error types
- Natural language error message generation for voice interfaces
- Centralized error handlers and recovery strategies
- Logging utilities

Main Components:
    - exceptions: Custom exception classes for all error scenarios
    - error_messages: User-friendly message generation for TTS
    - handlers: Decorators and utilities for error handling
"""

# Import all exceptions
from .exceptions import (
    # Base exceptions
    BookingSystemError,
    
    # Business logic errors
    BookingValidationError,
    NoAvailabilityError,
    CapacityExceededError,
    
    # Audio processing errors
    AudioProcessingError,
    AudioDeviceError,
    AudioRecordingError,
    AudioPlaybackError,
    SilenceDetectedError,
    UnclearAudioError,
    
    # Speech service errors
    SpeechServiceError,
    STTError,
    TTSError,
    APIKeyError,
    QuotaExceededError,
    RateLimitError,
    
    # LLM provider errors
    LLMProviderError,
    LLMTimeoutError,
    AllLLMProvidersFailed,
    
    # Database errors
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    
    # Notification errors
    NotificationError,
    SMSDeliveryError,
    EmailDeliveryError,
    
    # User interaction errors
    UserInteractionError,
    UserTimeoutError,
    AmbiguousInputError,
    UserInterruptionError,
    
    # State management errors
    StateTransitionError,
)

# Import error message generators
from .error_messages import (
    generate_error_message,
    generate_booking_validation_error_message,
    generate_no_availability_error_message,
    generate_capacity_error_message,
    generate_user_timeout_message,
    generate_technical_error_message,
    format_date_friendly,
    format_time_friendly,
    format_time_alternatives,
)

# Import error handlers
from .handlers import (
    log_error,
    log_error_recovery,
    handle_errors,
    retry_on_error,
    handle_database_error,
    handle_llm_provider_failure,
    handle_tts_failure,
    handle_notification_failure,
    handle_conversation_error,
    should_retry_error,
)

# Define public API
__all__ = [
    # Exceptions - Base
    "BookingSystemError",
    
    # Exceptions - Business Logic
    "BookingValidationError",
    "NoAvailabilityError",
    "CapacityExceededError",
    
    # Exceptions - Audio
    "AudioProcessingError",
    "AudioDeviceError",
    "AudioRecordingError",
    "AudioPlaybackError",
    "SilenceDetectedError",
    "UnclearAudioError",
    
    # Exceptions - Speech Services
    "SpeechServiceError",
    "STTError",
    "TTSError",
    "APIKeyError",
    "QuotaExceededError",
    "RateLimitError",
    
    # Exceptions - LLM
    "LLMProviderError",
    "LLMTimeoutError",
    "AllLLMProvidersFailed",
    
    # Exceptions - Database
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    
    # Exceptions - Notifications
    "NotificationError",
    "SMSDeliveryError",
    "EmailDeliveryError",
    
    # Exceptions - User Interaction
    "UserInteractionError",
    "UserTimeoutError",
    "AmbiguousInputError",
    "UserInterruptionError",
    
    # Exceptions - State
    "StateTransitionError",
    
    # Error Messages
    "generate_error_message",
    "generate_booking_validation_error_message",
    "generate_no_availability_error_message",
    "generate_capacity_error_message",
    "generate_user_timeout_message",
    "generate_technical_error_message",
    "format_date_friendly",
    "format_time_friendly",
    "format_time_alternatives",
    
    # Error Handlers
    "log_error",
    "log_error_recovery",
    "handle_errors",
    "retry_on_error",
    "handle_database_error",
    "handle_llm_provider_failure",
    "handle_tts_failure",
    "handle_notification_failure",
    "handle_conversation_error",
    "should_retry_error",
]
