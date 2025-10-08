# Quick Start Guide - Voice Agent Orchestrator

## Prerequisites

1. **Hardware**
   - Microphone (for user input)
   - Speakers (for agent responses)

2. **Software**
   - Python 3.9+
   - PostgreSQL database
   - Required Python packages (see requirements.txt)

3. **API Keys**
   - OpenAI API key (for LLM)
   - ElevenLabs API key (for TTS)

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your keys
nano .env
```

Required variables:
```bash
DATABASE_URL=postgresql://user:password@localhost/restaurant_booking
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
```

### 3. Initialize Database
```bash
python src/db_init.py
```

## Running the Agent

### Basic Usage
```bash
python src/main.py
```

### With Log Output
```bash
python src/main.py 2>&1 | tee logs/session.log
```

### As Module
```bash
python -m src.main
```

## Testing

### Test Imports
```bash
python examples/test_orchestrator.py
```

Expected output:
```
✓ All imports successful!
✓ VoiceAgent created successfully
✓ All components functional
```

## Usage Example

```python
from agent.orchestrator import VoiceAgent

# Create agent
agent = VoiceAgent()

# Initialize components
agent.initialize()

# Run conversation
success = agent.run()

# Clean up
agent.shutdown()
```

## Conversation Flow

1. **Agent greets** → "Hello! This is Alex..."
2. **Collects date** → "What date would you like?"
3. **Collects time** → "What time works for you?"
4. **Collects party size** → "How many people?"
5. **Collects name** → "Can I get your name?"
6. **Collects phone** → "And a phone number?"
7. **Confirms details** → "Let me confirm..."
8. **Creates booking** → "Perfect! Your reservation is confirmed..."

## Exit Commands

Say any of these to exit:
- "cancel"
- "goodbye"
- "exit"
- "quit"
- "stop"
- "nevermind"

Or press `Ctrl+C` for immediate exit.

## Troubleshooting

### "No audio devices found"
- Check microphone is connected
- Verify system audio settings
- On macOS: Grant microphone permissions

### "API key not configured"
- Check .env file exists
- Verify API keys are set correctly
- Restart terminal after editing .env

### "Database connection error"
- Ensure PostgreSQL is running
- Check DATABASE_URL format
- Run database initialization

### "Transcription returns placeholder"
- This is expected - Whisper is stub implementation
- Replace with real Whisper for production

## Current Limitations

⚠️ **Stub Implementations** (need replacement for production):
- Whisper STT (src/stt/whisper_transcriber.py)
- SMS notifications (src/notifications/sms.py)
- Email notifications (src/notifications/email.py)

## Next Steps

1. Replace stub implementations with real services
2. Run integration tests
3. Test with actual voice input
4. Monitor logs for errors
5. Tune timeout settings if needed

## Configuration Options

```python
# Custom timeouts
agent = VoiceAgent(
    input_timeout=20.0,      # User response timeout (default: 15s)
    extended_timeout=45.0     # Total timeout before exit (default: 30s)
)

# Inject mock components (for testing)
agent = VoiceAgent(
    session=mock_session,
    audio_manager=mock_audio,
    tts=mock_tts,
    transcriber=mock_transcriber
)
```

## Logs

Logs are written to:
- **Console**: INFO level and above
- **File**: `logs/agent_YYYY-MM-DD.log` (DEBUG level)

Log rotation:
- Daily at midnight
- 30 day retention
- Automatic compression

## Getting Help

- **Architecture**: See `docs/ORCHESTRATOR.md`
- **Implementation**: See `IMPLEMENTATION_SUMMARY.md`
- **Component Docs**: See `src/agent/README.md`
- **Issues**: Check logs in `logs/` directory

## Example Session

```
$ python src/main.py

2024-01-15 10:30:00 | INFO     | Starting VoiceAgent...
2024-01-15 10:30:01 | INFO     | All components initialized
2024-01-15 10:30:01 | INFO     | Playing greeting...

[Agent speaks]: "Hello! This is Alex from our restaurant..."

[User speaks]: "I'd like a table for 4 on Friday at 7pm"

2024-01-15 10:30:10 | INFO     | Extracted: date=2024-01-19, time=19:00, party_size=4
2024-01-15 10:30:10 | INFO     | State transition: COLLECTING_DATE -> COLLECTING_NAME

[Agent speaks]: "Great! I have you down for 4 people on Friday at 7 PM. Can I get your name?"

[User speaks]: "John Smith"

[Agent speaks]: "Thank you, John. And a phone number where we can reach you?"

[User speaks]: "555-123-4567"

[Agent speaks]: "Perfect! Let me confirm your reservation..."
[Agent speaks]: "All set! Your reservation is confirmed..."

2024-01-15 10:30:45 | INFO     | Booking created with ID: 123
2024-01-15 10:30:45 | INFO     | ✓ Session completed successfully
```

## Production Checklist

Before deploying to production:

- [ ] Replace Whisper stub with real implementation
- [ ] Integrate Twilio for SMS
- [ ] Integrate SendGrid for email
- [ ] Set up proper database backups
- [ ] Configure error alerting
- [ ] Set up monitoring/analytics
- [ ] Test with diverse voice samples
- [ ] Tune silence detection thresholds
- [ ] Configure rate limiting
- [ ] Set up log aggregation

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review `docs/ORCHESTRATOR.md`
3. Run test script: `python examples/test_orchestrator.py`
4. Check environment variables in `.env`
