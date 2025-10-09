"""
AudioManager - Handles audio recording, playback, and processing.
"""
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import sounddevice as sd
import soundfile as sf
from loguru import logger

from .config import AudioConfig, DEFAULT_CONFIG

 # Import centralized error handling
import sys
sys.path.insert(0, '..')
from error_handling.exceptions import (
    AudioProcessingError,
    SilenceDetectedError,
    UnclearAudioError
)
from error_handling.handlers import log_function_call, with_retry
 
# Import error handling
try:
    from ..error_handling.exceptions import (
        AudioProcessingError,
        TranscriptionError,
        UserTimeoutError,
    )
    from ..error_handling.handlers import log_error_with_context
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    # Fallback if error handling not available yet
    ERROR_HANDLING_AVAILABLE = False
    AudioProcessingError = Exception
    TranscriptionError = Exception
    UserTimeoutError = Exception
 

# Legacy exception aliases for backward compatibility
AudioDeviceError = AudioProcessingError
AudioRecordingError = AudioProcessingError
AudioPlaybackError = AudioProcessingError


class AudioManager:
    """
    Manages audio recording, playback, and processing operations.
    
    Features:
    - Microphone recording with configurable parameters
    - Speaker playback for audio files
    - Voice activity detection (silence detection)
    - Audio format conversions
    - Temporary WAV file management
    - Context manager support for proper resource cleanup
    
    Example:
        with AudioManager() as audio:
            audio.start_recording()
            time.sleep(3)
            audio_data, sample_rate = audio.stop_recording()
            audio.play_audio(audio_data, sample_rate)
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize AudioManager.
        
        Args:
            config: Audio configuration. If None, uses default configuration.
        
        Raises:
            AudioDeviceError: If no audio devices are available.
        """
        self.config = config or DEFAULT_CONFIG
        self._recording = False
        self._stream: Optional[sd.InputStream] = None
        self._audio_buffer: list = []
        self._temp_files: list[Path] = []
        
        # Create temp directory if it doesn't exist
        self._temp_dir = Path(self.config.temp_dir)
        self._temp_dir.mkdir(exist_ok=True)
        
        # Verify audio devices are available
        self._check_audio_devices()
        
        logger.info(f"AudioManager initialized with sample_rate={self.config.sample_rate}Hz, "
                   f"channels={self.config.channels}, bit_depth={self.config.bit_depth}")
    
    def _check_audio_devices(self) -> None:
        """
        Check if audio devices are available.
        
        Raises:
            AudioProcessingError: If no input or output devices are found.
        """
        try:
            devices = sd.query_devices()
            if devices is None or len(devices) == 0:
                raise AudioProcessingError(
                    message="No audio devices found",
                    user_message="I'm having trouble accessing audio devices. Please check your microphone and speaker connections.",
                    audio_type="device",
                    recoverable=False
                )
            
            # Check for input device
            input_device = sd.query_devices(kind='input')
            if input_device is None:
                raise AudioProcessingError(
                    message="No input (microphone) device found",
                    user_message="I can't access your microphone. Please check your microphone connection and permissions.",
                    audio_type="recording",
                    recoverable=False
                )
            
            # Check for output device
            output_device = sd.query_devices(kind='output')
            if output_device is None:
                raise AudioProcessingError(
                    message="No output (speaker) device found",
                    user_message="I can't access your speakers. Please check your speaker connection.",
                    audio_type="playback",
                    recoverable=False
                )
            
            logger.debug(f"Input device: {input_device['name']}")
            logger.debug(f"Output device: {output_device['name']}")
            
        except Exception as e:
            if isinstance(e, AudioProcessingError):
                raise
            raise AudioProcessingError(
                message=f"Failed to query audio devices: {str(e)}",
                user_message="I'm having trouble accessing audio devices. Please check your audio setup.",
                audio_type="device",
                recoverable=False
            )
    
    @log_function_call
    def start_recording(self) -> None:
        """
        Start recording audio from the default microphone.
        
        Raises:
            AudioProcessingError: If recording is already in progress or fails to start.
        """
        if self._recording:
            raise AudioProcessingError(
                message="Recording already in progress",
                user_message="I'm already recording. Please finish the current recording first.",
                audio_type="recording"
            )
        
        try:
            self._audio_buffer = []
            self._recording = True
            
            logger.info("Starting audio recording...")
            
            # Create input stream
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                blocksize=self.config.chunk_size,
                callback=self._audio_callback
            )
            
            self._stream.start()
            logger.info("Audio recording started successfully")
            
        except sd.PortAudioError as e:
            self._recording = False
            self._stream = None
            logger.error(f"Failed to start recording: {str(e)}")
            raise AudioProcessingError(
                message=f"Microphone not accessible: {str(e)}",
                user_message="I can't access your microphone. Please check your microphone permissions and connection.",
                audio_type="recording",
                recoverable=False
            )
        except Exception as e:
            self._recording = False
            self._stream = None
            logger.error(f"Unexpected error during recording start: {str(e)}")
            raise AudioProcessingError(
                message=f"Failed to start recording: {str(e)}",
                user_message="I'm having trouble starting the recording. Please try again.",
                audio_type="recording"
            )
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """
        Callback function for audio stream.
        
        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Time information
            status: Stream status
        """
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        if self._recording:
            # Copy audio data to buffer
            self._audio_buffer.append(indata.copy())
    
    @log_function_call
    def stop_recording(self) -> Tuple[np.ndarray, int]:
        """
        Stop recording and return the captured audio data.
        
        Returns:
            Tuple of (audio_data, sample_rate) where audio_data is numpy array
        
        Raises:
            AudioProcessingError: If no recording is in progress.
            SilenceDetectedError: If no audio was captured.
        """
        if not self._recording:
            raise AudioProcessingError(
                message="No recording in progress",
                user_message="I'm not currently recording. Please start recording first.",
                audio_type="recording"
            )
        
        try:
            self._recording = False
            
            # Stop and close stream
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            # Concatenate audio buffer
            if not self._audio_buffer:
                logger.warning("No audio data captured")
                raise SilenceDetectedError(
                    message="No audio data captured",
                    duration=0.0
                )
            
            audio_data = np.concatenate(self._audio_buffer, axis=0)
            
            # Check for silence
            duration = len(audio_data) / self.config.sample_rate
            if duration < 0.1:  # Less than 100ms
                logger.warning(f"Very short audio captured: {duration:.3f}s")
                raise SilenceDetectedError(
                    message=f"Audio too short: {duration:.3f}s",
                    duration=duration
                )
            
            # Check audio energy level
            rms = np.sqrt(np.mean(audio_data.astype(float) ** 2))
            if rms < 10:  # Very low energy
                logger.warning(f"Very low audio energy: {rms:.2f}")
                raise UnclearAudioError(
                    message=f"Audio energy too low: {rms:.2f}",
                    confidence_score=0.0
                )
            
            logger.info(f"Recording stopped. Captured {len(audio_data)} samples "
                       f"({duration:.2f} seconds, RMS={rms:.2f})")
            
            return audio_data, self.config.sample_rate
            
        except (SilenceDetectedError, UnclearAudioError):
            raise
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
            raise AudioProcessingError(
                message=f"Failed to stop recording: {str(e)}",
                user_message="I had trouble processing the recording. Please try again.",
                audio_type="recording"
            )
    
    @log_function_call
    @with_retry(max_attempts=2, delay=0.5, exceptions=(sd.PortAudioError,))
    def play_audio(self, audio_data: np.ndarray, sample_rate: Optional[int] = None) -> None:
        """
        Play audio data through the default speaker.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate in Hz. If None, uses config sample rate.
        
        Raises:
            AudioProcessingError: If playback fails.
        """
        if sample_rate is None:
            sample_rate = self.config.sample_rate
        
        if audio_data is None or len(audio_data) == 0:
            logger.warning("Attempted to play empty audio")
            raise AudioProcessingError(
                message="Cannot play empty audio",
                user_message="I don't have any audio to play.",
                audio_type="playback"
            )
        
        try:
            logger.info(f"Playing audio: {len(audio_data)} samples at {sample_rate}Hz")
            
            # Play audio and wait for completion
            sd.play(audio_data, sample_rate)
            sd.wait()
            
            logger.info("Audio playback completed")
            
        except sd.PortAudioError as e:
            logger.error(f"Failed to play audio: {str(e)}")
            raise AudioProcessingError(
                message=f"Speaker not accessible: {str(e)}",
                user_message="I can't access your speakers. Please check your speaker connection.",
                audio_type="playback",
                recoverable=False
            )
        except Exception as e:
            logger.error(f"Unexpected error during playback: {str(e)}")
            raise AudioProcessingError(
                message=f"Failed to play audio: {str(e)}",
                user_message="I'm having trouble playing the audio. Please check your speakers.",
                audio_type="playback"
            )
    
    def detect_silence(
        self,
        threshold: Optional[float] = None,
        duration: Optional[float] = None
    ) -> bool:
        """
        Detect if the current audio buffer ends with silence.
        
        Args:
            threshold: Silence threshold in dB. If None, uses config value.
            duration: Minimum silence duration in seconds. If None, uses config value.
        
        Returns:
            True if silence is detected for the specified duration, False otherwise.
        """
        if threshold is None:
            threshold = self.config.silence_threshold
        if duration is None:
            duration = self.config.silence_duration
        
        if not self._audio_buffer or len(self._audio_buffer) == 0:
            return False
        
        # Calculate required number of samples for silence duration
        required_samples = int(duration * self.config.sample_rate)
        
        # Concatenate recent audio buffer
        audio_data = np.concatenate(self._audio_buffer, axis=0)
        
        # Check if we have enough samples
        if len(audio_data) < required_samples:
            return False
        
        # Get the last 'duration' seconds of audio
        recent_audio = audio_data[-required_samples:]
        
        # Calculate RMS (Root Mean Square) energy
        # RMS gives us the average "loudness" of the audio signal
        rms = np.sqrt(np.mean(recent_audio**2))
        
        # Avoid log(0) by adding small epsilon
        # Very quiet audio could have RMS near zero, which would cause math errors
        if rms < 1e-10:
            db_level = -100.0
        else:
            # Convert to dB scale (decibels)
            # dB = 20 * log10(amplitude), standard audio measurement
            # Typical speech is -30dB to -10dB, silence is < -40dB
            db_level = 20 * np.log10(rms)
        
        is_silent = db_level < threshold
        
        if is_silent:
            logger.debug(f"Silence detected: {db_level:.2f}dB < {threshold}dB for {duration}s")
        
        return is_silent
    
    def record_with_timeout(
        self,
        max_duration: float,
        timeout_after_silence: Optional[float] = None,
        silence_threshold: Optional[float] = None,
        silence_duration: Optional[float] = None
    ) -> Tuple[np.ndarray, int, bool]:
        """
        Record audio with timeout and automatic stopping after silence.
        
        This method is useful for recording user responses where you want to:
        1. Set a maximum recording duration
        2. Automatically stop after detecting silence (user finished speaking)
        
        Args:
            max_duration: Maximum recording duration in seconds
            timeout_after_silence: Stop recording after this many seconds of silence (optional)
            silence_threshold: Silence threshold in dB (optional)
            silence_duration: Minimum silence duration to detect (optional)
        
        Returns:
            Tuple of (audio_data, sample_rate, timed_out):
                - audio_data: Recorded audio as numpy array
                - sample_rate: Sample rate in Hz
                - timed_out: True if max_duration was reached, False if stopped by silence
        
        Raises:
            AudioRecordingError: If recording fails
            AudioDeviceError: If microphone is not accessible
        
        Example:
            >>> audio_data, rate, timed_out = audio_manager.record_with_timeout(
            ...     max_duration=30.0,  # Max 30 seconds
            ...     timeout_after_silence=3.0  # Stop after 3 seconds of silence
            ... )
            >>> if timed_out:
            ...     print("User didn't respond in time")
        """
        import time
        
        # Start recording
        self.start_recording()
        
        start_time = time.time()
        timed_out = False
        silence_start = None
        
        try:
            while True:
                # Check max duration
                elapsed = time.time() - start_time
                if elapsed >= max_duration:
                    logger.info(f"Recording reached max duration: {max_duration}s")
                    timed_out = True
                    break
                
                # Check for silence if timeout_after_silence is set
                if timeout_after_silence is not None:
                    is_silent = self.detect_silence(
                        threshold=silence_threshold,
                        duration=silence_duration
                    )
                    
                    if is_silent:
                        if silence_start is None:
                            silence_start = time.time()
                            logger.debug("Silence detected, starting timeout counter")
                        else:
                            silence_elapsed = time.time() - silence_start
                            if silence_elapsed >= timeout_after_silence:
                                logger.info(f"Recording stopped after {silence_elapsed:.1f}s of silence")
                                break
                    else:
                        # Reset silence timer if audio detected
                        if silence_start is not None:
                            logger.debug("Audio detected, resetting silence timer")
                        silence_start = None
                
                # Small sleep to avoid busy waiting
                time.sleep(0.1)
            
            # Stop recording and return audio
            audio_data, sample_rate = self.stop_recording()
            
            return audio_data, sample_rate, timed_out
            
        except Exception as e:
            # Ensure recording is stopped on error
            if self._recording:
                try:
                    self.stop_recording()
                except Exception:
                    pass
            raise
    
    def wait_for_speech(
        self,
        timeout: float = 10.0,
        speech_threshold: Optional[float] = None,
        min_speech_duration: float = 0.5
    ) -> bool:
        """
        Wait for speech to begin, with timeout.
        
        Useful for detecting when a user starts speaking after a prompt.
        
        Args:
            timeout: Maximum time to wait for speech in seconds
            speech_threshold: Energy threshold above which is considered speech (dB)
            min_speech_duration: Minimum duration of speech to confirm (seconds)
        
        Returns:
            True if speech detected, False if timeout
        
        Raises:
            AudioRecordingError: If no recording is in progress
        
        Example:
            >>> audio_manager.start_recording()
            >>> if audio_manager.wait_for_speech(timeout=10.0):
            ...     print("User started speaking")
            ... else:
            ...     print("User timeout - no speech detected")
        """
        if not self._recording:
            raise AudioRecordingError("No recording in progress")
        
        if speech_threshold is None:
            # Use inverse of silence threshold (typically -40dB)
            speech_threshold = self.config.silence_threshold + 10  # e.g., -30dB
        
        start_time = time.time()
        speech_start = None
        
        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning(f"Speech detection timed out after {timeout}s")
                return False
            
            # Need enough audio buffer to analyze
            if not self._audio_buffer or len(self._audio_buffer) == 0:
                time.sleep(0.1)
                continue
            
            # Get recent audio
            audio_data = np.concatenate(self._audio_buffer, axis=0)
            
            # Get last 0.5 seconds
            sample_size = int(0.5 * self.config.sample_rate)
            if len(audio_data) < sample_size:
                time.sleep(0.1)
                continue
            
            recent_audio = audio_data[-sample_size:]
            
            # Calculate RMS energy
            rms = np.sqrt(np.mean(recent_audio**2))
            if rms < 1e-10:
                db_level = -100.0
            else:
                db_level = 20 * np.log10(rms)
            
            # Check if speech detected
            is_speech = db_level > speech_threshold
            
            if is_speech:
                if speech_start is None:
                    speech_start = time.time()
                    logger.debug(f"Speech detected: {db_level:.2f}dB > {speech_threshold}dB")
                else:
                    speech_elapsed = time.time() - speech_start
                    if speech_elapsed >= min_speech_duration:
                        logger.info(f"Speech confirmed after {speech_elapsed:.2f}s")
                        return True
            else:
                # Reset if silence detected
                speech_start = None
            
            time.sleep(0.1)
    
    def convert_sample_rate(
        self,
        audio_data: np.ndarray,
        original_rate: int,
        target_rate: int
    ) -> np.ndarray:
        """
        Convert audio sample rate using simple resampling.
        
        Args:
            audio_data: Input audio data
            original_rate: Original sample rate
            target_rate: Target sample rate
        
        Returns:
            Resampled audio data
        """
        if original_rate == target_rate:
            return audio_data
        
        logger.debug(f"Converting sample rate: {original_rate}Hz -> {target_rate}Hz")
        
        # Calculate resampling ratio
        ratio = target_rate / original_rate
        
        # Calculate new length
        new_length = int(len(audio_data) * ratio)
        
        # Simple linear interpolation resampling
        # We create new sample points evenly distributed across the original data
        # np.interp then fills in values using linear interpolation
        # This is faster than FFT-based resampling but lower quality (acceptable for speech)
        indices = np.linspace(0, len(audio_data) - 1, new_length)
        
        if audio_data.ndim == 1:
            resampled = np.interp(indices, np.arange(len(audio_data)), audio_data)
        else:
            # Handle multi-channel audio
            resampled = np.zeros((new_length, audio_data.shape[1]), dtype=audio_data.dtype)
            for channel in range(audio_data.shape[1]):
                resampled[:, channel] = np.interp(
                    indices,
                    np.arange(len(audio_data)),
                    audio_data[:, channel]
                )
        
        return resampled
    
    def convert_channels(
        self,
        audio_data: np.ndarray,
        target_channels: int
    ) -> np.ndarray:
        """
        Convert audio channel count (mono/stereo conversion).
        
        Args:
            audio_data: Input audio data
            target_channels: Target number of channels (1=mono, 2=stereo)
        
        Returns:
            Converted audio data
        """
        if audio_data.ndim == 1:
            current_channels = 1
        else:
            current_channels = audio_data.shape[1]
        
        if current_channels == target_channels:
            return audio_data
        
        logger.debug(f"Converting channels: {current_channels} -> {target_channels}")
        
        if target_channels == 1 and current_channels == 2:
            # Stereo to mono: average channels
            # Taking the mean of left and right channels preserves audio balance
            return np.mean(audio_data, axis=1)
        elif target_channels == 2 and current_channels == 1:
            # Mono to stereo: duplicate channel
            # Create identical left and right channels for stereo output
            return np.column_stack([audio_data, audio_data])
        else:
            raise ValueError(f"Unsupported channel conversion: {current_channels} -> {target_channels}")
    
    def save_to_wav(
        self,
        audio_data: np.ndarray,
        sample_rate: Optional[int] = None,
        filename: Optional[str] = None
    ) -> Path:
        """
        Save audio data to a WAV file.
        
        Args:
            audio_data: Audio data to save
            sample_rate: Sample rate in Hz. If None, uses config sample rate.
            filename: Output filename. If None, generates unique temporary filename.
        
        Returns:
            Path to the saved WAV file
        
        Raises:
            IOError: If file write fails
        """
        if sample_rate is None:
            sample_rate = self.config.sample_rate
        
        try:
            if filename is None:
                # Generate unique temporary filename
                unique_id = uuid.uuid4().hex[:8]
                timestamp = int(time.time())
                filename = f"recording_{timestamp}_{unique_id}.wav"
            
            filepath = self._temp_dir / filename
            
            # Save audio using soundfile
            sf.write(filepath, audio_data, sample_rate)
            
            # Track temp file for cleanup
            self._temp_files.append(filepath)
            
            logger.info(f"Audio saved to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save audio file: {str(e)}")
            raise IOError(f"Failed to save WAV file: {str(e)}")
    
    def load_from_wav(self, filepath: str | Path) -> Tuple[np.ndarray, int]:
        """
        Load audio data from a WAV file.
        
        Args:
            filepath: Path to WAV file
        
        Returns:
            Tuple of (audio_data, sample_rate)
        
        Raises:
            IOError: If file read fails
        """
        try:
            filepath = Path(filepath)
            logger.info(f"Loading audio from {filepath}")
            
            audio_data, sample_rate = sf.read(filepath)
            
            logger.debug(f"Loaded audio: {len(audio_data)} samples at {sample_rate}Hz")
            return audio_data, sample_rate
            
        except Exception as e:
            logger.error(f"Failed to load audio file: {str(e)}")
            raise IOError(f"Failed to load WAV file: {str(e)}")
    
    def cleanup(self) -> None:
        """
        Clean up resources and temporary files.
        """
        # Stop recording if in progress
        if self._recording:
            try:
                self.stop_recording()
            except Exception as e:
                logger.warning(f"Error stopping recording during cleanup: {str(e)}")
        
        # Delete temporary files
        for filepath in self._temp_files:
            try:
                if filepath.exists():
                    filepath.unlink()
                    logger.debug(f"Deleted temp file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {filepath}: {str(e)}")
        
        self._temp_files.clear()
        logger.info("AudioManager cleanup completed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.cleanup()
        return False
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during destruction
    
    # ========================================================================
    # Enhanced Error Handling Methods
    # ========================================================================
    
    def wait_for_speech(
        self,
        timeout: float = 10.0,
        silence_threshold: Optional[float] = None,
        silence_duration: float = 1.5
    ) -> bool:
        """
        Wait for user to speak with timeout detection.
        
        This method records audio and waits for speech activity.
        Returns True if speech detected, False if timeout occurred.
        
        Args:
            timeout: Maximum time to wait in seconds
            silence_threshold: Silence detection threshold in dB
            silence_duration: Minimum silence duration to consider speech ended
            
        Returns:
            True if speech detected, False if timeout
            
        Raises:
            UserTimeoutError: If user doesn't speak within timeout
            AudioRecordingError: If recording fails
        """
        try:
            self.start_recording()
            start_time = time.time()
            
            # Wait for speech or timeout
            while time.time() - start_time < timeout:
                time.sleep(0.1)
                
                # Check if we have audio data
                if self._audio_buffer and len(self._audio_buffer) > 0:
                    # Check if silence is detected (meaning speech has occurred and ended)
                    if self.detect_silence(silence_threshold, silence_duration):
                        self.stop_recording()
                        logger.info(f"Speech detected and completed in {time.time() - start_time:.2f}s")
                        return True
            
            # Timeout occurred
            self.stop_recording()
            
            # Check if any audio was captured
            if not self._audio_buffer or len(self._audio_buffer) == 0:
                logger.warning(f"User timeout: No speech detected in {timeout}s")
                
                if ERROR_HANDLING_AVAILABLE:
                    raise UserTimeoutError(
                        f"No speech detected within {timeout} seconds",
                        user_message="I didn't hear anything. Are you still there?",
                        timeout_seconds=int(timeout)
                    )
                else:
                    return False
            
            return False
            
        except AudioRecordingError:
            raise
        except Exception as e:
            logger.error(f"Error waiting for speech: {str(e)}")
            if ERROR_HANDLING_AVAILABLE:
                raise AudioProcessingError(
                    f"Failed to wait for speech: {str(e)}",
                    user_message="I'm having trouble with my audio system.",
                    audio_type="recording",
                    original_error=e
                )
            else:
                raise AudioRecordingError(f"Failed to wait for speech: {str(e)}")
    
    def record_with_timeout(
        self,
        duration: float = 5.0,
        detect_silence: bool = True,
        silence_threshold: Optional[float] = None,
        silence_duration: float = 1.0
    ) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """
        Record audio with automatic timeout and silence detection.
        
        Args:
            duration: Maximum recording duration in seconds
            detect_silence: Whether to stop recording on silence detection
            silence_threshold: Silence threshold in dB (None = use config)
            silence_duration: Minimum silence duration to stop (seconds)
            
        Returns:
            Tuple of (audio_data, sample_rate) or (None, None) if timeout/no audio
            
        Raises:
            AudioProcessingError: If recording fails
        """
        try:
            self.start_recording()
            start_time = time.time()
            
            while time.time() - start_time < duration:
                time.sleep(0.1)
                
                # Check for silence if enabled
                if detect_silence and self._audio_buffer:
                    if self.detect_silence(silence_threshold, silence_duration):
                        logger.info(f"Silence detected, stopping recording after {time.time() - start_time:.2f}s")
                        break
            
            audio_data, sample_rate = self.stop_recording()
            
            # Check if any meaningful audio was captured
            if len(audio_data) < int(0.1 * sample_rate):  # Less than 0.1 seconds
                logger.warning("Insufficient audio captured (likely silence)")
                
                if ERROR_HANDLING_AVAILABLE:
                    raise TranscriptionError(
                        "Insufficient audio captured",
                        user_message="I didn't catch that clearly. Could you repeat that?",
                        reason="silence"
                    )
                else:
                    return None, None
            
            return audio_data, sample_rate
            
        except (AudioRecordingError, AudioDeviceError):
            raise
        except Exception as e:
            logger.error(f"Error recording with timeout: {str(e)}")
            if ERROR_HANDLING_AVAILABLE:
                raise AudioProcessingError(
                    f"Failed to record audio: {str(e)}",
                    user_message="I'm having trouble recording audio.",
                    audio_type="recording",
                    original_error=e
                )
            else:
                raise AudioRecordingError(f"Failed to record audio: {str(e)}")
    
    def is_silent_audio(
        self,
        audio_data: np.ndarray,
        threshold: Optional[float] = None
    ) -> bool:
        """
        Check if audio data is silent (contains no speech).
        
        Args:
            audio_data: Audio data to check
            threshold: Silence threshold in dB (None = use config)
            
        Returns:
            True if audio is silent, False otherwise
        """
        if threshold is None:
            threshold = self.config.silence_threshold
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_data**2))
        
        # Avoid log(0)
        if rms < 1e-10:
            return True
        
        # Convert to dB
        db_level = 20 * np.log10(rms)
        
        return db_level < threshold
