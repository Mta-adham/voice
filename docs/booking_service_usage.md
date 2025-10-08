# BookingService Usage Guide

The `BookingService` class provides the core business logic for managing restaurant bookings.

## Overview

The BookingService handles:
- **Availability Management**: Query available time slots with capacity tracking
- **Booking Validation**: Validate booking requests against business rules
- **Booking Creation**: Create bookings with atomic transactions
- **Time Slot Generation**: Pre-generate time slots for future dates

## Quick Start

```python
from models.database import get_db_session
from services.booking_service import BookingService
from models.schemas import BookingCreate
from datetime import date, time, timedelta

# Create service instance with database session
with get_db_session() as session:
    booking_service = BookingService(session)
    
    # Check availability
    tomorrow = date.today() + timedelta(days=1)
    available_slots = booking_service.get_available_slots(
        date=tomorrow,
        party_size=4
    )
    
    print(f"Found {len(available_slots)} available slots")
    for slot in available_slots:
        print(f"  {slot.time}: {slot.remaining_capacity} seats remaining")
```

## API Reference

### `get_available_slots(date: date, party_size: int) -> List[TimeSlotInfo]`

Returns all available time slots for a given date that can accommodate the party size.

**Parameters:**
- `date`: Date to check availability
- `party_size`: Number of people in the party

**Returns:**
- List of `TimeSlotInfo` objects containing:
  - `id`: Time slot ID
  - `date`: Slot date
  - `time`: Slot time
  - `total_capacity`: Total capacity
  - `booked_capacity`: Currently booked capacity
  - `remaining_capacity`: Available capacity
  - `is_available`: Boolean indicating if party can be accommodated

**Filters Applied:**
- Only slots within operating hours for the day of week
- Only slots with sufficient capacity (`remaining_capacity >= party_size`)
- Filters out past time slots if date is today

**Example:**
```python
slots = booking_service.get_available_slots(
    date=date(2024, 12, 25),
    party_size=6
)

for slot in slots:
    if slot.is_available:
        print(f"{slot.time} - {slot.remaining_capacity} seats left")
```

---

### `validate_booking_request(date: date, time: time, party_size: int) -> Tuple[bool, str]`

Validates a booking request against all business rules.

**Parameters:**
- `date`: Requested booking date
- `time`: Requested booking time
- `party_size`: Number of people in the party

**Returns:**
- Tuple of `(is_valid, error_message)`
  - If valid: `(True, "")`
  - If invalid: `(False, "Specific error message")`

**Validation Rules:**
1. Date is not in the past
2. Date is not more than 30 days in the future (configurable)
3. Party size is between 1 and 8 (configurable)
4. Time is within operating hours for that day of week

**Example:**
```python
is_valid, error = booking_service.validate_booking_request(
    date=date(2024, 12, 25),
    time=time(18, 30),
    party_size=4
)

if not is_valid:
    print(f"Validation failed: {error}")
else:
    print("Booking request is valid!")
```

---

### `create_booking(booking_data: BookingCreate) -> Booking`

Creates a new booking with atomic transaction handling.

**Parameters:**
- `booking_data`: `BookingCreate` Pydantic model containing:
  - `date`: Booking date
  - `time_slot`: Booking time
  - `party_size`: Number of people
  - `customer_name`: Customer's name
  - `customer_phone`: Customer's phone number
  - `customer_email`: Customer's email (optional)
  - `special_requests`: Special requests (optional)

**Returns:**
- Created `Booking` object with confirmation ID

**Raises:**
- `ValidationError`: If validation rules fail
- `CapacityError`: If insufficient capacity
- `DatabaseError`: If database operation fails

**Transaction Guarantees:**
- Creates booking record AND updates time slot capacity atomically
- Uses database-level row locking to prevent race conditions
- Rolls back all changes if any step fails

**Example:**
```python
from models.schemas import BookingCreate

try:
    booking_data = BookingCreate(
        date=date(2024, 12, 25),
        time_slot=time(18, 30),
        party_size=4,
        customer_name="John Doe",
        customer_phone="+1234567890",
        customer_email="john@example.com",
        special_requests="Window seat preferred"
    )
    
    booking = booking_service.create_booking(booking_data)
    print(f"Booking confirmed! ID: {booking.id}")
    print(f"Status: {booking.status}")
    
except ValidationError as e:
    print(f"Validation error: {e}")
except CapacityError as e:
    print(f"Capacity error: {e}")
except DatabaseError as e:
    print(f"Database error: {e}")
```

---

### `generate_time_slots(date: date) -> None`

Pre-generates time slots for a given date based on operating hours and configuration.

**Parameters:**
- `date`: Date to generate time slots for

**Behavior:**
- Creates slots in 30-minute intervals (configurable via `slot_duration`)
- Only within operating hours for the day of week
- Initializes all slots with `total_capacity` from config
- Sets `booked_capacity` to 0
- Skips generation if slots already exist for the date

**Example:**
```python
# Generate slots for next week
for i in range(7):
    future_date = date.today() + timedelta(days=i+1)
    booking_service.generate_time_slots(future_date)

print("Time slots generated for next 7 days")
```

## Error Handling

The service defines custom exceptions for different error scenarios:

### `ValidationError`
Raised when booking validation fails (invalid date, party size, operating hours, etc.)

### `CapacityError`
Raised when there's insufficient capacity for the requested booking

### `DatabaseError`
Raised when database operations fail (connection issues, constraint violations, etc.)

### Example Error Handling:
```python
from services.booking_service import (
    ValidationError,
    CapacityError,
    DatabaseError
)

try:
    booking = booking_service.create_booking(booking_data)
except ValidationError as e:
    # Handle validation errors (show user-friendly message)
    return {"error": str(e)}, 400
except CapacityError as e:
    # Handle capacity issues (suggest alternative times)
    return {"error": str(e)}, 409
except DatabaseError as e:
    # Handle database errors (log and show generic error)
    logger.error(f"Database error: {e}")
    return {"error": "System error, please try again"}, 500
```

## Thread Safety

The BookingService uses database-level locking to ensure thread-safe capacity updates:

```python
# Uses SELECT ... FOR UPDATE to lock the time slot row
time_slot = session.query(TimeSlot).filter(...).with_for_update().first()
```

This prevents race conditions when multiple bookings are created simultaneously for the same time slot.

## Best Practices

1. **Always use within a session context:**
   ```python
   with get_db_session() as session:
       service = BookingService(session)
       # Use service here
   ```

2. **Handle all exception types:**
   - Catch specific exceptions for better error handling
   - Don't catch generic `Exception` unless logging and re-raising

3. **Pre-generate time slots:**
   - Run a daily job to generate slots for upcoming dates
   - This improves availability query performance

4. **Validate before creating:**
   - Although `create_booking` validates internally, you can call `validate_booking_request` first for better UX
   - Show validation errors before attempting to create the booking

5. **Use transactions properly:**
   - The service handles transactions internally
   - Don't commit/rollback the session outside the service methods

## Configuration

The service reads configuration from the `restaurant_config` table:

- `operating_hours`: Dictionary of opening/closing times per day
- `slot_duration`: Duration of each time slot in minutes (default: 30)
- `max_party_size`: Maximum party size allowed (default: 8)
- `booking_window_days`: How far ahead bookings can be made (default: 30)

Configuration is cached after first access for performance.
