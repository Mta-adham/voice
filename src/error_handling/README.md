# Error Handling Module

Comprehensive error handling system for the Restaurant Booking Voice Agent. This module provides custom exceptions, natural language error messages, fallback strategies, and graceful degradation across all system components.

## Overview

The error handling module consists of three main components:

1. **Custom Exceptions** (`exceptions.py`) - Structured exception classes for different error categories
2. **Error Messages** (`error_messages.py`) - Natural language message generation for voice responses
3. **Error Handlers** (`handlers.py`) - Centralized error handling utilities and logging

## Features

✅ **Comprehensive Error Coverage**
- Business logic errors (booking validation, availability)
- Technical errors (STT/TTS, LLM, database)
- User interaction errors (timeouts, ambiguous input)

✅ **Natural Language Responses**
- User-friendly messages without technical jargon
- Conversational tone suitable for voice agent
- Variety in phrasing for more natural interactions

✅ **Graceful Degradation**
- TTS fallback: ElevenLabs → pyttsx3 → gTTS
- LLM fallback: Primary provider → Alternative providers
- Non-blocking notification failures

✅ **Recovery Strategies**
- Alternative time slot suggestions
- Automatic retry with exponential backoff
- Database reconnection on transient failures

## Error Categories

### Business Logic Errors

```python
from error_handling import (
    BookingValidationError,
    NoAvailabilityError,
    InvalidDateError,
    InvalidTimeError,
    InvalidPartySizeError,
)

# Example: No availability
raise NoAvailabilityError(
    date=requested_date,
    time=requested_time,
    party_size=4,
    alternative_slots=[...],  # Alternative suggestions
)
```

### Technical Errors

```python
from error_handling import (
    AudioProcessingError,
    STTError,
    TTSError,
    LLMProviderError,
    DatabaseError,
    NotificationError,
)

# Example: LLM provider timeout
raise LLMTimeoutError(provider="openai")

# Example: Database connection error
raise DatabaseConnectionError(
    message="Connection lost",
    user_message="I'm having trouble connecting to our system. Please try again."
)
```

### User Interaction Errors

```python
from error_handling import (
    UserTimeoutError,
    AmbiguousInputError,
    UserCorrectionError,
)

# Example: User timeout
raise UserTimeoutError(
    timeout_seconds=10,
    prompt="What date would you like?",
    retry_count=1
)
```

## Usage Examples

### 1. Handling Booking Errors

```python
from error_handling import handle_booking_error, get_error_message

try:
    booking = booking_service.create_booking(booking_data)
except BookingValidationError as e:
    # Get structured error info
    error_info = handle_booking_error(
        error=e,
        user_id="user123",
        conversation_state="collecting_date"
    )
    
    # Get natural language message for voice response
    spoken_message = error_info["user_message"]
    
    # Check for alternatives
    if error_info["context"].get("alternatives"):
        alternatives = error_info["context"]["alternatives"]
        # Offer alternatives to user
```

### 2. Using Error Messages

```python
from error_handling import get_error_message, ErrorMessageGenerator

try:
    # ... some operation ...
except Exception as e:
    # Generate user-friendly message
    message = get_error_message(e)
    
    # Speak message to user via TTS
    tts.generate_speech_with_fallback(message)
```

### 3. TTS with Fallback

```python
from speech.elevenlabs_tts import ElevenLabsTTS

tts = ElevenLabsTTS()

try:
    # Automatically falls back to pyttsx3 or gTTS on failure
    audio_data, rate = tts.generate_speech_with_fallback(
        text="Your reservation is confirmed!",
        use_fallback=True
    )
except ElevenLabsTTSError as e:
    logger.error(f"All TTS methods failed: {e}")
    # Handle complete TTS failure
```

### 4. LLM with Provider Failover

```python
from services.llm_service import llm_chat_with_fallback

try:
    response = llm_chat_with_fallback(
        primary_provider="openai",
        messages=[{"role": "user", "content": "Hello"}],
        fallback_providers=["gemini", "claude"]
    )
    
    # Response includes which provider was used
    logger.info(f"Used provider: {response['provider']}")
    
except LLMError as e:
    logger.error(f"All LLM providers failed: {e}")
    # Handle complete LLM failure
```

### 5. Audio Recording with Timeout

```python
from audio.audio_manager import AudioManager

with AudioManager() as audio:
    # Record with automatic timeout after silence
    audio_data, rate, timed_out = audio.record_with_timeout(
        max_duration=30.0,  # Maximum 30 seconds
        timeout_after_silence=3.0  # Stop after 3 seconds of silence
    )
    
    if timed_out:
        # Handle user timeout
        raise UserTimeoutError(
            timeout_seconds=30,
            prompt="What date would you like?"
        )
```

### 6. Database Operations with Retry

```python
from models.database import get_db_session_with_retry, retry_on_db_error

# Using context manager with automatic retry
with get_db_session_with_retry(max_retries=3) as session:
    booking = session.query(Booking).filter_by(id=booking_id).first()

# Using decorator for custom functions
@retry_on_db_error(max_retries=3)
def create_booking(session, data):
    # ... database operations ...
    pass
```

## Configuration

### Fallback TTS

Fallback TTS requires optional dependencies:

```bash
pip install pyttsx3  # Offline TTS
pip install gTTS     # Google TTS (online)
```

If not installed, the system will skip unavailable fallbacks.

### LLM Provider Failover

Ensure API keys are configured for fallback providers:

```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

### Database Retry Settings

Configure retry behavior in database operations:

```python
# In models/database.py
retry_on_db_error(
    max_retries=3,           # Number of retries
    initial_delay=0.5,       # Initial delay in seconds
    backoff_factor=2.0,      # Exponential backoff multiplier
    retry_on=(OperationalError,)  # Exception types to retry
)
```

## Best Practices

### 1. Always Use User-Friendly Messages

```python
# ❌ Bad - Technical message
raise DatabaseError("Connection to PostgreSQL failed")

# ✅ Good - User-friendly message
raise DatabaseConnectionError(
    message="Connection to PostgreSQL failed",
    user_message="I'm having trouble connecting to our system. Please try again in a moment."
)
```

### 2. Include Context for Recovery

```python
# ✅ Good - Include alternatives
raise NoAvailabilityError(
    date=date,
    time=time,
    party_size=4,
    alternative_slots=get_alternatives()  # Help user find solution
)
```

### 3. Log Errors with Context

```python
from error_handling import log_error_with_context

try:
    # ... operation ...
except Exception as e:
    log_error_with_context(
        error=e,
        operation="create_booking",
        user_id=user_id,
        conversation_state=state,
        additional_context={"booking_data": booking_data}
    )
    raise
```

### 4. Handle Non-Critical Failures Gracefully

```python
try:
    send_confirmation_email(booking)
except EmailDeliveryError as e:
    # Log but don't fail the booking
    logger.warning(f"Email failed: {e}")
    # Still return success, user has booking
```

### 5. Use Appropriate Error Types

```python
# For validation errors
if party_size > max_size:
    raise InvalidPartySizeError(party_size, max_size)

# For availability issues
if not slots:
    raise NoAvailabilityError(date, time, party_size, alternatives)

# For technical issues
if connection_lost:
    raise DatabaseConnectionError(...)
```

## Integration with Conversation Flow

```python
from error_handling import get_error_message, handle_timeout_error

def handle_user_response(audio_manager, tts, max_wait=10):
    """Example of integrating error handling in conversation."""
    
    audio_manager.start_recording()
    
    # Wait for user to start speaking
    if not audio_manager.wait_for_speech(timeout=max_wait):
        # User didn't respond
        error = UserTimeoutError(
            timeout_seconds=max_wait,
            prompt="What date would you like?",
            retry_count=0
        )
        
        # Get natural language response
        message = get_error_message(error)
        
        # Speak to user
        audio_data, rate = tts.generate_speech_with_fallback(message)
        audio_manager.play_audio(audio_data, rate)
        
        return None
    
    # Continue with recording...
```

## Error Message Customization

You can customize error messages by modifying templates in `error_messages.py`:

```python
# In error_messages.py
TEMPLATES = {
    "no_availability_date": [
        "I'm sorry, but we're fully booked on {date_str}. {alternatives}",
        "Unfortunately, we don't have any availability on {date_str}. {alternatives}",
        # Add your custom messages here
    ],
}
```

## Testing Error Handling

```python
import pytest
from error_handling import NoAvailabilityError, get_error_message

def test_no_availability_message():
    """Test natural language message generation."""
    error = NoAvailabilityError(
        date=date(2024, 12, 25),
        time=time(19, 0),
        party_size=4,
        alternative_slots=[
            {"time": time(18, 0)},
            {"time": time(20, 0)},
        ]
    )
    
    message = get_error_message(error)
    
    assert "fully booked" in message.lower() or "no availability" in message.lower()
    assert "18" in message or "18:00" in message  # Alternative time mentioned
```

## Monitoring and Logging

All errors are logged with appropriate context using `loguru`:

```python
# Error logs include:
# - Error type and message
# - User ID and conversation state
# - Stack traces for unexpected errors
# - Retry attempts and outcomes

# Example log output:
# 2024-12-20 10:30:45 | ERROR | Booking validation failed | 
#   user_id=user123 | field=date | value=2024-12-15 | reason=past date
```

## Support

For issues or questions about error handling:
1. Check logs for detailed error context
2. Review error message templates
3. Verify fallback configurations
4. Check API keys for fallback services

## Future Enhancements

Potential improvements:
- [ ] Metrics collection for error rates
- [ ] A/B testing for error messages
- [ ] Multi-language support
- [ ] Custom error recovery workflows
- [ ] Integration with monitoring services (Sentry, etc.)
