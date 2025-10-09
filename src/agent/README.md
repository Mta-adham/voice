# Voice Agent Orchestrator

Main coordination logic for the restaurant booking voice agent system.

## Overview

The `VoiceAgent` class orchestrates all system components to provide a natural voice conversation experience for restaurant bookings. It manages the complete conversation loop from greeting to booking confirmation.

## Architecture

### Components Integrated

1. **AudioManager** - Records user speech and plays agent responses
2. **ElevenLabs TTS** - Converts text responses to natural speech
3. **Whisper STT** - Transcribes user speech to text
4. **ConversationStateManager** - Tracks conversation state and collected information
5. **NLU Extractor** - Extracts booking information from utterances
6. **Response Generator** - Creates contextual agent responses
7. **BookingService** - Checks availability and creates bookings
8. **Notification Services** - Sends SMS and email confirmations

## Main Flow

```
1. Initialize all components
2. Play greeting (TTS + Audio)
3. Main conversation loop:
   a. Listen for user input (with VAD)
   b. Transcribe audio (Whisper)
   c. Extract information (NLU)
   d. Update conversation state
   e. Determine next action
   f. Generate and speak response
   g. Check availability when ready
   h. Confirm details with user
   i. Create booking
   j. Send confirmations
4. Clean shutdown
```

## Usage

### Basic Usage

```python
from agent.orchestrator import VoiceAgent

# Create and initialize agent
agent = VoiceAgent()
agent.initialize()

# Run conversation
success = agent.run()

# Clean up
agent.shutdown()
```

### With Context Manager

```python
from agent.orchestrator import create_voice_agent

with create_voice_agent() as agent:
    agent.initialize()
    success = agent.run()
```

### From Main Entry Point

```bash
python -m src.main
```

## Configuration

### Timeout Settings

- `INPUT_TIMEOUT` (15s) - Timeout for user input
- `EXTENDED_TIMEOUT` (30s) - Extended timeout before ending call
- `MAX_SILENCE_DURATION` (2.0s) - Silence duration to detect end of speech
- `MAX_RECORDING_DURATION` (30s) - Maximum recording duration

### Custom Configuration

```python
agent = VoiceAgent(
    input_timeout=20.0,
    extended_timeout=40.0
)
```

## Error Handling

The orchestrator handles multiple error types:

### Audio Errors
- **AudioDeviceError** - Microphone/speaker not available
- **AudioRecordingError** - Recording fails
- **AudioPlaybackError** - Playback fails

### API Errors
- **WhisperTranscriptionError** - Speech recognition fails
- **ElevenLabsTTSError** - Text-to-speech fails
- **ResponseGenerationError** - LLM response generation fails

### Booking Errors
- **BookingValidationError** - Invalid booking parameters
- **CapacityError** - No availability
- **DatabaseError** - Database operation fails

### Recovery Strategies

1. **Transient Failures** - Retry with exponential backoff
2. **Unclear Audio** - Ask for clarification
3. **API Failures** - Use fallback responses
4. **Timeout** - Prompt user, then end gracefully
5. **User Exit** - Say goodbye and clean up

## Conversation States

The agent transitions through these states:

1. **GREETING** - Initial welcome
2. **COLLECTING_DATE** - Ask for booking date
3. **COLLECTING_TIME** - Ask for booking time
4. **COLLECTING_PARTY_SIZE** - Ask for number of people
5. **COLLECTING_NAME** - Ask for customer name
6. **COLLECTING_PHONE** - Ask for phone number
7. **CONFIRMING** - Review all details
8. **COMPLETED** - Booking confirmed

## Voice Activity Detection

The orchestrator uses silence detection to automatically determine when the user has finished speaking:

- Records audio continuously
- Monitors for silence periods
- Stops recording after 2 seconds of silence (after initial sound)
- Maximum recording duration: 30 seconds

## Booking Flow

### Information Collection
1. Collects date, time, party size, name, phone
2. Supports multi-field updates (user provides multiple items)
3. Handles corrections ("actually, make that 4 people")
4. Validates all inputs

### Availability Check
1. Validates booking against business rules
2. Checks time slot capacity
3. Presents alternatives if requested slot unavailable

### Confirmation
1. Reviews all details with user
2. Waits for verbal confirmation
3. Creates booking in database
4. Sends SMS and email confirmations

## Logging

Comprehensive logging at multiple levels:

- **INFO** - Major events (initialization, state transitions, bookings)
- **DEBUG** - Detailed information (audio durations, API calls)
- **WARNING** - Recoverable issues (timeouts, fallbacks)
- **ERROR** - Failures (API errors, database errors)

Logs are written to:
- `stderr` - Formatted for console
- `logs/agent_YYYY-MM-DD.log` - Daily rotating files

## Testing Considerations

### Unit Testing
- Mock all external dependencies (audio, TTS, STT, database)
- Test state transitions independently
- Test error handling paths

### Integration Testing
- Use test database
- Mock audio I/O but test real APIs
- Test complete conversation flows

### End-to-End Testing
- Requires microphone and speaker
- Test with actual voice input
- Verify booking creation and confirmations

## Dependencies

### Required Components
- AudioManager (src/audio)
- ElevenLabs TTS (src/speech)
- Whisper STT (src/stt) - *stub implementation*
- ConversationStateManager (src/conversation)
- NLU Extractor (src/nlu)
- Response Generator (src/response)
- BookingService (src/services)
- SMS Service (src/notifications) - *stub implementation*
- Email Service (src/notifications) - *stub implementation*

### External Services
- ElevenLabs API (text-to-speech)
- OpenAI API (LLM for responses and NLU)
- PostgreSQL (booking database)
- Twilio (SMS confirmations) - *to be implemented*
- SendGrid (email confirmations) - *to be implemented*

## Known Limitations

1. **Whisper STT** - Currently stub implementation, needs real Whisper integration
2. **SMS/Email** - Currently stub implementations, need Twilio/SendGrid integration
3. **Language Support** - English only
4. **Audio Format** - Requires 16kHz mono PCM
5. **Database Session** - Manual session management (not using context manager fully)

## Future Enhancements

- [ ] Support for multiple languages
- [ ] Better noise handling and audio preprocessing
- [ ] Real-time streaming transcription
- [ ] Interruption handling (user speaks while agent is speaking)
- [ ] Session persistence (resume interrupted conversations)
- [ ] Analytics and conversation metrics
- [ ] A/B testing different conversation strategies
