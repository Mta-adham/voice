"""
Conversation state definitions for the restaurant booking system.

This module defines all possible states in the booking conversation flow.
"""

from enum import Enum


class ConversationState(str, Enum):
    """
    Enum representing all possible states in a booking conversation.
    
    The conversation typically flows linearly through these states:
    greeting -> collecting_date -> collecting_time -> collecting_party_size 
    -> collecting_name -> collecting_phone -> confirming -> completed
    
    However, users can provide corrections that may cause non-linear transitions.
    """
    
    GREETING = "greeting"
    """Initial state when conversation starts."""
    
    COLLECTING_DATE = "collecting_date"
    """Collecting the desired booking date from the user."""
    
    COLLECTING_TIME = "collecting_time"
    """Collecting the desired booking time from the user."""
    
    COLLECTING_PARTY_SIZE = "collecting_party_size"
    """Collecting the number of people in the party."""
    
    COLLECTING_NAME = "collecting_name"
    """Collecting the customer's name for the reservation."""
    
    COLLECTING_PHONE = "collecting_phone"
    """Collecting the customer's phone number for the reservation."""
    
    CONFIRMING = "confirming"
    """Reviewing all collected information with the user before final confirmation."""
    
    COMPLETED = "completed"
    """Final state after booking is confirmed and saved."""
    
    def __str__(self) -> str:
        """Return the string value of the state."""
        return self.value
    
    @classmethod
    def get_ordered_states(cls) -> list['ConversationState']:
        """
        Get the typical linear progression order of states.
        
        Returns:
            List of ConversationState in expected order
        """
        return [
            cls.GREETING,
            cls.COLLECTING_DATE,
            cls.COLLECTING_TIME,
            cls.COLLECTING_PARTY_SIZE,
            cls.COLLECTING_NAME,
            cls.COLLECTING_PHONE,
            cls.CONFIRMING,
            cls.COMPLETED,
        ]
    
    def get_next_state(self) -> 'ConversationState':
        """
        Get the next state in linear progression.
        
        Returns:
            Next ConversationState in the flow
            
        Raises:
            ValueError: If called on COMPLETED state (no next state)
        """
        ordered = self.get_ordered_states()
        current_index = ordered.index(self)
        
        if current_index >= len(ordered) - 1:
            raise ValueError("COMPLETED state has no next state")
        
        return ordered[current_index + 1]
    
    def get_previous_state(self) -> 'ConversationState':
        """
        Get the previous state in linear progression.
        
        Returns:
            Previous ConversationState in the flow
            
        Raises:
            ValueError: If called on GREETING state (no previous state)
        """
        ordered = self.get_ordered_states()
        current_index = ordered.index(self)
        
        if current_index <= 0:
            raise ValueError("GREETING state has no previous state")
        
        return ordered[current_index - 1]
