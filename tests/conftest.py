"""
Pytest configuration and shared fixtures.
"""
import sys
import os
import tempfile
from pathlib import Path
from datetime import date, time, datetime, timedelta
from typing import Generator
import pytest
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from models.database import Base, Booking, TimeSlot, RestaurantConfig, init_db
from models.schemas import BookingCreate
from services.booking_service import BookingService


@pytest.fixture(scope="function")
def test_db_url() -> str:
    """
    Provide an in-memory SQLite database URL for testing.
    Each test gets a fresh database.
    """
    return "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine(test_db_url: str):
    """
    Create a test database engine with all tables.
    """
    engine = create_engine(test_db_url, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Create a database session for testing with automatic rollback.
    """
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture(scope="function")
def restaurant_config(db_session: Session) -> RestaurantConfig:
    """
    Create a default restaurant configuration for testing.
    """
    config = RestaurantConfig(
        id=1,
        operating_hours={
            "monday": {"open": "11:00", "close": "22:00"},
            "tuesday": {"open": "11:00", "close": "22:00"},
            "wednesday": {"open": "11:00", "close": "22:00"},
            "thursday": {"open": "11:00", "close": "22:00"},
            "friday": {"open": "11:00", "close": "23:00"},
            "saturday": {"open": "10:00", "close": "23:00"},
            "sunday": {"open": "10:00", "close": "21:00"}
        },
        slot_duration=30,
        max_party_size=8,
        booking_window_days=30
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


@pytest.fixture(scope="function")
def sample_time_slots(db_session: Session, restaurant_config: RestaurantConfig):
    """
    Create sample time slots for testing.
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    slots = [
        TimeSlot(date=tomorrow, time=time(12, 0), total_capacity=50, booked_capacity=0),
        TimeSlot(date=tomorrow, time=time(12, 30), total_capacity=50, booked_capacity=20),
        TimeSlot(date=tomorrow, time=time(18, 0), total_capacity=50, booked_capacity=45),
        TimeSlot(date=tomorrow, time=time(18, 30), total_capacity=50, booked_capacity=50),
        TimeSlot(date=tomorrow, time=time(19, 0), total_capacity=50, booked_capacity=10),
    ]
    
    for slot in slots:
        db_session.add(slot)
    
    db_session.commit()
    return slots


@pytest.fixture(scope="function")
def sample_booking_data() -> BookingCreate:
    """
    Create sample booking data for testing.
    """
    tomorrow = date.today() + timedelta(days=1)
    return BookingCreate(
        date=tomorrow,
        time_slot=time(12, 0),
        party_size=4,
        customer_name="John Doe",
        customer_phone="+1234567890",
        customer_email="john.doe@example.com",
        special_requests="Window seat preferred"
    )


@pytest.fixture(scope="function")
def booking_service(db_session: Session, restaurant_config: RestaurantConfig) -> BookingService:
    """
    Create a BookingService instance for testing.
    """
    return BookingService(db_session)


@pytest.fixture(scope="function")
def sample_audio_data() -> tuple[np.ndarray, int]:
    """
    Generate sample audio data for testing (1 second of 440Hz sine wave).
    """
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Convert to int16 format
    audio_data = (audio_data * 32767).astype(np.int16)
    
    return audio_data, sample_rate


@pytest.fixture(scope="function")
def sample_silence_audio() -> tuple[np.ndarray, int]:
    """
    Generate silent audio data for testing.
    """
    sample_rate = 16000
    duration = 1.0
    audio_data = np.zeros(int(sample_rate * duration), dtype=np.int16)
    return audio_data, sample_rate


@pytest.fixture(scope="function")
def temp_audio_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for audio files during testing.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def mock_llm_response() -> dict:
    """
    Mock LLM response data.
    """
    return {
        "content": "This is a mock LLM response for testing purposes.",
        "provider": "openai",
        "tokens_used": 20
    }


@pytest.fixture(scope="function")
def mock_env_vars(monkeypatch):
    """
    Set up mock environment variables for testing.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test_elevenlabs_key")
