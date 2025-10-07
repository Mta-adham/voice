"""
Database initialization and seeding script for restaurant booking system.

This script:
1. Initializes the database connection
2. Creates all tables
3. Seeds initial restaurant configuration with sensible defaults
"""
import os
import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
from models.database import (
    init_db,
    create_tables,
    get_db_session,
    RestaurantConfig,
)


def seed_restaurant_config() -> None:
    """
    Seed the database with initial restaurant configuration.
    Creates a single configuration row with sensible defaults.
    """
    with get_db_session() as session:
        # Check if config already exists
        existing_config = session.query(RestaurantConfig).filter_by(id=1).first()
        
        if existing_config:
            print("✓ Restaurant configuration already exists")
            print(f"  - Slot duration: {existing_config.slot_duration} minutes")
            print(f"  - Max party size: {existing_config.max_party_size}")
            print(f"  - Booking window: {existing_config.booking_window_days} days")
            return
        
        # Default operating hours (11 AM - 10 PM for all days)
        default_operating_hours = {
            "monday": {"open": "11:00", "close": "22:00"},
            "tuesday": {"open": "11:00", "close": "22:00"},
            "wednesday": {"open": "11:00", "close": "22:00"},
            "thursday": {"open": "11:00", "close": "22:00"},
            "friday": {"open": "11:00", "close": "23:00"},
            "saturday": {"open": "10:00", "close": "23:00"},
            "sunday": {"open": "10:00", "close": "21:00"},
        }
        
        # Create initial configuration
        config = RestaurantConfig(
            id=1,
            operating_hours=default_operating_hours,
            slot_duration=30,  # 30-minute time slots
            max_party_size=8,  # Maximum 8 people per party
            booking_window_days=30,  # Allow bookings up to 30 days in advance
        )
        
        session.add(config)
        session.commit()
        
        print("✓ Created initial restaurant configuration:")
        print(f"  - Slot duration: {config.slot_duration} minutes")
        print(f"  - Max party size: {config.max_party_size}")
        print(f"  - Booking window: {config.booking_window_days} days")
        print("  - Operating hours:")
        for day, hours in config.operating_hours.items():
            print(f"    • {day.capitalize()}: {hours['open']} - {hours['close']}")


def initialize_database(database_url: str | None = None) -> None:
    """
    Initialize the database: create tables and seed initial data.
    
    Args:
        database_url: Optional database connection string. If not provided,
                     will use DATABASE_URL environment variable.
    """
    try:
        print("Initializing database...")
        
        # Initialize database engine
        engine = init_db(database_url)
        print(f"✓ Connected to database: {engine.url.database}")
        
        # Create all tables
        print("\nCreating database tables...")
        create_tables()
        print("✓ Tables created successfully:")
        print("  - bookings")
        print("  - time_slots")
        print("  - restaurant_config")
        
        # Seed initial configuration
        print("\nSeeding initial data...")
        seed_restaurant_config()
        
        print("\n" + "="*50)
        print("Database initialization complete!")
        print("="*50)
        
    except Exception as e:
        print(f"\n✗ Error during database initialization: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main entry point for database initialization script.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print(
            "Error: DATABASE_URL environment variable is not set.\n"
            "Please set it to your PostgreSQL connection string.\n"
            "Example: postgresql://user:password@localhost:5432/restaurant_db",
            file=sys.stderr
        )
        sys.exit(1)
    
    print("="*50)
    print("Restaurant Booking System - Database Setup")
    print("="*50 + "\n")
    
    # Initialize database
    initialize_database(database_url)


if __name__ == "__main__":
    main()
