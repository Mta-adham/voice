"""
Centralized error handling utilities for the booking system.

This module provides utilities for:
- Error logging with context
- Error recovery strategies
- Graceful degradation
- Timeout management
"""
import time
import functools
from typing import Optional, Callable, Any, Dict, List, Type
from datetime import datetime
from loguru import logger

from .exceptions import (
    BookingSystemError,
    BookingValidationError,
    AudioProcessingError,
    LLMProviderError,
    DatabaseError,
    NotificationError,
    UserTimeoutError,
    ConfigurationError
)
from .error_messages import get_error_message, suggest_next_action


class ErrorContext:
    """
    Context manager for tracking error handling state.
    
    Tracks:
    - Current conversation state
    - User information
    - Error history
    - Recovery attempts
    """
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        conversation_state: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.conversation_state = conversation_state
        self.context_data = context_data or {}
        self.error_count = 0
        self.error_history: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
    
    def log_error(
        self,
        error: Exception,
        severity: str = "ERROR",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log error with full context.
        
        Args:
            error: Exception that occurred
            severity: Log severity level (ERROR, WARNING, CRITICAL)
            additional_context: Additional context information
        """
        self.error_count += 1
        
        # Build comprehensive error context
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "user_id": self.user_id,
            "conversation_state": self.conversation_state,
            "error_number": self.error_count,
            "session_duration": (datetime.now() - self.start_time).total_seconds()
        }
        
        # Add custom exception context if available
        if isinstance(error, BookingSystemError):
            error_entry["error_context"] = error.context
            error_entry["recoverable"] = error.recoverable
            error_entry["user_message"] = error.user_message
        
        # Add additional context
        if additional_context:
            error_entry["additional_context"] = additional_context
        
        # Store in history
        self.error_history.append(error_entry)
        
        # Log with appropriate severity
        log_func = getattr(logger, severity.lower(), logger.error)
        log_func(
            f"{error_entry['error_type']}: {error_entry['error_message']} | "
            f"User: {self.user_id} | State: {self.conversation_state} | "
            f"Error #{self.error_count}"
        )
        
        # Log stack trace for technical errors
        if severity == "ERROR" and not isinstance(error, (BookingValidationError, UserTimeoutError)):
            logger.exception("Stack trace:")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors in this context."""
        return {
            "total_errors": self.error_count,
            "error_types": [e["error_type"] for e in self.error_history],
            "session_duration": (datetime.now() - self.start_time).total_seconds(),
            "recoverable_errors": sum(
                1 for e in self.error_history
                if e.get("recoverable", True)
            )
        }


def handle_error_with_context(
    error: Exception,
    error_context: ErrorContext,
    should_raise: bool = False
) -> Dict[str, Any]:
    """
    Handle error with full context and return response.
    
    Args:
        error: Exception that occurred
        error_context: Error tracking context
        should_raise: Whether to re-raise after logging
        
    Returns:
        Dictionary with error response information:
        - user_message: Message to speak to user
        - next_action: Suggested next action
        - recoverable: Whether error is recoverable
        - should_retry: Whether operation should be retried
        
    Raises:
        Re-raises the error if should_raise is True
    """
    # Determine severity
    if isinstance(error, ConfigurationError):
        severity = "CRITICAL"
    elif isinstance(error, (DatabaseError, LLMProviderError)):
        severity = "ERROR"
    elif isinstance(error, BookingValidationError):
        severity = "WARNING"
    else:
        severity = "ERROR"
    
    # Log the error
    error_context.log_error(error, severity=severity)
    
    # Get user-friendly message
    user_message = get_error_message(error)
    next_action = suggest_next_action(error)
    
    # Determine if recoverable
    if isinstance(error, BookingSystemError):
        recoverable = error.recoverable
    else:
        recoverable = False
    
    # Determine if should retry
    should_retry = False
    if isinstance(error, (DatabaseError, LLMProviderError)):
        if hasattr(error, 'retry_possible'):
            should_retry = error.retry_possible
    
    response = {
        "user_message": user_message,
        "next_action": next_action,
        "recoverable": recoverable,
        "should_retry": should_retry,
        "error_type": type(error).__name__
    }
    
    if should_raise:
        raise
    
    return response


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions on specific exceptions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exception types to retry on
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            # All attempts failed, raise last exception
            raise last_exception
        
        return wrapper
    return decorator


def with_timeout(
    timeout_seconds: int,
    timeout_error: Optional[Type[Exception]] = None
):
    """
    Decorator for adding timeout to functions.
    
    Args:
        timeout_seconds: Timeout in seconds
        timeout_error: Exception type to raise on timeout
        
    Returns:
        Decorated function with timeout logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                error_class = timeout_error or UserTimeoutError
                raise error_class(
                    message=f"Function {func.__name__} timed out after {timeout_seconds}s",
                    timeout_seconds=timeout_seconds
                )
            
            # Set up timeout signal
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Cancel alarm and restore old handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        
        return wrapper
    return decorator


def graceful_degradation(
    fallback_func: Optional[Callable] = None,
    fallback_value: Any = None,
    log_message: Optional[str] = None
):
    """
    Decorator for graceful degradation when function fails.
    
    Args:
        fallback_func: Function to call if main function fails
        fallback_value: Value to return if main function fails
        log_message: Custom log message for degradation
        
    Returns:
        Decorated function with fallback logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                message = log_message or f"Function {func.__name__} failed, using fallback"
                logger.warning(f"{message}: {str(e)}")
                
                # Try fallback function
                if fallback_func:
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback also failed: {str(fallback_error)}")
                        return fallback_value
                
                # Return fallback value
                return fallback_value
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures.
    
    When a service fails repeatedly, the circuit breaker "opens" and
    immediately fails subsequent calls without attempting them, giving
    the service time to recover.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before trying again
            name: Name for logging purposes
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.name = name or "CircuitBreaker"
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        # Check if circuit is open
        if self.state == "open":
            # Check if timeout has passed
            if time.time() - self.last_failure_time >= self.timeout_seconds:
                logger.info(f"{self.name}: Attempting half-open state")
                self.state = "half-open"
            else:
                raise Exception(f"{self.name}: Circuit is open, service unavailable")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == "half-open":
                logger.info(f"{self.name}: Circuit closed after recovery")
                self.state = "closed"
            self.failure_count = 0
            self.last_failure_time = None
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Check if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(
                    f"{self.name}: Circuit opened after {self.failure_count} failures. "
                    f"Will retry in {self.timeout_seconds}s"
                )
            
            raise


def validate_and_handle_errors(
    func: Callable,
    error_context: ErrorContext,
    allowed_exceptions: Optional[tuple] = None
) -> Callable:
    """
    Wrapper that validates function execution and handles errors.
    
    Args:
        func: Function to wrap
        error_context: Error context for tracking
        allowed_exceptions: Exceptions that should be re-raised
        
    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check if this exception should be re-raised
            if allowed_exceptions and isinstance(e, allowed_exceptions):
                raise
            
            # Handle error with context
            response = handle_error_with_context(
                error=e,
                error_context=error_context,
                should_raise=False
            )
            
            return response
    
    return wrapper


def log_function_call(func: Callable) -> Callable:
    """
    Decorator for logging function calls and execution time.
    
    Args:
        func: Function to log
        
    Returns:
        Decorated function with logging
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.debug(f"Calling {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"{func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.3f}s: {str(e)}")
            raise
    
    return wrapper
