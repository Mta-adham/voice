# Voice Agent Orchestrator Documentation

## Overview

The Voice Agent Orchestrator (`src/agent/orchestrator.py`) is the main coordination layer for the restaurant booking voice agent system. It integrates all components into a seamless conversation loop that handles natural voice interactions from greeting to booking confirmation.

## Architecture

### Component Integration

The orchestrator coordinates these key components:

```
┌─────────────────────────────────────────────────────────────┐
│                      VoiceAgent                             │
│                    (Orchestrator)                           │
└──────┬──────────────────────────────────────────────┬───────┘
       │                                               │
       ├─► AudioManager         ──► Recording/Playback│
       ├─► ElevenLabsTTS        ──► Text-to-Speech   │
       ├─► WhisperTranscriber   ──► Speech-to-Text   │
       ├─► StateManager         ──► Conversation Flow│
       ├─► NLU Extractor        ──► Info Extraction  │
       ├─► ResponseGenerator    ──► Dynamic Responses│
       ├─► BookingService       ──► Availability/DB  │
       ├─► SMS Service          ──► Confirmations    │
       └─► Email Service        ──► Confirmations    │
```

## Implementation Details

### Initialization Flow

```python
agent = VoiceAgent()
agent.initialize()  # Verifies all dependencies
```

**Initialization Steps:**
1. Create database session
2. Initialize AudioManager (verify audio devices)
3. Initialize ElevenLabs TTS (verify API key)
4. Initialize Whisper transcriber
5. Create ConversationStateManager
6. Create BookingService with DB session

**Error Handling:**
- `InitializationError` - Wraps all initialization failures
- Specific checks for audio devices, API keys, database connection
- Detailed logging for debugging

### Main Conversation Loop

```python
success = agent.run()
```

**Loop Iteration:**

```
1. Listen for user input (with voice activity detection)
   ├─ Start recording
   ├─ Monitor for silence (2s threshold)
   └─ Stop when silence detected or timeout

2. Transcribe audio to text
   ├─ Send to Whisper STT
   └─ Handle transcription errors

3. Process utterance
   ├─ Extract booking information (NLU)
   ├─ Update conversation context
   └─ Detect corrections

4. Determine next action
   ├─ Check if all info collected
   ├─ Auto-advance conversation state
   └─ Decide: collect_info | confirm | complete | exit

5. Execute action
   ├─ Generate contextual response
   ├─ Convert to speech (TTS)
   └─ Play through speakers

6. Handle special cases
   ├─ Availability check (when date/time/party_size ready)
   ├─ Confirmation dialogue
   ├─ Booking creation
   └─ Send confirmations
```

### Voice Activity Detection

The orchestrator implements sophisticated VAD:

```python
def _listen_for_input(self, timeout: float = None) -> Optional[Tuple[np.ndarray, int]]:
    # Start recording
    self._audio_manager.start_recording()
    
    # Monitor for speech end
    while True:
        if self._audio_manager.detect_silence(duration=2.0):
            if has_sound:  # Only stop after detecting initial sound
                break
        
        # Check timeouts
        if elapsed > timeout:
            return None
```

**Features:**
- Waits for initial sound before monitoring silence
- Configurable silence threshold (2 seconds default)
- Timeout handling (15s default, 30s extended)
- Maximum recording duration safety (30s)

### Information Extraction

```python
def _process_utterance(self, utterance: str) -> Dict[str, Any]:
    # Get current context
    context_dict = {
        "date": context.date,
        "time": context.time,
        # ... other fields
        "current_date": date.today()
    }
    
    # Extract information using NLU
    extraction = extract_booking_info(utterance, context_dict)
    
    # Update state manager
    updates = self._build_updates(extraction)
    update_result = self._state_manager.update_context(**updates)
    
    return processing_result
```

**Capabilities:**
- Extracts multiple fields simultaneously
- Handles corrections ("actually, make that 4 people")
- Validates all extracted values
- Detects ambiguity and need for clarification

### State Management

**State Progression:**
```
GREETING
   ↓
COLLECTING_DATE
   ↓
COLLECTING_TIME
   ↓
COLLECTING_PARTY_SIZE
   ↓
COLLECTING_NAME
   ↓
COLLECTING_PHONE
   ↓
CONFIRMING
   ↓
COMPLETED
```

**State Transitions:**
```python
def _determine_next_action(self) -> str:
    if context.is_complete():
        # All info collected
        self._state_manager.transition_to(ConversationState.CONFIRMING)
        return "confirm"
    
    # Auto-advance based on missing fields
    new_state = self._state_manager.auto_advance_state()
    return "collect_info"
```

### Booking Creation

```python
def _create_booking(self) -> Optional[int]:
    booking_data = BookingCreate(
        date=context.date,
        time_slot=context.time,
        party_size=context.party_size,
        customer_name=context.name,
        customer_phone=context.phone,
        status="confirmed"
    )
    
    booking = self._booking_service.create_booking(booking_data)
    return booking.id
```

**Atomic Transaction:**
1. Validate booking parameters
2. Check time slot capacity (with row lock)
3. Create booking record
4. Update slot capacity
5. Commit or rollback

### Error Handling Strategy

#### Audio Errors
```python
try:
    audio_result = self._listen_for_input()
except AudioRecordingError:
    # Ask user to repeat
    self._generate_and_speak_response("clarification")
```

#### Transcription Errors
```python
utterance = self._transcribe_audio(audio_data, sample_rate)
if not utterance or utterance.strip() == "":
    # Ask for clarification
    self._generate_and_speak_response("clarification")
    continue
```

#### API Errors
```python
try:
    response = generate_response(state, context)
except ResponseGenerationError:
    # Use fallback response
    response = get_fallback_response(state)
```

#### Booking Errors
```python
try:
    booking_id = self._create_booking()
except CapacityError:
    # No availability
    self._generate_and_speak_response("no_availability")
except ValidationError as e:
    # Invalid parameters
    logger.error(f"Validation failed: {e}")
```

### Timeout Handling

**Two-Tier Timeout:**

```python
# First timeout (15s)
if audio_result is None:
    self._timeout_count += 1
    if self._timeout_count == 1:
        # Prompt user
        self._generate_and_speak_response("clarification")
        continue

# Second timeout (30s total)
if self._timeout_count >= 2:
    # End call gracefully
    self._generate_and_speak_response("goodbye")
    break
```

### Confirmation Flow

```python
# Present details for confirmation
self._generate_and_speak_response("confirming", data=booking_details)

# Listen for confirmation
confirmation_utterance = self._transcribe_audio(audio_data, sample_rate)

# Check for positive confirmation
confirm_keywords = ["yes", "correct", "confirm", "right"]
is_confirmed = any(keyword in confirmation_utterance.lower() 
                   for keyword in confirm_keywords)

if is_confirmed:
    booking_id = self._create_booking()
    self._send_confirmations()
    self._state_manager.transition_to(ConversationState.COMPLETED)
```

### Notification Flow

```python
def _send_confirmations(self) -> None:
    booking_details = {
        "booking_id": self._booking_id,
        "name": context.name,
        "date": context.date.strftime("%A, %B %d, %Y"),
        "time": context.time.strftime("%I:%M %p"),
        "party_size": context.party_size,
        "phone": context.phone,
    }
    
    # Send SMS
    try:
        send_sms_confirmation(context.phone, booking_details)
    except SMSError as e:
        logger.error(f"SMS failed: {e}")
        # Continue anyway - booking is still created
    
    # Send Email (if available)
    # ... similar error handling
```

### Graceful Shutdown

```python
def shutdown(self) -> None:
    # Stop any active recording
    if self._audio_manager and self._audio_manager._recording:
        self._audio_manager.stop_recording()
    
    # Close database session
    if self._session:
        self._session.close()
    
    # Log session summary
    if self._booking_id:
        logger.info(f"Session completed with booking ID: {self._booking_id}")
```

## Configuration Options

### Timeout Configuration
```python
agent = VoiceAgent(
    input_timeout=20.0,      # User input timeout
    extended_timeout=40.0     # Total timeout before exit
)
```

### Component Injection (for testing)
```python
agent = VoiceAgent(
    session=mock_session,
    audio_manager=mock_audio,
    tts=mock_tts,
    transcriber=mock_transcriber
)
```

## Usage Examples

### Basic Usage

```python
from agent.orchestrator import VoiceAgent

# Create and run agent
agent = VoiceAgent()
agent.initialize()
success = agent.run()
agent.shutdown()
```

### With Context Manager

```python
from agent.orchestrator import create_voice_agent

with create_voice_agent() as agent:
    agent.initialize()
    success = agent.run()
    # Automatic shutdown
```

### Custom Configuration

```python
agent = VoiceAgent(
    input_timeout=20.0,
    extended_timeout=45.0
)
agent.initialize()
agent.run()
```

### Production Deployment

```bash
# Run with proper logging
python src/main.py 2>&1 | tee logs/agent.log
```

## Testing Strategy

### Unit Tests
- Mock all external dependencies
- Test individual methods in isolation
- Verify error handling paths

```python
def test_listen_for_input():
    mock_audio = Mock(spec=AudioManager)
    agent = VoiceAgent(audio_manager=mock_audio)
    # Test VAD logic
```

### Integration Tests
- Use test database
- Mock audio I/O
- Test real API calls (with test keys)

```python
def test_booking_flow():
    agent = VoiceAgent(session=test_session)
    # Test full information collection to booking
```

### End-to-End Tests
- Requires actual hardware
- Use pre-recorded audio samples
- Verify complete flows

## Performance Considerations

### Latency Sources
1. **Speech-to-Text**: ~1-3 seconds (Whisper)
2. **NLU Extraction**: ~0.5-1 second (LLM)
3. **Response Generation**: ~0.5-1 second (LLM)
4. **Text-to-Speech**: ~0.5-2 seconds (ElevenLabs)

**Total Response Time**: ~3-7 seconds per turn

### Optimization Opportunities
- Cache common responses
- Parallel API calls where possible
- Stream TTS audio while generating
- Reduce LLM prompt sizes

## Logging

### Log Levels

**INFO**: Major events
```
- Component initialization
- State transitions
- Booking creation
- Session completion
```

**DEBUG**: Detailed information
```
- Audio durations
- Transcription results
- Extraction details
- Context updates
```

**WARNING**: Recoverable issues
```
- Timeouts
- Fallback usage
- Validation failures
```

**ERROR**: Failures
```
- API errors
- Database errors
- Hardware failures
```

### Log Files

```
logs/
├── agent_2024-01-01.log  # Daily rotating
├── agent_2024-01-02.log
└── ...
```

## Known Limitations

1. **Whisper STT**: Currently stub - needs real implementation
2. **SMS/Email**: Currently stubs - need Twilio/SendGrid
3. **Interruptions**: Cannot handle user interrupting agent speech
4. **Background Noise**: Limited noise cancellation
5. **Multiple Languages**: English only
6. **Session Persistence**: No resume capability

## Future Enhancements

### Short Term
- [ ] Implement real Whisper integration
- [ ] Add Twilio SMS integration
- [ ] Add SendGrid email integration
- [ ] Better noise handling

### Medium Term
- [ ] Support interruptions
- [ ] Streaming transcription
- [ ] Multi-language support
- [ ] Session persistence

### Long Term
- [ ] Real-time conversation analytics
- [ ] A/B testing framework
- [ ] Voice authentication
- [ ] Sentiment analysis

## Troubleshooting

### Common Issues

**"No audio devices found"**
- Check microphone/speaker connections
- Verify permissions (especially on macOS)
- Try different audio device

**"API key not configured"**
- Check .env file exists
- Verify ELEVENLABS_API_KEY is set
- Check OPENAI_API_KEY for LLM calls

**"Database connection error"**
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env
- Verify database schema is initialized

**"Transcription returns placeholder"**
- Whisper is currently stub implementation
- Replace with real Whisper integration

## Contributing

When modifying the orchestrator:

1. Maintain backward compatibility
2. Add comprehensive logging
3. Handle all error cases
4. Update tests
5. Document configuration changes
6. Update this documentation

## References

- [AudioManager Documentation](../src/audio/README.md)
- [Response Generator Documentation](../src/response/README.md)
- [NLU Extractor Documentation](../src/nlu/README.md)
- [Booking Service API](../src/services/booking_service.py)
- [Conversation States](../src/conversation/states.py)
