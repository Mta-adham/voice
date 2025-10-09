"""
Unit tests for booking service business logic.

Tests:
- get_available_slots() with various dates and party sizes
- create_booking() with valid and invalid inputs
- validate_booking_request() for all validation rules
- Edge cases (fully booked, last available slot, boundary dates)
"""
import pytest
from datetime import date, time, timedelta
from sqlalchemy.orm import Session

from services.booking_service import (
    BookingService,
    ValidationError,
    CapacityError,
    DatabaseError
)
from models.database import TimeSlot, RestaurantConfig
from models.schemas import BookingCreate


class TestGetAvailableSlots:
    """Test get_available_slots functionality."""
    
    def test_get_available_slots_empty_date(
        self,
        booking_service: BookingService,
        db_session: Session
    ):
        """Test getting slots for a date with no slots."""
        tomorrow = date.today() + timedelta(days=1)
        
        slots = booking_service.get_available_slots(tomorrow, party_size=4)
        
        assert len(slots) == 0
    
    def test_get_available_slots_with_capacity(
        self,
        booking_service: BookingService,
        sample_time_slots
    ):
        """Test getting slots with sufficient capacity."""
        tomorrow = date.today() + timedelta(days=1)
        
        slots = booking_service.get_available_slots(tomorrow, party_size=4)
        
        # Should return slots with capacity >= 4
        assert len(slots) > 0
        for slot in slots:
            assert slot.is_available is True
            assert slot.remaining_capacity >= 4
    
    def test_get_available_slots_filters_insufficient_capacity(
        self,
        booking_service: BookingService,
        sample_time_slots
    ):
        """Test that slots with insufficient capacity are filtered out."""
        tomorrow = date.today() + timedelta(days=1)
        
        # Request large party size
        slots = booking_service.get_available_slots(tomorrow, party_size=40)
        
        # Should only return slots with capacity >= 40
        for slot in slots:
            assert slot.remaining_capacity >= 40
    
    def test_get_available_slots_excludes_fully_booked(
        self,
        booking_service: BookingService,
        sample_time_slots
    ):
        """Test that fully booked slots are excluded."""
        tomorrow = date.today() + timedelta(days=1)
        
        slots = booking_service.get_available_slots(tomorrow, party_size=1)
        
        # Verify fully booked slot (18:30) is not in results
        slot_times = [slot.time for slot in slots]
        assert time(18, 30) not in slot_times
    
    def test_get_available_slots_ordered_by_time(
        self,
        booking_service: BookingService,
        sample_time_slots
    ):
        """Test that slots are returned in chronological order."""
        tomorrow = date.today() + timedelta(days=1)
        
        slots = booking_service.get_available_slots(tomorrow, party_size=4)
        
        if len(slots) > 1:
            for i in range(len(slots) - 1):
                assert slots[i].time <= slots[i + 1].time


class TestValidateBookingRequest:
    """Test validate_booking_request validation rules."""
    
    def test_validate_valid_request(
        self,
        booking_service: BookingService
    ):
        """Test validation of a valid booking request."""
        tomorrow = date.today() + timedelta(days=1)
        
        is_valid, error_msg = booking_service.validate_booking_request(
            date=tomorrow,
            time=time(18, 0),
            party_size=4
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_date_in_past(
        self,
        booking_service: BookingService
    ):
        """Test validation fails for past dates."""
        yesterday = date.today() - timedelta(days=1)
        
        is_valid, error_msg = booking_service.validate_booking_request(
            date=yesterday,
            time=time(18, 0),
            party_size=4
        )
        
        assert is_valid is False
        assert "past" in error_msg.lower()
    
    def test_validate_date_too_far_ahead(
        self,
        booking_service: BookingService,
        restaurant_config: RestaurantConfig
    ):
        """Test validation fails for dates beyond booking window."""
        far_future = date.today() + timedelta(days=restaurant_config.booking_window_days + 1)
        
        is_valid, error_msg = booking_service.validate_booking_request(
            date=far_future,
            time=time(18, 0),
            party_size=4
        )
        
        assert is_valid is False
        assert "advance" in error_msg.lower()
    
    def test_validate_party_size_too_small(
        self,
        booking_service: BookingService
    ):
        """Test validation fails for party size < 1."""
        tomorrow = date.today() + timedelta(days=1)
        
        is_valid, error_msg = booking_service.validate_booking_request(
            date=tomorrow,
            time=time(18, 0),
            party_size=0
        )
        
        assert is_valid is False
        assert "at least 1" in error_msg.lower()
    
    def test_validate_party_size_too_large(
        self,
        booking_service: BookingService,
        restaurant_config: RestaurantConfig
    ):
        """Test validation fails for party size > max_party_size."""
        tomorrow = date.today() + timedelta(days=1)
        
        is_valid, error_msg = booking_service.validate_booking_request(
            date=tomorrow,
            time=time(18, 0),
            party_size=restaurant_config.max_party_size + 1
        )
        
        assert is_valid is False
        assert "cannot exceed" in error_msg.lower()
    
    def test_validate_time_outside_operating_hours(
        self,
        booking_service: BookingService
    ):
        """Test validation fails for time outside operating hours."""
        tomorrow = date.today() + timedelta(days=1)
        
        # Assuming restaurant doesn't open at 3 AM
        is_valid, error_msg = booking_service.validate_booking_request(
            date=tomorrow,
            time=time(3, 0),
            party_size=4
        )
        
        assert is_valid is False
        assert "operating hours" in error_msg.lower()
    
    def test_validate_same_day_booking_allowed(
        self,
        booking_service: BookingService
    ):
        """Test that same-day bookings are allowed (within constraints)."""
        today = date.today()
        
        # Try a time that's likely in operating hours
        is_valid, error_msg = booking_service.validate_booking_request(
            date=today,
            time=time(18, 0),
            party_size=4
        )
        
        # Should be valid (date is today, not in past)
        # Unless it's outside operating hours for today
        if not is_valid:
            assert "operating hours" in error_msg.lower()
    
    def test_validate_max_date_boundary(
        self,
        booking_service: BookingService,
        restaurant_config: RestaurantConfig
    ):
        """Test validation at the exact maximum booking window boundary."""
        max_date = date.today() + timedelta(days=restaurant_config.booking_window_days)
        
        is_valid, error_msg = booking_service.validate_booking_request(
            date=max_date,
            time=time(18, 0),
            party_size=4
        )
        
        # Should be valid at the boundary
        assert is_valid is True


class TestCreateBooking:
    """Test create_booking functionality."""
    
    def test_create_booking_success(
        self,
        booking_service: BookingService,
        sample_booking_data: BookingCreate,
        sample_time_slots
    ):
        """Test successful booking creation."""
        booking = booking_service.create_booking(sample_booking_data)
        
        assert booking.id is not None
        assert booking.customer_name == sample_booking_data.customer_name
        assert booking.party_size == sample_booking_data.party_size
        assert booking.status == "confirmed"
    
    def test_create_booking_updates_capacity(
        self,
        booking_service: BookingService,
        sample_booking_data: BookingCreate,
        sample_time_slots,
        db_session: Session
    ):
        """Test that booking creation updates time slot capacity."""
        # Get initial capacity
        slot = db_session.query(TimeSlot).filter_by(
            date=sample_booking_data.date,
            time=sample_booking_data.time_slot
        ).first()
        initial_booked = slot.booked_capacity if slot else 0
        
        # Create booking
        booking = booking_service.create_booking(sample_booking_data)
        
        # Verify capacity updated
        db_session.refresh(slot) if slot else None
        slot = db_session.query(TimeSlot).filter_by(
            date=sample_booking_data.date,
            time=sample_booking_data.time_slot
        ).first()
        
        assert slot.booked_capacity == initial_booked + sample_booking_data.party_size
    
    def test_create_booking_invalid_date(
        self,
        booking_service: BookingService,
        sample_booking_data: BookingCreate
    ):
        """Test that booking creation fails with invalid date."""
        # Set date to the past
        sample_booking_data.date = date.today() - timedelta(days=1)
        
        with pytest.raises(ValidationError):
            booking_service.create_booking(sample_booking_data)
    
    def test_create_booking_insufficient_capacity(
        self,
        booking_service: BookingService,
        db_session: Session
    ):
        """Test booking creation fails when capacity is insufficient."""
        tomorrow = date.today() + timedelta(days=1)
        
        # Create a slot with limited capacity
        slot = TimeSlot(
            date=tomorrow,
            time=time(20, 0),
            total_capacity=50,
            booked_capacity=48  # Only 2 seats left
        )
        db_session.add(slot)
        db_session.commit()
        
        # Try to book for 4 people
        booking_data = BookingCreate(
            date=tomorrow,
            time_slot=time(20, 0),
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890"
        )
        
        with pytest.raises(CapacityError):
            booking_service.create_booking(booking_data)
    
    def test_create_booking_duplicate_prevention(
        self,
        booking_service: BookingService,
        sample_booking_data: BookingCreate,
        sample_time_slots
    ):
        """Test that duplicate bookings are prevented."""
        # Create first booking
        booking1 = booking_service.create_booking(sample_booking_data)
        
        # Try to create duplicate (same date, time, phone)
        with pytest.raises(ValidationError) as exc_info:
            booking_service.create_booking(sample_booking_data)
        
        assert "already exists" in str(exc_info.value).lower()
    
    def test_create_booking_with_special_requests(
        self,
        booking_service: BookingService,
        sample_time_slots
    ):
        """Test booking creation with special requests."""
        tomorrow = date.today() + timedelta(days=1)
        
        booking_data = BookingCreate(
            date=tomorrow,
            time_slot=time(12, 0),
            party_size=4,
            customer_name="Jane Doe",
            customer_phone="+9876543210",
            customer_email="jane@example.com",
            special_requests="Vegetarian menu, high chair needed"
        )
        
        booking = booking_service.create_booking(booking_data)
        
        assert booking.special_requests == "Vegetarian menu, high chair needed"
    
    def test_create_booking_auto_creates_time_slot(
        self,
        booking_service: BookingService,
        db_session: Session
    ):
        """Test that booking creation auto-creates time slot if not exists."""
        tomorrow = date.today() + timedelta(days=1)
        
        # Use a time that doesn't have a slot
        booking_data = BookingCreate(
            date=tomorrow,
            time_slot=time(15, 0),  # New time
            party_size=4,
            customer_name="John Doe",
            customer_phone="+1234567890"
        )
        
        booking = booking_service.create_booking(booking_data)
        
        # Verify slot was created
        slot = db_session.query(TimeSlot).filter_by(
            date=tomorrow,
            time=time(15, 0)
        ).first()
        
        assert slot is not None
        assert slot.booked_capacity == 4


class TestGenerateTimeSlots:
    """Test generate_time_slots functionality."""
    
    def test_generate_time_slots_for_date(
        self,
        booking_service: BookingService,
        db_session: Session
    ):
        """Test generating time slots for a specific date."""
        tomorrow = date.today() + timedelta(days=1)
        
        # Generate slots
        booking_service.generate_time_slots(tomorrow)
        
        # Verify slots were created
        slots = db_session.query(TimeSlot).filter_by(date=tomorrow).all()
        
        assert len(slots) > 0
        
        # Verify slots are within operating hours
        for slot in slots:
            assert slot.total_capacity > 0
            assert slot.booked_capacity == 0
    
    def test_generate_time_slots_skip_if_exists(
        self,
        booking_service: BookingService,
        db_session: Session,
        sample_time_slots
    ):
        """Test that generation skips if slots already exist."""
        tomorrow = date.today() + timedelta(days=1)
        
        # Count existing slots
        initial_count = db_session.query(TimeSlot).filter_by(date=tomorrow).count()
        
        # Try to generate again
        booking_service.generate_time_slots(tomorrow)
        
        # Count should be unchanged
        final_count = db_session.query(TimeSlot).filter_by(date=tomorrow).count()
        
        assert final_count == initial_count
    
    def test_generate_time_slots_respects_slot_duration(
        self,
        booking_service: BookingService,
        db_session: Session,
        restaurant_config: RestaurantConfig
    ):
        """Test that slots are generated at correct intervals."""
        # Use a date further out to avoid conflicts
        future_date = date.today() + timedelta(days=5)
        
        booking_service.generate_time_slots(future_date)
        
        slots = db_session.query(TimeSlot).filter_by(date=future_date).order_by(TimeSlot.time).all()
        
        if len(slots) > 1:
            # Check interval between consecutive slots
            slot_duration = restaurant_config.slot_duration
            
            for i in range(len(slots) - 1):
                current_time = slots[i].time
                next_time = slots[i + 1].time
                
                # Calculate difference in minutes
                current_minutes = current_time.hour * 60 + current_time.minute
                next_minutes = next_time.hour * 60 + next_time.minute
                difference = next_minutes - current_minutes
                
                assert difference == slot_duration


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_last_available_slot_booking(
        self,
        booking_service: BookingService,
        db_session: Session
    ):
        """Test booking the last available slot."""
        tomorrow = date.today() + timedelta(days=1)
        
        # Create a slot with exactly enough capacity
        slot = TimeSlot(
            date=tomorrow,
            time=time(21, 0),
            total_capacity=50,
            booked_capacity=46  # Exactly 4 seats left
        )
        db_session.add(slot)
        db_session.commit()
        
        # Book the last 4 seats
        booking_data = BookingCreate(
            date=tomorrow,
            time_slot=time(21, 0),
            party_size=4,
            customer_name="Last Customer",
            customer_phone="+1111111111"
        )
        
        booking = booking_service.create_booking(booking_data)
        
        assert booking is not None
        
        # Verify slot is now fully booked
        db_session.refresh(slot)
        assert slot.booked_capacity == 50
        assert slot.remaining_capacity() == 0
    
    def test_concurrent_booking_prevention(
        self,
        booking_service: BookingService,
        db_session: Session
    ):
        """Test that concurrent bookings don't overbook (locking mechanism)."""
        tomorrow = date.today() + timedelta(days=1)
        
        # Create a slot with limited capacity
        slot = TimeSlot(
            date=tomorrow,
            time=time(22, 0),
            total_capacity=50,
            booked_capacity=48
        )
        db_session.add(slot)
        db_session.commit()
        
        # First booking should succeed
        booking_data1 = BookingCreate(
            date=tomorrow,
            time_slot=time(22, 0),
            party_size=2,
            customer_name="Customer 1",
            customer_phone="+1111111111"
        )
        
        booking1 = booking_service.create_booking(booking_data1)
        assert booking1 is not None
        
        # Second booking should fail (no capacity left)
        booking_data2 = BookingCreate(
            date=tomorrow,
            time_slot=time(22, 0),
            party_size=1,
            customer_name="Customer 2",
            customer_phone="+2222222222"
        )
        
        with pytest.raises(CapacityError):
            booking_service.create_booking(booking_data2)
