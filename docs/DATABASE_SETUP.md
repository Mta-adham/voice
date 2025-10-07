# Database Setup Guide

## Overview

The restaurant booking system uses PostgreSQL with SQLAlchemy ORM for database management. This guide covers the database schema, setup, and usage.

## Database Schema

### Tables

#### 1. `bookings`
Stores customer reservations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique booking ID |
| date | Date | Not Null | Reservation date |
| time_slot | Time | Not Null | Reservation time |
| party_size | Integer | Not Null, Check (1-8) | Number of people |
| customer_name | String(255) | Not Null | Customer's name |
| customer_phone | String(50) | Not Null | Customer's phone number |
| customer_email | String(255) | Nullable | Customer's email |
| special_requests | Text | Nullable | Special requests or dietary needs |
| status | Enum | Not Null, Default: 'confirmed' | Booking status (pending, confirmed, completed, cancelled) |
| created_at | Timestamp | Not Null, Default: now() | When booking was created |

**Constraints:**
- Unique: (date, time_slot, customer_phone) - Prevents duplicate bookings
- Index: (date, time_slot) - Fast availability queries

#### 2. `time_slots`
Tracks available time slots with capacity management.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique slot ID |
| date | Date | Not Null | Date of time slot |
| time | Time | Not Null | Time of slot |
| total_capacity | Integer | Not Null | Total seating capacity |
| booked_capacity | Integer | Not Null, Default: 0 | Currently booked seats |

**Constraints:**
- Unique: (date, time) - One slot per date/time
- Index: (date) - Fast date range queries

#### 3. `restaurant_config`
Single-row configuration table for restaurant settings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Always 1 | Configuration ID |
| operating_hours | JSON | Not Null | Opening/closing times per day |
| slot_duration | Integer | Not Null, Default: 30 | Time slot duration in minutes |
| max_party_size | Integer | Not Null, Default: 8 | Maximum party size |
| booking_window_days | Integer | Not Null, Default: 30 | How far ahead bookings allowed |

**Constraints:**
- Check: (id = 1) - Ensures only one config row

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Copy the example environment file and configure your database:

```bash
cp .env.example .env
```

Edit `.env` and set your PostgreSQL connection string:

```
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

### 3. Initialize Database

Run the initialization script to create tables and seed initial configuration:

```bash
python src/db_init.py
```

This will:
- Connect to PostgreSQL
- Create all tables with proper constraints
- Seed initial restaurant configuration with sensible defaults

## Usage Examples

### Basic CRUD Operations

```python
from models import (
    init_db, get_db_session, 
    Booking, TimeSlot, RestaurantConfig
)
from models.schemas import BookingCreate
from datetime import date, time

# Initialize database connection
init_db()

# Create a booking
with get_db_session() as session:
    booking = Booking(
        date=date(2024, 12, 25),
        time_slot=time(18, 30),
        party_size=4,
        customer_name="John Doe",
        customer_phone="+1234567890",
        customer_email="john@example.com",
        status="confirmed"
    )
    session.add(booking)
    # Commit happens automatically on context exit

# Query bookings
with get_db_session() as session:
    bookings = session.query(Booking).filter(
        Booking.date == date(2024, 12, 25)
    ).all()
    
    for booking in bookings:
        print(f"{booking.customer_name} - {booking.time_slot}")

# Check time slot availability
with get_db_session() as session:
    slot = session.query(TimeSlot).filter(
        TimeSlot.date == date(2024, 12, 25),
        TimeSlot.time == time(18, 30)
    ).first()
    
    if slot and slot.is_available(party_size=4):
        print(f"Available! {slot.remaining_capacity()} seats left")
```

### Using Pydantic Validation

```python
from models.schemas import BookingCreate, BookingResponse
from pydantic import ValidationError

# Valid booking data
try:
    booking_data = BookingCreate(
        date=date(2024, 12, 25),
        time_slot=time(18, 30),
        party_size=4,
        customer_name="John Doe",
        customer_phone="+1234567890",
        customer_email="john@example.com"
    )
    print("Booking valid!")
except ValidationError as e:
    print(f"Validation error: {e}")

# Invalid booking (party size > 8)
try:
    invalid_booking = BookingCreate(
        date=date(2024, 12, 25),
        time_slot=time(18, 30),
        party_size=10,  # Invalid!
        customer_name="Jane Smith",
        customer_phone="+1987654321"
    )
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Data Validation

### Phone Number Format
Accepts various formats:
- `+1234567890`
- `(123) 456-7890`
- `123-456-7890`
- `1234567890`

Must contain 10-15 digits.

### Email Format
Standard email validation:
- Must have `@` symbol
- Valid domain format
- Optional (can be None)

### Date Validation
- Cannot be in the past
- Must be within booking window (default: 30 days)

### Party Size
- Must be between 1 and 8 people
- Enforced by both Pydantic validation and database constraint

## Configuration

Default restaurant configuration:

```json
{
    "operating_hours": {
        "monday": {"open": "11:00", "close": "22:00"},
        "tuesday": {"open": "11:00", "close": "22:00"},
        "wednesday": {"open": "11:00", "close": "22:00"},
        "thursday": {"open": "11:00", "close": "22:00"},
        "friday": {"open": "11:00", "close": "23:00"},
        "saturday": {"open": "10:00", "close": "23:00"},
        "sunday": {"open": "10:00", "close": "21:00"}
    },
    "slot_duration": 30,
    "max_party_size": 8,
    "booking_window_days": 30
}
```

To modify configuration:

```python
with get_db_session() as session:
    config = session.query(RestaurantConfig).first()
    config.slot_duration = 45  # Change to 45-minute slots
    config.max_party_size = 10  # Allow larger parties
    # Commit happens automatically
```

## Connection Management

The system uses connection pooling for efficient database access:

- Pool size: 5 connections
- Max overflow: 10 additional connections
- Pre-ping enabled: Checks connection health before use
- Auto-rollback: Transactions rolled back on error
- Auto-close: Sessions closed properly after use

## Troubleshooting

### Connection Issues

If you see connection errors:

1. Verify PostgreSQL is running
2. Check DATABASE_URL is correct
3. Ensure database exists: `createdb restaurant_db`
4. Check user permissions

### Migration Issues

To recreate tables from scratch:

```python
from models.database import Base, engine, init_db

init_db()
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
```

### Performance

For production use:
- Increase pool size if handling many concurrent requests
- Add additional indexes based on query patterns
- Consider partitioning `bookings` table by date for large datasets
- Use connection pooler like PgBouncer for very high traffic

## Security Notes

- Never commit `.env` file with credentials
- Use strong passwords for database users
- Restrict database access to application servers only
- Enable SSL for database connections in production
- Regular backups recommended
