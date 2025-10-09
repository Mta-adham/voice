# Error Handling System

Comprehensive error handling infrastructure for the restaurant booking voice assistant.

## Overview

This module provides a complete error handling system that covers all aspects of the booking system including business logic errors, technical failures, and user interaction issues. The system is designed to:

- **Generate natural, conversational error messages** suitable for voice interfaces
- **Provide graceful degradation** when services fail
- **Maintain conversation context** across error recovery
- **Log errors comprehensively** for debugging
- **Offer alternatives** when primary requests cannot be fulfilled

## Components

### 1. `exceptions.py` - Exception Hierarchy

Comprehensive custom exception classes organized by category:

#### Business Logic Errors
- `BookingValidationError` - Invalid dates, party sizes, time slots, data formats
- `NoAvailabilityError` - No availability for requested date/time/party_size (includes alternatives)
- `CapacityExceededError` - Party size exceeds available capacity

#### Technical Errors - Audio
- `AudioDeviceError` - Audio device not available or lacks permissions
- `AudioRecordingError` - Audio recording fails
- `AudioPlaybackError` - Audio playback fails
- `SilenceDetectedError` - Only silence detected in audio input
- `UnclearAudioError` - Audio quality too poor for transcription

#### Technical Errors - Speech Services
- `STTError` - Speech-to-Text (Whisper) failures
- `TTSError` - Text-to-Speech failures
- `APIKeyError` - Invalid or missing API key
- `QuotaExceededError` - API quota exceeded
- `RateLimitError` - API rate limit hit

#### Technical Errors - LLM
- `LLMProviderError` - LLM provider failures
- `LLMTimeoutError` - LLM request timeouts
- `AllLLMProvidersFailed` - All configured LLM providers failed

#### Technical Errors - Database
- `DatabaseError` - Database operations fail
- `DatabaseConnectionError` - Database connection fails
- `DatabaseQueryError` - Database query fails

#### Technical Errors - Notifications
- `NotificationError` - Base notification error (non-blocking)
- `SMSDeliveryError` - SMS delivery failure
- `EmailDeliveryError` - Email delivery failure

#### User Interaction Errors
- `UserTimeoutError` - User does not respond after prompt
- `AmbiguousInputError` - Ambiguous or incomplete information
- `UserInterruptionError` - User speaks while agent is speaking

### 2. `error_messages.py` - Natural Language Messages

User-friendly message generation for all error types:

```python
from error_handling import generate_error_message

# Automatically generates appropriate message for any exception
user_message = generate_error_message(
    error=some_exception,
    context={"conversation_state": "collecting_date"},
    retry_count=1
)
```

Features:
- **Conversational tone** suitable for voice output
- **Context-aware messages** adapt to the situation
- **Alternative suggestions** when possible
- **Avoids technical jargon** in spoken responses

### 3. `handlers.py` - Error Handling Utilities

Centralized error handling with decorators and recovery strategies:

#### Decorators

```python
from error_handling import handle_errors, retry_on_error

@handle_errors(fallback_return=[], exceptions=(DatabaseError,))
def get_bookings():
    return query_database()

@retry_on_error(max_retries=3, exceptions=(DatabaseConnectionError,))
def connect_to_database():
    return create_connection()
```

#### Recovery Functions

```python
from error_handling import (
    handle_database_error,
    handle_llm_provider_failure,
    handle_tts_failure,
    handle_notification_failure,
    handle_conversation_error
)

# Handle database errors with retry logic
success, result = handle_database_error(
    error=db_error,
    operation="get_availability",
    retry_func=lambda: query_availability(),
    max_retries=3
)

# Handle LLM failures with provider failover
success, result = handle_llm_provider_failure(
    error=llm_error,
    failed_provider="openai",
    alternative_providers=["gemini", "claude"],
    llm_call_func=llm_chat,
    messages=[{"role": "user", "content": "Hello"}]
)
```

## New Services

### 1. `speech/whisper_stt.py` - Whisper STT Service

Speech-to-Text service with comprehensive error handling:

```python
from speech.whisper_stt import WhisperSTT

# Initialize (supports both API and local models)
stt = WhisperSTT(use_api=True)  # or use_api=False for local

# Transcribe audio
try:
    text = stt.transcribe_audio(audio_data, sample_rate)
except SilenceDetectedError:
    # Handle silence
    pass
except UnclearAudioError:
    # Handle poor audio quality
    pass
except STTError as e:
    # Handle other STT errors
    pass
```

Features:
- **API and local model support**
- **Automatic silence detection**
- **Audio quality validation**
- **Retry logic for transient failures**
- **Fallback to local model if API fails**

### 2. `services/notification_service.py` - Notification Service

SMS and Email delivery with graceful degradation:

```python
from services.notification_service import NotificationService

notification_service = NotificationService()

# Send booking confirmation (failures don't block booking flow)
results = notification_service.send_booking_confirmation(
    booking_data={
        "confirmation_id": "ABC123",
        "date": "2024-12-25",
        "time": "18:00",
        "party_size": 4,
        "customer_name": "John Doe"
    },
    phone="+1234567890",
    email="john@example.com"
)

# Check results
if not results["sms_sent"]:
    logger.warning(f"SMS failed: {results['sms_error']}")
if not results["email_sent"]:
    logger.warning(f"Email failed: {results['email_error']}")
```

Features:
- **Twilio SMS integration**
- **SendGrid email integration**
- **Template-based formatting**
- **Graceful degradation** (failures don't block booking)
- **Automatic fallback** between channels

## Enhanced Services

### 1. Audio Manager - Timeout Detection

Added timeout detection and speech activity monitoring:

```python
from audio.audio_manager import AudioManager

audio = AudioManager()

# Start recording with timeout
audio.start_recording(timeout_seconds=10.0)

# Check for timeout
is_timeout, elapsed = audio.check_user_timeout()
if is_timeout:
    raise UserTimeoutError(timeout_duration=elapsed)

# Check for speech activity
if audio.has_speech_activity():
    logger.info("User is speaking")

# Get silence duration
silence_duration = audio.get_silence_duration()
```

### 2. ElevenLabs TTS - Fallback Options

Added fallback TTS engines (pyttsx3, gTTS):

```python
from speech.elevenlabs_tts import ElevenLabsTTS, generate_speech_with_fallback

# Initialize primary TTS
tts = ElevenLabsTTS()

# Generate speech with automatic fallback
try:
    audio_data, sample_rate = generate_speech_with_fallback(
        text="Welcome to our restaurant!",
        primary_tts=tts,
        use_fallback=True  # Will try gTTS and pyttsx3 if ElevenLabs fails
    )
except Exception as e:
    # All TTS engines failed
    logger.error(f"All TTS engines failed: {e}")
```

Fallback order:
1. **ElevenLabs** (best quality, requires API key)
2. **gTTS** (good quality, requires internet)
3. **pyttsx3** (offline, always available)

### 3. LLM Service - Provider Failover

Added automatic provider failover:

```python
from services.llm_service import llm_chat_with_fallback, get_available_providers

# Get list of available providers
available = get_available_providers()  # ["openai", "gemini", "claude"]

# Call with automatic failover
try:
    response = llm_chat_with_fallback(
        messages=[{"role": "user", "content": "Hello"}],
        preferred_provider="openai",
        fallback_providers=["gemini", "claude"]
    )
except AllLLMProvidersFailed as e:
    # All providers failed
    logger.error(f"All LLM providers failed: {e.failed_providers}")
```

### 4. Booking Service - Centralized Error Handling

Updated to use centralized exceptions:

```python
from services.booking_service import BookingService
from error_handling import (
    BookingValidationError,
    NoAvailabilityError,
    CapacityExceededError
)

service = BookingService(session)

try:
    booking = service.create_booking(booking_data)
except BookingValidationError as e:
    # Invalid input - show friendly message
    user_msg = generate_error_message(e)
except NoAvailabilityError as e:
    # No availability - suggest alternatives
    if e.alternatives:
        user_msg = f"Sorry, but I can suggest: {e.alternatives}"
except CapacityExceededError as e:
    # Not enough capacity
    user_msg = f"Only {e.available_capacity} seats available"
```

## Usage Examples

### Example 1: Complete Error Handling in Conversation Flow

```python
from error_handling import (
    generate_error_message,
    handle_conversation_error,
    UserTimeoutError,
    STTError,
    BookingValidationError
)

def handle_user_input(audio_data, context, retry_count=0):
    """Handle user input with comprehensive error handling."""
    
    try:
        # Transcribe audio
        text = stt.transcribe_audio(audio_data, sample_rate)
        
        # Extract information
        extracted = extract_booking_info(text, context)
        
        # Validate
        validate_booking_request(
            extracted.date,
            extracted.time,
            extracted.party_size,
            raise_on_invalid=True
        )
        
        return extracted
        
    except SilenceDetectedError as e:
        response = handle_conversation_error(e, context, retry_count)
        return {"action": "retry_prompt", "message": response["message"]}
        
    except STTError as e:
        response = handle_conversation_error(e, context, retry_count)
        return {"action": "retry", "message": response["message"]}
        
    except BookingValidationError as e:
        user_msg = generate_error_message(e, context)
        return {"action": "clarify", "message": user_msg}
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        response = handle_conversation_error(e, context, retry_count)
        return {"action": response["action"], "message": response["message"]}
```

### Example 2: Database Operations with Retry

```python
from error_handling import retry_on_error, DatabaseConnectionError

@retry_on_error(
    max_retries=3,
    exceptions=(DatabaseConnectionError,),
    backoff_factor=2.0
)
def get_available_slots(date, party_size):
    """Get available time slots with automatic retry."""
    with get_db_session() as session:
        service = BookingService(session)
        return service.get_available_slots(date, party_size)
```

### Example 3: TTS with Graceful Degradation

```python
from speech.elevenlabs_tts import generate_speech_with_fallback
from error_handling import TTSError, log_error

def speak_message(text: str) -> None:
    """Speak message with fallback TTS options."""
    try:
        audio_data, sample_rate = generate_speech_with_fallback(
            text=text,
            primary_tts=elevenlabs_tts,
            use_fallback=True
        )
        
        audio_manager.play_audio(audio_data, sample_rate)
        
    except Exception as e:
        log_error(e, context={"text": text})
        # Last resort: print to console
        print(f"[VOICE]: {text}")
```

## Best Practices

1. **Always use specific exceptions** rather than generic Exception
2. **Include context** in exceptions for better debugging and user messages
3. **Use decorators** for common patterns (retry, error handling)
4. **Generate user-friendly messages** using `generate_error_message()`
5. **Log errors** with `log_error()` for comprehensive debugging
6. **Implement graceful degradation** for non-critical services
7. **Provide alternatives** when primary requests fail
8. **Test error scenarios** to ensure proper handling

## Environment Variables

Required environment variables for services:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/booking_db

# LLM Providers (at least one required)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...

# Speech Services
ELEVENLABS_API_KEY=...

# Notifications (optional)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
SENDGRID_API_KEY=...
```

## Testing

Test error handling with different scenarios:

```python
# Test timeout
audio.start_recording(timeout_seconds=1.0)
time.sleep(2.0)
assert audio.check_user_timeout()[0] == True

# Test validation errors
try:
    service.validate_booking_request(
        date=date.today() - timedelta(days=1),  # Past date
        time=time(18, 0),
        party_size=4,
        raise_on_invalid=True
    )
except BookingValidationError as e:
    assert "past" in str(e).lower()

# Test provider failover
response = llm_chat_with_fallback(
    messages=[{"role": "user", "content": "test"}],
    preferred_provider="invalid_provider",
    fallback_providers=["openai"]
)
assert response["provider"] == "openai"
```

## Logging

All errors are logged with comprehensive context:

```python
from error_handling import log_error

log_error(
    error=exception,
    context={
        "user_id": "user123",
        "conversation_state": "collecting_date",
        "retry_count": 1
    },
    level="error",
    include_traceback=True
)
```

Log levels:
- **ERROR**: For failures that need attention
- **WARNING**: For degraded service (fallbacks used)
- **INFO**: For error recovery success
- **DEBUG**: For detailed error context

## Success Criteria Checklist

- [x] No unhandled exceptions cause system crashes
- [x] All error scenarios from technical specs are handled
- [x] User receives natural, helpful responses for all error conditions
- [x] Alternative options offered when primary request cannot be fulfilled
- [x] All errors logged with sufficient context for debugging
- [x] System degrades gracefully when non-critical services fail
- [x] Conversation state maintained across error recovery
- [x] User-friendly error responses suitable for voice format

## Integration Notes

To integrate error handling into your conversation orchestrator:

1. Import error handling components
2. Wrap service calls with try-except blocks
3. Use `generate_error_message()` for user-friendly messages
4. Use `handle_conversation_error()` for complete error handling
5. Implement timeout checks in audio recording loops
6. Use fallback functions for TTS and LLM
7. Handle notification failures gracefully (don't block booking)

See examples above for specific integration patterns.
