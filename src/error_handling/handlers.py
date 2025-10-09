"""
Centralized error handling utilities for the booking voice agent.

This module provides:
- Error handler class for consistent error processing
- Logging with context information
- Recovery strategies and retry logic
- Integration helpers for different system components
"""

from typing import Optional, Dict, Any, Callable, TypeVar
from datetime import datetime
from loguru import logger
import traceback
import sys

from .exceptions import (
    BookingAgentError,
    BookingValidationError,
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
    InterruptionError,
)
from .error_messages import get_error_message


T = TypeVar('T')


class ErrorHandler:
    """
    Centralized error handler for the booking voice agent.
    
    This class provides consistent error handling across all components:
    - Logs errors with context
    - Generates user-friendly messages
    - Determines if errors are recoverable
    - Provides retry and fallback strategies
    """
    
    def __init__(
        self,
        log_errors: bool = True,
        generate_messages: bool = True,
        user_id: Optional[str] = None
    ):
        """
        Initialize error handler.
        
        Args:
            log_errors: Whether to log errors
            generate_messages: Whether to generate user-friendly messages
            user_id: Optional user identifier for context
        """
        self.log_errors = log_errors
        self.generate_messages = generate_messages
        self.user_id = user_id
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        log_level: str = "ERROR"
    ) -> Dict[str, Any]:
        """
        Handle an error with logging and message generation.
        
        Args:
            error: Exception to handle
            context: Additional context information
            log_level: Logging level (ERROR, WARNING, INFO)
            
        Returns:
            Dictionary with:
                - error_type: Type of error
                - user_message: Message to speak to user
                - technical_message: Technical error details
                - recoverable: Whether error is recoverable
                - context: Error context
                - should_retry: Whether operation should be retried
        """
        context = context or {}
        
        # Add timestamp and user_id to context
        context.update({
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": self.user_id,
        })
        
        # Extract error information
        error_type = type(error).__name__
        technical_message = str(error)
        
        # Check if it's a BookingAgentError with additional context
        if isinstance(error, BookingAgentError):
            context.update(error.context)
            recoverable = error.recoverable
        else:
            recoverable = True  # Assume recoverable unless specified
        
        # Generate user-friendly message
        if self.generate_messages:
            user_message = get_error_message(error)
        else:
            user_message = technical_message
        
        # Log the error
        if self.log_errors:
            log_error_with_context(
                error=error,
                context=context,
                level=log_level
            )
        
        # Determine retry strategy
        should_retry = self._should_retry(error)
        
        return {
            "error_type": error_type,
            "user_message": user_message,
            "technical_message": technical_message,
            "recoverable": recoverable,
            "context": context,
            "should_retry": should_retry,
        }
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if operation should be retried based on error type."""
        # Retriable errors
        if isinstance(error, (DatabaseError, LLMProviderError)):
            if isinstance(error, DatabaseError) and error.can_retry:
                return True
            if isinstance(error, LLMProviderError) and error.can_retry:
                return True
        
        # Non-retriable errors
        if isinstance(error, (
            BookingValidationError,
            InvalidDateError,
            InvalidTimeError,
            PartySizeTooLargeError,
            NoAvailabilityError,
        )):
            return False
        
        # Default to not retrying
        return False
    
    def wrap_function(
        self,
        func: Callable[..., T],
        error_context: Optional[Dict[str, Any]] = None,
        on_error: Optional[Callable[[Exception], Any]] = None
    ) -> Callable[..., T]:
        """
        Wrap a function with error handling.
        
        Args:
            func: Function to wrap
            error_context: Context to include in error logs
            on_error: Optional callback to call on error
            
        Returns:
            Wrapped function with error handling
        """
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Handle the error
                result = self.handle_error(e, error_context)
                
                # Call error callback if provided
                if on_error:
                    on_error(e)
                
                # Re-raise if not recoverable
                if not result["recoverable"]:
                    raise
                
                return None
        
        return wrapper


# ============================================================================
# Specialized Error Handlers
# ============================================================================

def handle_booking_error(
    error: Exception,
    booking_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle booking-related errors.
    
    Args:
        error: Booking error
        booking_context: Context about the booking attempt
        
    Returns:
        Error handling result dictionary
    """
    context = booking_context or {}
    context["component"] = "booking_service"
    
    handler = ErrorHandler()
    return handler.handle_error(error, context)


def handle_audio_error(
    error: Exception,
    audio_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle audio processing errors.
    
    Args:
        error: Audio error
        audio_context: Context about the audio operation
        
    Returns:
        Error handling result dictionary
    """
    context = audio_context or {}
    context["component"] = "audio_manager"
    
    handler = ErrorHandler()
    return handler.handle_error(error, context)


def handle_llm_error(
    error: Exception,
    llm_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle LLM provider errors.
    
    Args:
        error: LLM error
        llm_context: Context about the LLM call
        
    Returns:
        Error handling result dictionary
    """
    context = llm_context or {}
    context["component"] = "llm_service"
    
    # LLM errors should be logged as warnings unless critical
    log_level = "WARNING" if isinstance(error, LLMProviderError) else "ERROR"
    
    handler = ErrorHandler()
    return handler.handle_error(error, context, log_level=log_level)


def handle_database_error(
    error: Exception,
    db_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle database errors.
    
    Args:
        error: Database error
        db_context: Context about the database operation
        
    Returns:
        Error handling result dictionary
    """
    context = db_context or {}
    context["component"] = "database"
    
    handler = ErrorHandler()
    return handler.handle_error(error, context)


# ============================================================================
# Logging Utilities
# ============================================================================

def log_error_with_context(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "ERROR",
    include_traceback: bool = True
) -> None:
    """
    Log error with full context information.
    
    Args:
        error: Exception to log
        context: Additional context information
        level: Log level (ERROR, WARNING, INFO)
        include_traceback: Whether to include full stack trace
    """
    context = context or {}
    
    # Build log message
    error_type = type(error).__name__
    error_message = str(error)
    
    # Format context for logging
    context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
    
    log_message = f"{error_type}: {error_message}"
    if context_str:
        log_message += f" | Context: {context_str}"
    
    # Log with appropriate level
    log_func = getattr(logger, level.lower(), logger.error)
    
    if include_traceback:
        # Get traceback
        tb_str = "".join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))
        log_message += f"\n{tb_str}"
    
    log_func(log_message)


def log_recovery_attempt(
    error: Exception,
    recovery_strategy: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a recovery attempt for an error.
    
    Args:
        error: Original error
        recovery_strategy: Description of recovery strategy
        context: Additional context
    """
    context = context or {}
    context["recovery_strategy"] = recovery_strategy
    
    logger.info(
        f"Attempting recovery from {type(error).__name__}: {recovery_strategy}"
    )


def log_recovery_success(
    error: Exception,
    recovery_strategy: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log successful error recovery.
    
    Args:
        error: Original error that was recovered from
        recovery_strategy: Description of recovery strategy
        context: Additional context
    """
    context = context or {}
    context["recovery_strategy"] = recovery_strategy
    
    logger.info(
        f"Successfully recovered from {type(error).__name__} using {recovery_strategy}"
    )


def log_recovery_failure(
    error: Exception,
    recovery_strategy: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log failed error recovery.
    
    Args:
        error: Original error
        recovery_strategy: Description of failed recovery strategy
        context: Additional context
    """
    context = context or {}
    context["recovery_strategy"] = recovery_strategy
    
    logger.warning(
        f"Failed to recover from {type(error).__name__} using {recovery_strategy}"
    )


# ============================================================================
# Retry Utilities
# ============================================================================

def with_retry(
    func: Callable[..., T],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    retriable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[..., T]:
    """
    Decorator to add retry logic to a function.
    
    Args:
        func: Function to wrap with retry logic
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        retriable_exceptions: Tuple of exception types to retry
        on_retry: Optional callback called before each retry
        
    Returns:
        Wrapped function with retry logic
    """
    import time
    
    def wrapper(*args, **kwargs):
        current_delay = delay
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except retriable_exceptions as e:
                last_exception = e
                
                if attempt < max_retries:
                    # Log retry attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    # Wait before retry
                    time.sleep(current_delay)
                    current_delay *= backoff
                else:
                    # Max retries reached
                    logger.error(
                        f"Max retries ({max_retries}) reached for {func.__name__}: {e}"
                    )
                    raise
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
    
    return wrapper


def is_retriable_error(error: Exception) -> bool:
    """
    Check if an error is retriable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error should be retried
    """
    # Database errors with can_retry flag
    if isinstance(error, DatabaseError) and error.can_retry:
        return True
    
    # LLM errors with can_retry flag
    if isinstance(error, LLMProviderError) and error.can_retry:
        return True
    
    # Timeout errors are retriable
    if isinstance(error, UserTimeoutError):
        return error.retry_count < error.max_retries
    
    # Audio processing errors might be retriable
    if isinstance(error, TranscriptionError) and error.reason in ["silence", "unclear_audio"]:
        return True
    
    return False
