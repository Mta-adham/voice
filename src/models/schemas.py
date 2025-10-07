"""
Pydantic models for data validation and serialization.
"""
import re
from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class BookingCreate(BaseModel):
    """
    Pydantic model for validating incoming booking requests.
    """
    date: date = Field(..., description="Booking date")
    time_slot: time = Field(..., description="Booking time slot")
    party_size: int = Field(..., ge=1, le=8, description="Number of people (1-8)")
    customer_name: str = Field(..., min_length=1, max_length=255, description="Customer name")
    customer_phone: str = Field(..., min_length=10, max_length=50, description="Customer phone number")
    customer_email: Optional[str] = Field(None, max_length=255, description="Customer email (optional)")
    special_requests: Optional[str] = Field(None, description="Special requests or dietary restrictions")

    @field_validator("date")
    @classmethod
    def validate_date_not_in_past(cls, v: date) -> date:
        """Validate that the booking date is not in the past."""
        if v < date.today():
            raise ValueError("Booking date cannot be in the past")
        return v

    @field_validator("customer_phone")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """
        Validate phone number format.
        Accepts formats like: +1234567890, (123) 456-7890, 123-456-7890, 1234567890
        """
        # Remove common separators and spaces
        cleaned = re.sub(r'[\s\-\(\)\.]', '', v)
        
        # Check if it contains only digits and optional leading +
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError(
                "Phone number must contain 10-15 digits and may include spaces, "
                "dashes, parentheses, or a leading +"
            )
        
        return v

    @field_validator("customer_email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is None or v.strip() == "":
            return None
        
        # Basic email validation regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        
        return v

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, v: str) -> str:
        """Validate customer name is not empty after stripping whitespace."""
        if not v.strip():
            raise ValueError("Customer name cannot be empty")
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2024-12-25",
                "time_slot": "18:30:00",
                "party_size": 4,
                "customer_name": "John Doe",
                "customer_phone": "+1234567890",
                "customer_email": "john.doe@example.com",
                "special_requests": "Window seat preferred"
            }
        }
    )


class BookingResponse(BaseModel):
    """
    Pydantic model for formatting booking data in API responses.
    """
    id: int
    date: date
    time_slot: time
    party_size: int
    customer_name: str
    customer_phone: str
    customer_email: Optional[str]
    special_requests: Optional[str]
    status: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode for SQLAlchemy models
        json_schema_extra={
            "example": {
                "id": 1,
                "date": "2024-12-25",
                "time_slot": "18:30:00",
                "party_size": 4,
                "customer_name": "John Doe",
                "customer_phone": "+1234567890",
                "customer_email": "john.doe@example.com",
                "special_requests": "Window seat preferred",
                "status": "confirmed",
                "created_at": "2024-01-15T10:30:00"
            }
        }
    )


class TimeSlotInfo(BaseModel):
    """
    Pydantic model representing available time slot information.
    """
    id: int
    date: date
    time: time
    total_capacity: int
    booked_capacity: int
    remaining_capacity: int
    is_available: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "date": "2024-12-25",
                "time": "18:30:00",
                "total_capacity": 50,
                "booked_capacity": 32,
                "remaining_capacity": 18,
                "is_available": True
            }
        }
    )


class TimeSlotCreate(BaseModel):
    """
    Pydantic model for creating new time slots.
    """
    date: date = Field(..., description="Date for the time slot")
    time: time = Field(..., description="Time for the slot")
    total_capacity: int = Field(..., gt=0, description="Total seating capacity")

    @field_validator("date")
    @classmethod
    def validate_date_not_in_past(cls, v: date) -> date:
        """Validate that the time slot date is not in the past."""
        if v < date.today():
            raise ValueError("Time slot date cannot be in the past")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2024-12-25",
                "time": "18:30:00",
                "total_capacity": 50
            }
        }
    )


class RestaurantConfigResponse(BaseModel):
    """
    Pydantic model for restaurant configuration responses.
    """
    id: int
    operating_hours: dict
    slot_duration: int
    max_party_size: int
    booking_window_days: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
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
        }
    )


class BookingUpdate(BaseModel):
    """
    Pydantic model for updating existing bookings.
    """
    date: Optional[date] = None
    time_slot: Optional[time] = None
    party_size: Optional[int] = Field(None, ge=1, le=8)
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_phone: Optional[str] = Field(None, min_length=10, max_length=50)
    customer_email: Optional[str] = Field(None, max_length=255)
    special_requests: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|confirmed|completed|cancelled)$")

    @field_validator("date")
    @classmethod
    def validate_date_not_in_past(cls, v: Optional[date]) -> Optional[date]:
        """Validate that the booking date is not in the past."""
        if v is not None and v < date.today():
            raise ValueError("Booking date cannot be in the past")
        return v

    @field_validator("customer_phone")
    @classmethod
    def validate_phone_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format if provided."""
        if v is None:
            return None
        
        cleaned = re.sub(r'[\s\-\(\)\.]', '', v)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError(
                "Phone number must contain 10-15 digits and may include spaces, "
                "dashes, parentheses, or a leading +"
            )
        return v

    @field_validator("customer_email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is None or v.strip() == "":
            return None
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "party_size": 6,
                "special_requests": "Birthday celebration",
                "status": "confirmed"
            }
        }
    )
