"""
SQLAlchemy database models and session management for restaurant booking system.
"""
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Date,
    Time,
    DateTime,
    Enum,
    Index,
    UniqueConstraint,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from sqlalchemy.engine import Engine

# Create declarative base
Base = declarative_base()

# Database engine and session factory (initialized by init_db)
engine: Engine | None = None
SessionLocal: sessionmaker | None = None


class Booking(Base):
    """
    Booking model representing a customer's restaurant reservation.
    """
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    time_slot = Column(Time, nullable=False)
    party_size = Column(
        Integer,
        nullable=False,
        # Check constraint: party size must be between 1 and 8
    )
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(50), nullable=False)
    customer_email = Column(String(255), nullable=True)
    special_requests = Column(Text, nullable=True)
    status = Column(
        Enum("pending", "confirmed", "completed", "cancelled", name="booking_status"),
        nullable=False,
        default="confirmed",
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Table constraints
    __table_args__ = (
        # Composite unique constraint to prevent duplicate bookings
        UniqueConstraint("date", "time_slot", "customer_phone", name="uq_booking_date_time_phone"),
        # Check constraint for party size
        CheckConstraint("party_size >= 1 AND party_size <= 8", name="ck_party_size_range"),
        # Index for fast availability queries
        Index("ix_booking_date_time", "date", "time_slot"),
    )

    def __repr__(self) -> str:
        return (
            f"<Booking(id={self.id}, date={self.date}, time_slot={self.time_slot}, "
            f"party_size={self.party_size}, customer_name='{self.customer_name}', "
            f"status='{self.status}')>"
        )


class TimeSlot(Base):
    """
    TimeSlot model representing available time slots with capacity tracking.
    """
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    total_capacity = Column(Integer, nullable=False)
    booked_capacity = Column(Integer, nullable=False, default=0)

    # Table constraints
    __table_args__ = (
        # Unique constraint on date and time
        UniqueConstraint("date", "time", name="uq_time_slot_date_time"),
        # Index for range queries on date
        Index("ix_time_slot_date", "date"),
    )

    def is_available(self, party_size: int) -> bool:
        """
        Check if the time slot has enough capacity for the requested party size.
        
        Args:
            party_size: Number of people in the party
            
        Returns:
            True if there's enough capacity, False otherwise
        """
        return (self.total_capacity - self.booked_capacity) >= party_size

    def remaining_capacity(self) -> int:
        """
        Calculate remaining capacity for this time slot.
        
        Returns:
            Number of remaining seats
        """
        return self.total_capacity - self.booked_capacity

    def __repr__(self) -> str:
        return (
            f"<TimeSlot(id={self.id}, date={self.date}, time={self.time}, "
            f"total_capacity={self.total_capacity}, booked_capacity={self.booked_capacity}, "
            f"remaining={self.remaining_capacity()})>"
        )


class RestaurantConfig(Base):
    """
    RestaurantConfig model storing global restaurant configuration (single row).
    """
    __tablename__ = "restaurant_config"

    id = Column(Integer, primary_key=True, default=1)
    operating_hours = Column(
        JSON,
        nullable=False,
        # Stores opening/closing times per day of week
        # Format: {"monday": {"open": "09:00", "close": "22:00"}, ...}
    )
    slot_duration = Column(Integer, nullable=False, default=30)  # Minutes
    max_party_size = Column(Integer, nullable=False, default=8)
    booking_window_days = Column(
        Integer,
        nullable=False,
        default=30,
        # How far ahead bookings are allowed
    )

    # Table constraints
    __table_args__ = (
        # Ensure only one configuration row exists
        CheckConstraint("id = 1", name="ck_single_config_row"),
    )

    def __repr__(self) -> str:
        return (
            f"<RestaurantConfig(id={self.id}, slot_duration={self.slot_duration}, "
            f"max_party_size={self.max_party_size}, booking_window_days={self.booking_window_days})>"
        )


def get_database_url() -> str:
    """
    Get database URL from environment variables.
    
    Returns:
        Database connection string
        
    Raises:
        ValueError: If DATABASE_URL is not set
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please set it to your PostgreSQL connection string."
        )
    return database_url


def init_db(database_url: str | None = None) -> Engine:
    """
    Initialize database engine and session factory.
    
    Args:
        database_url: Optional database connection string. If not provided,
                     will use DATABASE_URL environment variable.
    
    Returns:
        SQLAlchemy Engine instance
        
    Raises:
        ValueError: If database_url is not provided and DATABASE_URL env var is not set
    """
    global engine, SessionLocal
    
    if database_url is None:
        database_url = get_database_url()
    
    # Create engine
    engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,  # Enable connection health checks
        pool_size=5,
        max_overflow=10,
    )
    
    # Create session factory
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    
    return engine


def create_tables() -> None:
    """
    Create all tables in the database.
    
    Raises:
        RuntimeError: If database engine is not initialized
    """
    if engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db() first.")
    
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup.
    
    Yields:
        SQLAlchemy Session instance
        
    Example:
        with get_db_session() as session:
            booking = session.query(Booking).first()
    
    Raises:
        RuntimeError: If session factory is not initialized
    """
    if SessionLocal is None:
        raise RuntimeError("Session factory not initialized. Call init_db() first.")
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for getting database sessions (useful for FastAPI).
    
    Yields:
        SQLAlchemy Session instance
    """
    with get_db_session() as session:
        yield session
