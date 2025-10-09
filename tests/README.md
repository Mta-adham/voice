# Test Suite

This directory contains comprehensive unit, integration, and end-to-end tests for the restaurant booking system.

## Test Files

### test_database.py
**Database Models and CRUD Operations**
- Database connection and initialization
- Booking CRUD operations (create, read, update, delete)
- TimeSlot model and capacity tracking
- RestaurantConfig management
- Database constraints and validation
- Unique constraint enforcement
- Check constraint validation

### test_booking_logic.py
**Booking Service Business Logic**
- `get_available_slots()` with various dates and party sizes
- `create_booking()` with valid and invalid inputs
- `validate_booking_request()` for all validation rules:
  - Same day to 30 days ahead validation
  - Maximum 8 people party size
  - Valid time slots within operating hours
  - Capacity enforcement
- Edge cases (fully booked, last available slot, boundary dates)
- Time slot auto-generation
- Concurrent booking prevention

### test_llm_abstraction.py
**LLM Service Integration**
- Mock API calls for OpenAI, Gemini, and Claude
- `llm_chat()` returns standardized format for each provider
- Error handling (rate limits, timeouts, invalid credentials)
- Retry logic with tenacity
- Token usage tracking
- Parameter validation
- Provider routing

### test_audio_system.py
**Audio Recording and Playback**
- Mock microphone input and speaker output
- `start_recording()` and `stop_recording()` operations
- `play_audio()` with sample audio data
- `detect_silence()` with various audio inputs
- Audio format conversions
- Resource cleanup and context manager support
- Audio device error handling

### test_stt_tts.py
**Speech-to-Text and Text-to-Speech**
- Mock Whisper transcription with test audio files
- `transcribe_audio()` with clear and unclear audio
- Mock ElevenLabs API calls
- `generate_speech()` with various text inputs
- Audio caching for common phrases
- Cache eviction (LRU)
- Error handling for both services
- API quota and rate limit handling

### test_conversation_flow.py
**Conversation State Management**
- State transitions through complete booking flow
- Context storage and retrieval
- Handling corrections (user changes date/time)
- Context switching (user provides multiple fields at once)
- Missing field detection
- Auto-advance state logic
- Validation during state transitions

### test_end_to_end.py
**End-to-End Integration Tests**
- Mock all external services (LLMs, STT, TTS, SMS, Email)
- Complete happy path conversation from requirements
- Booking creation in database verification
- Confirmation sending verification
- Graceful conversation ending
- Error recovery
- Multiple fields at once handling
- Correction handling in full flow

## Test Fixtures

### conftest.py
Contains shared pytest fixtures:
- `test_db_url`: In-memory SQLite database URL
- `db_engine`: Test database engine with all tables
- `db_session`: Database session with automatic rollback
- `restaurant_config`: Default restaurant configuration
- `sample_time_slots`: Pre-populated time slots for testing
- `sample_booking_data`: Sample booking data
- `booking_service`: BookingService instance
- `sample_audio_data`: Generated audio data for tests
- `sample_silence_audio`: Silent audio data
- `temp_audio_dir`: Temporary directory for audio files
- `mock_llm_response`: Mock LLM API response
- `mock_env_vars`: Mock environment variables

### fixtures/
Directory containing sample audio files for testing:
- `sample_audio_clear.wav`: Clear speech simulation
- `sample_audio_unclear.wav`: Noisy/unclear audio
- `sample_audio_silence.wav`: Silent audio
- `sample_audio_mixed.wav`: Mixed audio (speech + silence)

Generate fixtures with:
```bash
cd tests/fixtures
python generate_audio.py
```

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run with verbose output:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_database.py -v
pytest tests/test_booking_logic.py -v
pytest tests/test_llm_abstraction.py -v
pytest tests/test_audio_system.py -v
pytest tests/test_stt_tts.py -v
pytest tests/test_conversation_flow.py -v
pytest tests/test_end_to_end.py -v
```

### Run specific test class:
```bash
pytest tests/test_booking_logic.py::TestValidateBookingRequest -v
```

### Run specific test:
```bash
pytest tests/test_database.py::TestBookingCRUD::test_create_booking_valid_data -v
```

### Run with coverage:
```bash
# All modules
pytest tests/ --cov=src --cov-report=html

# Specific modules
pytest tests/ --cov=src/services --cov=src/models --cov-report=html

# Terminal report
pytest tests/ --cov=src --cov-report=term-missing
```

### Run with markers:
```bash
# Run only unit tests (if markers are defined)
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration
```

## Test Database

Tests use an in-memory SQLite database that is created fresh for each test function. This ensures:
- ✅ Fast test execution
- ✅ No side effects between tests
- ✅ No need for database cleanup
- ✅ Easy CI/CD integration
- ✅ Isolated test environment

## External Service Mocking

All external API calls are mocked in tests:
- **LLM Providers**: OpenAI, Gemini, Claude API calls are mocked
- **TTS Service**: ElevenLabs API calls are mocked
- **STT Service**: Whisper transcription is mocked
- **Audio Devices**: Microphone and speaker interactions are mocked
- **Email/SMS**: Communication services are mocked (when implemented)

This ensures:
- Tests run without internet connection
- No API costs during testing
- Fast and reliable test execution
- Predictable test behavior

## Success Criteria

All tests must pass to verify:

### Database & Models
- ✅ Database connection and table creation
- ✅ CRUD operations work correctly
- ✅ Constraints are enforced (unique, check, foreign key)
- ✅ Data validation at model level

### Booking Logic
- ✅ Availability queries correctly calculate remaining capacity per slot
- ✅ Cannot create booking for past dates or dates beyond 30-day window
- ✅ Cannot create booking for party size > 8 or < 1
- ✅ Cannot create booking outside operating hours
- ✅ Cannot create booking if insufficient capacity in time slot
- ✅ Booking creation is atomic (either booking + capacity update both succeed, or both fail)
- ✅ Concurrent bookings don't create overbooking (via database-level locking)
- ✅ Generated time slots respect operating hours and slot duration configuration

### LLM Integration
- ✅ All three LLM providers (OpenAI, Gemini, Claude) work with unified interface
- ✅ Error handling for authentication, rate limits, timeouts
- ✅ Retry logic works as expected
- ✅ Token usage is tracked correctly

### Audio System
- ✅ Recording can start and stop properly
- ✅ Playback works with various audio formats
- ✅ Silence detection works correctly
- ✅ Resources are cleaned up properly
- ✅ Error handling for device issues

### STT/TTS
- ✅ Speech generation works with various text inputs
- ✅ Audio caching reduces API calls
- ✅ Cache eviction works properly
- ✅ Error handling for API issues

### Conversation Flow
- ✅ State transitions follow the expected flow
- ✅ Context updates work correctly
- ✅ Corrections are detected and handled
- ✅ Multiple fields can be updated at once
- ✅ Missing fields are detected
- ✅ Invalid transitions are blocked

### End-to-End
- ✅ Complete happy path conversation works
- ✅ Booking is created and stored in database
- ✅ Corrections during conversation work
- ✅ Multiple fields provided at once work
- ✅ Capacity validation works during full flow
- ✅ Error recovery works properly

## Continuous Integration

These tests are designed to run in CI/CD pipelines. They:
- Don't require external services
- Use in-memory database (no setup needed)
- Complete quickly (< 30 seconds for full suite)
- Provide clear failure messages
- Support parallel execution (where safe)

## Test Data Generation

### Database Seeding
```bash
# Generate test data in actual database
python scripts/seed_database.py

# Reset and re-seed
python scripts/seed_database.py --reset
```

### Audio Fixtures
```bash
# Generate sample audio files
cd tests/fixtures
python generate_audio.py
```

## Demo

Run the interactive demo to see the system in action:
```bash
# Interactive mode
python scripts/demo.py

# Automated mode
python scripts/demo.py --mode auto
```
