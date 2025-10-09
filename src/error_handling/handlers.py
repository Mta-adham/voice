"""
Centralized Error Handling Utilities.

This module provides handler functions for different error types,
implementing logging, error recovery, and graceful degradation strategies.
"""

from typing import Optional, Dict, Any, Callable
from loguru import logger

from .exceptions import (
    BookingSystemError,
    BookingValidationError,
    AudioProcessingError,
    LLMProviderError,
    DatabaseError,
    NotificationError,
    UserTimeoutError,
)
from .error_messages import get_error_message


class ErrorHandler:
    """
    Centralized error handler for the booking system.
    
    Provides consistent error logging, recovery strategies,
    and user message generation.
    """
    
    @staticmethod
    def handle_error(
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        log_level: str = "error",
    ) -> Dict[str, Any]:
        """
        Handle any error with logging and message generation.
        
        Args:
            error: Exception that occurred
            context: Additional context for logging
            log_level: Log level (error, warning, info)
        
        Returns:
            Dictionary with error handling results:
            - error_type: Type of error
            - user_message: Message to speak to user
            - recoverable: Whether error is recoverable
            - context: Error context
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "recoverable": True,
            "user_message": "",
            "context": context or {},
        }
        
        # Extract additional info from BookingSystemError
        if isinstance(error, BookingSystemError):
            error_info["recoverable"] = error.recoverable
            error_info["context"].update(error.context)
        
        # Generate user-friendly message
        error_info["user_message"] = get_error_message(error)
        
        # Log the error
        log_msg = f"Error handled: {error_info['error_type']} - {error_info['error_message']}"
        if error_info["context"]:
            log_msg += f" | Context: {error_info['context']}"
        
        if log_level == "error":
            logger.error(log_msg)
        elif log_level == "warning":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        return error_info


def handle_booking_error(
    error: BookingValidationError,
    user_id: Optional[str] = None,
    conversation_state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle booking validation errors.
    
    Args:
        error: BookingValidationError instance
        user_id: User identifier for logging
        conversation_state: Current conversation state
    
    Returns:
        Error handling result with user message and alternatives
    """
    context = {
        "user_id": user_id,
        "conversation_state": conversation_state,
        "field": error.field,
        "value": error.value,
        "alternatives": error.alternatives,
    }
    
    logger.warning(
        f"Booking validation failed | "
        f"user_id={user_id} | "
        f"field={error.field} | "
        f"value={error.value} | "
        f"reason={error.message}"
    )
    
    return ErrorHandler.handle_error(error, context, log_level="warning")


def handle_audio_error(
    error: AudioProcessingError,
    audio_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle audio processing errors.
    
    Args:
        error: AudioProcessingError instance
        audio_type: Type of audio operation (recording, playback, stt, tts)
    
    Returns:
        Error handling result with user message
    """
    context = {
        "audio_type": audio_type,
        "error_type": error.error_type,
    }
    
    logger.error(
        f"Audio processing error | "
        f"type={error.error_type} | "
        f"message={error.message}"
    )
    
    return ErrorHandler.handle_error(error, context)


def handle_llm_error(
    error: LLMProviderError,
    fallback_providers: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Handle LLM provider errors with fallback strategy.
    
    Args:
        error: LLMProviderError instance
        fallback_providers: List of alternative providers to try
    
    Returns:
        Error handling result with fallback suggestions
    """
    context = {
        "provider": error.provider,
        "error_type": error.error_type,
        "retry_possible": error.retry_possible,
        "fallback_providers": fallback_providers or [],
    }
    
    logger.error(
        f"LLM provider error | "
        f"provider={error.provider} | "
        f"error_type={error.error_type} | "
        f"retry_possible={error.retry_possible}"
    )
    
    result = ErrorHandler.handle_error(error, context)
    
    # Add fallback provider information
    if fallback_providers:
        result["fallback_available"] = True
        result["fallback_providers"] = fallback_providers
    
    return result


def handle_database_error(
    error: DatabaseError,
    operation: Optional[str] = None,
    retry_count: int = 0,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Handle database errors with retry strategy.
    
    Args:
        error: DatabaseError instance
        operation: Database operation that failed
        retry_count: Current retry count
        max_retries: Maximum retry attempts
    
    Returns:
        Error handling result with retry information
    """
    context = {
        "operation": operation,
        "error_type": error.error_type,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "should_retry": error.retry_possible and retry_count < max_retries,
    }
    
    logger.error(
        f"Database error | "
        f"operation={operation} | "
        f"error_type={error.error_type} | "
        f"retry_count={retry_count}/{max_retries}"
    )
    
    result = ErrorHandler.handle_error(error, context)
    result["should_retry"] = context["should_retry"]
    
    return result


def handle_notification_error(
    error: NotificationError,
    booking_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Handle notification delivery errors.
    
    Non-critical errors - log but don't fail the booking.
    
    Args:
        error: NotificationError instance
        booking_id: Booking ID for reference
    
    Returns:
        Error handling result
    """
    context = {
        "booking_id": booking_id,
        "notification_type": error.notification_type,
        "recipient": error.recipient,
    }
    
    logger.warning(
        f"Notification delivery failed | "
        f"type={error.notification_type} | "
        f"recipient={error.recipient} | "
        f"booking_id={booking_id} | "
        f"message={error.message}"
    )
    
    # Log as warning since booking should still succeed
    return ErrorHandler.handle_error(error, context, log_level="warning")


def handle_timeout_error(
    error: UserTimeoutError,
    user_id: Optional[str] = None,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Handle user timeout errors.
    
    Args:
        error: UserTimeoutError instance
        user_id: User identifier
        max_retries: Maximum retry attempts before ending conversation
    
    Returns:
        Error handling result with retry/end decision
    """
    context = {
        "user_id": user_id,
        "timeout_seconds": error.timeout_seconds,
        "retry_count": error.retry_count,
        "max_retries": max_retries,
        "should_end_conversation": error.retry_count >= max_retries,
    }
    
    logger.warning(
        f"User timeout | "
        f"user_id={user_id} | "
        f"timeout={error.timeout_seconds}s | "
        f"retry_count={error.retry_count}/{max_retries}"
    )
    
    result = ErrorHandler.handle_error(error, context, log_level="warning")
    result["should_end_conversation"] = context["should_end_conversation"]
    
    return result


def with_error_handling(
    operation_name: str,
    log_context: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Decorator for adding error handling to functions.
    
    Args:
        operation_name: Name of the operation for logging
        log_context: Additional context for logging
    
    Returns:
        Decorator function
    
    Example:
        @with_error_handling("create_booking", {"user_id": "123"})
        def create_booking(data):
            # ... booking logic ...
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                logger.debug(f"Starting operation: {operation_name}")
                result = func(*args, **kwargs)
                logger.debug(f"Completed operation: {operation_name}")
                return result
            except BookingSystemError as e:
                logger.error(
                    f"Operation failed: {operation_name} | "
                    f"error={type(e).__name__} | "
                    f"message={str(e)}"
                )
                if log_context:
                    logger.error(f"Context: {log_context}")
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in operation: {operation_name} | "
                    f"error={type(e).__name__} | "
                    f"message={str(e)}"
                )
                if log_context:
                    logger.error(f"Context: {log_context}")
                raise
        return wrapper
    return decorator


def log_error_with_context(
    error: Exception,
    operation: str,
    user_id: Optional[str] = None,
    conversation_state: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log error with full context for debugging.
    
    Args:
        error: Exception that occurred
        operation: Operation being performed
        user_id: User identifier
        conversation_state: Current conversation state
        additional_context: Any additional context
    """
    context = {
        "operation": operation,
        "user_id": user_id,
        "conversation_state": conversation_state,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if additional_context:
        context.update(additional_context)
    
    # Include stack trace for non-BookingSystemError exceptions
    if not isinstance(error, BookingSystemError):
        logger.exception(f"Error in {operation}: {context}")
    else:
        logger.error(f"Error in {operation}: {context}")
