# Error Handling System

Comprehensive error handling system for the restaurant booking voice agent.

## Overview

This module provides centralized error handling with:
- **Custom exception classes** for different error categories
- **Natural language error messages** for voice output
- **Graceful degradation** strategies for technical failures
- **Automatic retry logic** for transient errors
- **Context-aware logging** for debugging

## Architecture

### Exception Hierarchy

```
BookingAgentError (base)
├── Business Logic Errors
│   ├── BookingValidationError
│   ├── NoAvailabilityError
│   ├── InvalidDateError
│   ├── InvalidTimeError
│   └── PartySizeTooLargeError
├── Technical Errors
│   ├── AudioProcessingError
│   │   ├── TranscriptionError
│   │   └── TextToSpeechError
│   ├── LLMProviderError
│   ├── DatabaseError
│   └── NotificationError
└── User Interaction Errors
    ├── UserTimeoutError
    ├── AmbiguousInputError
    └── InterruptionError
```

All exceptions include:
- **user_message**: Friendly message for voice output
- **context**: Additional error context
- **recoverable**: Whether conversation can continue

## Usage

### Basic Error Handling

```python
from error_handling import (
    BookingValidationError,
    get_error_message,
    handle_booking_error
)

# Raise an error
try:
    if party_size > 8:
        raise PartySizeTooLargeError(
            "Party size exceeds maximum",
            party_size=party_size,
            max_party_size=8
        )
except PartySizeTooLargeError as e:
    # Get user-friendly message
    message = get_error_message(e)
    # "I'm sorry, but our maximum party size is 8 people..."
    
    # Or handle with full context
    result = handle_booking_error(e)
    print(result["user_message"])  # Speak this to user
    print(result["recoverable"])    # Continue conversation?
```

### Error Message Generation

```python
from error_handling.error_messages import ErrorMessageGenerator

generator = ErrorMessageGenerator(agent_name="Alex")

# Generate contextual error messages
error = NoAvailabilityError(
    "No slots available",
    date=date(2024, 12, 25),
    time=time(19, 0),
    party_size=4,
    available_alternatives=[time(18, 0), time(20, 0)]
)

message = generator.generate_message(error)
# "I'm sorry, but we don't have availability at 7:00 PM for 4 people 
#  on Tuesday, December 25. However, I do have openings at 6:00 PM 
#  or 8:00 PM. Would any of those work for you?"
```

### Centralized Error Handler

```python
from error_handling.handlers import ErrorHandler

handler = ErrorHandler(
    log_errors=True,
    generate_messages=True,
    user_id="user123"
)

try:
    # Some operation
    booking = create_booking(data)
except Exception as e:
    result = handler.handle_error(e, context={
        "booking_date": str(data.date),
        "component": "booking_service"
    })
    
    # result contains:
    # - error_type: "PartySizeTooLargeError"
    # - user_message: Friendly message to speak
    # - technical_message: Technical details for logs
    # - recoverable: bool
    # - should_retry: bool
```

## Graceful Degradation

### TTS Fallback

```python
from speech.elevenlabs_tts import TTSWithFallback

# Automatically falls back to pyttsx3/gTTS if ElevenLabs fails
tts = TTSWithFallback(
    elevenlabs_api_key=api_key,
    enable_fallback=True,
    prefer_gtts=True  # Use gTTS over pyttsx3
)

# Will use ElevenLabs, fall back to gTTS if unavailable
audio_data, sample_rate = tts.generate_speech("Hello!")
print(f"Using provider: {tts.get_current_provider()}")
```

### LLM Provider Failover

```python
from services.llm_service import llm_chat_with_failover

# Tries OpenAI first, falls back to Gemini, then Claude
response = llm_chat_with_failover(
    messages=[{"role": "user", "content": "Hello"}],
    preferred_provider="openai",
    fallback_providers=["gemini", "claude"]
)

print(f"Response from {response['provider']}: {response['content']}")
```

### Database Retry Logic

```python
from models.database import get_db_session_with_retry, init_db_with_retry

# Initialize DB with automatic retry on connection failure
engine = init_db_with_retry(
    database_url=db_url,
    max_retries=3,
    retry_delay=2.0
)

# Use sessions with automatic retry
with get_db_session_with_retry(max_retries=3) as session:
    booking = session.query(Booking).first()
    # Automatically retries on transient database errors
```

## Timeout Handling

### Audio Timeout

```python
from audio.audio_manager import AudioManager

audio = AudioManager()

try:
    # Wait for user to speak with timeout
    has_speech = audio.wait_for_speech(timeout=10.0)
    
    if not has_speech:
        # Handle timeout
        print("User didn't respond")
except UserTimeoutError as e:
    message = get_error_message(e)
    # "I didn't hear anything. Are you still there?"
```

### Conversation Timeout

```python
from conversation.state_manager import ConversationStateManager

manager = ConversationStateManager(enable_error_handling=True)

# Handle user timeout
result = manager.handle_timeout(timeout_seconds=10)

if result.get("should_end_conversation"):
    # Max timeouts reached, end conversation gracefully
    print(result["user_message"])
    # "I haven't heard from you, so I'll end this call..."
else:
    # Ask user if they're still there
    print(result["user_message"])
    # "I didn't hear anything. Are you still there?"
```

## Error Logging

All errors are logged with full context:

```python
from error_handling.handlers import log_error_with_context

try:
    # Some operation
    result = process_booking(data)
except Exception as e:
    log_error_with_context(
        error=e,
        context={
            "user_id": "user123",
            "conversation_state": "COLLECTING_DATE",
            "booking_date": "2024-12-25",
            "component": "booking_service"
        },
        level="ERROR",
        include_traceback=True
    )
```

Log output includes:
- Error type and message
- Full context dictionary
- Stack trace (if enabled)
- Timestamp and user ID

## Retry Utilities

### Function Retry Decorator

```python
from error_handling.handlers import with_retry

@with_retry(
    max_retries=3,
    delay=1.0,
    backoff=2.0,
    retriable_exceptions=(OperationalError, DisconnectionError)
)
def query_database():
    return session.query(Booking).all()

# Automatically retries on database errors with exponential backoff
bookings = query_database()
```

### Manual Retry Check

```python
from error_handling.handlers import is_retriable_error

try:
    result = some_operation()
except Exception as e:
    if is_retriable_error(e):
        # This error should be retried
        logger.info("Retrying operation...")
        result = some_operation()
    else:
        # Not retriable, handle differently
        raise
```

## Error Categories

### Business Logic Errors

**Not retriable** - User needs to provide different input

- `BookingValidationError`: General validation failure
- `NoAvailabilityError`: No slots available for request
- `InvalidDateError`: Date in past or beyond booking window
- `InvalidTimeError`: Time outside operating hours
- `PartySizeTooLargeError`: Party size exceeds maximum

### Technical Errors

**May be retriable** - System issue, might be transient

- `AudioProcessingError`: Audio recording/playback issues
- `TranscriptionError`: Speech-to-text failure
- `TextToSpeechError`: TTS generation failure (triggers fallback)
- `LLMProviderError`: LLM API failure (triggers failover)
- `DatabaseError`: Database connection/query issues (retries)
- `NotificationError`: SMS/email delivery failure (non-blocking)

### User Interaction Errors

**Recoverable** - Conversation can continue

- `UserTimeoutError`: User didn't respond (re-prompt)
- `AmbiguousInputError`: Input unclear (ask for clarification)
- `InterruptionError`: User spoke while agent speaking (pause and listen)

## Integration with Existing Code

The error handling system is designed to work seamlessly with existing code:

### Booking Service

```python
from services.booking_service import BookingService

service = BookingService(session)

# Validation now raises enhanced exceptions
try:
    service.validate_booking_request(
        date=booking_date,
        time=booking_time,
        party_size=party_size,
        raise_enhanced_errors=True
    )
except InvalidDateError as e:
    # Get user-friendly message
    message = get_error_message(e)
    # "I'm sorry, but that date has already passed..."
```

### State Manager

```python
from conversation.state_manager import ConversationStateManager

manager = ConversationStateManager(enable_error_handling=True)

# Handle validation errors during updates
try:
    result = manager.update_context(date="2024-12-25")
except BookingValidationError as e:
    result = manager.handle_validation_error(e, field="date")
    print(result["user_message"])
```

## Best Practices

1. **Always use context**: Include relevant context when raising errors
   ```python
   raise NoAvailabilityError(
       "No slots available",
       date=booking_date,
       party_size=party_size,
       available_alternatives=alternative_slots  # Helps generate better messages
   )
   ```

2. **Log with context**: Use `log_error_with_context` for debugging
   ```python
   log_error_with_context(
       error=e,
       context={"user_id": user_id, "state": current_state}
   )
   ```

3. **Check recoverability**: Determine if conversation can continue
   ```python
   if result["recoverable"]:
       # Continue conversation, ask for correction
       speak(result["user_message"])
   else:
       # End conversation gracefully
       speak(result["user_message"])
       end_call()
   ```

4. **Use fallbacks**: Enable fallback services for critical functionality
   ```python
   tts = TTSWithFallback(enable_fallback=True)  # TTS always works
   response = llm_chat_with_failover(...)       # LLM always responds
   ```

5. **Retry transient errors**: Use retry logic for database and API calls
   ```python
   engine = init_db_with_retry(max_retries=3)
   with get_db_session_with_retry() as session:
       # Operations automatically retry on transient errors
   ```

## Testing Error Handling

```python
# Test error messages
from error_handling.error_messages import ErrorMessageGenerator

generator = ErrorMessageGenerator()

# Test various error scenarios
errors = [
    InvalidDateError("Past date", date=date(2020, 1, 1), reason="past"),
    PartySizeTooLargeError("Too large", party_size=10, max_party_size=8),
    UserTimeoutError("Timeout", timeout_seconds=10, retry_count=0)
]

for error in errors:
    message = generator.generate_message(error)
    print(f"{type(error).__name__}: {message}")
```

## Success Criteria

✅ No unhandled exceptions cause system crashes
✅ All error scenarios have user-friendly voice messages
✅ Alternative options offered when primary request fails
✅ All errors logged with sufficient debugging context
✅ System degrades gracefully when non-critical services fail
✅ Conversation state maintained across error recovery
✅ Timeout handling prevents indefinite waiting
✅ TTS fallback ensures voice output always works
✅ LLM failover ensures conversation always continues
✅ Database retries handle transient connection issues

## Dependencies

- `loguru`: For logging
- `tenacity`: For retry logic (in LLM service)
- `pyttsx3` or `gtts`: For TTS fallback (optional)

## Files

- `exceptions.py`: Custom exception classes
- `error_messages.py`: Natural language message generation
- `handlers.py`: Centralized error handling utilities
- `README.md`: This documentation
