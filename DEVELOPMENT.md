# Development Documentation

## Table of Contents

- [Technical Architecture](#technical-architecture)
- [Module Descriptions](#module-descriptions)
- [Design Decisions](#design-decisions)
- [Database Schema](#database-schema)
- [API Integrations](#api-integrations)
- [State Machine](#state-machine)
- [Error Handling](#error-handling)
- [Testing Strategy](#testing-strategy)
- [Future Enhancements](#future-enhancements)
- [Contributing Guidelines](#contributing-guidelines)

## Technical Architecture

### Overview

The Restaurant Booking Voice Agent is built as a modular, event-driven system with clear separation of concerns. The architecture follows these principles:

1. **Modularity**: Each component has a single, well-defined responsibility
2. **Abstraction**: LLM and speech services are abstracted for provider flexibility
3. **State Management**: Explicit state machine for conversation flow
4. **Data Validation**: Pydantic models ensure data integrity
5. **Error Resilience**: Comprehensive error handling with retry logic

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Language** | Python 3.9+ | Core application language |
| **Database** | PostgreSQL 13+ | Persistent data storage |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Validation** | Pydantic 2.5 | Data validation and serialization |
| **Audio I/O** | sounddevice, soundfile | Audio recording/playback |
| **STT** | OpenAI Whisper | Speech recognition |
| **TTS** | ElevenLabs API | Speech synthesis |
| **LLM** | OpenAI/Gemini/Claude | Natural language understanding |
| **Testing** | pytest | Unit and integration testing |
| **Logging** | loguru | Structured logging |

### System Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│              (Audio I/O, Speech Services)                    │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                          │
│      (Conversation Manager, State Machine, NLU)             │
├─────────────────────────────────────────────────────────────┤
│                    Business Logic Layer                      │
│           (Booking Service, Validation, Rules)               │
├─────────────────────────────────────────────────────────────┤
│                     Data Access Layer                        │
│              (SQLAlchemy Models, Database)                   │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│          (PostgreSQL, LLM APIs, Audio Devices)               │
└─────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### Core Modules

#### 1. `src/audio/` - Audio Management
**Responsibility**: Handle all audio input/output operations

**Key Components:**
- `audio_manager.py`: Main audio interface with recording and playback
- `config.py`: Audio configuration (sample rate, channels, formats)
- `recorder.py`: Microphone recording with silence detection
- `player.py`: Audio playback functionality
- `file_handler.py`: Audio file I/O operations
- `utils.py`: Audio processing utilities

**Design Notes:**
- Uses `sounddevice` for cross-platform compatibility
- 16kHz mono audio optimized for speech processing
- Silence detection using RMS (Root Mean Square) analysis
- Context manager support for proper resource cleanup

#### 2. `src/speech/` - Speech Services
**Responsibility**: Speech-to-text and text-to-speech conversion

**Key Components:**
- `elevenlabs_tts.py`: ElevenLabs TTS integration with caching

**Design Notes:**
- Local caching of TTS audio reduces API calls and latency
- LRU cache eviction maintains 100MB size limit
- MD5 hashing for cache keys (text + voice_id)
- Automatic retry with exponential backoff for rate limits

#### 3. `src/conversation/` - Conversation Management
**Responsibility**: Manage conversation state and context

**Key Components:**
- `states.py`: ConversationState enum defining all possible states
- `context.py`: ConversationContext Pydantic model for data storage
- `state_manager.py`: State transition logic and validation

**Design Notes:**
- Explicit state machine prevents invalid transitions
- Context stores all collected booking information
- Validators ensure data integrity at field level
- Supports corrections and multi-field updates

**State Flow:**
```
GREETING → COLLECTING_DATE → COLLECTING_TIME → COLLECTING_PARTY_SIZE 
→ COLLECTING_NAME → COLLECTING_PHONE → CONFIRMING → COMPLETED
```

#### 4. `src/nlu/` - Natural Language Understanding
**Responsibility**: Extract structured information from utterances

**Key Components:**
- `extractor.py`: Main extraction logic using LLMs
- `parsers.py`: Date/time parsing, phone validation
- `prompts.py`: LLM prompts for extraction tasks

**Design Notes:**
- LLM-based extraction handles variations in natural language
- Post-processing validates and normalizes extracted data
- Correction detection using keyword patterns
- Confidence scoring for each extracted field

**Extraction Process:**
1. LLM extracts raw structured data from utterance
2. Post-processing validates and normalizes fields
3. Confidence scores identify low-quality extractions
4. Correction detection flags updates to existing fields

#### 5. `src/response/` - Response Generation
**Responsibility**: Generate natural, context-aware responses

**Key Components:**
- `generator.py`: Main response generation using LLMs
- `prompts.py`: State-specific prompt templates
- `personality.py`: Agent personality and voice configuration

**Design Notes:**
- Dynamic prompt generation based on state and context
- Template-based prompts ensure consistency
- LLM generates natural variations
- Context awareness for personalized responses

#### 6. `src/services/` - Business Services
**Responsibility**: Core business logic and external integrations

**Key Components:**
- `booking_service.py`: Booking creation, validation, availability
- `llm_service.py`: Unified LLM interface with multi-provider support

**Design Notes:**
- BookingService encapsulates all booking business rules
- Atomic transactions for booking creation
- LLM service provides failover between providers
- Retry logic with exponential backoff

#### 7. `src/models/` - Data Models
**Responsibility**: Database models and schemas

**Key Components:**
- `database.py`: SQLAlchemy models and session management
- `schemas.py`: Pydantic schemas for validation

**Design Notes:**
- Booking, TimeSlot, and RestaurantConfig models
- Pydantic for request/response validation
- SQLAlchemy for database operations
- Connection pooling for performance

## Design Decisions

### 1. Hybrid Conversation Approach

**Decision**: Use state machine + LLM hybrid approach

**Rationale:**
- Pure LLM-driven: Too unpredictable, hard to debug, expensive
- Pure rule-based: Too rigid, poor user experience
- Hybrid: Best of both worlds - structured flow with natural language flexibility

**Implementation:**
- State machine ensures required information is collected
- LLM provides natural language understanding and generation
- NLU extracts information; state machine validates progression

### 2. Local Audio Instead of Phone System

**Decision**: Process audio locally using microphone/speakers

**Rationale:**
- Faster development and testing
- No telephony infrastructure required
- Lower operational costs
- Easier debugging and iteration
- Can be extended to phone system later (Twilio)

**Trade-offs:**
- Not suitable for remote customers
- Requires local hardware
- Single user at a time

### 3. LLM Abstraction Layer

**Decision**: Create unified interface for multiple LLM providers

**Rationale:**
- Avoid vendor lock-in
- Cost optimization (choose cheapest for task)
- Failover capability
- Easy provider comparison

**Implementation:**
```python
# Unified interface
response = llm_chat(
    messages=[{"role": "user", "content": "..."}],
    provider="gemini",  # or "openai", "claude"
    temperature=0.7
)
```

**Benefits:**
- Switch providers via configuration
- Graceful degradation if one provider fails
- A/B testing different models

### 4. State Machine vs Pure LLM

**Decision**: Explicit state machine for conversation flow

**Rationale:**
- **Predictability**: Always know what information to collect next
- **Validation**: Enforce business rules at each step
- **Debugging**: Clear state transitions in logs
- **Testing**: Each state can be tested independently
- **Cost**: Fewer LLM calls needed

**Trade-off:**
- Less flexible than pure LLM approach
- More code to maintain
- **Justification**: Reliability and cost control outweigh flexibility

### 5. PostgreSQL for Storage

**Decision**: Use PostgreSQL over NoSQL alternatives

**Rationale:**
- **ACID transactions**: Critical for booking consistency
- **Relations**: Natural fit for bookings, time slots, config
- **Constraints**: Database-level validation (unique constraints, foreign keys)
- **Maturity**: Battle-tested, excellent tooling
- **SQL**: Complex queries for availability checking

## Database Schema

### Tables

#### `bookings`
Stores customer reservation information.

```sql
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time_slot TIME NOT NULL,
    party_size INTEGER NOT NULL CHECK (party_size >= 1 AND party_size <= 8),
    customer_name VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50) NOT NULL,
    customer_email VARCHAR(255),
    special_requests TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (date, time_slot, customer_phone)
);

CREATE INDEX idx_booking_date_time ON bookings(date, time_slot);
```

**Fields:**
- `id`: Auto-incrementing primary key
- `date`: Booking date (not in past)
- `time_slot`: Reservation time
- `party_size`: Number of guests (1-8)
- `customer_name`: Guest name
- `customer_phone`: Contact number
- `customer_email`: Optional email
- `special_requests`: Dietary restrictions, preferences
- `status`: `pending`, `confirmed`, `completed`, `cancelled`
- `created_at`: Booking creation timestamp

**Constraints:**
- Unique constraint prevents duplicate bookings (same date/time/phone)
- Check constraint enforces party size limits
- Index on date/time for fast availability queries

#### `time_slots`
Tracks available time slots and capacity.

```sql
CREATE TABLE time_slots (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time TIME NOT NULL,
    total_capacity INTEGER NOT NULL,
    booked_capacity INTEGER NOT NULL DEFAULT 0,
    UNIQUE (date, time)
);

CREATE INDEX idx_time_slot_date ON time_slots(date);
```

**Fields:**
- `id`: Auto-incrementing primary key
- `date`: Slot date
- `time`: Slot time
- `total_capacity`: Maximum number of guests
- `booked_capacity`: Currently booked guests

**Design Notes:**
- Capacity tracking allows overbooking control
- One slot per date/time combination
- Updated atomically with booking creation

#### `restaurant_config`
Global restaurant configuration (single row).

```sql
CREATE TABLE restaurant_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    operating_hours JSONB NOT NULL,
    slot_duration INTEGER NOT NULL DEFAULT 30,
    max_party_size INTEGER NOT NULL DEFAULT 8,
    booking_window_days INTEGER NOT NULL DEFAULT 30
);
```

**Fields:**
- `id`: Always 1 (single configuration row)
- `operating_hours`: JSON with hours per day
- `slot_duration`: Time slot length in minutes
- `max_party_size`: Maximum guests per booking
- `booking_window_days`: How far ahead bookings allowed

**Operating Hours Format:**
```json
{
    "monday": {"open": "11:00", "close": "22:00"},
    "tuesday": {"open": "11:00", "close": "22:00"},
    ...
}
```

### Relationships

```
RestaurantConfig (1)
        ↓ (defines rules for)
    Bookings (N)
        ↓ (references)
    TimeSlots (N)
```

- Configuration defines business rules
- Bookings reference time slots implicitly
- Time slots track capacity across all bookings

## API Integrations

### 1. OpenAI Whisper (Speech-to-Text)

**Purpose**: Convert spoken audio to text

**Integration Method**: Local model (no API calls)

**Model**: `openai-whisper` package

**Implementation:**
```python
import whisper

model = whisper.load_model("base")
result = model.transcribe(audio_file, language="en")
text = result["text"]
```

**Characteristics:**
- **Latency**: 1-3 seconds for typical utterance
- **Accuracy**: Excellent for clear speech
- **Cost**: Free (runs locally)
- **Languages**: Multilingual support

**Error Handling:**
- Retry on model load failure
- Fallback to empty transcription
- Log transcription confidence

### 2. ElevenLabs (Text-to-Speech)

**Purpose**: Generate natural-sounding speech

**API Documentation**: https://docs.elevenlabs.io/

**Authentication**: API key in header

**Implementation:**
```python
from elevenlabs import generate, Voice

audio = generate(
    text="Hello, welcome to our restaurant!",
    voice=Voice(voice_id="21m00Tcm4TlvDq8ikWAM"),  # Rachel
    api_key=api_key
)
```

**Characteristics:**
- **Latency**: 500ms - 2s depending on text length
- **Quality**: Very natural, professional
- **Cost**: $0.30 per 1K characters (Creator tier)
- **Free Tier**: 10K characters/month

**Optimization:**
- Local cache with MD5 keys
- LRU eviction at 100MB
- Reuse common phrases

**Error Handling:**
- Retry on rate limit (429)
- Exponential backoff
- Fallback to error message

### 3. LLM Providers

#### Google Gemini

**Purpose**: Natural language understanding and generation

**API Documentation**: https://ai.google.dev/docs

**Model**: `gemini-pro`

**Characteristics:**
- **Latency**: 500ms - 2s
- **Quality**: Excellent for conversation
- **Cost**: Free tier with generous limits
- **Best For**: Development and moderate production use

**Error Handling:**
- Retry on timeout
- Fallback to other providers

#### OpenAI GPT

**Purpose**: NLU and response generation

**API Documentation**: https://platform.openai.com/docs

**Models**: `gpt-3.5-turbo`, `gpt-4`

**Characteristics:**
- **Latency**: 500ms - 1.5s (3.5), 2-4s (4)
- **Quality**: Excellent
- **Cost**: $0.002 per 1K tokens (3.5)
- **Best For**: Production use

#### Anthropic Claude

**Purpose**: NLU and response generation

**API Documentation**: https://docs.anthropic.com/

**Models**: `claude-3-opus`, `claude-3-sonnet`

**Characteristics:**
- **Latency**: 1-3s
- **Quality**: Excellent, especially for reasoning
- **Cost**: Variable by model
- **Best For**: Complex reasoning tasks

### Retry Strategy

All API calls use `tenacity` for automatic retry:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError)
)
def call_api(...):
    # API call here
```

**Parameters:**
- **Max Attempts**: 3
- **Wait Strategy**: Exponential backoff (2s, 4s, 8s)
- **Retry Conditions**: Rate limits, timeouts, connection errors

## State Machine

### States

```python
class ConversationState(str, Enum):
    GREETING = "greeting"
    COLLECTING_DATE = "collecting_date"
    COLLECTING_TIME = "collecting_time"
    COLLECTING_PARTY_SIZE = "collecting_party_size"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_PHONE = "collecting_phone"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
```

### Transition Rules

**Valid Transitions:**
- Forward progression through states
- Jump to CONFIRMING when all fields collected
- Return to any collection state for corrections
- COMPLETED is terminal (no transitions out)

**Invalid Transitions:**
- Cannot skip to CONFIRMING without all required fields
- Cannot go to COMPLETED from non-CONFIRMING states
- Cannot transition from COMPLETED

**Implementation:**
```python
def can_transition_to(self, target: ConversationState) -> Tuple[bool, str]:
    # Validation logic
    if target == ConversationState.COMPLETED:
        if self.current != ConversationState.CONFIRMING:
            return False, "Can only complete from confirming state"
    return True, ""
```

### State Data

Each state maintains:
- **Current state**: Where we are in the conversation
- **Context**: All collected booking information
- **Missing fields**: What still needs to be collected
- **History**: Previous state (for corrections)

### Auto-Advancement

After collecting information, the state machine can automatically advance:

```python
def auto_advance_state(self) -> Optional[ConversationState]:
    if self.context.is_complete():
        return ConversationState.CONFIRMING
    else:
        return self._next_missing_field_state()
```

## Error Handling

### Error Hierarchy

```
Exception
├── AudioDeviceError (audio not available)
├── AudioRecordingError (recording failure)
├── AudioPlaybackError (playback failure)
├── LLMError (LLM API failure)
│   ├── RateLimitError
│   ├── AuthenticationError
│   └── TimeoutError
├── BookingServiceError (booking logic)
│   ├── ValidationError
│   ├── CapacityError
│   └── DatabaseError
├── ResponseGenerationError (response creation)
└── StateTransitionError (invalid state change)
```

### Error Handling Strategy

#### 1. Retry with Backoff
For transient failures (network, rate limits):
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def call_external_api():
    # API call
```

#### 2. Fallback
For service unavailability:
```python
try:
    response = llm_chat(provider="gemini", ...)
except LLMError:
    response = llm_chat(provider="openai", ...)  # Fallback
```

#### 3. Graceful Degradation
For non-critical features:
```python
try:
    audio_cache = load_from_cache(key)
except CacheError:
    audio_cache = None  # Generate fresh
```

#### 4. User-Friendly Messages
For user-facing errors:
```python
try:
    booking = create_booking(data)
except CapacityError:
    return "I'm sorry, that time slot is now fully booked. Would you like to try a different time?"
```

### Logging Strategy

**Log Levels:**
- **DEBUG**: Detailed info for debugging (state transitions, cache hits)
- **INFO**: Important events (booking created, API calls)
- **WARNING**: Recoverable errors (retry attempts, validation failures)
- **ERROR**: Unrecoverable errors (database down, all providers failed)
- **CRITICAL**: System failures (database connection lost)

**Implementation:**
```python
from loguru import logger

logger.info(f"Booking created: {booking.id}")
logger.warning(f"Rate limit hit, retrying in {wait}s")
logger.error(f"All LLM providers failed: {errors}")
```

## Testing Strategy

### Test Pyramid

```
      ┌──────────┐
      │   E2E    │  10%
     ┌────────────┐
     │Integration │  30%
    ┌──────────────┐
    │     Unit     │  60%
    └──────────────┘
```

### Unit Tests

**Coverage Goal**: 80%+ for core business logic

**Test Structure:**
```python
def test_booking_validation():
    """Test booking validation rules."""
    service = BookingService(mock_session)
    
    # Test past date rejection
    is_valid, error = service.validate_booking_request(
        date=date.today() - timedelta(days=1),
        time=time(19, 0),
        party_size=4
    )
    assert not is_valid
    assert "past" in error.lower()
```

**Key Areas:**
- Booking validation logic
- State transition rules
- Date/time parsing
- Information extraction
- Response generation

### Integration Tests

**Purpose**: Test component interactions

**Examples:**
```python
def test_booking_creation_flow(db_session):
    """Test complete booking creation."""
    service = BookingService(db_session)
    
    booking_data = BookingCreate(
        date=date.today() + timedelta(days=7),
        time_slot=time(19, 0),
        party_size=4,
        customer_name="John Doe",
        customer_phone="+1234567890"
    )
    
    booking = service.create_booking(booking_data)
    assert booking.id is not None
    assert booking.status == "confirmed"
```

### Mock Strategy

**Mock External Services:**
- LLM API calls
- ElevenLabs API
- Audio devices (for CI/CD)

**Real Components:**
- Database (use test database)
- State machine logic
- Validation logic

**Implementation:**
```python
@pytest.fixture
def mock_llm_service(monkeypatch):
    def mock_chat(*args, **kwargs):
        return {"content": "Mocked response", "provider": "test"}
    
    monkeypatch.setattr("services.llm_service.llm_chat", mock_chat)
```

### Test Fixtures

**Database Fixtures:**
```python
@pytest.fixture
def db_session():
    """Provide test database session."""
    engine = create_engine("postgresql://test:test@localhost/test_db")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.rollback()
    session.close()
```

## Future Enhancements

### Phase 1: Core Improvements

1. **Telephone Integration**
   - **Technology**: Twilio Voice API
   - **Effort**: 2-3 weeks
   - **Benefits**: Remote access, scalability
   - **Changes**: Replace AudioManager with Twilio streams

2. **SMS/Email Notifications**
   - **Technology**: Twilio SMS, SendGrid
   - **Effort**: 1 week
   - **Benefits**: Booking confirmations, reminders
   - **Implementation**: Add notification service module

3. **Multi-language Support**
   - **Technology**: Whisper (already multilingual), LLM language detection
   - **Effort**: 2 weeks
   - **Benefits**: Broader customer base
   - **Changes**: Add language detection, translated prompts

### Phase 2: Advanced Features

4. **Booking Modification/Cancellation**
   - **Effort**: 2 weeks
   - **Benefits**: Complete booking lifecycle
   - **Changes**: Add states, authentication logic

5. **Wait List Management**
   - **Effort**: 2 weeks
   - **Benefits**: Better capacity utilization
   - **Changes**: Add wait list table, notification logic

6. **Analytics Dashboard**
   - **Technology**: Dash/Streamlit
   - **Effort**: 2 weeks
   - **Benefits**: Business insights
   - **Features**: Booking trends, peak times, cancellation rates

### Phase 3: Production Readiness

7. **Authentication & Security**
   - **Features**: Customer accounts, booking verification
   - **Effort**: 3 weeks
   - **Technologies**: JWT, password hashing

8. **Horizontal Scaling**
   - **Technologies**: Redis for session state, load balancer
   - **Effort**: 2 weeks
   - **Benefits**: Handle multiple concurrent calls

9. **Advanced Monitoring**
   - **Technologies**: Prometheus, Grafana
   - **Effort**: 1 week
   - **Metrics**: API latency, success rates, error rates

### Known Limitations

1. **Single Conversation**: Cannot handle multiple simultaneous conversations
2. **No Authentication**: Anyone can make/view bookings
3. **English Only**: Currently supports only English language
4. **No Cancellation**: Cannot modify or cancel existing bookings
5. **Local Audio Only**: Requires local microphone/speakers
6. **No Payment**: Cannot process payments or deposits

## Contributing Guidelines

### Code Style

**Python Style**: Follow PEP 8

**Tools:**
```bash
# Format code
black src/

# Sort imports
isort src/

# Type checking
mypy src/

# Linting
pylint src/
```

**Key Conventions:**
- Type hints for all function signatures
- Docstrings for all public functions (Google style)
- Max line length: 100 characters
- Use `f-strings` for string formatting

### Git Workflow

**Branch Naming:**
- Feature: `feature/add-sms-notifications`
- Bug fix: `fix/audio-device-detection`
- Refactor: `refactor/llm-service-interface`

**Commit Messages:**
```
type(scope): Short description

Longer description if needed.

Closes #123
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make Changes**
   - Write tests first (TDD)
   - Implement feature
   - Ensure tests pass
   - Update documentation

3. **Pre-PR Checklist**
   - [ ] Tests pass: `pytest tests/`
   - [ ] Code formatted: `black src/`
   - [ ] Imports sorted: `isort src/`
   - [ ] Docstrings added/updated
   - [ ] DEVELOPMENT.md updated (if architecture changed)

4. **Create Pull Request**
   - Clear description of changes
   - Link to related issues
   - Screenshots/examples if applicable

5. **Code Review**
   - Address review comments
   - Keep PR focused (one feature/fix)

6. **Merge**
   - Squash commits
   - Delete feature branch

### Testing Requirements

**For All PRs:**
- Existing tests must pass
- New features must have tests
- Bug fixes must have regression tests
- Coverage should not decrease

**Running Tests:**
```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_booking_service.py

# With coverage
pytest --cov=src tests/

# Verbose output
pytest -v tests/
```

### Documentation Requirements

**For New Features:**
- Add docstrings to all public functions
- Update README.md if user-facing
- Update DEVELOPMENT.md if architecture changes
- Add examples to docstrings

**Docstring Format (Google Style):**
```python
def create_booking(booking_data: BookingCreate) -> Booking:
    """
    Create a new restaurant booking.
    
    Args:
        booking_data: Validated booking information
        
    Returns:
        Created booking with assigned ID
        
    Raises:
        ValidationError: If booking data is invalid
        CapacityError: If time slot is fully booked
        
    Example:
        >>> data = BookingCreate(date=date.today(), ...)
        >>> booking = create_booking(data)
        >>> print(booking.id)
        42
    """
```

### Development Setup

**Local Development:**
```bash
# Create environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools

# Set up pre-commit hooks
pre-commit install

# Run in development mode
export DEBUG=true
export LOG_LEVEL=DEBUG
python src/main.py
```

**Development Tools:**
```bash
# Auto-format on save (VS Code)
{
    "python.formatting.provider": "black",
    "editor.formatOnSave": true
}

# Enable type checking
{
    "python.linting.mypyEnabled": true
}
```

### Getting Help

**Resources:**
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Questions and ideas
- **Documentation**: README.md, DEVELOPMENT.md, inline docs

**Before Asking:**
1. Check existing issues
2. Read documentation
3. Review code comments
4. Try debugging with increased logging (`LOG_LEVEL=DEBUG`)

---

**Last Updated**: [Add date]
**Maintainers**: [Add names/contacts]
