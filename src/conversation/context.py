"""
Conversation context model for storing booking information during conversation.

This module defines the ConversationContext Pydantic model that stores all
information collected during a booking conversation.
"""

import re
from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from .states import ConversationState


class ConversationContext(BaseModel):
    """
    Pydantic model for storing all conversation context and collected booking information.
    
    This model tracks:
    - Current conversation state
    - All booking fields (date, time, party_size, name, phone, special_requests)
    - Which fields have been collected
    
    Attributes:
        current_state: Current state of the conversation
        date: Booking date (optional until collected)
        time: Booking time (optional until collected)
        party_size: Number of people (optional until collected)
        name: Customer name (optional until collected)
        phone: Customer phone number (optional until collected)
        special_requests: Any special requests or dietary restrictions
    """
    
    current_state: ConversationState = Field(
        default=ConversationState.GREETING,
        description="Current state of the conversation"
    )
    
    date: Optional[date] = Field(
        default=None,
        description="Booking date"
    )
    
    time: Optional[time] = Field(
        default=None,
        description="Booking time slot"
    )
    
    party_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of people in the party (1-20)"
    )
    
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Customer name"
    )
    
    phone: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=50,
        description="Customer phone number"
    )
    
    special_requests: Optional[str] = Field(
        default=None,
        description="Special requests or dietary restrictions"
    )
    
    @field_validator("date")
    @classmethod
    def validate_date_not_in_past(cls, v: Optional[date]) -> Optional[date]:
        """
        Validate that the booking date is not in the past.
        
        Args:
            v: Date value to validate
            
        Returns:
            Validated date or None
            
        Raises:
            ValueError: If date is in the past
        """
        if v is not None and v < date.today():
            raise ValueError("Booking date cannot be in the past")
        return v
    
    @field_validator("date")
    @classmethod
    def validate_date_range(cls, v: Optional[date]) -> Optional[date]:
        """
        Validate that the booking date is within reasonable range (up to 90 days).
        
        Args:
            v: Date value to validate
            
        Returns:
            Validated date or None
            
        Raises:
            ValueError: If date is more than 90 days in the future
        """
        if v is not None:
            from datetime import timedelta
            max_date = date.today() + timedelta(days=90)
            if v > max_date:
                raise ValueError("Booking date cannot be more than 90 days in the future")
        return v
    
    @field_validator("party_size")
    @classmethod
    def validate_party_size_positive(cls, v: Optional[int]) -> Optional[int]:
        """
        Validate that party size is positive and reasonable.
        
        Args:
            v: Party size to validate
            
        Returns:
            Validated party size or None
            
        Raises:
            ValueError: If party size is invalid
        """
        if v is not None:
            if v < 1:
                raise ValueError("Party size must be at least 1")
            if v > 20:
                raise ValueError("Party size cannot exceed 20 people")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate phone number format.
        Accepts formats like: +1234567890, (123) 456-7890, 123-456-7890, 1234567890
        
        Args:
            v: Phone number to validate
            
        Returns:
            Validated phone number or None
            
        Raises:
            ValueError: If phone format is invalid
        """
        if v is None or v.strip() == "":
            return None
        
        # Remove common separators and spaces
        cleaned = re.sub(r'[\s\-\(\)\.]', '', v)
        
        # Check if it contains only digits and optional leading +
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            raise ValueError(
                "Phone number must contain 10-15 digits and may include spaces, "
                "dashes, parentheses, or a leading +"
            )
        
        return v
    
    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate that name is not empty after stripping whitespace.
        
        Args:
            v: Name to validate
            
        Returns:
            Validated and stripped name or None
            
        Raises:
            ValueError: If name is empty
        """
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Customer name cannot be empty")
        return v
    
    @field_validator("time")
    @classmethod
    def validate_time_reasonable(cls, v: Optional[time]) -> Optional[time]:
        """
        Validate that time is within reasonable restaurant hours (5 AM to 11:59 PM).
        
        Args:
            v: Time to validate
            
        Returns:
            Validated time or None
            
        Raises:
            ValueError: If time is outside reasonable hours
        """
        if v is not None:
            # Check if time is within reasonable restaurant hours
            if v.hour < 5 or v.hour >= 24:
                raise ValueError("Booking time must be between 5:00 AM and 11:59 PM")
        return v
    
    def get_collected_fields(self) -> list[str]:
        """
        Get list of field names that have been collected (non-None values).
        
        Returns:
            List of field names with values
        """
        collected = []
        if self.date is not None:
            collected.append("date")
        if self.time is not None:
            collected.append("time")
        if self.party_size is not None:
            collected.append("party_size")
        if self.name is not None:
            collected.append("name")
        if self.phone is not None:
            collected.append("phone")
        # Note: special_requests is optional and not required
        return collected
    
    def get_missing_required_fields(self) -> list[str]:
        """
        Get list of required field names that have not been collected yet.
        
        Required fields are: date, time, party_size, name, phone
        Special requests is optional.
        
        Returns:
            List of missing required field names
        """
        required_fields = ["date", "time", "party_size", "name", "phone"]
        collected = self.get_collected_fields()
        return [field for field in required_fields if field not in collected]
    
    def is_complete(self) -> bool:
        """
        Check if all required fields have been collected.
        
        Returns:
            True if all required fields are present, False otherwise
        """
        return len(self.get_missing_required_fields()) == 0
    
    def to_booking_dict(self) -> dict:
        """
        Convert context to a dictionary suitable for booking creation.
        
        Returns:
            Dictionary with booking fields
            
        Raises:
            ValueError: If not all required fields are collected
        """
        if not self.is_complete():
            missing = self.get_missing_required_fields()
            raise ValueError(f"Cannot create booking: missing fields {missing}")
        
        return {
            "date": self.date,
            "time_slot": self.time,
            "party_size": self.party_size,
            "customer_name": self.name,
            "customer_phone": self.phone,
            "special_requests": self.special_requests,
        }
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_state": "collecting_date",
                "date": "2024-12-25",
                "time": "18:30:00",
                "party_size": 4,
                "name": "John Doe",
                "phone": "+1234567890",
                "special_requests": "Window seat preferred"
            }
        }
    )
