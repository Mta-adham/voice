"""
BookingService - Core booking business logic for restaurant booking system.

This service handles:
- Availability management and time slot queries
- Booking validation with business rules
- Booking creation with atomic transactions
- Time slot generation based on operating hours
"""
from datetime import date, time, datetime, timedelta
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError, OperationalError
from loguru import logger

from models.database import Booking, TimeSlot, RestaurantConfig
from models.schemas import BookingCreate, TimeSlotInfo

# Import centralized error handling
try:
    from ..error_handling.exceptions import (
        BookingValidationError,
        NoAvailabilityError,
        CapacityExceededError,
        DatabaseError,
        DatabaseConnectionError,
        DatabaseQueryError,
    )
    from ..error_handling.handlers import handle_errors, retry_on_error
except ImportError:
    # Fallback to local exceptions if error_handling not available
    logger.warning("Centralized error handling not available, using local exceptions")
    
    class BookingValidationError(Exception):
        """Exception raised when booking validation fails."""
        pass
    
    class NoAvailabilityError(Exception):
        """Exception raised when there is no availability."""
        pass
    
    class CapacityExceededError(Exception):
        """Exception raised when there's insufficient capacity."""
        pass
    
    class DatabaseError(Exception):
        """Exception raised when database operations fail."""
        pass
    
    class DatabaseConnectionError(DatabaseError):
        """Exception raised when database connection fails."""
        pass
    
    class DatabaseQueryError(DatabaseError):
        """Exception raised when database query fails."""
        pass
    
    # Mock decorators if not available
    def handle_errors(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    def retry_on_error(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


# Keep old exception names for backward compatibility
class BookingServiceError(Exception):
    """Base exception for booking service errors (deprecated, use BookingValidationError)."""
    pass


class ValidationError(BookingValidationError):
    """Deprecated alias for BookingValidationError."""
    pass


class CapacityError(CapacityExceededError):
    """Deprecated alias for CapacityExceededError."""
    pass


class BookingService:
    """
    Service class that encapsulates all booking business logic.
    
    This service is responsible for:
    - Managing time slot availability
    - Validating booking requests
    - Creating bookings with capacity tracking
    - Generating time slots for future dates
    """
    
    def __init__(self, session: Session):
        """
        Initialize the booking service with a database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self._config_cache: Optional[RestaurantConfig] = None
    
    @retry_on_error(max_retries=3, exceptions=(OperationalError,), backoff_factor=1.0)
    def _get_restaurant_config(self) -> RestaurantConfig:
        """
        Get restaurant configuration from database with caching.
        
        Returns:
            RestaurantConfig instance
            
        Raises:
            DatabaseError: If configuration is not found or database error occurs
        """
        if self._config_cache is not None:
            return self._config_cache
        
        try:
            config = self.session.query(RestaurantConfig).filter_by(id=1).first()
            if not config:
                raise DatabaseError(
                    "Restaurant configuration not found. Please run database initialization.",
                    user_message="I'm having trouble accessing the restaurant configuration. Please try again in a moment.",
                    operation="get_config"
                )
            self._config_cache = config
            return config
        except OperationalError as e:
            raise DatabaseConnectionError(
                f"Database connection error: {str(e)}",
                original_error=e
            )
    
    def _parse_time(self, time_str: str) -> time:
        """
        Parse time string in HH:MM format.
        
        Args:
            time_str: Time string in HH:MM format
            
        Returns:
            time object
        """
        hours, minutes = map(int, time_str.split(':'))
        return time(hour=hours, minute=minutes)
    
    def _get_operating_hours(self, target_date: date) -> Tuple[Optional[time], Optional[time]]:
        """
        Get operating hours for a specific date.
        
        Args:
            target_date: Date to get operating hours for
            
        Returns:
            Tuple of (open_time, close_time) or (None, None) if closed
        """
        config = self._get_restaurant_config()
        day_name = target_date.strftime('%A').lower()
        
        if day_name not in config.operating_hours:
            return None, None
        
        hours = config.operating_hours[day_name]
        open_time = self._parse_time(hours['open'])
        close_time = self._parse_time(hours['close'])
        
        return open_time, close_time
    
    def get_available_slots(self, date: date, party_size: int) -> List[TimeSlotInfo]:
        """
        Returns all time slots on given date that have enough capacity for the party.
        
        Args:
            date: Date to check availability
            party_size: Number of people in the party
            
        Returns:
            List of TimeSlotInfo objects with available slots
            
        Raises:
            DatabaseError: If database query fails
        """
        try:
            # Get all time slots for the date
            time_slots = self.session.query(TimeSlot).filter(
                TimeSlot.date == date
            ).order_by(TimeSlot.time).all()
            
            # Get operating hours for the date
            open_time, close_time = self._get_operating_hours(date)
            
            # Filter slots
            available_slots = []
            now = datetime.now()
            
            for slot in time_slots:
                # Check if within operating hours
                if open_time and close_time:
                    if not (open_time <= slot.time < close_time):
                        continue
                
                # Filter out past time slots if date is today
                if date == datetime.now().date():
                    slot_datetime = datetime.combine(date, slot.time)
                    if slot_datetime <= now:
                        continue
                
                # Check if has enough capacity
                remaining = slot.remaining_capacity()
                is_available = slot.is_available(party_size)
                
                slot_info = TimeSlotInfo(
                    id=slot.id,
                    date=slot.date,
                    time=slot.time,
                    total_capacity=slot.total_capacity,
                    booked_capacity=slot.booked_capacity,
                    remaining_capacity=remaining,
                    is_available=is_available
                )
                
                # Only return slots with enough capacity
                if is_available:
                    available_slots.append(slot_info)
            
            return available_slots
            
        except OperationalError as e:
            raise DatabaseError(f"Database query failed: {str(e)}")
    
    def validate_booking_request(
        self, 
        date: date, 
        time: time, 
        party_size: int,
        raise_on_invalid: bool = False
    ) -> Tuple[bool, str]:
        """
        Validate booking request against business rules.
        
        Args:
            date: Requested booking date
            time: Requested booking time
            party_size: Number of people in the party
            raise_on_invalid: If True, raise BookingValidationError instead of returning False
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
            
        Raises:
            BookingValidationError: If raise_on_invalid=True and validation fails
        """
        config = self._get_restaurant_config()
        today = datetime.now().date()
        
        # Check date is not in the past
        if date < today:
            error_msg = "Booking date cannot be in the past"
            if raise_on_invalid:
                raise BookingValidationError(
                    error_msg,
                    field="date",
                    value=date,
                    context={"today": today}
                )
            return False, error_msg
        
        # Check date is not more than booking_window_days in the future
        max_date = today + timedelta(days=config.booking_window_days)
        if date > max_date:
            error_msg = f"Bookings can only be made up to {config.booking_window_days} days in advance"
            if raise_on_invalid:
                raise BookingValidationError(
                    error_msg,
                    field="date",
                    value=date,
                    context={
                        "booking_window_days": config.booking_window_days,
                        "max_date": max_date
                    }
                )
            return False, error_msg
        
        # Check party_size is within allowed range
        if party_size < 1:
            error_msg = "Party size must be at least 1"
            if raise_on_invalid:
                raise BookingValidationError(
                    error_msg,
                    field="party_size",
                    value=party_size
                )
            return False, error_msg
        
        if party_size > config.max_party_size:
            error_msg = f"Party size cannot exceed {config.max_party_size} people"
            if raise_on_invalid:
                raise BookingValidationError(
                    error_msg,
                    field="party_size",
                    value=party_size,
                    context={"max_party_size": config.max_party_size}
                )
            return False, error_msg
        
        # Check requested time is within operating hours for that day of week
        open_time, close_time = self._get_operating_hours(date)
        day_name = date.strftime('%A')
        
        if open_time is None or close_time is None:
            error_msg = f"Restaurant is closed on {day_name}s"
            if raise_on_invalid:
                raise BookingValidationError(
                    error_msg,
                    field="date",
                    value=date,
                    context={"day_name": day_name}
                )
            return False, error_msg
        
        if not (open_time <= time < close_time):
            error_msg = f"Requested time is outside operating hours ({open_time.strftime('%H:%M')} - {close_time.strftime('%H:%M')})"
            if raise_on_invalid:
                raise BookingValidationError(
                    error_msg,
                    field="time",
                    value=time,
                    context={
                        "open_time": open_time.strftime('%H:%M'),
                        "close_time": close_time.strftime('%H:%M'),
                        "day_name": day_name,
                        "requested_time": time.strftime('%H:%M')
                    }
                )
            return False, error_msg
        
        return True, ""
    
    def create_booking(self, booking_data: BookingCreate) -> Booking:
        """
        Create new booking and update time slot capacity.
        
        This method performs an atomic transaction:
        1. Verify availability with database lock
        2. Create booking record
        3. Update time_slot.booked_capacity
        
        Args:
            booking_data: Booking data to create
            
        Returns:
            Created Booking instance with confirmation ID
            
        Raises:
            ValidationError: If booking validation fails
            CapacityError: If insufficient capacity
            DatabaseError: If database operation fails
        """
        try:
            # Validate booking request
            is_valid, error_msg = self.validate_booking_request(
                booking_data.date,
                booking_data.time_slot,
                booking_data.party_size
            )
            
            if not is_valid:
                raise BookingValidationError(error_msg)
            
            # Start atomic transaction - get time slot with row lock
            time_slot = self.session.query(TimeSlot).filter(
                and_(
                    TimeSlot.date == booking_data.date,
                    TimeSlot.time == booking_data.time_slot
                )
            ).with_for_update().first()
            
            # If time slot doesn't exist, create it
            if not time_slot:
                config = self._get_restaurant_config()
                # TODO: Add default_capacity to RestaurantConfig table
                # For now using a reasonable default of 50 seats per time slot
                default_capacity = 50
                time_slot = TimeSlot(
                    date=booking_data.date,
                    time=booking_data.time_slot,
                    total_capacity=default_capacity,
                    booked_capacity=0
                )
                self.session.add(time_slot)
                self.session.flush()  # Get the ID
            
            # Verify availability (double-check with lock held)
            if not time_slot.is_available(booking_data.party_size):
                remaining = time_slot.remaining_capacity()
                raise CapacityExceededError(
                    f"Insufficient capacity. Only {remaining} seats remaining for this time slot.",
                    requested_size=booking_data.party_size,
                    available_capacity=remaining,
                    context={
                        "date": booking_data.date,
                        "time": booking_data.time_slot,
                        "time_slot_id": time_slot.id
                    }
                )
            
            # Create booking
            booking = Booking(
                date=booking_data.date,
                time_slot=booking_data.time_slot,
                party_size=booking_data.party_size,
                customer_name=booking_data.customer_name,
                customer_phone=booking_data.customer_phone,
                customer_email=booking_data.customer_email,
                special_requests=booking_data.special_requests,
                status="confirmed",
                created_at=datetime.utcnow()
            )
            
            self.session.add(booking)
            
            # Update time slot capacity
            time_slot.booked_capacity += booking_data.party_size
            
            # Commit transaction
            self.session.commit()
            
            return booking
            
        except IntegrityError as e:
            self.session.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            # Check for duplicate booking
            if 'uq_booking_date_time_phone' in error_msg:
                raise BookingValidationError(
                    "A booking with this phone number already exists for this date and time",
                    field="customer_phone",
                    value=booking_data.customer_phone,
                    context={
                        "date": booking_data.date,
                        "time": booking_data.time_slot
                    }
                )
            
            raise DatabaseError(
                f"Database constraint violation: {error_msg}",
                operation="create_booking",
                original_error=e
            )
            
        except (BookingValidationError, CapacityExceededError):
            self.session.rollback()
            raise
            
        except OperationalError as e:
            self.session.rollback()
            raise DatabaseConnectionError(
                f"Database operation failed: {str(e)}",
                original_error=e
            )
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error creating booking: {str(e)}")
            raise DatabaseError(
                f"Unexpected error creating booking: {str(e)}",
                operation="create_booking",
                original_error=e
            )
    
    def generate_time_slots(self, date: date) -> None:
        """
        Pre-generate time slots for a given date based on operating hours and slot_duration.
        
        Creates slots in configured intervals within operating hours.
        Initializes all slots with total_capacity from config and booked_capacity=0.
        Skips if slots already exist for the date.
        
        Args:
            date: Date to generate time slots for
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Check if slots already exist for this date
            existing_count = self.session.query(TimeSlot).filter(
                TimeSlot.date == date
            ).count()
            
            if existing_count > 0:
                return  # Slots already exist, skip generation
            
            # Get operating hours for the date
            open_time, close_time = self._get_operating_hours(date)
            
            if open_time is None or close_time is None:
                # Restaurant is closed on this day
                return
            
            # Get configuration
            config = self._get_restaurant_config()
            slot_duration = config.slot_duration
            # TODO: Add default_capacity to RestaurantConfig table
            # For now using a reasonable default of 50 seats per time slot
            total_capacity = 50
            
            # Generate time slots
            current_time = datetime.combine(date, open_time)
            close_datetime = datetime.combine(date, close_time)
            
            slots_to_add = []
            
            while current_time < close_datetime:
                time_slot = TimeSlot(
                    date=date,
                    time=current_time.time(),
                    total_capacity=total_capacity,
                    booked_capacity=0
                )
                slots_to_add.append(time_slot)
                
                # Move to next slot
                current_time += timedelta(minutes=slot_duration)
            
            # Bulk insert all slots
            if slots_to_add:
                self.session.bulk_save_objects(slots_to_add)
                self.session.commit()
                
        except IntegrityError:
            # Slots were created by another process, rollback and ignore
            self.session.rollback()
            
        except OperationalError as e:
            self.session.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}")
            
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error generating time slots: {str(e)}")
