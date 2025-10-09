"""
Centralized error handling utilities for the booking system.

This module provides decorators and utilities for consistent error handling,
logging, and recovery across all system components.
"""
import functools
import traceback
from typing import Optional, Callable, Any, Dict, Type, Tuple
from loguru import logger

from .exceptions import (
    BookingSystemError,
    DatabaseError,
    DatabaseConnectionError,
    LLMProviderError,
    AllLLMProvidersFailed,
    SpeechServiceError,
    NotificationError,
    UserTimeoutError,
    AudioProcessingError,
)
from .error_messages import generate_error_message


# ============================================================================
# Error Logging Utilities
# ============================================================================

def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error",
    include_traceback: bool = True
) -> None:
    """
    Log an error with comprehensive context information.
    
    Args:
        error: Exception to log
        context: Additional context information (user_id, conversation_state, etc.)
        level: Log level (error, warning, critical)
        include_traceback: Whether to include full traceback
    """
    error_info = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "context": context or {},
    }
    
    # Add additional error attributes if available
    if isinstance(error, BookingSystemError):
        error_info["recoverable"] = error.recoverable
        error_info["user_message"] = error.user_message
        error_info["error_context"] = error.context
    
    # Build log message
    log_message = f"Error: {error.__class__.__name__} - {str(error)}"
    
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        log_message += f" | Context: {context_str}"
    
    # Log with appropriate level
    log_func = getattr(logger, level, logger.error)
    
    if include_traceback and level in ["error", "critical"]:
        log_func(log_message)
        logger.error(f"Traceback:\n{traceback.format_exc()}")
    else:
        log_func(log_message)
    
    # Log structured error info for debugging
    logger.debug(f"Error details: {error_info}")


def log_error_recovery(
    error: Exception,
    recovery_action: str,
    success: bool,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log error recovery attempt.
    
    Args:
        error: Original exception
        recovery_action: Description of recovery action taken
        success: Whether recovery was successful
        context: Additional context
    """
    status = "succeeded" if success else "failed"
    logger.info(
        f"Error recovery {status}: {error.__class__.__name__} | "
        f"Action: {recovery_action} | "
        f"Context: {context or {}}"
    )


# ============================================================================
# Error Handler Decorators
# ============================================================================

def handle_errors(
    fallback_return: Any = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_level: str = "error",
    reraise: bool = False,
    context_provider: Optional[Callable] = None
):
    """
    Decorator for handling errors with logging and optional fallback.
    
    Args:
        fallback_return: Value to return if error occurs (if reraise=False)
        exceptions: Tuple of exception types to catch
        log_level: Log level for caught exceptions
        reraise: Whether to re-raise exception after logging
        context_provider: Optional function to provide additional context
        
    Example:
        @handle_errors(fallback_return=[], exceptions=(DatabaseError,))
        def get_bookings():
            return query_database()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                # Get context if provider is available
                context = {}
                if context_provider:
                    try:
                        context = context_provider()
                    except Exception:
                        pass
                
                # Add function info to context
                context["function"] = func.__name__
                context["module"] = func.__module__
                
                # Log the error
                log_error(e, context=context, level=log_level)
                
                # Re-raise or return fallback
                if reraise:
                    raise
                else:
                    return fallback_return
        
        return wrapper
    return decorator


def retry_on_error(
    max_retries: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    backoff_factor: float = 1.0,
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying function on specific exceptions.
    
    Args:
        max_retries: Maximum number of retry attempts
        exceptions: Tuple of exception types to retry on
        backoff_factor: Multiplier for exponential backoff (seconds)
        on_retry: Optional callback function called on each retry
        
    Example:
        @retry_on_error(max_retries=3, exceptions=(DatabaseConnectionError,))
        def connect_to_database():
            return create_connection()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Calculate backoff time
                        import time
                        wait_time = backoff_factor * (2 ** attempt)
                        
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} "
                            f"after {e.__class__.__name__}. Waiting {wait_time:.2f}s..."
                        )
                        
                        # Call retry callback if provided
                        if on_retry:
                            try:
                                on_retry(e, attempt)
                            except Exception as callback_error:
                                logger.warning(f"Error in retry callback: {callback_error}")
                        
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_retries} retry attempts failed for {func.__name__}"
                        )
            
            # All retries exhausted, raise last exception
            raise last_exception
        
        return wrapper
    return decorator


# ============================================================================
# Error Recovery Strategies
# ============================================================================

def handle_database_error(
    error: Exception,
    operation: str,
    retry_func: Optional[Callable] = None,
    max_retries: int = 3
) -> Tuple[bool, Optional[Any]]:
    """
    Handle database errors with retry logic.
    
    Args:
        error: Database exception
        operation: Description of database operation
        retry_func: Optional function to retry
        max_retries: Maximum number of retries
        
    Returns:
        Tuple of (success, result)
    """
    logger.error(f"Database error during {operation}: {str(error)}")
    
    # If it's a connection error and we have a retry function, try again
    if retry_func and max_retries > 0:
        import time
        
        for attempt in range(max_retries):
            try:
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                result = retry_func()
                log_error_recovery(error, f"retry {operation}", success=True)
                return True, result
            except Exception as retry_error:
                logger.warning(f"Retry {attempt + 1}/{max_retries} failed: {retry_error}")
                continue
    
    log_error_recovery(error, f"retry {operation}", success=False)
    return False, None


def handle_llm_provider_failure(
    error: Exception,
    failed_provider: str,
    alternative_providers: list,
    llm_call_func: Callable,
    **call_kwargs
) -> Tuple[bool, Optional[Any]]:
    """
    Handle LLM provider failure by trying alternative providers.
    
    Args:
        error: LLM provider exception
        failed_provider: Name of failed provider
        alternative_providers: List of alternative provider names
        llm_call_func: Function to call LLM (should accept provider param)
        **call_kwargs: Additional arguments for LLM call
        
    Returns:
        Tuple of (success, result)
    """
    logger.warning(f"LLM provider {failed_provider} failed: {str(error)}")
    
    failed_providers = {failed_provider: error}
    
    # Try each alternative provider
    for provider in alternative_providers:
        try:
            logger.info(f"Trying alternative LLM provider: {provider}")
            result = llm_call_func(provider=provider, **call_kwargs)
            log_error_recovery(
                error,
                f"switch to {provider}",
                success=True,
                context={"failed_provider": failed_provider}
            )
            return True, result
        except Exception as alt_error:
            logger.warning(f"Alternative provider {provider} also failed: {alt_error}")
            failed_providers[provider] = alt_error
            continue
    
    # All providers failed
    logger.error(f"All LLM providers failed: {failed_providers}")
    log_error_recovery(error, "try alternative providers", success=False)
    
    return False, None


def handle_tts_failure(
    error: Exception,
    text: str,
    fallback_tts_func: Optional[Callable] = None
) -> Tuple[bool, Optional[Any]]:
    """
    Handle TTS failure by trying fallback TTS engine.
    
    Args:
        error: TTS exception
        text: Text to synthesize
        fallback_tts_func: Optional fallback TTS function
        
    Returns:
        Tuple of (success, audio_data)
    """
    logger.warning(f"Primary TTS failed: {str(error)}")
    
    if fallback_tts_func:
        try:
            logger.info("Attempting fallback TTS engine")
            audio_data = fallback_tts_func(text)
            log_error_recovery(error, "use fallback TTS", success=True)
            return True, audio_data
        except Exception as fallback_error:
            logger.error(f"Fallback TTS also failed: {fallback_error}")
            log_error_recovery(error, "use fallback TTS", success=False)
    
    return False, None


def handle_notification_failure(
    error: Exception,
    notification_type: str,
    alternative_channel: Optional[Callable] = None,
    **channel_kwargs
) -> bool:
    """
    Handle notification failure by trying alternative channel.
    
    Notification failures should never block the booking flow.
    
    Args:
        error: Notification exception
        notification_type: Type of notification (sms, email)
        alternative_channel: Optional alternative notification function
        **channel_kwargs: Arguments for alternative channel
        
    Returns:
        True if alternative succeeded, False otherwise
    """
    logger.warning(f"{notification_type} notification failed: {str(error)}")
    
    if alternative_channel:
        try:
            logger.info(f"Attempting alternative notification channel")
            alternative_channel(**channel_kwargs)
            log_error_recovery(error, f"use alternative channel", success=True)
            return True
        except Exception as alt_error:
            logger.warning(f"Alternative notification channel also failed: {alt_error}")
            log_error_recovery(error, f"use alternative channel", success=False)
    
    # Log but don't block
    logger.warning(f"Notification delivery failed, but continuing with booking flow")
    return False


# ============================================================================
# Conversation Error Handling
# ============================================================================

def handle_conversation_error(
    error: Exception,
    conversation_context: Dict[str, Any],
    retry_count: int = 0
) -> Dict[str, Any]:
    """
    Handle errors during conversation flow.
    
    Returns a response dictionary with error message and recovery action.
    
    Args:
        error: Exception that occurred
        conversation_context: Current conversation context
        retry_count: Number of times this error has been retried
        
    Returns:
        Dictionary with 'message', 'action', and 'recoverable' keys
    """
    # Log the error with conversation context
    log_error(
        error,
        context={
            "conversation_state": conversation_context.get("state"),
            "user_id": conversation_context.get("user_id"),
            "retry_count": retry_count,
        },
        level="error"
    )
    
    # Generate user-friendly message
    user_message = generate_error_message(
        error,
        context=conversation_context,
        retry_count=retry_count
    )
    
    # Determine recovery action
    if isinstance(error, UserTimeoutError):
        if retry_count >= 2:
            action = "end_conversation"
        else:
            action = "retry_prompt"
    
    elif isinstance(error, NotificationError):
        # Notification errors should not interrupt flow
        action = "continue"
    
    elif isinstance(error, (DatabaseError, DatabaseConnectionError)):
        if retry_count >= 3:
            action = "escalate"
        else:
            action = "retry"
    
    elif isinstance(error, AllLLMProvidersFailed):
        action = "escalate"
    
    elif isinstance(error, BookingSystemError):
        if error.recoverable:
            action = "retry" if retry_count < 3 else "clarify"
        else:
            action = "escalate"
    
    else:
        # Unknown error
        action = "retry" if retry_count < 2 else "escalate"
    
    return {
        "message": user_message,
        "action": action,
        "recoverable": getattr(error, "recoverable", True),
        "error_type": error.__class__.__name__,
        "retry_count": retry_count,
    }


def should_retry_error(error: Exception, retry_count: int, max_retries: int = 3) -> bool:
    """
    Determine if an error should be retried.
    
    Args:
        error: Exception to check
        retry_count: Current retry count
        max_retries: Maximum allowed retries
        
    Returns:
        True if should retry, False otherwise
    """
    if retry_count >= max_retries:
        return False
    
    # Check if error is recoverable
    if isinstance(error, BookingSystemError):
        return error.recoverable
    
    # Retry on transient errors
    transient_errors = (
        DatabaseConnectionError,
        LLMProviderError,
        AudioProcessingError,
    )
    
    return isinstance(error, transient_errors)
