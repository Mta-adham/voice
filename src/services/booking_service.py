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

from models.database import Booking, TimeSlot, RestaurantConfig
from models.schemas import BookingCreate, TimeSlotInfo

# Import enhanced error handling
try:
    from error_handling.exceptions import (
        BookingValidationError,
        NoAvailabilityError,
        InvalidDateError,
        InvalidTimeError,
        PartySizeTooLargeError,
        DatabaseError as EnhancedDatabaseError,
    )
    from error_handling.handlers import log_error_with_context
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    # Fallback to basic exceptions
    ERROR_HANDLING_AVAILABLE = False
    BookingValidationError = Exception
    NoAvailabilityError = Exception
    InvalidDateError = Exception
    InvalidTimeError = Exception
    PartySizeTooLargeError = Exception
    EnhancedDatabaseError = Exception


class BookingServiceError(Exception):
    """Base exception for booking service errors."""
    pass


class ValidationError(BookingServiceError):
    """Exception raised when booking validation fails."""
    pass


class CapacityError(BookingServiceError):
    """Exception raised when there's insufficient capacity."""
    pass


class DatabaseError(BookingServiceError):
    """Exception raised when database operations fail."""
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
                    "Restaurant configuration not found. Please run database initialization."
                )
            self._config_cache = config
            return config
        except OperationalError as e:
            raise DatabaseError(f"Database connection error: {str(e)}")
    
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
        raise_enhanced_errors: bool = True
    ) -> Tuple[bool, str]:
        """
        Validate booking request against business rules.
        
        Args:
            date: Requested booking date
            time: Requested booking time
            party_size: Number of people in the party
            raise_enhanced_errors: If True, raise enhanced exception types
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
            
        Raises:
            InvalidDateError: If date is invalid (when raise_enhanced_errors=True)
            InvalidTimeError: If time is invalid (when raise_enhanced_errors=True)
            PartySizeTooLargeError: If party size exceeds max (when raise_enhanced_errors=True)
        """
        config = self._get_restaurant_config()
        today = datetime.now().date()
        
        # Check date is not in the past
        if date < today:
            if raise_enhanced_errors and ERROR_HANDLING_AVAILABLE:
                raise InvalidDateError(
                    "Booking date cannot be in the past",
                    date=date,
                    reason="past"
                )
            return False, "Booking date cannot be in the past"
        
        # Check date is not more than booking_window_days in the future
        max_date = today + timedelta(days=config.booking_window_days)
        if date > max_date:
            if raise_enhanced_errors and ERROR_HANDLING_AVAILABLE:
                raise InvalidDateError(
                    f"Bookings can only be made up to {config.booking_window_days} days in advance",
                    date=date,
                    reason="too_far"
                )
            return False, f"Bookings can only be made up to {config.booking_window_days} days in advance"
        
        # Check party_size is within allowed range
        if party_size < 1:
            if raise_enhanced_errors and ERROR_HANDLING_AVAILABLE:
                raise BookingValidationError(
                    "Party size must be at least 1",
                    field="party_size",
                    value=party_size
                )
            return False, "Party size must be at least 1"
        
        if party_size > config.max_party_size:
            if raise_enhanced_errors and ERROR_HANDLING_AVAILABLE:
                raise PartySizeTooLargeError(
                    f"Party size {party_size} exceeds maximum {config.max_party_size}",
                    party_size=party_size,
                    max_party_size=config.max_party_size
                )
            return False, f"Party size cannot exceed {config.max_party_size} people"
        
        # Check requested time is within operating hours for that day of week
        open_time, close_time = self._get_operating_hours(date)
        
        if open_time is None or close_time is None:
            if raise_enhanced_errors and ERROR_HANDLING_AVAILABLE:
                raise InvalidDateError(
                    f"Restaurant is closed on {date.strftime('%A')}s",
                    date=date,
                    reason="closed"
                )
            return False, f"Restaurant is closed on {date.strftime('%A')}s"
        
        if not (open_time <= time < close_time):
            if raise_enhanced_errors and ERROR_HANDLING_AVAILABLE:
                raise InvalidTimeError(
                    f"Requested time is outside operating hours",
                    time=time,
                    operating_hours=(open_time, close_time)
                )
            return False, f"Requested time is outside operating hours ({open_time.strftime('%H:%M')} - {close_time.strftime('%H:%M')})"
        
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
                raise ValidationError(error_msg)
            
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
                
                # Raise enhanced error if available
                if ERROR_HANDLING_AVAILABLE:
                    # Try to get alternative slots
                    try:
                        alternatives = self.get_available_slots(
                            booking_data.date,
                            booking_data.party_size
                        )
                    except Exception:
                        alternatives = []
                    
                    raise NoAvailabilityError(
                        f"Insufficient capacity for {booking_data.party_size} people",
                        date=booking_data.date,
                        time=booking_data.time_slot,
                        party_size=booking_data.party_size,
                        available_alternatives=alternatives
                    )
                else:
                    raise CapacityError(
                        f"Insufficient capacity. Only {remaining} seats remaining for this time slot."
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
                raise ValidationError(
                    "A booking with this phone number already exists for this date and time"
                )
            
            raise DatabaseError(f"Database constraint violation: {error_msg}")
            
        except (ValidationError, CapacityError):
            self.session.rollback()
            raise
            
        except OperationalError as e:
            self.session.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}")
            
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error creating booking: {str(e)}")
    
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
