"""
Centralized logging configuration for the booking system.

This module configures loguru for structured logging with different
levels and formats for development vs production.
"""
import sys
from pathlib import Path
from typing import Optional
from loguru import logger
from datetime import datetime


def configure_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str = "logs",
    rotation: str = "100 MB",
    retention: str = "30 days",
    format_type: str = "detailed"
) -> None:
    """
    Configure loguru logging for the application.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to files in addition to console
        log_dir: Directory for log files
        rotation: When to rotate log files (e.g., "100 MB", "1 day")
        retention: How long to keep old log files
        format_type: Format style ("simple", "detailed", "json")
    """
    # Remove default logger
    logger.remove()
    
    # Define format strings
    if format_type == "simple":
        format_string = "<level>{level: <8}</level> | <level>{message}</level>"
    elif format_type == "json":
        format_string = "{message}"  # Will be JSON serialized
    else:  # detailed
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    # Add console handler (always)
    logger.add(
        sys.stderr,
        format=format_string,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handlers if enabled
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # General log file (all levels)
        logger.add(
            log_path / "booking_system_{time:YYYY-MM-DD}.log",
            format=format_string,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True
        )
        
        # Error log file (ERROR and CRITICAL only)
        logger.add(
            log_path / "errors_{time:YYYY-MM-DD}.log",
            format=format_string,
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True
        )
        
        # Separate log for booking transactions (for audit trail)
        logger.add(
            log_path / "bookings_{time:YYYY-MM-DD}.log",
            format=format_string,
            level="INFO",
            rotation="1 day",
            retention="1 year",  # Keep booking logs longer
            compression="zip",
            filter=lambda record: "BOOKING" in record["extra"].get("category", "")
        )
    
    logger.info(
        f"Logging configured: level={log_level}, "
        f"file_logging={log_to_file}, "
        f"format={format_type}"
    )


def log_booking_event(
    event_type: str,
    user_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    details: Optional[dict] = None
) -> None:
    """
    Log a booking-related event for audit trail.
    
    Args:
        event_type: Type of event (e.g., "CREATED", "MODIFIED", "CANCELLED")
        user_id: User identifier (phone, email, etc.)
        booking_id: Booking confirmation ID
        details: Additional event details
    """
    details = details or {}
    
    logger.bind(category="BOOKING").info(
        f"BOOKING {event_type} | "
        f"user={user_id} | "
        f"booking_id={booking_id} | "
        f"details={details}"
    )


def log_conversation_event(
    event_type: str,
    user_id: Optional[str] = None,
    state: Optional[str] = None,
    details: Optional[dict] = None
) -> None:
    """
    Log a conversation-related event.
    
    Args:
        event_type: Type of event (e.g., "STARTED", "STATE_CHANGE", "COMPLETED", "ABANDONED")
        user_id: User identifier
        state: Conversation state
        details: Additional event details
    """
    details = details or {}
    
    logger.bind(category="CONVERSATION").info(
        f"CONVERSATION {event_type} | "
        f"user={user_id} | "
        f"state={state} | "
        f"details={details}"
    )


def log_api_call(
    service: str,
    operation: str,
    success: bool,
    duration: float,
    details: Optional[dict] = None
) -> None:
    """
    Log an external API call.
    
    Args:
        service: Service name (e.g., "openai", "elevenlabs", "twilio")
        operation: Operation performed (e.g., "generate_speech", "send_sms")
        success: Whether the call succeeded
        duration: Duration in seconds
        details: Additional call details
    """
    details = details or {}
    level = "INFO" if success else "WARNING"
    
    logger.bind(category="API").log(
        level,
        f"API {service}.{operation} | "
        f"success={success} | "
        f"duration={duration:.3f}s | "
        f"details={details}"
    )


def log_error_with_context(
    error: Exception,
    context: dict,
    severity: str = "ERROR"
) -> None:
    """
    Log an error with full context information.
    
    Args:
        error: Exception that occurred
        context: Context dictionary with relevant information
        severity: Log severity (ERROR, WARNING, CRITICAL)
    """
    logger.bind(category="ERROR", **context).log(
        severity,
        f"Error occurred: {type(error).__name__}: {str(error)}"
    )
    
    # Log stack trace for ERROR and CRITICAL
    if severity in ["ERROR", "CRITICAL"]:
        logger.exception(error)


class LogContext:
    """
    Context manager for adding context to all logs within a block.
    
    Example:
        with LogContext(user_id="12345", conversation_state="GREETING"):
            logger.info("Processing user input")
            # All logs within this block will include user_id and conversation_state
    """
    
    def __init__(self, **context):
        """
        Initialize log context.
        
        Args:
            **context: Context key-value pairs to add to logs
        """
        self.context = context
        self.token = None
    
    def __enter__(self):
        """Enter context - bind context to logger."""
        self.token = logger.contextualize(**self.context)
        self.token.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - unbind context."""
        if self.token:
            self.token.__exit__(exc_type, exc_val, exc_tb)


# Performance monitoring decorator
def log_performance(operation_name: Optional[str] = None):
    """
    Decorator to log function performance.
    
    Args:
        operation_name: Name of operation (defaults to function name)
        
    Example:
        @log_performance("booking_creation")
        def create_booking(data):
            # ...
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.bind(category="PERFORMANCE").debug(
                    f"Performance | {name} | "
                    f"duration={duration:.3f}s | "
                    f"success=True"
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.bind(category="PERFORMANCE").warning(
                    f"Performance | {name} | "
                    f"duration={duration:.3f}s | "
                    f"success=False | "
                    f"error={type(e).__name__}"
                )
                
                raise
        
        return wrapper
    return decorator


# Initialize logging with default settings
def init_logging(environment: str = "development") -> None:
    """
    Initialize logging with environment-specific settings.
    
    Args:
        environment: Environment name ("development", "production", "test")
    """
    if environment == "production":
        configure_logging(
            log_level="INFO",
            log_to_file=True,
            format_type="detailed",
            rotation="100 MB",
            retention="90 days"
        )
    elif environment == "test":
        configure_logging(
            log_level="WARNING",
            log_to_file=False,
            format_type="simple"
        )
    else:  # development
        configure_logging(
            log_level="DEBUG",
            log_to_file=True,
            format_type="detailed",
            rotation="50 MB",
            retention="7 days"
        )
    
    logger.info(f"Logging initialized for {environment} environment")


# Auto-initialize with development settings if run as main module
if __name__ == "__main__":
    init_logging("development")
    
    # Test logging
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Test context
    with LogContext(user_id="test123", operation="test"):
        logger.info("Message with context")
    
    # Test booking event
    log_booking_event(
        event_type="CREATED",
        user_id="test123",
        booking_id="BK-001",
        details={"date": "2024-12-25", "time": "18:00"}
    )
