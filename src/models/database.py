"""
SQLAlchemy database models and session management for restaurant booking system.
"""
import os
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Callable, TypeVar, Any

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
from sqlalchemy.exc import OperationalError, DatabaseError as SQLAlchemyDatabaseError
from loguru import logger

T = TypeVar('T')

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


def retry_on_db_error(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    retry_on: tuple = (OperationalError,)
) -> Callable:
    """
    Decorator for retrying database operations on transient errors.
    
    Implements exponential backoff retry strategy for database operations
    that may fail due to temporary issues like connection problems or deadlocks.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay on each retry
        retry_on: Tuple of exception types to retry on
    
    Returns:
        Decorator function
    
    Example:
        @retry_on_db_error(max_retries=3)
        def create_booking(session, data):
            # ... database operation ...
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries}): {str(e)} | "
                            f"Retrying in {delay:.2f}s"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"Database operation failed after {max_retries} retries: {str(e)}"
                        )
                except Exception as e:
                    # Don't retry on non-transient errors
                    logger.error(f"Database operation failed with non-retryable error: {str(e)}")
                    raise
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


def check_db_connection() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        True if connection is healthy, False otherwise
    """
    if engine is None:
        logger.warning("Database engine not initialized")
        return False
    
    try:
        # Try a simple query
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.debug("Database connection healthy")
        return True
    except Exception as e:
        logger.error(f"Database connection unhealthy: {str(e)}")
        return False


def reconnect_db(max_attempts: int = 3, delay: float = 2.0) -> bool:
    """
    Attempt to reconnect to the database.
    
    Args:
        max_attempts: Maximum number of reconnection attempts
        delay: Delay between attempts in seconds
    
    Returns:
        True if reconnection successful, False otherwise
    """
    global engine, SessionLocal
    
    if engine is None:
        logger.error("Cannot reconnect: engine was never initialized")
        return False
    
    database_url = str(engine.url)
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Attempting database reconnection (attempt {attempt}/{max_attempts})")
            
            # Dispose of existing engine
            engine.dispose()
            
            # Recreate engine
            engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            
            # Recreate session factory
            SessionLocal = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
            
            # Test connection
            if check_db_connection():
                logger.info("Database reconnection successful")
                return True
            
        except Exception as e:
            logger.error(f"Reconnection attempt {attempt} failed: {str(e)}")
        
        if attempt < max_attempts:
            time.sleep(delay)
    
    logger.error(f"Failed to reconnect after {max_attempts} attempts")
    return False


@contextmanager
def get_db_session_with_retry(
    max_retries: int = 3,
    reconnect_on_failure: bool = True
) -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic retry and reconnection.
    
    This is an enhanced version of get_db_session that:
    - Retries transient errors
    - Attempts to reconnect on connection failures
    - Provides better error logging
    
    Args:
        max_retries: Maximum number of retry attempts
        reconnect_on_failure: Whether to attempt reconnection on connection errors
    
    Yields:
        SQLAlchemy Session instance
    
    Example:
        with get_db_session_with_retry() as session:
            booking = session.query(Booking).first()
    
    Raises:
        RuntimeError: If session factory is not initialized
        OperationalError: If database operations fail after retries
    """
    if SessionLocal is None:
        raise RuntimeError("Session factory not initialized. Call init_db() first.")
    
    last_exception = None
    
    for attempt in range(max_retries):
        session = None
        try:
            session = SessionLocal()
            yield session
            session.commit()
            return  # Success!
            
        except OperationalError as e:
            last_exception = e
            logger.warning(
                f"Database operation error (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            
            if session:
                session.rollback()
                session.close()
            
            # Try to reconnect if it's a connection error
            if reconnect_on_failure and attempt < max_retries - 1:
                if "connection" in str(e).lower():
                    logger.info("Attempting database reconnection")
                    if reconnect_db():
                        continue
            
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            
        except Exception as e:
            last_exception = e
            logger.error(f"Database error: {str(e)}")
            if session:
                session.rollback()
                session.close()
            raise
        finally:
            if session and session.is_active:
                session.close()
    
    # All retries exhausted
    logger.error(f"Database operation failed after {max_retries} attempts")
    raise last_exception
