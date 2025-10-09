"""
Timeout management for user interactions in the voice booking system.

This module handles:
- User response timeouts
- Silence detection
- Re-prompting logic
- Conversation abandonment
"""
import time
from typing import Optional, Callable
from datetime import datetime, timedelta
from loguru import logger

from .exceptions import UserTimeoutError, SilenceDetectedError


class TimeoutManager:
    """
    Manages timeouts for user interactions.
    
    Tracks when user was last heard from and triggers appropriate
    error handling when timeouts occur.
    """
    
    def __init__(
        self,
        initial_timeout_seconds: int = 10,
        reprompt_timeout_seconds: int = 15,
        max_reprompts: int = 2,
        abandonment_timeout_seconds: int = 60
    ):
        """
        Initialize timeout manager.
        
        Args:
            initial_timeout_seconds: Timeout for first response
            reprompt_timeout_seconds: Timeout after re-prompting
            max_reprompts: Maximum number of re-prompts before giving up
            abandonment_timeout_seconds: Time before considering conversation abandoned
        """
        self.initial_timeout = initial_timeout_seconds
        self.reprompt_timeout = reprompt_timeout_seconds
        self.max_reprompts = max_reprompts
        self.abandonment_timeout = abandonment_timeout_seconds
        
        self.last_activity_time: Optional[datetime] = None
        self.prompt_count = 0
        self.total_timeouts = 0
        self.conversation_start_time = datetime.now()
    
    def reset(self) -> None:
        """Reset timeout tracking for new conversation."""
        self.last_activity_time = datetime.now()
        self.prompt_count = 0
        self.total_timeouts = 0
        self.conversation_start_time = datetime.now()
        logger.debug("Timeout manager reset")
    
    def mark_activity(self) -> None:
        """Mark that user activity was detected."""
        self.last_activity_time = datetime.now()
        self.prompt_count = 0  # Reset prompt count on activity
        logger.debug("User activity detected, timeout reset")
    
    def mark_prompt(self) -> None:
        """Mark that a prompt was sent to user."""
        self.prompt_count += 1
        self.last_activity_time = datetime.now()
        logger.debug(f"Prompt sent to user (count: {self.prompt_count})")
    
    def check_timeout(self, raise_on_timeout: bool = True) -> bool:
        """
        Check if user has timed out.
        
        Args:
            raise_on_timeout: If True, raise UserTimeoutError on timeout
            
        Returns:
            True if timed out, False otherwise
            
        Raises:
            UserTimeoutError: If timeout occurred and raise_on_timeout=True
        """
        if self.last_activity_time is None:
            # No activity yet
            return False
        
        elapsed = (datetime.now() - self.last_activity_time).total_seconds()
        
        # Determine timeout threshold based on prompt count
        if self.prompt_count == 0:
            timeout_threshold = self.initial_timeout
        else:
            timeout_threshold = self.reprompt_timeout
        
        # Check if timed out
        if elapsed > timeout_threshold:
            self.total_timeouts += 1
            logger.warning(
                f"User timeout detected: {elapsed:.1f}s elapsed, "
                f"threshold: {timeout_threshold}s, "
                f"prompt count: {self.prompt_count}"
            )
            
            if raise_on_timeout:
                raise UserTimeoutError(
                    message=f"User timeout after {elapsed:.1f}s",
                    timeout_seconds=int(elapsed),
                    prompt_count=self.prompt_count
                )
            
            return True
        
        return False
    
    def should_reprompt(self) -> bool:
        """
        Check if we should re-prompt the user.
        
        Returns:
            True if should re-prompt, False if should give up
        """
        return self.prompt_count < self.max_reprompts
    
    def should_abandon(self) -> bool:
        """
        Check if conversation should be abandoned due to inactivity.
        
        Returns:
            True if should abandon conversation
        """
        if self.last_activity_time is None:
            return False
        
        elapsed = (datetime.now() - self.last_activity_time).total_seconds()
        return elapsed > self.abandonment_timeout
    
    def get_reprompt_message(self) -> str:
        """
        Get appropriate re-prompt message based on timeout count.
        
        Returns:
            Re-prompt message string
        """
        if self.prompt_count == 1:
            return "Are you still there? I haven't heard from you."
        elif self.prompt_count == 2:
            return "I'm still here when you're ready. Just let me know if you'd like to continue."
        else:
            return "I haven't heard from you in a while. I'll end this call now, but feel free to call back anytime to make your reservation. Goodbye!"
    
    def get_statistics(self) -> dict:
        """Get timeout statistics."""
        session_duration = (datetime.now() - self.conversation_start_time).total_seconds()
        
        return {
            "session_duration": session_duration,
            "total_timeouts": self.total_timeouts,
            "current_prompt_count": self.prompt_count,
            "last_activity": self.last_activity_time.isoformat() if self.last_activity_time else None,
            "seconds_since_activity": (datetime.now() - self.last_activity_time).total_seconds() if self.last_activity_time else None
        }


class SilenceDetector:
    """
    Detects silence or unclear audio in user input.
    
    Works with audio data to determine if user actually spoke.
    """
    
    def __init__(
        self,
        silence_threshold_db: float = -40.0,
        min_speech_duration: float = 0.5,
        max_silence_duration: float = 5.0
    ):
        """
        Initialize silence detector.
        
        Args:
            silence_threshold_db: Threshold in dB for considering audio as silence
            min_speech_duration: Minimum duration (seconds) to consider as speech
            max_silence_duration: Maximum silence before raising error
        """
        self.silence_threshold_db = silence_threshold_db
        self.min_speech_duration = min_speech_duration
        self.max_silence_duration = max_silence_duration
    
    def check_silence(
        self,
        audio_data,
        sample_rate: int,
        raise_on_silence: bool = True
    ) -> bool:
        """
        Check if audio data contains only silence.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of audio
            raise_on_silence: If True, raise SilenceDetectedError on silence
            
        Returns:
            True if silence detected, False otherwise
            
        Raises:
            SilenceDetectedError: If silence detected and raise_on_silence=True
        """
        import numpy as np
        
        if audio_data is None or len(audio_data) == 0:
            if raise_on_silence:
                raise SilenceDetectedError(
                    message="No audio data captured",
                    duration=0.0
                )
            return True
        
        # Calculate audio duration
        duration = len(audio_data) / sample_rate
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_data.astype(float) ** 2))
        
        # Convert to dB
        if rms > 0:
            db = 20 * np.log10(rms)
        else:
            db = -100  # Very quiet
        
        logger.debug(f"Audio check: duration={duration:.2f}s, energy={db:.1f}dB")
        
        # Check if below silence threshold
        if db < self.silence_threshold_db:
            logger.warning(f"Silence detected: {db:.1f}dB < {self.silence_threshold_db}dB")
            
            if raise_on_silence:
                raise SilenceDetectedError(
                    message=f"Audio energy too low: {db:.1f}dB",
                    duration=duration
                )
            
            return True
        
        # Check if duration is too short
        if duration < self.min_speech_duration:
            logger.warning(f"Audio too short: {duration:.2f}s < {self.min_speech_duration}s")
            
            if raise_on_silence:
                raise SilenceDetectedError(
                    message=f"Audio duration too short: {duration:.2f}s",
                    duration=duration
                )
            
            return True
        
        return False


def with_user_timeout(
    timeout_manager: TimeoutManager,
    on_timeout: Optional[Callable] = None
):
    """
    Decorator for functions that wait for user input.
    
    Args:
        timeout_manager: TimeoutManager instance to use
        on_timeout: Optional callback function to call on timeout
        
    Returns:
        Decorated function with timeout handling
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Mark that we're waiting for user input
            timeout_manager.mark_prompt()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Mark activity received
                timeout_manager.mark_activity()
                
                return result
                
            except UserTimeoutError as e:
                logger.warning(f"User timeout in {func.__name__}: {e}")
                
                # Call timeout handler if provided
                if on_timeout:
                    return on_timeout(e)
                
                # Otherwise re-raise
                raise
        
        return wrapper
    return decorator
