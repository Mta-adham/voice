"""
Unit tests for database models and operations.

Tests:
- Database connection and initialization
- Creating bookings with valid data
- Querying bookings by date/time/customer
- Updating booking status
- Time slot capacity tracking
- Constraint violations (invalid data)
"""
import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.database import Booking, TimeSlot, RestaurantConfig, init_db, get_db_session
from models.schemas import BookingCreate


class TestDatabaseConnection:
    """Test database initialization and connectivity."""
    
    def test_init_db_with_url(self, test_db_url):
        """Test database initialization with explicit URL."""
        engine = init_db(test_db_url)
        assert engine is not None
        assert engine.url.database == ":memory:"
    
    def test_db_session_creation(self, db_session: Session):
        """Test that database session can be created."""
        assert db_session is not None
        assert db_session.is_active


class TestBookingCRUD:
    """Test CRUD operations on Booking model."""
    
    def test_create_booking_valid_data(self, db_session: Session):
        """Test creating a booking with valid data."""
        tomorrow = date.today() + timedelta(days=1)
        
        booking = Booking(
            date=tomorrow,
            time_slot=time(18, 30),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890",
            customer_email="john@example.com",
            special_requests="Window seat",
            status="confirmed"
        )
        
        db_session.add(booking)
        db_session.commit()
        db_session.refresh(booking)
        
        assert booking.id is not None
        assert booking.customer_name == "John Doe"
        assert booking.party_size == 4
        assert booking.status == "confirmed"
    
    def test_read_booking_by_id(self, db_session: Session):
        """Test querying a booking by ID."""
        tomorrow = date.today() + timedelta(days=1)
        
        booking = Booking(
            date=tomorrow,
            time_slot=time(18, 30),
            party_size=4,
            customer_name="Jane Smith",
            customer_phone="+9876543210",
            status="confirmed"
        )
        
        db_session.add(booking)
        db_session.commit()
        
        # Query by ID
        retrieved = db_session.query(Booking).filter_by(id=booking.id).first()
        
        assert retrieved is not None
        assert retrieved.customer_name == "Jane Smith"
        assert retrieved.party_size == 4
    
    def test_query_bookings_by_date(self, db_session: Session):
        """Test querying bookings by date."""
        tomorrow = date.today() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        # Create bookings on different dates
        booking1 = Booking(
            date=tomorrow,
            time_slot=time(18, 30),
            party_size=4,
            customer_name="Customer 1",
            customer_phone="+1111111111",
            status="confirmed"
        )
        
        booking2 = Booking(
            date=day_after,
            time_slot=time(19, 0),
            party_size=2,
            customer_name="Customer 2",
            customer_phone="+2222222222",
            status="confirmed"
        )
        
        db_session.add_all([booking1, booking2])
        db_session.commit()
        
        # Query bookings for tomorrow
        results = db_session.query(Booking).filter_by(date=tomorrow).all()
        
        assert len(results) == 1
        assert results[0].customer_name == "Customer 1"
    
    def test_query_bookings_by_phone(self, db_session: Session):
        """Test querying bookings by customer phone."""
        tomorrow = date.today() + timedelta(days=1)
        phone = "+1234567890"
        
        booking = Booking(
            date=tomorrow,
            time_slot=time(18, 30),
            party_size=4,
            customer_name="John Doe",
            customer_phone=phone,
            status="confirmed"
        )
        
        db_session.add(booking)
        db_session.commit()
        
        # Query by phone
        results = db_session.query(Booking).filter_by(customer_phone=phone).all()
        
        assert len(results) == 1
        assert results[0].customer_phone == phone
    
    def test_update_booking_status(self, db_session: Session):
        """Test updating booking status."""
        tomorrow = date.today() + timedelta(days=1)
        
        booking = Booking(
            date=tomorrow,
            time_slot=time(18, 30),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890",
            status="confirmed"
        )
        
        db_session.add(booking)
        db_session.commit()
        
        # Update status
        booking.status = "completed"
        db_session.commit()
        
        # Verify update
        db_session.refresh(booking)
        assert booking.status == "completed"
    
    def test_delete_booking(self, db_session: Session):
        """Test deleting a booking."""
        tomorrow = date.today() + timedelta(days=1)
        
        booking = Booking(
            date=tomorrow,
            time_slot=time(18, 30),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890",
            status="confirmed"
        )
        
        db_session.add(booking)
        db_session.commit()
        booking_id = booking.id
        
        # Delete
        db_session.delete(booking)
        db_session.commit()
        
        # Verify deletion
        result = db_session.query(Booking).filter_by(id=booking_id).first()
        assert result is None


class TestBookingConstraints:
    """Test database constraints on Booking model."""
    
    def test_party_size_constraint_min(self, db_session: Session):
        """Test party size minimum constraint (must be >= 1)."""
        tomorrow = date.today() + timedelta(days=1)
        
        booking = Booking(
            date=tomorrow,
            time_slot=time(18, 30),
            party_size=0,  # Invalid: too small
            customer_name="John Doe",
            customer_phone="+1234567890",
            status="confirmed"
        )
        
        db_session.add(booking)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_party_size_constraint_max(self, db_session: Session):
        """Test party size maximum constraint (must be <= 8)."""
        tomorrow = date.today() + timedelta(days=1)
        
        booking = Booking(
            date=tomorrow,
            time_slot=time(18, 30),
            party_size=9,  # Invalid: too large
            customer_name="John Doe",
            customer_phone="+1234567890",
            status="confirmed"
        )
        
        db_session.add(booking)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_duplicate_booking_constraint(self, db_session: Session):
        """Test unique constraint on date/time/phone combination."""
        tomorrow = date.today() + timedelta(days=1)
        booking_time = time(18, 30)
        phone = "+1234567890"
        
        # Create first booking
        booking1 = Booking(
            date=tomorrow,
            time_slot=booking_time,
            party_size=4,
            customer_name="John Doe",
            customer_phone=phone,
            status="confirmed"
        )
        
        db_session.add(booking1)
        db_session.commit()
        
        # Try to create duplicate booking
        booking2 = Booking(
            date=tomorrow,
            time_slot=booking_time,
            party_size=2,
            customer_name="John Doe",
            customer_phone=phone,  # Same phone, date, time
            status="confirmed"
        )
        
        db_session.add(booking2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestTimeSlotModel:
    """Test TimeSlot model and capacity tracking."""
    
    def test_create_time_slot(self, db_session: Session):
        """Test creating a time slot."""
        tomorrow = date.today() + timedelta(days=1)
        
        slot = TimeSlot(
            date=tomorrow,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=0
        )
        
        db_session.add(slot)
        db_session.commit()
        db_session.refresh(slot)
        
        assert slot.id is not None
        assert slot.total_capacity == 50
        assert slot.booked_capacity == 0
    
    def test_time_slot_is_available(self, db_session: Session):
        """Test is_available method on TimeSlot."""
        tomorrow = date.today() + timedelta(days=1)
        
        slot = TimeSlot(
            date=tomorrow,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=45
        )
        
        # Should be available for party of 5
        assert slot.is_available(5) is True
        
        # Should not be available for party of 6
        assert slot.is_available(6) is False
    
    def test_time_slot_remaining_capacity(self, db_session: Session):
        """Test remaining_capacity method on TimeSlot."""
        tomorrow = date.today() + timedelta(days=1)
        
        slot = TimeSlot(
            date=tomorrow,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=32
        )
        
        assert slot.remaining_capacity() == 18
    
    def test_update_booked_capacity(self, db_session: Session):
        """Test updating booked capacity after booking."""
        tomorrow = date.today() + timedelta(days=1)
        
        slot = TimeSlot(
            date=tomorrow,
            time=time(18, 0),
            total_capacity=50,
            booked_capacity=0
        )
        
        db_session.add(slot)
        db_session.commit()
        
        # Simulate booking
        slot.booked_capacity += 4
        db_session.commit()
        
        db_session.refresh(slot)
        assert slot.booked_capacity == 4
        assert slot.remaining_capacity() == 46
    
    def test_unique_constraint_on_date_time(self, db_session: Session):
        """Test unique constraint on date and time combination."""
        tomorrow = date.today() + timedelta(days=1)
        slot_time = time(18, 0)
        
        # Create first slot
        slot1 = TimeSlot(
            date=tomorrow,
            time=slot_time,
            total_capacity=50,
            booked_capacity=0
        )
        
        db_session.add(slot1)
        db_session.commit()
        
        # Try to create duplicate slot
        slot2 = TimeSlot(
            date=tomorrow,
            time=slot_time,
            total_capacity=50,
            booked_capacity=0
        )
        
        db_session.add(slot2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestRestaurantConfig:
    """Test RestaurantConfig model."""
    
    def test_create_restaurant_config(self, db_session: Session):
        """Test creating restaurant configuration."""
        config = RestaurantConfig(
            id=1,
            operating_hours={
                "monday": {"open": "11:00", "close": "22:00"},
                "friday": {"open": "11:00", "close": "23:00"}
            },
            slot_duration=30,
            max_party_size=8,
            booking_window_days=30
        )
        
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)
        
        assert config.id == 1
        assert config.slot_duration == 30
        assert config.max_party_size == 8
    
    def test_restaurant_config_single_row_constraint(self, db_session: Session, restaurant_config: RestaurantConfig):
        """Test that only one configuration row is allowed."""
        # Try to create second config
        config2 = RestaurantConfig(
            id=2,  # Different ID
            operating_hours={"monday": {"open": "09:00", "close": "20:00"}},
            slot_duration=30,
            max_party_size=8,
            booking_window_days=30
        )
        
        db_session.add(config2)
        
        # Should fail due to check constraint
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_query_restaurant_config(self, db_session: Session, restaurant_config: RestaurantConfig):
        """Test querying restaurant configuration."""
        config = db_session.query(RestaurantConfig).filter_by(id=1).first()
        
        assert config is not None
        assert config.slot_duration == 30
        assert "monday" in config.operating_hours
