"""
Conversation state manager for orchestrating booking conversation flow.

This module provides the ConversationStateManager class that manages:
- State transitions with validation
- Context updates with correction detection
- Multi-field updates (context switching)
- State progression logic
"""

from datetime import date, time
from typing import Optional, Any, Dict, List
from loguru import logger

from .states import ConversationState
from .context import ConversationContext


class StateTransitionError(Exception):
    """Exception raised when an invalid state transition is attempted."""
    pass


class ConversationStateManager:
    """
    Manages conversation state transitions and context for restaurant booking.
    
    This class orchestrates the conversation flow, ensuring:
    - Valid state transitions
    - Proper context updates
    - Correction handling
    - Multi-field updates (context switching)
    - Comprehensive logging
    
    Attributes:
        context: Current conversation context with all collected information
    """
    
    def __init__(self, initial_state: ConversationState = ConversationState.GREETING):
        """
        Initialize the conversation state manager.
        
        Args:
            initial_state: Starting state for the conversation (default: GREETING)
        """
        self.context = ConversationContext(current_state=initial_state)
        logger.info(f"ConversationStateManager initialized with state: {initial_state}")
    
    def get_current_state(self) -> ConversationState:
        """
        Get the current conversation state.
        
        Returns:
            Current ConversationState
        """
        return self.context.current_state
    
    def get_context(self) -> ConversationContext:
        """
        Get the current conversation context.
        
        Returns:
            Current ConversationContext with all collected information
        """
        return self.context
    
    def get_missing_fields(self) -> List[str]:
        """
        Get list of required fields that have not been collected yet.
        
        Returns:
            List of missing required field names
        """
        missing = self.context.get_missing_required_fields()
        logger.debug(f"Missing required fields: {missing}")
        return missing
    
    def can_transition_to(self, target_state: ConversationState) -> tuple[bool, str]:
        """
        Check if transition to target state is valid.
        
        Validates:
        - Cannot go backwards from COMPLETED
        - Cannot skip to CONFIRMING without all required fields
        - Cannot skip to COMPLETED from non-CONFIRMING states
        
        Args:
            target_state: State to transition to
            
        Returns:
            Tuple of (is_valid, reason). If valid, reason is empty string.
        """
        current = self.context.current_state
        
        # COMPLETED state is terminal - no transitions from it
        if current == ConversationState.COMPLETED:
            return False, "Cannot transition from COMPLETED state"
        
        # Can always reset to GREETING
        if target_state == ConversationState.GREETING:
            return True, ""
        
        # Cannot transition to COMPLETED unless coming from CONFIRMING
        if target_state == ConversationState.COMPLETED:
            if current != ConversationState.CONFIRMING:
                return False, "Can only transition to COMPLETED from CONFIRMING state"
            # Also check that all required fields are present
            if not self.context.is_complete():
                missing = self.get_missing_fields()
                return False, f"Cannot complete booking: missing fields {missing}"
            return True, ""
        
        # Cannot skip to CONFIRMING without all required fields
        if target_state == ConversationState.CONFIRMING:
            if not self.context.is_complete():
                missing = self.get_missing_fields()
                return False, f"Cannot confirm: missing required fields {missing}"
            return True, ""
        
        # All other transitions are allowed (for correction support)
        return True, ""
    
    def transition_to(self, new_state: ConversationState) -> None:
        """
        Transition to a new conversation state with validation.
        
        Args:
            new_state: State to transition to
            
        Raises:
            StateTransitionError: If transition is not valid
        """
        old_state = self.context.current_state
        
        # Validate transition
        can_transition, reason = self.can_transition_to(new_state)
        if not can_transition:
            logger.warning(
                f"Invalid state transition from {old_state} to {new_state}: {reason}"
            )
            raise StateTransitionError(reason)
        
        # Perform transition
        self.context.current_state = new_state
        logger.info(f"State transition: {old_state} -> {new_state}")
    
    def update_context(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Update conversation context with new information.
        
        This method:
        - Detects corrections (updates to already-set fields)
        - Supports multi-field updates (context switching)
        - Validates all updates
        - Logs all changes
        
        Supported fields:
        - date: booking date
        - time: booking time
        - party_size: number of people
        - name: customer name
        - phone: customer phone number
        - special_requests: special requests
        
        Args:
            **kwargs: Field names and values to update
            
        Returns:
            Dictionary with update results:
            - updated: list of fields that were updated
            - corrections: list of fields that were corrected
            - errors: dict of fields that failed validation
            
        Example:
            >>> manager.update_context(date="2024-12-25", time="18:30", party_size=4)
            {'updated': ['date', 'time', 'party_size'], 'corrections': [], 'errors': {}}
        """
        result = {
            "updated": [],
            "corrections": [],
            "errors": {}
        }
        
        # Track which fields were already set (for correction detection)
        collected_before = set(self.context.get_collected_fields())
        
        # Process each field update
        for field_name, value in kwargs.items():
            # Skip if field doesn't exist in context
            if not hasattr(self.context, field_name):
                logger.warning(f"Unknown field in update_context: {field_name}")
                result["errors"][field_name] = f"Unknown field: {field_name}"
                continue
            
            # Get old value for logging
            old_value = getattr(self.context, field_name)
            
            try:
                # Update the field
                setattr(self.context, field_name, value)
                
                # Re-validate the entire model to ensure all validators run
                self.context.model_validate(self.context.model_dump())
                
                # Determine if this was a correction
                is_correction = field_name in collected_before and old_value is not None
                
                if is_correction:
                    result["corrections"].append(field_name)
                    logger.info(
                        f"Context correction: {field_name} changed from {old_value} to {value}"
                    )
                else:
                    result["updated"].append(field_name)
                    logger.info(f"Context updated: {field_name} = {value}")
                    
            except ValueError as e:
                # Validation failed - revert the change
                setattr(self.context, field_name, old_value)
                result["errors"][field_name] = str(e)
                logger.warning(f"Validation failed for {field_name}: {e}")
        
        # Log summary
        if result["updated"] or result["corrections"]:
            logger.info(
                f"Context update complete. "
                f"Updated: {result['updated']}, "
                f"Corrections: {result['corrections']}, "
                f"Errors: {list(result['errors'].keys())}"
            )
        
        return result
    
    def auto_advance_state(self) -> Optional[ConversationState]:
        """
        Automatically advance to the next appropriate state based on collected information.
        
        This method determines the next state by:
        1. If all fields collected -> CONFIRMING
        2. Otherwise -> next field collection state based on what's missing
        
        Returns:
            The new state after auto-advance, or None if state didn't change
        """
        current = self.context.current_state
        
        # Don't auto-advance from these states
        if current in [ConversationState.GREETING, ConversationState.CONFIRMING, ConversationState.COMPLETED]:
            return None
        
        # If all fields are collected, move to confirming
        if self.context.is_complete():
            can_confirm, _ = self.can_transition_to(ConversationState.CONFIRMING)
            if can_confirm:
                self.transition_to(ConversationState.CONFIRMING)
                return ConversationState.CONFIRMING
        
        # Otherwise, find the next missing field state
        missing = self.get_missing_fields()
        if not missing:
            return None
        
        # Map fields to their collection states
        field_to_state = {
            "date": ConversationState.COLLECTING_DATE,
            "time": ConversationState.COLLECTING_TIME,
            "party_size": ConversationState.COLLECTING_PARTY_SIZE,
            "name": ConversationState.COLLECTING_NAME,
            "phone": ConversationState.COLLECTING_PHONE,
        }
        
        # Get next missing field in order
        ordered_states = ConversationState.get_ordered_states()
        for state in ordered_states:
            for field, field_state in field_to_state.items():
                if state == field_state and field in missing:
                    if state != current:
                        self.transition_to(state)
                        return state
        
        return None
    
    def reset(self) -> None:
        """
        Reset conversation to initial state and clear all context.
        
        This creates a fresh ConversationContext and returns to GREETING state.
        """
        logger.info("Resetting conversation state manager")
        old_context = self.context
        self.context = ConversationContext(current_state=ConversationState.GREETING)
        logger.info(
            f"Reset complete. Cleared context with fields: {old_context.get_collected_fields()}"
        )
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a summary of conversation progress.
        
        Returns:
            Dictionary containing:
            - current_state: current conversation state
            - collected_fields: list of collected field names
            - missing_fields: list of missing required field names
            - is_complete: whether all required fields are collected
            - progress_percentage: percentage of required fields collected (0-100)
        """
        collected = self.context.get_collected_fields()
        missing = self.get_missing_fields()
        required_count = 5  # date, time, party_size, name, phone
        collected_count = required_count - len(missing)
        
        return {
            "current_state": str(self.context.current_state),
            "collected_fields": collected,
            "missing_fields": missing,
            "is_complete": self.context.is_complete(),
            "progress_percentage": int((collected_count / required_count) * 100),
        }
    
    def handle_multi_field_input(
        self, 
        date_val: Optional[date] = None,
        time_val: Optional[time] = None,
        party_size_val: Optional[int] = None,
        name_val: Optional[str] = None,
        phone_val: Optional[str] = None,
        special_requests_val: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle context switching by accepting multiple fields at once.
        
        This is a convenience method for scenarios where the user provides
        multiple pieces of information in a single utterance.
        
        Example:
            User says: "Friday at 7 PM for 4 people"
            Call: handle_multi_field_input(date=..., time=..., party_size=4)
        
        Args:
            date_val: Booking date
            time_val: Booking time
            party_size_val: Number of people
            name_val: Customer name
            phone_val: Customer phone
            special_requests_val: Special requests
            
        Returns:
            Dictionary with update results from update_context()
        """
        updates = {}
        
        if date_val is not None:
            updates["date"] = date_val
        if time_val is not None:
            updates["time"] = time_val
        if party_size_val is not None:
            updates["party_size"] = party_size_val
        if name_val is not None:
            updates["name"] = name_val
        if phone_val is not None:
            updates["phone"] = phone_val
        if special_requests_val is not None:
            updates["special_requests"] = special_requests_val
        
        if updates:
            logger.info(f"Multi-field context update with {len(updates)} fields")
            return self.update_context(**updates)
        
        return {"updated": [], "corrections": [], "errors": {}}
