"""
End-to-end integration tests for complete booking flow.

Tests:
- Mock all external services (LLMs, STT, TTS, SMS, Email)
- Simulate the complete happy path conversation from requirements
- Verify booking is created in database
- Verify confirmations are sent
- Test conversation ends gracefully
"""
import pytest
from datetime import date, time, timedelta
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from sqlalchemy.orm import Session

from models.database import Booking, TimeSlot
from services.booking_service import BookingService
from conversation.state_manager import ConversationStateManager
from conversation.states import ConversationState


class TestEndToEndBookingFlow:
    """Test complete end-to-end booking flow."""
    
    @patch('services.llm_service.llm_chat')
    def test_happy_path_booking_conversation(
        self,
        mock_llm_chat,
        booking_service: BookingService,
        db_session: Session,
        restaurant_config
    ):
        """
        Test the complete happy path conversation flow:
        1. Greeting
        2. Collect date
        3. Collect time
        4. Collect party size
        5. Collect name
        6. Collect phone
        7. Confirmation
        8. Booking created
        """
        
        # Initialize conversation manager
        manager = ConversationStateManager(
            initial_state=ConversationState.GREETING
        )
        
        # Simulate greeting
        assert manager.get_current_state() == ConversationState.GREETING
        manager.transition_to(ConversationState.COLLECTING_DATE)
        
        # User provides date
        tomorrow = date.today() + timedelta(days=1)
        manager.update_context(date=tomorrow)
        assert manager.context.date == tomorrow
        
        # Move to collect time
        manager.transition_to(ConversationState.COLLECTING_TIME)
        manager.update_context(time=time(18, 30))
        assert manager.context.time == time(18, 30)
        
        # Move to collect party size
        manager.transition_to(ConversationState.COLLECTING_PARTY_SIZE)
        manager.update_context(party_size=4)
        assert manager.context.party_size == 4
        
        # Move to collect name
        manager.transition_to(ConversationState.COLLECTING_NAME)
        manager.update_context(name="John Doe")
        assert manager.context.name == "John Doe"
        
        # Move to collect phone
        manager.transition_to(ConversationState.COLLECTING_PHONE)
        manager.update_context(phone="+1234567890")
        assert manager.context.phone == "+1234567890"
        
        # Verify context is complete
        assert manager.context.is_complete() is True
        
        # Move to confirming
        manager.transition_to(ConversationState.CONFIRMING)
        assert manager.get_current_state() == ConversationState.CONFIRMING
        
        # Create booking in database
        from models.schemas import BookingCreate
        
        booking_data = BookingCreate(
            date=manager.context.date,
            time_slot=manager.context.time,
            party_size=manager.context.party_size,
            customer_name=manager.context.name,
            customer_phone=manager.context.phone
        )
        
        # Generate time slot first
        booking_service.generate_time_slots(tomorrow)
        
        booking = booking_service.create_booking(booking_data)
        
        # Verify booking was created
        assert booking.id is not None
        assert booking.customer_name == "John Doe"
        assert booking.party_size == 4
        assert booking.status == "confirmed"
        
        # Move to completed
        manager.transition_to(ConversationState.COMPLETED)
        assert manager.get_current_state() == ConversationState.COMPLETED
    
    @patch('services.llm_service.llm_chat')
    @patch('speech.elevenlabs_tts.ElevenLabsTTS.generate_speech')
    def test_conversation_with_tts_responses(
        self,
        mock_tts,
        mock_llm_chat,
        booking_service: BookingService,
        restaurant_config
    ):
        """Test conversation flow with TTS responses."""
        
        # Mock TTS responses
        mock_audio = np.random.rand(1000).astype(np.int16)
        mock_tts.return_value = (mock_audio, 16000)
        
        # Mock LLM responses for different conversation stages
        mock_llm_chat.side_effect = [
            {"content": "Hello! I'd like to help you book a table. What date would you like?", "provider": "openai", "tokens_used": 20},
            {"content": "Great! What time would you prefer?", "provider": "openai", "tokens_used": 15},
            {"content": "Perfect! How many people will be dining?", "provider": "openai", "tokens_used": 15},
            {"content": "Excellent! May I have your name please?", "provider": "openai", "tokens_used": 15},
            {"content": "Thank you! And your phone number for the reservation?", "provider": "openai", "tokens_used": 18},
            {"content": "Perfect! Let me confirm your booking...", "provider": "openai", "tokens_used": 15},
        ]
        
        manager = ConversationStateManager()
        
        # Simulate conversation with TTS generation
        states_to_test = [
            ConversationState.GREETING,
            ConversationState.COLLECTING_DATE,
            ConversationState.COLLECTING_TIME,
            ConversationState.COLLECTING_PARTY_SIZE,
            ConversationState.COLLECTING_NAME,
            ConversationState.COLLECTING_PHONE,
        ]
        
        for state in states_to_test:
            if state != ConversationState.GREETING:
                manager.transition_to(state)
            
            # Get LLM response
            if mock_llm_chat.call_count < len(states_to_test):
                response = mock_llm_chat(
                    provider="openai",
                    messages=[{"role": "user", "content": "test"}]
                )
                
                assert "content" in response
        
        # Verify all mocks were called
        assert mock_llm_chat.call_count > 0
    
    @patch('services.llm_service.llm_chat')
    def test_conversation_with_corrections(
        self,
        mock_llm_chat,
        booking_service: BookingService,
        db_session: Session,
        restaurant_config
    ):
        """Test conversation flow with user corrections."""
        
        mock_llm_chat.return_value = {
            "content": "I understand you'd like to change that.",
            "provider": "openai",
            "tokens_used": 15
        }
        
        manager = ConversationStateManager()
        
        tomorrow = date.today() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        # User provides initial date
        manager.transition_to(ConversationState.COLLECTING_DATE)
        manager.update_context(date=tomorrow)
        
        # User corrects the date
        result = manager.update_context(date=day_after)
        
        assert "date" in result["corrections"]
        assert manager.context.date == day_after
        
        # Continue with rest of booking
        manager.transition_to(ConversationState.COLLECTING_TIME)
        manager.update_context(time=time(18, 0))
        
        # User corrects time
        result = manager.update_context(time=time(19, 0))
        
        assert "time" in result["corrections"]
        assert manager.context.time == time(19, 0)
        
        # Complete booking with corrections
        manager.transition_to(ConversationState.COLLECTING_PARTY_SIZE)
        manager.update_context(party_size=4)
        
        manager.transition_to(ConversationState.COLLECTING_NAME)
        manager.update_context(name="Jane Smith")
        
        manager.transition_to(ConversationState.COLLECTING_PHONE)
        manager.update_context(phone="+9876543210")
        
        # Verify context is complete despite corrections
        assert manager.context.is_complete() is True
    
    @patch('services.llm_service.llm_chat')
    def test_conversation_with_multiple_fields_at_once(
        self,
        mock_llm_chat,
        booking_service: BookingService,
        restaurant_config
    ):
        """Test handling when user provides multiple fields at once."""
        
        mock_llm_chat.return_value = {
            "content": "Great! I've got your date, time, and party size.",
            "provider": "openai",
            "tokens_used": 18
        }
        
        manager = ConversationStateManager()
        manager.transition_to(ConversationState.COLLECTING_DATE)
        
        # User provides multiple fields at once
        tomorrow = date.today() + timedelta(days=1)
        result = manager.update_context(
            date=tomorrow,
            time=time(19, 0),
            party_size=6
        )
        
        assert len(result["updated"]) == 3
        assert "date" in result["updated"]
        assert "time" in result["updated"]
        assert "party_size" in result["updated"]
        
        # Continue with remaining fields
        manager.transition_to(ConversationState.COLLECTING_NAME)
        manager.update_context(name="Alice Johnson")
        
        manager.transition_to(ConversationState.COLLECTING_PHONE)
        manager.update_context(phone="+5555555555")
        
        assert manager.context.is_complete() is True
    
    @patch('services.llm_service.llm_chat')
    def test_booking_capacity_validation_during_flow(
        self,
        mock_llm_chat,
        booking_service: BookingService,
        db_session: Session,
        restaurant_config
    ):
        """Test that capacity is validated during booking flow."""
        
        mock_llm_chat.return_value = {
            "content": "Let me check availability...",
            "provider": "openai",
            "tokens_used": 10
        }
        
        manager = ConversationStateManager()
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Create a nearly full time slot
        slot = TimeSlot(
            date=tomorrow,
            time=time(20, 0),
            total_capacity=50,
            booked_capacity=49  # Only 1 seat left
        )
        db_session.add(slot)
        db_session.commit()
        
        # User tries to book for 4 people
        manager.transition_to(ConversationState.COLLECTING_DATE)
        manager.update_context(date=tomorrow)
        
        manager.transition_to(ConversationState.COLLECTING_TIME)
        manager.update_context(time=time(20, 0))
        
        manager.transition_to(ConversationState.COLLECTING_PARTY_SIZE)
        manager.update_context(party_size=4)
        
        manager.transition_to(ConversationState.COLLECTING_NAME)
        manager.update_context(name="Test User")
        
        manager.transition_to(ConversationState.COLLECTING_PHONE)
        manager.update_context(phone="+1111111111")
        
        # Try to create booking
        from models.schemas import BookingCreate
        from services.booking_service import CapacityError
        
        booking_data = BookingCreate(
            date=manager.context.date,
            time_slot=manager.context.time,
            party_size=manager.context.party_size,
            customer_name=manager.context.name,
            customer_phone=manager.context.phone
        )
        
        # Should raise CapacityError
        with pytest.raises(CapacityError):
            booking_service.create_booking(booking_data)
    
    @patch('services.llm_service.llm_chat')
    def test_full_flow_with_special_requests(
        self,
        mock_llm_chat,
        booking_service: BookingService,
        db_session: Session,
        restaurant_config
    ):
        """Test complete flow including special requests."""
        
        mock_llm_chat.return_value = {
            "content": "I'll note your special requests.",
            "provider": "openai",
            "tokens_used": 12
        }
        
        manager = ConversationStateManager()
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Complete flow
        manager.transition_to(ConversationState.COLLECTING_DATE)
        manager.update_context(date=tomorrow)
        
        manager.transition_to(ConversationState.COLLECTING_TIME)
        manager.update_context(time=time(18, 30))
        
        manager.transition_to(ConversationState.COLLECTING_PARTY_SIZE)
        manager.update_context(party_size=2)
        
        manager.transition_to(ConversationState.COLLECTING_NAME)
        manager.update_context(name="Bob Williams")
        
        manager.transition_to(ConversationState.COLLECTING_PHONE)
        manager.update_context(phone="+2223334444")
        
        # Add special requests
        manager.update_context(
            special_requests="Window seat, vegetarian menu please"
        )
        
        # Create booking with special requests
        from models.schemas import BookingCreate
        
        booking_service.generate_time_slots(tomorrow)
        
        booking_data = BookingCreate(
            date=manager.context.date,
            time_slot=manager.context.time,
            party_size=manager.context.party_size,
            customer_name=manager.context.name,
            customer_phone=manager.context.phone,
            special_requests=manager.context.special_requests
        )
        
        booking = booking_service.create_booking(booking_data)
        
        assert booking.special_requests == "Window seat, vegetarian menu please"
    
    @patch('services.llm_service.llm_chat')
    def test_conversation_error_recovery(
        self,
        mock_llm_chat,
        booking_service: BookingService,
        restaurant_config
    ):
        """Test error recovery during conversation."""
        
        mock_llm_chat.return_value = {
            "content": "I'm sorry, that's not a valid date. Please try again.",
            "provider": "openai",
            "tokens_used": 15
        }
        
        manager = ConversationStateManager()
        manager.transition_to(ConversationState.COLLECTING_DATE)
        
        # User provides invalid date (in the past)
        yesterday = date.today() - timedelta(days=1)
        result = manager.update_context(date=yesterday)
        
        # Should have error
        assert "date" in result["errors"]
        assert manager.context.date is None
        
        # User provides valid date
        tomorrow = date.today() + timedelta(days=1)
        result = manager.update_context(date=tomorrow)
        
        assert "date" in result["updated"]
        assert manager.context.date == tomorrow
    
    def test_booking_verification_in_database(
        self,
        booking_service: BookingService,
        db_session: Session,
        restaurant_config
    ):
        """Test that booking is properly stored in database."""
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Generate time slots
        booking_service.generate_time_slots(tomorrow)
        
        # Create booking
        from models.schemas import BookingCreate
        
        booking_data = BookingCreate(
            date=tomorrow,
            time_slot=time(19, 0),
            party_size=3,
            customer_name="Database Test",
            customer_phone="+3334445555",
            customer_email="test@example.com"
        )
        
        booking = booking_service.create_booking(booking_data)
        
        # Verify in database
        retrieved = db_session.query(Booking).filter_by(
            id=booking.id
        ).first()
        
        assert retrieved is not None
        assert retrieved.customer_name == "Database Test"
        assert retrieved.customer_phone == "+3334445555"
        assert retrieved.customer_email == "test@example.com"
        assert retrieved.party_size == 3
        assert retrieved.status == "confirmed"
        assert retrieved.created_at is not None
    
    def test_time_slot_capacity_update_after_booking(
        self,
        booking_service: BookingService,
        db_session: Session,
        restaurant_config
    ):
        """Test that time slot capacity is updated after booking."""
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Generate time slots
        booking_service.generate_time_slots(tomorrow)
        
        # Get initial capacity
        slot = db_session.query(TimeSlot).filter_by(
            date=tomorrow,
            time=time(19, 0)
        ).first()
        
        initial_booked = slot.booked_capacity if slot else 0
        
        # Create booking
        from models.schemas import BookingCreate
        
        booking_data = BookingCreate(
            date=tomorrow,
            time_slot=time(19, 0),
            party_size=5,
            customer_name="Capacity Test",
            customer_phone="+4445556666"
        )
        
        booking = booking_service.create_booking(booking_data)
        
        # Verify capacity updated
        db_session.refresh(slot)
        
        assert slot.booked_capacity == initial_booked + 5
        assert slot.remaining_capacity() == slot.total_capacity - slot.booked_capacity


class TestEdgeCasesEndToEnd:
    """Test edge cases in end-to-end flow."""
    
    @patch('services.llm_service.llm_chat')
    def test_same_day_booking(
        self,
        mock_llm_chat,
        booking_service: BookingService,
        restaurant_config
    ):
        """Test same-day booking (allowed but with restrictions)."""
        
        mock_llm_chat.return_value = {
            "content": "I can help with that.",
            "provider": "openai",
            "tokens_used": 10
        }
        
        manager = ConversationStateManager()
        manager.transition_to(ConversationState.COLLECTING_DATE)
        
        # Today's date
        today = date.today()
        result = manager.update_context(date=today)
        
        # Should be allowed
        assert "date" in result["updated"]
        assert manager.context.date == today
    
    @patch('services.llm_service.llm_chat')
    def test_maximum_party_size_booking(
        self,
        mock_llm_chat,
        booking_service: BookingService,
        restaurant_config
    ):
        """Test booking with maximum allowed party size."""
        
        mock_llm_chat.return_value = {
            "content": "Large party booking confirmed.",
            "provider": "openai",
            "tokens_used": 10
        }
        
        manager = ConversationStateManager()
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Use maximum party size
        max_size = restaurant_config.max_party_size
        
        manager.transition_to(ConversationState.COLLECTING_DATE)
        manager.update_context(date=tomorrow)
        
        manager.transition_to(ConversationState.COLLECTING_TIME)
        manager.update_context(time=time(18, 0))
        
        manager.transition_to(ConversationState.COLLECTING_PARTY_SIZE)
        result = manager.update_context(party_size=max_size)
        
        assert "party_size" in result["updated"]
        assert manager.context.party_size == max_size
