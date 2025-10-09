# Testing Documentation

This document provides a comprehensive overview of the test suite for the restaurant booking system.

## Overview

The test suite includes:
- **7 test modules** with comprehensive unit, integration, and end-to-end tests
- **Mock-based testing** for all external services (no real API calls)
- **Database fixtures** with in-memory SQLite for isolation
- **Audio fixtures** for testing speech processing
- **Automated scripts** for database seeding and demos

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── test_database.py               # Database CRUD tests
├── test_booking_logic.py          # Booking validation tests
├── test_llm_abstraction.py        # LLM provider tests
├── test_audio_system.py           # Audio recording/playback tests
├── test_stt_tts.py               # Speech services tests
├── test_conversation_flow.py      # State management tests
├── test_end_to_end.py            # Full integration tests
├── fixtures/
│   ├── generate_audio.py         # Audio file generator
│   └── README.md
└── README.md

scripts/
├── seed_database.py              # Database seeding
├── demo.py                       # Interactive demo
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Test Fixtures

```bash
cd tests/fixtures
python generate_audio.py
```

### 3. Run Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_database.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### 4. Seed Database (Optional)

```bash
# For development/testing with actual database
python scripts/seed_database.py
```

### 5. Run Demo

```bash
# Interactive mode
python scripts/demo.py

# Automated mode
python scripts/demo.py --mode auto
```

## Test Modules

### test_database.py (Database Layer)

Tests all database models and operations:
- ✅ Connection and initialization
- ✅ Booking CRUD operations
- ✅ TimeSlot capacity tracking
- ✅ RestaurantConfig management
- ✅ Constraint validation
- ✅ Unique/check constraints

**Key Tests:**
- `test_create_booking_valid_data` - Booking creation
- `test_party_size_constraint_min/max` - Constraint enforcement
- `test_duplicate_booking_constraint` - Uniqueness checks
- `test_time_slot_is_available` - Capacity calculations

### test_booking_logic.py (Business Logic)

Tests booking service business rules:
- ✅ Availability queries
- ✅ Booking validation (dates, party size, hours)
- ✅ Capacity management
- ✅ Time slot generation
- ✅ Edge cases

**Key Tests:**
- `test_validate_booking_request` - All validation rules
- `test_get_available_slots_filters_insufficient_capacity` - Capacity filtering
- `test_create_booking_insufficient_capacity` - Capacity enforcement
- `test_last_available_slot_booking` - Edge case handling

### test_llm_abstraction.py (LLM Integration)

Tests unified LLM provider interface:
- ✅ OpenAI GPT integration
- ✅ Google Gemini integration
- ✅ Anthropic Claude integration
- ✅ Error handling (auth, rate limits, timeouts)
- ✅ Retry logic
- ✅ Token tracking

**Key Tests:**
- `test_call_openai_success` - OpenAI API calls
- `test_call_gemini_success` - Gemini API calls
- `test_call_claude_success` - Claude API calls
- `test_llm_chat_routes_to_*` - Provider routing

### test_audio_system.py (Audio Processing)

Tests audio recording and playback:
- ✅ Recording start/stop
- ✅ Playback functionality
- ✅ Silence detection
- ✅ Format conversions
- ✅ Resource cleanup
- ✅ Device error handling

**Key Tests:**
- `test_start_recording_success` - Recording initiation
- `test_stop_recording_success` - Recording completion
- `test_play_audio_success` - Audio playback
- `test_detect_silence_with_silence` - Silence detection

### test_stt_tts.py (Speech Services)

Tests speech-to-text and text-to-speech:
- ✅ ElevenLabs TTS integration
- ✅ Audio caching
- ✅ Cache eviction (LRU)
- ✅ Error handling
- ✅ Whisper STT (mocked)

**Key Tests:**
- `test_generate_speech_success` - Speech generation
- `test_generate_speech_with_cache_hit` - Caching
- `test_cache_eviction_lru` - LRU eviction
- `test_tts_quota_exceeded` - Error handling

### test_conversation_flow.py (State Management)

Tests conversation state machine:
- ✅ State transitions
- ✅ Context updates
- ✅ Corrections handling
- ✅ Multi-field updates
- ✅ Missing field detection
- ✅ Validation during transitions

**Key Tests:**
- `test_transition_linear_progression` - State flow
- `test_update_with_correction` - Correction detection
- `test_update_multiple_fields` - Context switching
- `test_transition_to_confirming_without_complete_info` - Validation

### test_end_to_end.py (Integration)

Tests complete booking flow:
- ✅ Happy path conversation
- ✅ Database persistence
- ✅ Corrections during flow
- ✅ Multiple fields at once
- ✅ Capacity validation
- ✅ Error recovery

**Key Tests:**
- `test_happy_path_booking_conversation` - Full flow
- `test_conversation_with_corrections` - Correction handling
- `test_conversation_with_multiple_fields_at_once` - Context switching
- `test_booking_capacity_validation_during_flow` - Capacity checks

## Fixtures and Test Data

### Database Fixtures (conftest.py)

- `test_db_url`: In-memory SQLite URL
- `db_engine`: Fresh database engine per test
- `db_session`: Session with auto-rollback
- `restaurant_config`: Default configuration
- `sample_time_slots`: Pre-populated slots
- `booking_service`: Service instance

### Audio Fixtures

- `sample_audio_data`: 440Hz sine wave (1 second)
- `sample_silence_audio`: Silent audio (1 second)
- `temp_audio_dir`: Temporary directory
- Generated WAV files in `tests/fixtures/`

### Mock Fixtures

- `mock_llm_response`: Standard LLM response format
- `mock_env_vars`: Environment variables
- All external APIs are mocked via `@patch` decorators

## Mocking Strategy

### External Services

All external API calls are mocked to ensure:
- ✅ No real API costs during testing
- ✅ Fast test execution
- ✅ Reliable, predictable behavior
- ✅ No internet required

**Mocked Services:**
- OpenAI GPT API
- Google Gemini API
- Anthropic Claude API
- ElevenLabs TTS API
- Whisper STT (local model)
- Audio devices (microphone/speaker)

### Database

- In-memory SQLite for each test
- Fresh database per test function
- No cleanup needed
- Fast and isolated

## Running Tests

### Basic Usage

```bash
# All tests
pytest tests/

# Verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Show local variables on failure
pytest tests/ -l
```

### Specific Tests

```bash
# Single file
pytest tests/test_database.py

# Single class
pytest tests/test_booking_logic.py::TestValidateBookingRequest

# Single test
pytest tests/test_database.py::TestBookingCRUD::test_create_booking_valid_data
```

### Coverage Reports

```bash
# HTML report (opens in browser)
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Terminal report with missing lines
pytest tests/ --cov=src --cov-report=term-missing

# Specific modules
pytest tests/ --cov=src/services --cov=src/models
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto
```

## Scripts

### Database Seeding

Populate database with test data:

```bash
# Basic seeding
python scripts/seed_database.py

# Reset and re-seed
python scripts/seed_database.py --reset

# Seed for 60 days
python scripts/seed_database.py --days 60
```

Creates:
- Restaurant configuration
- Time slots for N days
- Sample bookings

### Interactive Demo

Walk through booking conversation:

```bash
# Interactive (user input)
python scripts/demo.py

# Automated (predefined responses)
python scripts/demo.py --mode auto

# Mock mode (no external calls)
python scripts/demo.py --mode mock
```

## Success Criteria

All tests pass ✅ verifying:

### Core Functionality
- Database operations work correctly
- Booking validation enforces all business rules
- Capacity is tracked and enforced
- Time slots are generated correctly

### External Integrations
- All three LLM providers work via unified interface
- Speech services integrate properly
- Audio system handles recording/playback
- Error handling works for all external services

### Conversation Flow
- State machine transitions correctly
- Context is maintained throughout conversation
- Corrections are handled properly
- Multiple fields can be updated at once

### End-to-End
- Complete booking flow works from start to finish
- Data persists correctly to database
- Error recovery works at all stages

## CI/CD Integration

Tests are designed for continuous integration:
- ✅ No external dependencies
- ✅ Fast execution (< 30 seconds)
- ✅ Deterministic results
- ✅ Clear failure messages
- ✅ Coverage reporting
- ✅ Parallel execution support

### Example CI Configuration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: cd tests/fixtures && python generate_audio.py
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Audio Fixture Generation Fails

```bash
cd tests/fixtures
python generate_audio.py
```

Ensure `soundfile` and `numpy` are installed.

### Database Connection Errors

Set `DATABASE_URL` environment variable:
```bash
export DATABASE_URL="sqlite:///:memory:"
```

### Import Errors

Ensure `src/` is in Python path:
```python
# conftest.py handles this automatically
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

### Mock Not Working

Ensure patch target is correct:
```python
# Patch where it's imported, not where it's defined
@patch('services.llm_service.openai.OpenAI')  # Correct
@patch('openai.OpenAI')  # May not work
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Mocking**: Mock all external services
3. **Fixtures**: Use fixtures for common setup
4. **Assertions**: Use descriptive assertion messages
5. **Coverage**: Aim for >90% coverage
6. **Speed**: Keep tests fast (<1 second each)
7. **Clarity**: Test names should describe what they test

## Next Steps

1. Run full test suite: `pytest tests/ -v`
2. Check coverage: `pytest tests/ --cov=src --cov-report=html`
3. Seed database: `python scripts/seed_database.py`
4. Try demo: `python scripts/demo.py --mode auto`
5. Add more tests as needed for new features

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- Tests README: `tests/README.md`
- Scripts README: `scripts/README.md`
