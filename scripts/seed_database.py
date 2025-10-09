#!/usr/bin/env python3
"""
Database seeding script for restaurant booking system.

This script:
- Initializes time slots for next 30 days
- Sets restaurant configuration (hours, capacity, slot duration)
- Creates sample bookings for testing
- Can be run multiple times (idempotent)

Usage:
    python scripts/seed_database.py [--reset]

Options:
    --reset     Clear existing data before seeding
"""
import sys
import argparse
from pathlib import Path
from datetime import date, time, timedelta, datetime
from typing import List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.database import (
    init_db,
    create_tables,
    get_db_session,
    Booking,
    TimeSlot,
    RestaurantConfig
)
from services.booking_service import BookingService


def create_restaurant_config(session) -> RestaurantConfig:
    """
    Create or update restaurant configuration.
    
    Args:
        session: Database session
    
    Returns:
        RestaurantConfig instance
    """
    print("Setting up restaurant configuration...")
    
    # Check if config already exists
    config = session.query(RestaurantConfig).filter_by(id=1).first()
    
    if config:
        print("  ✓ Restaurant configuration already exists")
        return config
    
    # Create new configuration
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
        slot_duration=30,  # 30-minute slots
        max_party_size=8,
        booking_window_days=30
    )
    
    session.add(config)
    session.commit()
    session.refresh(config)
    
    print(f"  ✓ Created restaurant configuration")
    print(f"    - Slot duration: {config.slot_duration} minutes")
    print(f"    - Max party size: {config.max_party_size} people")
    print(f"    - Booking window: {config.booking_window_days} days")
    
    return config


def generate_time_slots_for_range(
    session,
    booking_service: BookingService,
    start_date: date,
    days: int
) -> int:
    """
    Generate time slots for a range of dates.
    
    Args:
        session: Database session
        booking_service: BookingService instance
        start_date: Starting date
        days: Number of days to generate
    
    Returns:
        Total number of slots generated
    """
    print(f"\nGenerating time slots for {days} days starting from {start_date}...")
    
    total_slots = 0
    
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        
        # Check if slots already exist
        existing_count = session.query(TimeSlot).filter_by(
            date=current_date
        ).count()
        
        if existing_count > 0:
            print(f"  ⊙ {current_date}: {existing_count} slots already exist")
            total_slots += existing_count
            continue
        
        # Generate slots for this date
        booking_service.generate_time_slots(current_date)
        
        # Count generated slots
        new_count = session.query(TimeSlot).filter_by(
            date=current_date
        ).count()
        
        print(f"  ✓ {current_date}: Generated {new_count} slots")
        total_slots += new_count
    
    print(f"\nTotal time slots: {total_slots}")
    return total_slots


def create_sample_bookings(session, config: RestaurantConfig) -> List[Booking]:
    """
    Create sample bookings for testing.
    
    Args:
        session: Database session
        config: Restaurant configuration
    
    Returns:
        List of created bookings
    """
    print("\nCreating sample bookings...")
    
    bookings = []
    tomorrow = date.today() + timedelta(days=1)
    
    sample_data = [
        {
            "date": tomorrow,
            "time_slot": time(12, 0),
            "party_size": 4,
            "customer_name": "Alice Johnson",
            "customer_phone": "+1234567890",
            "customer_email": "alice@example.com",
            "special_requests": "Window seat preferred"
        },
        {
            "date": tomorrow,
            "time_slot": time(18, 30),
            "party_size": 2,
            "customer_name": "Bob Smith",
            "customer_phone": "+9876543210",
            "customer_email": "bob@example.com",
            "special_requests": None
        },
        {
            "date": tomorrow + timedelta(days=1),
            "time_slot": time(19, 0),
            "party_size": 6,
            "customer_name": "Carol Williams",
            "customer_phone": "+5555555555",
            "customer_email": "carol@example.com",
            "special_requests": "Birthday celebration, need high chair"
        },
        {
            "date": tomorrow + timedelta(days=2),
            "time_slot": time(20, 0),
            "party_size": 3,
            "customer_name": "David Brown",
            "customer_phone": "+1111111111",
            "customer_email": None,
            "special_requests": "Vegetarian menu"
        },
    ]
    
    for data in sample_data:
        # Check if booking already exists
        existing = session.query(Booking).filter_by(
            date=data["date"],
            time_slot=data["time_slot"],
            customer_phone=data["customer_phone"]
        ).first()
        
        if existing:
            print(f"  ⊙ Booking for {data['customer_name']} already exists")
            bookings.append(existing)
            continue
        
        # Get or create time slot
        slot = session.query(TimeSlot).filter_by(
            date=data["date"],
            time=data["time_slot"]
        ).first()
        
        if not slot:
            # Create slot if doesn't exist
            slot = TimeSlot(
                date=data["date"],
                time=data["time_slot"],
                total_capacity=50,
                booked_capacity=0
            )
            session.add(slot)
            session.flush()
        
        # Check capacity
        if not slot.is_available(data["party_size"]):
            print(f"  ✗ Cannot create booking for {data['customer_name']} - insufficient capacity")
            continue
        
        # Create booking
        booking = Booking(
            date=data["date"],
            time_slot=data["time_slot"],
            party_size=data["party_size"],
            customer_name=data["customer_name"],
            customer_phone=data["customer_phone"],
            customer_email=data["customer_email"],
            special_requests=data["special_requests"],
            status="confirmed",
            created_at=datetime.utcnow()
        )
        
        session.add(booking)
        
        # Update slot capacity
        slot.booked_capacity += data["party_size"]
        
        bookings.append(booking)
        print(f"  ✓ Created booking for {data['customer_name']} "
              f"({data['party_size']} people on {data['date']} at {data['time_slot']})")
    
    session.commit()
    
    print(f"\nTotal sample bookings: {len(bookings)}")
    return bookings


def reset_database(session):
    """
    Clear all data from the database.
    
    Args:
        session: Database session
    """
    print("\n⚠️  Resetting database...")
    
    # Delete in correct order (respecting foreign keys)
    booking_count = session.query(Booking).delete()
    print(f"  ✓ Deleted {booking_count} bookings")
    
    slot_count = session.query(TimeSlot).delete()
    print(f"  ✓ Deleted {slot_count} time slots")
    
    # Note: RestaurantConfig is recreated, not deleted (single row table)
    
    session.commit()
    print("  ✓ Database reset complete")


def main():
    """Main seeding function."""
    parser = argparse.ArgumentParser(
        description="Seed the restaurant booking database with initial data"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing data before seeding"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to generate time slots for (default: 30)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Restaurant Booking System - Database Seeding")
    print("=" * 60)
    
    try:
        # Initialize database
        print("\nInitializing database connection...")
        engine = init_db()
        create_tables()
        print("  ✓ Database initialized")
        
        with get_db_session() as session:
            # Reset if requested
            if args.reset:
                reset_database(session)
            
            # Create restaurant configuration
            config = create_restaurant_config(session)
            
            # Create booking service
            booking_service = BookingService(session)
            
            # Generate time slots
            start_date = date.today()
            generate_time_slots_for_range(
                session,
                booking_service,
                start_date,
                args.days
            )
            
            # Create sample bookings
            create_sample_bookings(session, config)
        
        print("\n" + "=" * 60)
        print("✓ Database seeding completed successfully!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
