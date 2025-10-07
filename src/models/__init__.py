"""
Models package - SQLAlchemy ORM models and Pydantic schemas.
"""
from .database import (
    Base,
    Booking,
    TimeSlot,
    RestaurantConfig,
    init_db,
    create_tables,
    get_db_session,
    get_db,
)

from .schemas import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    TimeSlotInfo,
    TimeSlotCreate,
    RestaurantConfigResponse,
)

__all__ = [
    # Database models
    "Base",
    "Booking",
    "TimeSlot",
    "RestaurantConfig",
    # Database utilities
    "init_db",
    "create_tables",
    "get_db_session",
    "get_db",
    # Pydantic schemas
    "BookingCreate",
    "BookingResponse",
    "BookingUpdate",
    "TimeSlotInfo",
    "TimeSlotCreate",
    "RestaurantConfigResponse",
]
