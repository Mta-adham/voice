# 🎙️ Restaurant Booking Voice Agent

An intelligent, voice-driven restaurant reservation system that provides a natural conversational experience for making table bookings. The agent uses advanced speech recognition, natural language understanding, and text-to-speech to create a seamless booking experience through voice interaction.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [Conversation Flow](#conversation-flow)
- [Troubleshooting](#troubleshooting)
- [API Services](#api-services)
- [License](#license)

## 🌟 Overview

This voice agent enables customers to make restaurant reservations through natural voice conversations. It handles date and time selection, party size specification, customer information collection, and booking confirmation—all through an intuitive voice interface.

**Key Capabilities:**
- Natural language conversation flow
- Multi-provider LLM support (OpenAI, Google Gemini, Anthropic Claude)
- Speech-to-text using OpenAI Whisper
- Natural-sounding text-to-speech via ElevenLabs
- Intelligent information extraction and validation
- Real-time availability checking
- PostgreSQL-backed booking management
- Correction handling and context switching

## ✨ Features

### Conversational AI
- **Natural Language Understanding**: Extracts booking details from conversational speech
- **Context Awareness**: Maintains conversation state and handles corrections
- **Flexible Dialog**: Supports non-linear conversations and multi-field updates
- **Intelligent Prompting**: Guides users through the booking process naturally

### Voice Interface
- **Speech Recognition**: High-quality transcription using Whisper
- **Natural TTS**: Professional voice synthesis with ElevenLabs
- **Audio Management**: Recording, playback, and silence detection
- **Voice Activity Detection**: Automatic speech endpoint detection

### Booking Management
- **Availability Checking**: Real-time time slot validation
- **Capacity Tracking**: Automatic management of restaurant capacity
- **Date/Time Validation**: Business rule enforcement
- **Operating Hours**: Configurable restaurant schedule
- **Special Requests**: Support for dietary restrictions and preferences

### Database Features
- **PostgreSQL Backend**: Robust data persistence
- **ACID Transactions**: Guaranteed data consistency
- **Booking History**: Complete audit trail
- **Time Slot Management**: Dynamic availability tracking
- **Configuration Management**: Flexible restaurant settings

## 📦 Prerequisites

### System Requirements
- **Python**: 3.9 or higher
- **PostgreSQL**: 13 or higher
- **Operating System**: Linux, macOS, or Windows
- **Audio**: Microphone and speakers/headphones

### Audio Dependencies (Linux)
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev python3-pyaudio

# Fedora/RHEL
sudo dnf install portaudio-devel

# macOS (with Homebrew)
brew install portaudio
```

### API Accounts Required
1. **At least one LLM provider**:
   - [Google Gemini](https://makersuite.google.com/app/apikey) (recommended - free tier available)
   - [OpenAI](https://platform.openai.com/api-keys) (GPT-3.5/GPT-4)
   - [Anthropic Claude](https://console.anthropic.com/)

2. **ElevenLabs** (required):
   - [ElevenLabs TTS](https://elevenlabs.io/) - Free tier: 10,000 characters/month

3. **PostgreSQL Database** (required):
   - Local installation or cloud provider (AWS RDS, Google Cloud SQL, etc.)

## 🚀 Installation

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd restaurant-booking-voice-agent
```

### Step 2: Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set Up PostgreSQL Database

**Option A: Local PostgreSQL**
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE restaurant_booking;
CREATE USER booking_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE restaurant_booking TO booking_user;
\q
```

**Option B: Docker PostgreSQL**
```bash
docker run --name restaurant-db \
  -e POSTGRES_DB=restaurant_booking \
  -e POSTGRES_USER=booking_user \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  -d postgres:13
```

### Step 5: Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or use your preferred editor
```

See [Configuration](#configuration) section for detailed setup.

### Step 6: Initialize Database
```bash
# Run database initialization script
python src/db_init.py
```

This will:
- Create all required tables (bookings, time_slots, restaurant_config)
- Seed initial restaurant configuration
- Set default operating hours

### Step 7: Verify Installation
```bash
# Test audio system
python src/audio/demo.py

# Run tests (optional)
pytest tests/
```

## ⚙️ Configuration

### Required Environment Variables

Edit your `.env` file with the following required variables:

```bash
# Database (REQUIRED)
DATABASE_URL=postgresql://booking_user:secure_password@localhost:5432/restaurant_booking

# At least ONE LLM provider (REQUIRED)
GEMINI_API_KEY=your-gemini-api-key-here
# OR
OPENAI_API_KEY=sk-your-openai-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Text-to-Speech (REQUIRED)
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
```

### Optional Configuration

```bash
# Notification services (not yet implemented)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

SENDGRID_API_KEY=your-sendgrid-key

# Restaurant information
RESTAURANT_NAME=Your Restaurant Name
RESTAURANT_PHONE=+1234567890
RESTAURANT_ADDRESS=123 Main St, City, State
```

### Database Configuration

The restaurant configuration (operating hours, capacity, booking window) is stored in the database and can be modified:

```python
from models.database import get_db_session, RestaurantConfig

with get_db_session() as session:
    config = session.query(RestaurantConfig).filter_by(id=1).first()
    config.max_party_size = 10
    config.booking_window_days = 60
    session.commit()
```

## 🎯 Usage

### Running the Voice Agent

```bash
# Start the voice agent
python src/main.py
```

**Note**: The main orchestrator (`main.py`) is currently under development. For now, you can test individual components:

```bash
# Test audio recording/playback
python src/audio/demo.py

# Test speech-to-text
python -c "from speech import whisper_stt; # test STT"

# Test text-to-speech
python -c "from speech.elevenlabs_tts import ElevenLabsTTS; tts = ElevenLabsTTS(); tts.generate_speech('Hello, welcome!')"

# Test booking service
python -c "from services.booking_service import BookingService; # test service"
```

### Example Conversation Flow

```
Agent: "Hello! Thank you for calling. I'd be happy to help you make a reservation. 
        What date would you like to book?"

User: "I'd like to book for this Friday at 7 PM for four people"

Agent: "Perfect! I have you down for Friday, December 22nd at 7:00 PM for a party 
        of four. Let me check availability... Great news! We have that time available. 
        May I have your name for the reservation?"

User: "John Smith"

Agent: "Thank you, John. And what's the best phone number to reach you?"

User: "555-1234"

Agent: "Perfect! Let me confirm your reservation: Friday, December 22nd at 7:00 PM 
        for 4 people under the name John Smith. Phone: 555-1234. Is everything correct?"

User: "Yes, that's correct"

Agent: "Wonderful! Your reservation is confirmed. We look forward to seeing you 
        on Friday at 7 PM. Is there anything else I can help you with?"
```

## 🏗️ Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                     (Microphone / Speaker)                      │
└────────────────┬──────────────────────────┬─────────────────────┘
                 │                          │
                 ▼                          ▼
┌─────────────────────────┐    ┌───────────────────────────┐
│    AudioManager         │    │   ElevenLabs TTS          │
│  - Recording            │    │  - Speech Synthesis        │
│  - Playback             │    │  - Voice Output            │
│  - Silence Detection    │    │  - Audio Caching           │
└────────────┬────────────┘    └───────────────────────────┘
             │
             ▼
┌─────────────────────────┐
│   Whisper STT           │
│  - Speech Recognition   │
│  - Transcription        │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│               Conversation Orchestrator (Main)                  │
│                                                                 │
│  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ State Manager    │  │   NLU Engine    │  │  Response    │ │
│  │ - States         │  │ - Extraction    │  │  Generator   │ │
│  │ - Transitions    │  │ - Parsing       │  │ - LLM-based  │ │
│  │ - Context        │  │ - Validation    │  │ - Natural    │ │
│  └──────────────────┘  └─────────────────┘  └──────────────┘ │
└────────────┬────────────────────────┬────────────────────────────┘
             │                        │
             ▼                        ▼
┌──────────────────────┐    ┌─────────────────────────────┐
│  LLM Service         │    │   Booking Service           │
│  - OpenAI            │    │  - Availability Check       │
│  - Gemini            │    │  - Validation               │
│  - Claude            │    │  - Booking Creation         │
│  - Retry Logic       │    │  - Capacity Management      │
└──────────────────────┘    └────────────┬────────────────┘
                                         │
                                         ▼
                            ┌─────────────────────────┐
                            │  PostgreSQL Database    │
                            │  - Bookings             │
                            │  - Time Slots           │
                            │  - Configuration        │
                            └─────────────────────────┘
```

### Component Descriptions

- **AudioManager**: Handles microphone input and speaker output with silence detection
- **Whisper STT**: Converts speech to text using OpenAI's Whisper model
- **ElevenLabs TTS**: Generates natural-sounding speech from text responses
- **Conversation State Manager**: Manages dialog flow and conversation state
- **NLU Engine**: Extracts structured booking information from user utterances
- **Response Generator**: Creates natural, context-aware responses using LLMs
- **LLM Service**: Unified interface for multiple LLM providers with failover
- **Booking Service**: Business logic for availability, validation, and booking creation
- **PostgreSQL Database**: Persistent storage for bookings and configuration

## 🔄 Conversation Flow

### State Machine

The conversation follows a state-based flow:

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

**Key Features:**
- **Non-linear flow**: Users can provide multiple pieces of information at once
- **Correction handling**: Users can correct previously provided information
- **Context switching**: Natural transitions between different booking fields
- **Validation at each step**: Real-time validation of user input

### Information Extraction

The NLU engine can extract multiple fields from a single utterance:

```
Input: "I'd like to book for Friday at 7 PM for 4 people"
Extracted:
  - date: "2024-12-22" (Friday)
  - time: "19:00"
  - party_size: 4
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Audio Device Not Found
```
Error: No audio devices found
```

**Solution**:
- **Linux**: Install portaudio: `sudo apt-get install portaudio19-dev`
- **macOS**: Install portaudio: `brew install portaudio`
- **Windows**: PyAudio should work out of the box
- Check microphone permissions in system settings
- List available devices: `python src/audio/demo.py`

#### 2. Database Connection Error
```
Error: could not connect to server: Connection refused
```

**Solution**:
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check DATABASE_URL in `.env` file
- Verify database exists: `psql -U booking_user -d restaurant_booking`
- Check firewall settings if using remote database

#### 3. API Rate Limits
```
Error: Rate limit exceeded
```

**Solution**:
- **ElevenLabs**: Free tier has character limits - upgrade or reduce usage
- **OpenAI**: Check quota at platform.openai.com/account/usage
- **Gemini**: Very generous free tier - should rarely hit limits
- The system has automatic retry with exponential backoff

#### 4. Poor Transcription Quality
```
Issue: Speech recognition not accurate
```

**Solution**:
- Ensure quiet environment with minimal background noise
- Speak clearly at normal pace
- Check microphone positioning (6-12 inches from mouth)
- Verify microphone quality and settings
- Adjust silence detection threshold in AudioConfig

#### 5. Import Errors
```
ModuleNotFoundError: No module named 'X'
```

**Solution**:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- For PyAudio issues on Linux: `sudo apt-get install python3-pyaudio`

#### 6. Database Migration Issues
```
Error: Table already exists
```

**Solution**:
- Drop and recreate: `python src/db_init.py --force` (if implemented)
- Or manually: `DROP DATABASE restaurant_booking; CREATE DATABASE restaurant_booking;`
- Then run: `python src/db_init.py`

## 📚 API Services

### Required Services

| Service | Purpose | Free Tier | Pricing Link |
|---------|---------|-----------|--------------|
| **PostgreSQL** | Database | Yes (self-hosted) | [Providers](https://www.postgresql.org/support/professional_hosting/) |
| **ElevenLabs** | Text-to-Speech | 10K chars/month | [Pricing](https://elevenlabs.io/pricing) |

### LLM Providers (Choose One or More)

| Provider | Purpose | Free Tier | Best For | Pricing |
|----------|---------|-----------|----------|---------|
| **Google Gemini** | Conversation & NLU | Generous free tier | Development | [Free](https://ai.google.dev/pricing) |
| **OpenAI** | Conversation & NLU | Pay-as-you-go | Production | [Pricing](https://openai.com/pricing) |
| **Anthropic Claude** | Conversation & NLU | Pay-as-you-go | Advanced use | [Pricing](https://www.anthropic.com/pricing) |

### Future Services (Not Yet Implemented)

| Service | Purpose | Status |
|---------|---------|--------|
| **Twilio** | SMS notifications | Planned |
| **SendGrid** | Email notifications | Planned |

### Cost Estimates

**Typical monthly costs for moderate usage (100 bookings/month):**

- **ElevenLabs**: ~$5 (Creator tier for 30K characters)
- **Gemini**: $0 (within free tier)
- **OpenAI GPT-3.5**: ~$2-3 for API calls
- **PostgreSQL**: $0 (self-hosted) or $15-30 (managed)

**Total**: $5-40/month depending on choices

## 📖 Additional Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Technical architecture and development guide
- **[docs/AUDIO_SYSTEM.md](docs/AUDIO_SYSTEM.md)**: Audio system documentation
- **[docs/DATABASE_SETUP.md](docs/DATABASE_SETUP.md)**: Database setup details
- **[docs/RESPONSE_GENERATION.md](docs/RESPONSE_GENERATION.md)**: Response generation guide

## 🤝 Contributing

Contributions are welcome! Please see [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

## 📄 License

[Add your license information here]

## 👥 Contact

[Add contact information here]

## 🙏 Acknowledgments

- OpenAI Whisper for speech recognition
- ElevenLabs for natural TTS
- LLM providers (Google, OpenAI, Anthropic)
- Open source community

---

**Note**: This project is under active development. Some features mentioned in the architecture may not be fully implemented yet. See [DEVELOPMENT.md](DEVELOPMENT.md) for current status and roadmap.
