"""
Voice Agent Orchestrator - Main coordination logic for restaurant booking system.

This module provides the VoiceAgent class that orchestrates all system components
in a continuous conversation loop until booking completion or user exit.
"""
import time
import signal
from datetime import datetime, date as date_type, time as time_type
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager

import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from ..audio.audio_manager import (
    AudioManager,
    AudioDeviceError,
    AudioRecordingError,
    AudioPlaybackError
)
from ..speech.elevenlabs_tts import ElevenLabsTTS, ElevenLabsTTSError
from ..stt.whisper_transcriber import WhisperTranscriber, WhisperTranscriptionError
from ..conversation.state_manager import ConversationStateManager, StateTransitionError
from ..conversation.states import ConversationState
from ..nlu.extractor import extract_booking_info, BookingExtractionResult
from ..response.generator import generate_response, ResponseGenerationError, get_fallback_response
from ..services.booking_service import (
    BookingService,
    BookingServiceError,
    ValidationError as BookingValidationError,
    CapacityError
)
from ..notifications.sms import send_sms_confirmation, SMSError
from ..notifications.email import send_email_confirmation, EmailError
from ..models.database import get_db_session
from ..models.schemas import BookingCreate


class VoiceAgentError(Exception):
    """Base exception for voice agent errors."""
    pass


class InitializationError(VoiceAgentError):
    """Raised when agent initialization fails."""
    pass


class VoiceAgent:
    """
    Main orchestrator for the voice-based restaurant booking agent.
    
    This class coordinates all system components to provide a natural voice
    conversation experience for restaurant bookings.
    
    Features:
    - Audio recording with voice activity detection
    - Speech-to-text transcription
    - Natural language understanding
    - Conversation state management
    - Dynamic response generation
    - Text-to-speech playback
    - Booking availability checking
    - Database booking creation
    - SMS and email confirmations
    - Comprehensive error handling
    - Timeout management
    """
    
    # Timeout settings (in seconds)
    INPUT_TIMEOUT = 15  # Timeout for user input
    EXTENDED_TIMEOUT = 30  # Extended timeout before ending call
    MAX_SILENCE_DURATION = 2.0  # Silence duration to detect end of speech
    
    # Recording settings
    MAX_RECORDING_DURATION = 30  # Maximum recording duration
    
    def __init__(
        self,
        session: Optional[Session] = None,
        audio_manager: Optional[AudioManager] = None,
        tts: Optional[ElevenLabsTTS] = None,
        transcriber: Optional[WhisperTranscriber] = None,
        input_timeout: float = INPUT_TIMEOUT,
        extended_timeout: float = EXTENDED_TIMEOUT
    ):
        """
        Initialize the voice agent.
        
        Args:
            session: Database session (if None, creates new session)
            audio_manager: AudioManager instance (if None, creates new)
            tts: ElevenLabsTTS instance (if None, creates new)
            transcriber: WhisperTranscriber instance (if None, creates new)
            input_timeout: Timeout for user input in seconds
            extended_timeout: Extended timeout before ending call
        """
        logger.info("Initializing VoiceAgent...")
        
        # Configuration
        self.input_timeout = input_timeout
        self.extended_timeout = extended_timeout
        
        # Components (initialized in initialize() method)
        self._session = session
        self._audio_manager = audio_manager
        self._tts = tts
        self._transcriber = transcriber
        self._state_manager: Optional[ConversationStateManager] = None
        self._booking_service: Optional[BookingService] = None
        
        # State tracking
        self._initialized = False
        self._should_exit = False
        self._timeout_count = 0
        self._booking_id: Optional[int] = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("VoiceAgent created (not yet initialized)")
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals for graceful shutdown."""
        logger.warning(f"Received signal {signum}, initiating shutdown...")
        self._should_exit = True
    
    def initialize(self) -> None:
        """
        Initialize all components and verify dependencies.
        
        Raises:
            InitializationError: If initialization fails
        """
        if self._initialized:
            logger.warning("VoiceAgent already initialized")
            return
        
        logger.info("Starting component initialization...")
        
        try:
            # Initialize database session
            if self._session is None:
                logger.info("Creating database session...")
                # get_db_session is a generator, get the session from it
                session_gen = get_db_session()
                self._session = next(session_gen)
            
            # Initialize audio manager
            if self._audio_manager is None:
                logger.info("Initializing AudioManager...")
                self._audio_manager = AudioManager()
            
            # Initialize TTS
            if self._tts is None:
                logger.info("Initializing ElevenLabs TTS...")
                self._tts = ElevenLabsTTS()
            
            # Initialize transcriber
            if self._transcriber is None:
                logger.info("Initializing Whisper transcriber...")
                self._transcriber = WhisperTranscriber()
            
            # Initialize conversation state manager
            logger.info("Initializing ConversationStateManager...")
            self._state_manager = ConversationStateManager()
            
            # Initialize booking service
            logger.info("Initializing BookingService...")
            self._booking_service = BookingService(self._session)
            
            self._initialized = True
            logger.info("✓ All components initialized successfully")
            
        except AudioDeviceError as e:
            error_msg = f"Audio device initialization failed: {str(e)}"
            logger.error(error_msg)
            raise InitializationError(error_msg) from e
        
        except ElevenLabsTTSError as e:
            error_msg = f"TTS initialization failed: {str(e)}"
            logger.error(error_msg)
            raise InitializationError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Unexpected initialization error: {str(e)}"
            logger.error(error_msg)
            raise InitializationError(error_msg) from e
    
    def _generate_greeting(self) -> str:
        """
        Generate initial greeting message.
        
        Returns:
            Greeting text
        """
        try:
            logger.info("Generating greeting...")
            greeting = generate_response("greeting")
            logger.info(f"Greeting generated: {greeting[:50]}...")
            return greeting
        except ResponseGenerationError as e:
            logger.warning(f"Failed to generate greeting: {e}, using fallback")
            return get_fallback_response("greeting")
    
    def _listen_for_input(self, timeout: float = None) -> Optional[Tuple[np.ndarray, int]]:
        """
        Listen for user input with voice activity detection.
        
        Uses silence detection to automatically stop recording when user finishes speaking.
        
        Args:
            timeout: Maximum time to wait for input (uses instance timeout if None)
            
        Returns:
            Tuple of (audio_data, sample_rate) or None if timeout/error
        """
        if timeout is None:
            timeout = self.input_timeout
        
        logger.info(f"Listening for user input (timeout: {timeout}s)...")
        
        try:
            self._audio_manager.start_recording()
            start_time = time.time()
            last_sound_time = start_time
            has_sound = False
            
            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.warning(f"Input timeout after {elapsed:.1f}s")
                    self._audio_manager.stop_recording()
                    return None
                
                # Check for user exit signal
                if self._should_exit:
                    logger.info("Exit signal detected during recording")
                    self._audio_manager.stop_recording()
                    return None
                
                # Check for silence (end of speech)
                if self._audio_manager.detect_silence(duration=self.MAX_SILENCE_DURATION):
                    if has_sound:  # Only stop if we detected sound first
                        silence_duration = time.time() - last_sound_time
                        if silence_duration >= self.MAX_SILENCE_DURATION:
                            logger.info(f"Silence detected for {silence_duration:.1f}s, stopping recording")
                            break
                else:
                    # Sound detected
                    has_sound = True
                    last_sound_time = time.time()
                
                # Prevent busy waiting
                time.sleep(0.1)
                
                # Safety check: max recording duration
                if elapsed > self.MAX_RECORDING_DURATION:
                    logger.warning(f"Max recording duration reached ({self.MAX_RECORDING_DURATION}s)")
                    break
            
            audio_data, sample_rate = self._audio_manager.stop_recording()
            
            # Check if we got valid audio
            if len(audio_data) == 0:
                logger.warning("No audio data captured")
                return None
            
            duration = len(audio_data) / sample_rate
            logger.info(f"Recorded {duration:.2f}s of audio")
            
            return audio_data, sample_rate
            
        except AudioRecordingError as e:
            logger.error(f"Recording error: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error during recording: {e}")
            return None
    
    def _transcribe_audio(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """
        Transcribe audio to text using Whisper.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of audio
            
        Returns:
            Transcribed text or None if transcription fails
        """
        try:
            logger.info("Transcribing audio...")
            text = self._transcriber.transcribe(audio_data, sample_rate)
            logger.info(f"Transcription: '{text}'")
            return text
        
        except WhisperTranscriptionError as e:
            logger.error(f"Transcription error: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Unexpected transcription error: {e}")
            return None
    
    def _process_utterance(self, utterance: str) -> Dict[str, Any]:
        """
        Process user utterance: extract information and update state.
        
        Args:
            utterance: Transcribed user speech
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing utterance: '{utterance}'")
        
        # Get current context
        context = self._state_manager.get_context()
        context_dict = {
            "date": context.date,
            "time": context.time,
            "party_size": context.party_size,
            "name": context.name,
            "phone": context.phone,
            "current_date": date_type.today()
        }
        
        # Extract booking information
        try:
            extraction = extract_booking_info(utterance, context_dict)
            logger.info(f"Extracted info: {extraction.to_dict()}")
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            extraction = BookingExtractionResult()
        
        # Update context with extracted information
        updates = {}
        if extraction.date:
            updates["date"] = datetime.fromisoformat(extraction.date).date()
        if extraction.time:
            hour, minute = map(int, extraction.time.split(':'))
            updates["time"] = time_type(hour=hour, minute=minute)
        if extraction.party_size:
            updates["party_size"] = extraction.party_size
        if extraction.name:
            updates["name"] = extraction.name
        if extraction.phone:
            updates["phone"] = extraction.phone
        if extraction.special_requests:
            updates["special_requests"] = extraction.special_requests
        
        update_result = {}
        if updates:
            update_result = self._state_manager.update_context(**updates)
            logger.info(f"Context update result: {update_result}")
        
        return {
            "extraction": extraction,
            "updates": updates,
            "update_result": update_result,
            "is_correction": extraction.is_correction,
            "needs_clarification": extraction.needs_clarification
        }
    
    def _determine_next_action(self) -> str:
        """
        Determine next action based on current state and context.
        
        Returns:
            Action string: 'collect_info', 'check_availability', 'confirm', 'complete', 'exit'
        """
        current_state = self._state_manager.get_current_state()
        context = self._state_manager.get_context()
        
        logger.info(f"Determining next action | state: {current_state}")
        
        # Check for exit conditions
        if self._should_exit:
            return "exit"
        
        # Check current state
        if current_state == ConversationState.COMPLETED:
            return "complete"
        
        if current_state == ConversationState.CONFIRMING:
            return "confirm"
        
        # Check if we have all required information
        if context.is_complete():
            # All info collected, move to confirmation
            logger.info("All required information collected, moving to confirmation")
            try:
                self._state_manager.transition_to(ConversationState.CONFIRMING)
                return "confirm"
            except StateTransitionError as e:
                logger.error(f"Failed to transition to CONFIRMING: {e}")
                return "collect_info"
        
        # Still need to collect information
        missing = self._state_manager.get_missing_fields()
        logger.info(f"Still need to collect: {missing}")
        
        # Auto-advance state based on what's missing
        new_state = self._state_manager.auto_advance_state()
        if new_state:
            logger.info(f"Auto-advanced to state: {new_state}")
        
        return "collect_info"
    
    def _handle_availability_check(self) -> Tuple[bool, Optional[list]]:
        """
        Check booking availability for current date/time/party_size.
        
        Returns:
            Tuple of (has_availability, available_slots)
        """
        context = self._state_manager.get_context()
        
        if not all([context.date, context.time, context.party_size]):
            logger.warning("Cannot check availability: missing required fields")
            return False, None
        
        try:
            logger.info(
                f"Checking availability | date: {context.date} | "
                f"time: {context.time} | party_size: {context.party_size}"
            )
            
            # Validate the booking request
            is_valid, error_msg = self._booking_service.validate_booking_request(
                context.date,
                context.time,
                context.party_size
            )
            
            if not is_valid:
                logger.warning(f"Booking validation failed: {error_msg}")
                return False, None
            
            # Get available slots
            available_slots = self._booking_service.get_available_slots(
                context.date,
                context.party_size
            )
            
            # Check if requested time is available
            requested_time = context.time
            has_exact_slot = any(slot.time == requested_time for slot in available_slots)
            
            logger.info(
                f"Availability check complete | "
                f"total_slots: {len(available_slots)} | "
                f"exact_match: {has_exact_slot}"
            )
            
            return has_exact_slot, available_slots
            
        except BookingServiceError as e:
            logger.error(f"Availability check error: {e}")
            return False, None
    
    def _handle_confirmation(self, user_confirmed: bool) -> bool:
        """
        Handle user confirmation response.
        
        Args:
            user_confirmed: Whether user confirmed the booking
            
        Returns:
            True if booking should proceed, False otherwise
        """
        if user_confirmed:
            logger.info("User confirmed booking")
            return True
        else:
            logger.info("User did not confirm, returning to information collection")
            # Transition back to collecting info
            try:
                self._state_manager.transition_to(ConversationState.COLLECTING_DATE)
            except StateTransitionError:
                pass
            return False
    
    def _create_booking(self) -> Optional[int]:
        """
        Create booking in database.
        
        Returns:
            Booking ID if successful, None otherwise
        """
        context = self._state_manager.get_context()
        
        if not context.is_complete():
            logger.error("Cannot create booking: missing required information")
            return None
        
        try:
            logger.info("Creating booking in database...")
            
            booking_data = BookingCreate(
                date=context.date,
                time_slot=context.time,
                party_size=context.party_size,
                customer_name=context.name,
                customer_phone=context.phone,
                customer_email=None,  # Optional field
                special_requests=context.special_requests,
                status="confirmed"
            )
            
            booking = self._booking_service.create_booking(booking_data)
            
            logger.info(
                f"✓ Booking created successfully | "
                f"booking_id: {booking.id} | "
                f"confirmation_code: {booking.confirmation_code}"
            )
            
            self._booking_id = booking.id
            return booking.id
            
        except (BookingValidationError, CapacityError) as e:
            logger.error(f"Booking creation failed: {e}")
            return None
        
        except BookingServiceError as e:
            logger.error(f"Booking service error: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error creating booking: {e}")
            return None
    
    def _send_confirmations(self) -> None:
        """
        Send SMS and email confirmations after successful booking.
        """
        context = self._state_manager.get_context()
        
        if not self._booking_id:
            logger.warning("No booking ID available for confirmations")
            return
        
        # Prepare booking details
        booking_details = {
            "booking_id": self._booking_id,
            "name": context.name,
            "date": context.date.strftime("%A, %B %d, %Y") if context.date else "N/A",
            "time": context.time.strftime("%I:%M %p") if context.time else "N/A",
            "party_size": context.party_size,
            "phone": context.phone,
        }
        
        # Send SMS confirmation
        if context.phone:
            try:
                logger.info(f"Sending SMS confirmation to {context.phone}...")
                send_sms_confirmation(context.phone, booking_details)
                logger.info("✓ SMS confirmation sent")
            except SMSError as e:
                logger.error(f"Failed to send SMS confirmation: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending SMS: {e}")
        
        # Send email confirmation (if email was provided)
        # Note: email is optional in our context
        # In production, this would check if email was collected
        logger.info("Email confirmation skipped (email not collected in this flow)")
    
    def _generate_and_speak_response(
        self,
        state: str,
        context_dict: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Generate response and speak it to the user.
        
        Args:
            state: Current conversation state
            context_dict: Context dictionary for response generation
            data: Additional data for response generation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate response text
            logger.info(f"Generating response for state: {state}")
            
            if context_dict is None:
                context_obj = self._state_manager.get_context()
                context_dict = {
                    "date": context_obj.date,
                    "time": context_obj.time,
                    "party_size": context_obj.party_size,
                    "name": context_obj.name,
                    "phone": context_obj.phone,
                }
            
            try:
                response_text = generate_response(state, context=context_dict, data=data)
            except ResponseGenerationError as e:
                logger.warning(f"Response generation failed: {e}, using fallback")
                response_text = get_fallback_response(state)
            
            logger.info(f"Response generated: {response_text[:100]}...")
            
            # Convert to speech
            logger.info("Converting response to speech...")
            audio_data, sample_rate = self._tts.generate_speech(response_text)
            
            # Play audio
            logger.info("Playing response...")
            self._audio_manager.play_audio(audio_data, sample_rate)
            
            logger.info("✓ Response spoken successfully")
            return True
            
        except ElevenLabsTTSError as e:
            logger.error(f"TTS error: {e}")
            return False
        
        except AudioPlaybackError as e:
            logger.error(f"Audio playback error: {e}")
            return False
        
        except Exception as e:
            logger.error(f"Unexpected error in response generation/speaking: {e}")
            return False
    
    def run(self) -> bool:
        """
        Run the main conversation loop.
        
        Returns:
            True if booking completed successfully, False otherwise
        """
        if not self._initialized:
            logger.error("Agent not initialized. Call initialize() first.")
            return False
        
        logger.info("=" * 60)
        logger.info("Starting voice agent conversation loop")
        logger.info("=" * 60)
        
        try:
            # Play greeting
            logger.info("Playing initial greeting...")
            greeting = self._generate_greeting()
            audio_data, sample_rate = self._tts.generate_speech(greeting)
            self._audio_manager.play_audio(audio_data, sample_rate)
            
            # Transition to collecting information
            self._state_manager.transition_to(ConversationState.COLLECTING_DATE)
            
            # Main conversation loop
            while not self._should_exit:
                current_state = self._state_manager.get_current_state()
                logger.info(f"\n--- Loop iteration | state: {current_state} ---")
                
                # Check if conversation is complete
                if current_state == ConversationState.COMPLETED:
                    logger.info("Conversation completed successfully")
                    return True
                
                # Listen for user input
                audio_result = self._listen_for_input()
                
                if audio_result is None:
                    # Timeout or no input
                    self._timeout_count += 1
                    logger.warning(f"No input received (timeout count: {self._timeout_count})")
                    
                    if self._timeout_count >= 2:
                        # Extended timeout - end call
                        logger.info("Multiple timeouts, ending call")
                        self._generate_and_speak_response("goodbye")
                        break
                    else:
                        # First timeout - prompt user
                        self._generate_and_speak_response(
                            "clarification",
                            data={"clarification_needed": "a response"}
                        )
                        continue
                
                # Reset timeout counter on successful input
                self._timeout_count = 0
                audio_data, sample_rate = audio_result
                
                # Transcribe audio
                utterance = self._transcribe_audio(audio_data, sample_rate)
                
                if not utterance or utterance.strip() == "":
                    logger.warning("Empty transcription, asking for clarification")
                    self._generate_and_speak_response(
                        "clarification",
                        data={"clarification_needed": "what you said"}
                    )
                    continue
                
                # Check for exit keywords
                exit_keywords = ["cancel", "goodbye", "exit", "quit", "stop", "nevermind"]
                if any(keyword in utterance.lower() for keyword in exit_keywords):
                    logger.info(f"Exit keyword detected in: '{utterance}'")
                    self._generate_and_speak_response("goodbye")
                    break
                
                # Process utterance
                processing_result = self._process_utterance(utterance)
                
                # Determine next action
                next_action = self._determine_next_action()
                logger.info(f"Next action: {next_action}")
                
                if next_action == "exit":
                    logger.info("Exit action triggered")
                    self._generate_and_speak_response("goodbye")
                    break
                
                elif next_action == "complete":
                    logger.info("Booking complete, ending conversation")
                    break
                
                elif next_action == "confirm":
                    # Generate confirmation response with all details
                    context = self._state_manager.get_context()
                    self._generate_and_speak_response(
                        "confirming",
                        data={"booking_details": {
                            "date": context.date,
                            "time": context.time,
                            "party_size": context.party_size,
                            "name": context.name,
                            "phone": context.phone,
                        }}
                    )
                    
                    # Listen for confirmation
                    audio_result = self._listen_for_input()
                    if audio_result:
                        audio_data, sample_rate = audio_result
                        confirmation_utterance = self._transcribe_audio(audio_data, sample_rate)
                        
                        # Check for confirmation keywords
                        confirm_keywords = ["yes", "correct", "confirm", "right", "yep", "yeah"]
                        is_confirmed = any(
                            keyword in confirmation_utterance.lower()
                            for keyword in confirm_keywords
                        )
                        
                        if is_confirmed:
                            # Create booking
                            booking_id = self._create_booking()
                            
                            if booking_id:
                                # Send confirmations
                                self._send_confirmations()
                                
                                # Transition to completed
                                self._state_manager.transition_to(ConversationState.COMPLETED)
                                
                                # Generate completion message
                                self._generate_and_speak_response("completed")
                                
                                logger.info("✓ Booking flow completed successfully")
                                return True
                            else:
                                # Booking creation failed
                                logger.error("Booking creation failed")
                                self._generate_and_speak_response(
                                    "no_availability",
                                    data={"alternatives": "Please try a different time or call us directly"}
                                )
                                break
                        else:
                            # User did not confirm
                            logger.info("User did not confirm booking")
                            self._handle_confirmation(False)
                            self._generate_and_speak_response("collecting_date")
                    
                elif next_action == "collect_info":
                    # Generate appropriate response based on current state
                    current_state = self._state_manager.get_current_state()
                    state_str = str(current_state)
                    
                    # If we got multiple pieces of info, acknowledge them
                    if len(processing_result.get("updates", {})) > 1:
                        self._generate_and_speak_response("acknowledge_multiple_info")
                    
                    # Generate next question
                    self._generate_and_speak_response(state_str)
            
            logger.info("Conversation loop ended")
            return False
            
        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt received")
            self._generate_and_speak_response("goodbye")
            return False
        
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            return False
        
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """
        Clean shutdown: close audio streams, DB connections, log session.
        """
        logger.info("Shutting down VoiceAgent...")
        
        try:
            # Stop any active recording
            if self._audio_manager and self._audio_manager._recording:
                try:
                    self._audio_manager.stop_recording()
                except Exception as e:
                    logger.warning(f"Error stopping recording: {e}")
            
            # Close database session
            if self._session:
                try:
                    self._session.close()
                    logger.info("Database session closed")
                except Exception as e:
                    logger.warning(f"Error closing database session: {e}")
            
            # Log session summary
            if self._booking_id:
                logger.info(f"Session completed with booking ID: {self._booking_id}")
            else:
                logger.info("Session ended without booking")
            
            logger.info("✓ VoiceAgent shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


@contextmanager
def create_voice_agent(**kwargs):
    """
    Context manager for VoiceAgent lifecycle.
    
    Usage:
        with create_voice_agent() as agent:
            agent.initialize()
            success = agent.run()
    """
    agent = VoiceAgent(**kwargs)
    try:
        yield agent
    finally:
        agent.shutdown()
