# Error Handling System

Comprehensive error handling framework for the voice-based restaurant booking system.

## Overview

This module provides centralized error handling with:
- **Custom exception classes** for all error types
- **Natural language error messages** optimized for voice output
- **Graceful degradation** strategies (TTS fallback, LLM provider failover)
- **Timeout management** for user interactions
- **Centralized logging** with structured context

## Architecture

### 1. Exception Hierarchy

```
BookingSystemError (base)
├── Business Logic Errors
│   ├── BookingValidationError
│   ├── NoAvailabilityError
│   ├── InvalidDateError
│   ├── InvalidTimeError
│   └── InvalidPartySizeError
│
├── Audio Processing Errors
│   ├── AudioProcessingError
│   ├── STTError
│   ├── TTSError
│   ├── UnclearAudioError
│   └── SilenceDetectedError
│
├── Technical Errors
│   ├── LLMProviderError
│   ├── DatabaseError
│   └── NotificationError
│
├── User Interaction Errors
│   ├── UserTimeoutError
│   ├── AmbiguousInputError
│   └── UserInterruptionError
│
└── System Errors
    └── ConfigurationError
```

### 2. Key Components

#### exceptions.py
Custom exception classes with:
- Human-readable error messages
- User-friendly messages for voice output
- Context information for debugging
- Recoverability flags

#### error_messages.py
Natural language message generation:
- Converts exceptions to speakable messages
- Suggests alternative actions
- Formats dates/times in friendly format
- Includes alternative suggestions when available

#### handlers.py
Error handling utilities:
- `ErrorContext`: Context manager for error tracking
- `with_retry`: Decorator for automatic retries
- `with_timeout`: Decorator for timeout handling
- `graceful_degradation`: Decorator for fallback logic
- `CircuitBreaker`: Prevents cascading failures

#### timeout_manager.py
User interaction timeout management:
- `TimeoutManager`: Tracks user response times
- `SilenceDetector`: Detects silent or unclear audio
- Re-prompting logic
- Conversation abandonment detection

#### logging_config.py
Centralized logging configuration:
- Structured logging with loguru
- Separate log files for errors, bookings, etc.
- Performance monitoring
- Contextual logging

## Usage Examples

### 1. Basic Error Handling

```python
from error_handling import (
    BookingValidationError,
    get_error_message,
    ErrorContext,
    handle_error_with_context
)

# Create error context
error_context = ErrorContext(
    user_id="12345",
    conversation_state="COLLECTING_DATE"
)

try:
    # Some operation that might fail
    validate_booking(date, time, party_size)
except Exception as e:
    # Handle error and get user-friendly response
    response = handle_error_with_context(
        error=e,
        error_context=error_context,
        should_raise=False
    )
    
    # Speak the error message to user
    tts.speak(response["user_message"])
    
    # Take suggested action if available
    if response["next_action"]:
        prompt_user(response["next_action"])
```

### 2. Graceful Degradation

```python
from error_handling import graceful_degradation

@graceful_degradation(
    fallback_value="Default response",
    log_message="LLM call failed, using fallback"
)
def call_llm(messages):
    # Try primary LLM
    return llm_chat("openai", messages)
```

### 3. Timeout Management

```python
from error_handling import TimeoutManager, UserTimeoutError

timeout_manager = TimeoutManager(
    initial_timeout_seconds=10,
    max_reprompts=2
)

# Start conversation
timeout_manager.reset()

# Wait for user input
timeout_manager.mark_prompt()
user_input = record_audio()
timeout_manager.mark_activity()

# Check for timeout
try:
    timeout_manager.check_timeout()
except UserTimeoutError as e:
    if timeout_manager.should_reprompt():
        message = timeout_manager.get_reprompt_message()
        tts.speak(message)
    else:
        # Give up and end conversation
        end_conversation()
```

### 4. Automatic Retry

```python
from error_handling import with_retry
from sqlalchemy.exc import OperationalError

@with_retry(
    max_attempts=3,
    delay=1.0,
    backoff=2.0,
    exceptions=(OperationalError,)
)
def query_database():
    return session.query(Booking).all()
```

### 5. Circuit Breaker Pattern

```python
from error_handling import CircuitBreaker

# Create circuit breaker for external service
sms_circuit = CircuitBreaker(
    failure_threshold=5,
    timeout_seconds=60,
    name="SMS Service"
)

try:
    sms_circuit.call(send_sms, phone_number, message)
except Exception as e:
    # Circuit is open, service unavailable
    logger.warning(f"SMS service unavailable: {e}")
    # Try alternative notification method
```

### 6. Structured Logging

```python
from error_handling import (
    init_logging,
    LogContext,
    log_booking_event,
    log_performance
)

# Initialize logging
init_logging(environment="production")

# Use context for all logs in block
with LogContext(user_id="12345", session_id="abc-123"):
    logger.info("Processing booking request")
    # All logs here will include user_id and session_id

# Log booking events for audit trail
log_booking_event(
    event_type="CREATED",
    user_id="12345",
    booking_id="BK-001",
    details={"date": "2024-12-25", "time": "18:00"}
)

# Performance monitoring
@log_performance("booking_creation")
def create_booking(data):
    # Function execution time will be logged
    pass
```

## Error Recovery Strategies

### 1. Business Logic Errors
- **No availability**: Suggest alternative time slots
- **Invalid date**: Prompt for valid date within booking window
- **Invalid time**: Show operating hours and re-prompt
- **Invalid party size**: Suggest calling for large groups

### 2. Audio Processing Errors
- **Unclear audio**: Ask user to repeat
- **Silence detected**: Check if user is still there
- **STT failure**: Re-prompt with simpler language
- **TTS failure**: Fall back to alternative TTS provider

### 3. Technical Errors
- **LLM provider failure**: Try alternative providers (OpenAI → Gemini → Claude)
- **Database connection error**: Retry with exponential backoff
- **Notification failure**: Try alternative channel (SMS → Email or vice versa)

### 4. User Interaction Errors
- **Timeout**: Re-prompt up to 2 times, then gracefully end
- **Ambiguous input**: Ask clarifying questions
- **Interruption**: Acknowledge and let user continue

## Integration with Existing Modules

### booking_service.py
- Raises `BookingValidationError`, `NoAvailabilityError`, etc.
- Includes alternative suggestions in exceptions
- Uses `@log_function_call` and `@with_retry` decorators

### llm_service.py
- Enhanced with automatic provider failover
- Tries all available providers before failing
- Returns attempted providers in response

### audio_manager.py
- Raises `AudioProcessingError`, `SilenceDetectedError`, etc.
- Validates audio quality (energy, duration)
- Uses retry logic for transient failures

### speech/tts_fallback.py
- New unified TTS service
- Tries ElevenLabs → gTTS → pyttsx3
- Transparent fallback on failures

## Configuration

### Environment Variables
```bash
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Enable file logging
LOG_TO_FILE=true

# Log directory
LOG_DIR=logs

# Environment (development, production, test)
ENVIRONMENT=production
```

### Timeout Configuration
```python
# In your orchestrator/agent:
timeout_manager = TimeoutManager(
    initial_timeout_seconds=10,    # First response timeout
    reprompt_timeout_seconds=15,   # After re-prompt timeout
    max_reprompts=2,                # Max re-prompts before giving up
    abandonment_timeout_seconds=60 # Total timeout before abandoning
)
```

### Logging Configuration
```python
from error_handling import configure_logging

configure_logging(
    log_level="INFO",
    log_to_file=True,
    log_dir="logs",
    rotation="100 MB",
    retention="30 days",
    format_type="detailed"  # "simple", "detailed", or "json"
)
```

## Testing

### Test Error Messages
```python
from error_handling import get_error_message, InvalidDateError
from datetime import date

error = InvalidDateError(
    message="Date in past",
    invalid_date=date(2023, 1, 1),
    reason="past"
)

message = get_error_message(error)
print(message)
# "I'm sorry, but that date has already passed. We can only book..."
```

### Test Timeout Manager
```python
from error_handling import TimeoutManager
import time

manager = TimeoutManager(initial_timeout_seconds=2)
manager.reset()
manager.mark_prompt()

time.sleep(3)  # Simulate delay

try:
    manager.check_timeout()
except UserTimeoutError:
    print("Timeout detected correctly")
```

## Best Practices

1. **Always use custom exceptions**: Don't raise generic `Exception` or `ValueError`
2. **Provide context**: Include relevant information in exception context
3. **Log at appropriate level**: DEBUG for trace, INFO for events, WARNING for recoverable errors, ERROR for failures
4. **Use error context**: Track errors within conversation context
5. **Handle errors gracefully**: Always provide user-friendly voice messages
6. **Suggest alternatives**: When possible, offer alternative options to user
7. **Monitor performance**: Use `@log_performance` on critical paths
8. **Test error paths**: Ensure all error scenarios are tested

## Maintenance

### Adding New Error Types
1. Add exception class to `exceptions.py`
2. Add message handler to `error_messages.py`
3. Update `__init__.py` exports
4. Add usage example to this README

### Monitoring
- Check `logs/errors_*.log` for error patterns
- Monitor `logs/bookings_*.log` for audit trail
- Review circuit breaker open/close events
- Analyze timeout statistics

## Dependencies

- `loguru`: Structured logging
- `tenacity`: Retry logic (already used in llm_service)
- Standard library: `functools`, `time`, `datetime`, `typing`

## Future Enhancements

- [ ] Error rate alerting (email/SMS on high error rate)
- [ ] Metrics dashboard (error types, recovery rates)
- [ ] A/B testing for error messages
- [ ] Voice sentiment analysis for error detection
- [ ] Automatic error message optimization based on user feedback
