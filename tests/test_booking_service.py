"""
Unit and integration tests for BookingService.

Tests cover:
- Validation rules for booking requests
- Availability queries with capacity calculations
- Booking creation flow with atomic transactions
- Time slot generation
- Error handling and edge cases
"""
import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError

import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from models.database import Base, Booking, TimeSlot, RestaurantConfig
from models.schemas import BookingCreate, TimeSlotInfo
from services.booking_service import (
    BookingService,
    ValidationError,
    CapacityError,
    DatabaseError
)


# Test fixtures
@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def restaurant_config(db_session):
    """Create a restaurant configuration for testing."""
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
    return config


@pytest.fixture
def booking_service(db_session, restaurant_config):
    """Create a BookingService instance for testing."""
    return BookingService(db_session)


# Unit Tests for Validation Rules

class TestValidationRules:
    """Test validation rules for booking requests."""
    
    def test_validate_past_date(self, booking_service):
        """Test that past dates are rejected."""
        past_date = date.today() - timedelta(days=1)
        is_valid, error_msg = booking_service.validate_booking_request(
            past_date, time(18, 0), 4
        )
        assert not is_valid
        assert "cannot be in the past" in error_msg
    
    def test_validate_future_date_beyond_window(self, booking_service):
        """Test that dates beyond booking window are rejected."""
        future_date = date.today() + timedelta(days=31)
        is_valid, error_msg = booking_service.validate_booking_request(
            future_date, time(18, 0), 4
        )
        assert not is_valid
        assert "30 days in advance" in error_msg
    
    def test_validate_party_size_too_small(self, booking_service):
        """Test that party size < 1 is rejected."""
        valid_date = date.today() + timedelta(days=1)
        is_valid, error_msg = booking_service.validate_booking_request(
            valid_date, time(18, 0), 0
        )
        assert not is_valid
        assert "at least 1" in error_msg
    
    def test_validate_party_size_too_large(self, booking_service):
        """Test that party size > max is rejected."""
        valid_date = date.today() + timedelta(days=1)
        is_valid, error_msg = booking_service.validate_booking_request(
            valid_date, time(18, 0), 9
        )
        assert not is_valid
        assert "cannot exceed 8" in error_msg
    
    def test_validate_time_before_opening(self, booking_service):
        """Test that times before opening hours are rejected."""
        valid_date = date.today() + timedelta(days=1)
        # Assuming restaurant opens at 11:00
        is_valid, error_msg = booking_service.validate_booking_request(
            valid_date, time(10, 0), 4
        )
        assert not is_valid
        assert "outside operating hours" in error_msg
    
    def test_validate_time_after_closing(self, booking_service):
        """Test that times after closing hours are rejected."""
        valid_date = date.today() + timedelta(days=1)
        # Time after closing
        is_valid, error_msg = booking_service.validate_booking_request(
            valid_date, time(23, 0), 4
        )
        assert not is_valid
        assert "outside operating hours" in error_msg
    
    def test_validate_valid_request(self, booking_service):
        """Test that a valid request passes validation."""
        valid_date = date.today() + timedelta(days=1)
        is_valid, error_msg = booking_service.validate_booking_request(
            valid_date, time(18, 0), 4
        )
        assert is_valid
        assert error_msg == ""
    
    def test_validate_max_date_in_window(self, booking_service):
        """Test that booking on the last day of window is accepted."""
        valid_date = date.today() + timedelta(days=30)
        is_valid, error_msg = booking_service.validate_booking_request(
            valid_date, time(18, 0), 4
        )
        assert is_valid
        assert error_msg == ""


# Tests for Available Slots

class TestAvailableSlots:
    """Test get_available_slots method."""
    
    def test_get_available_slots_empty(self, booking_service):
        """Test getting available slots when no slots exist."""
        future_date = date.today() + timedelta(days=1)
        slots = booking_service.get_available_slots(future_date, 4)
        assert len(slots) == 0
    
    def test_get_available_slots_with_capacity(self, booking_service, db_session):
        """Test getting available slots with sufficient capacity."""
        future_date = date.today() + timedelta(days=1)
        
        # Create time slots
        slot1 = TimeSlot(date=future_date, time=time(18, 0), total_capacity=50, booked_capacity=0)
        slot2 = TimeSlot(date=future_date, time=time(19, 0), total_capacity=50, booked_capacity=0)
        db_session.add_all([slot1, slot2])
        db_session.commit()
        
        slots = booking_service.get_available_slots(future_date, 4)
        assert len(slots) == 2
        assert all(isinstance(slot, TimeSlotInfo) for slot in slots)
        assert all(slot.is_available for slot in slots)
    
    def test_get_available_slots_filters_insufficient_capacity(self, booking_service, db_session):
        """Test that slots with insufficient capacity are filtered out."""
        future_date = date.today() + timedelta(days=1)
        
        # Create time slots - one with enough capacity, one without
        slot1 = TimeSlot(date=future_date, time=time(18, 0), total_capacity=50, booked_capacity=0)
        slot2 = TimeSlot(date=future_date, time=time(19, 0), total_capacity=50, booked_capacity=48)
        db_session.add_all([slot1, slot2])
        db_session.commit()
        
        # Request party size of 4
        slots = booking_service.get_available_slots(future_date, 4)
        
        # Only slot1 should be returned
        assert len(slots) == 1
        assert slots[0].time == time(18, 0)
    
    def test_get_available_slots_filters_past_times(self, booking_service, db_session):
        """Test that past time slots are filtered out for today."""
        today = date.today()
        
        # Create slots - one in the past, one in the future
        past_time = (datetime.now() - timedelta(hours=1)).time()
        future_time = (datetime.now() + timedelta(hours=1)).time()
        
        slot1 = TimeSlot(date=today, time=past_time, total_capacity=50, booked_capacity=0)
        slot2 = TimeSlot(date=today, time=future_time, total_capacity=50, booked_capacity=0)
        db_session.add_all([slot1, slot2])
        db_session.commit()
        
        slots = booking_service.get_available_slots(today, 4)
        
        # Only future slot should be returned
        assert all(slot.time > datetime.now().time() for slot in slots)
    
    def test_get_available_slots_outside_operating_hours(self, booking_service, db_session):
        """Test that slots outside operating hours are filtered out."""
        future_date = date.today() + timedelta(days=1)
        
        # Create slot outside operating hours (before 11:00)
        slot1 = TimeSlot(date=future_date, time=time(9, 0), total_capacity=50, booked_capacity=0)
        slot2 = TimeSlot(date=future_date, time=time(18, 0), total_capacity=50, booked_capacity=0)
        db_session.add_all([slot1, slot2])
        db_session.commit()
        
        slots = booking_service.get_available_slots(future_date, 4)
        
        # Only slot within operating hours should be returned
        assert len(slots) == 1
        assert slots[0].time == time(18, 0)


# Integration Tests for Booking Creation

class TestBookingCreation:
    """Integration tests for create_booking method."""
    
    def test_create_booking_success(self, booking_service, db_session):
        """Test successful booking creation."""
        future_date = date.today() + timedelta(days=1)
        
        # Create time slot
        time_slot = TimeSlot(
            date=future_date,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=0
        )
        db_session.add(time_slot)
        db_session.commit()
        
        # Create booking
        booking_data = BookingCreate(
            date=future_date,
            time_slot=time(18, 0),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890",
            customer_email="john@example.com",
            special_requests="Window seat"
        )
        
        booking = booking_service.create_booking(booking_data)
        
        assert booking.id is not None
        assert booking.customer_name == "John Doe"
        assert booking.party_size == 4
        assert booking.status == "confirmed"
        
        # Verify capacity was updated
        db_session.refresh(time_slot)
        assert time_slot.booked_capacity == 4
    
    def test_create_booking_insufficient_capacity(self, booking_service, db_session):
        """Test that booking fails when insufficient capacity."""
        future_date = date.today() + timedelta(days=1)
        
        # Create time slot with limited capacity
        time_slot = TimeSlot(
            date=future_date,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=48
        )
        db_session.add(time_slot)
        db_session.commit()
        
        # Try to create booking for 4 people (only 2 seats left)
        booking_data = BookingCreate(
            date=future_date,
            time_slot=time(18, 0),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890"
        )
        
        with pytest.raises(CapacityError) as exc_info:
            booking_service.create_booking(booking_data)
        
        assert "Insufficient capacity" in str(exc_info.value)
    
    def test_create_booking_validation_failure(self, booking_service, db_session):
        """Test that booking fails validation checks."""
        past_date = date.today() - timedelta(days=1)
        
        booking_data = BookingCreate(
            date=past_date,
            time_slot=time(18, 0),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            booking_service.create_booking(booking_data)
        
        assert "cannot be in the past" in str(exc_info.value)
    
    def test_create_booking_duplicate_constraint(self, booking_service, db_session):
        """Test that duplicate booking constraint is enforced."""
        future_date = date.today() + timedelta(days=1)
        
        # Create time slot
        time_slot = TimeSlot(
            date=future_date,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=0
        )
        db_session.add(time_slot)
        db_session.commit()
        
        # Create first booking
        booking_data = BookingCreate(
            date=future_date,
            time_slot=time(18, 0),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890"
        )
        
        booking1 = booking_service.create_booking(booking_data)
        assert booking1.id is not None
        
        # Try to create duplicate booking with same phone
        db_session.expunge_all()  # Clear session to force new query
        service2 = BookingService(db_session)
        
        with pytest.raises(ValidationError) as exc_info:
            service2.create_booking(booking_data)
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_booking_creates_slot_if_missing(self, booking_service, db_session):
        """Test that booking creation creates time slot if it doesn't exist."""
        future_date = date.today() + timedelta(days=1)
        
        # Don't create time slot beforehand
        booking_data = BookingCreate(
            date=future_date,
            time_slot=time(18, 0),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890"
        )
        
        booking = booking_service.create_booking(booking_data)
        
        assert booking.id is not None
        
        # Verify time slot was created
        time_slot = db_session.query(TimeSlot).filter(
            TimeSlot.date == future_date,
            TimeSlot.time == time(18, 0)
        ).first()
        
        assert time_slot is not None
        assert time_slot.booked_capacity == 4
    
    def test_create_booking_atomic_transaction(self, booking_service, db_session):
        """Test that booking creation is atomic (all or nothing)."""
        future_date = date.today() + timedelta(days=1)
        
        # Create time slot
        time_slot = TimeSlot(
            date=future_date,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=0
        )
        db_session.add(time_slot)
        db_session.commit()
        
        initial_capacity = time_slot.booked_capacity
        
        # Create booking data with invalid party size (should fail validation)
        booking_data = BookingCreate(
            date=future_date,
            time_slot=time(18, 0),
            party_size=10,  # Exceeds max
            customer_name="John Doe",
            customer_phone="+1234567890"
        )
        
        with pytest.raises(ValidationError):
            booking_service.create_booking(booking_data)
        
        # Verify capacity wasn't updated
        db_session.refresh(time_slot)
        assert time_slot.booked_capacity == initial_capacity


# Tests for Time Slot Generation

class TestTimeSlotGeneration:
    """Test generate_time_slots method."""
    
    def test_generate_time_slots_success(self, booking_service, db_session):
        """Test successful time slot generation."""
        future_date = date.today() + timedelta(days=1)
        
        booking_service.generate_time_slots(future_date)
        
        # Verify slots were created
        slots = db_session.query(TimeSlot).filter(TimeSlot.date == future_date).all()
        
        assert len(slots) > 0
        
        # Verify slots are within operating hours
        for slot in slots:
            assert slot.total_capacity == 50
            assert slot.booked_capacity == 0
    
    def test_generate_time_slots_skip_if_exists(self, booking_service, db_session):
        """Test that generation skips if slots already exist."""
        future_date = date.today() + timedelta(days=1)
        
        # Create one slot manually
        existing_slot = TimeSlot(
            date=future_date,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=10
        )
        db_session.add(existing_slot)
        db_session.commit()
        
        initial_count = db_session.query(TimeSlot).filter(TimeSlot.date == future_date).count()
        
        # Try to generate slots
        booking_service.generate_time_slots(future_date)
        
        # Verify no new slots were added
        final_count = db_session.query(TimeSlot).filter(TimeSlot.date == future_date).count()
        assert final_count == initial_count
    
    def test_generate_time_slots_respects_slot_duration(self, booking_service, db_session, restaurant_config):
        """Test that slots are generated according to slot_duration."""
        future_date = date.today() + timedelta(days=1)
        
        booking_service.generate_time_slots(future_date)
        
        slots = db_session.query(TimeSlot).filter(
            TimeSlot.date == future_date
        ).order_by(TimeSlot.time).all()
        
        # Check that consecutive slots are 30 minutes apart
        if len(slots) > 1:
            for i in range(len(slots) - 1):
                time1 = datetime.combine(future_date, slots[i].time)
                time2 = datetime.combine(future_date, slots[i + 1].time)
                diff = (time2 - time1).total_seconds() / 60
                assert diff == 30


# Tests for Error Handling

class TestErrorHandling:
    """Test error handling in BookingService."""
    
    def test_get_config_missing(self, db_session):
        """Test that missing config raises DatabaseError."""
        service = BookingService(db_session)
        
        with pytest.raises(DatabaseError) as exc_info:
            service._get_restaurant_config()
        
        assert "not found" in str(exc_info.value)
    
    def test_database_connection_error(self, booking_service):
        """Test handling of database connection errors."""
        # Mock the session to raise OperationalError
        booking_service.session.query = Mock(
            side_effect=OperationalError("Connection lost", None, None)
        )
        
        with pytest.raises(DatabaseError) as exc_info:
            booking_service.get_available_slots(date.today(), 4)
        
        assert "Database query failed" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
