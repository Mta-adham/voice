"""
AudioManager - Handles audio recording, playback, and processing.
"""
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import sounddevice as sd
import soundfile as sf
from loguru import logger

from .config import AudioConfig, DEFAULT_CONFIG

# Import error handling exceptions
try:
    from ..error_handling.exceptions import (
        AudioDeviceError,
        AudioRecordingError,
        AudioPlaybackError,
        SilenceDetectedError,
        UserTimeoutError,
    )
except ImportError:
    # Fallback to local exceptions if error_handling not available
    class AudioDeviceError(Exception):
        """Raised when audio device is not available or lacks permissions."""
        pass

    class AudioRecordingError(Exception):
        """Raised when audio recording fails."""
        pass

    class AudioPlaybackError(Exception):
        """Raised when audio playback fails."""
        pass

    class SilenceDetectedError(Exception):
        """Raised when only silence is detected."""
        pass

    class UserTimeoutError(Exception):
        """Raised when user does not respond."""
        pass


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
        
        # Timeout tracking
        self._recording_start_time: Optional[datetime] = None
        self._last_speech_time: Optional[datetime] = None
        self._timeout_seconds: float = 10.0  # Default user timeout
        
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
            AudioDeviceError: If no input or output devices are found.
        """
        try:
            devices = sd.query_devices()
            if devices is None or len(devices) == 0:
                raise AudioDeviceError("No audio devices found")
            
            # Check for input device
            input_device = sd.query_devices(kind='input')
            if input_device is None:
                raise AudioDeviceError("No input (microphone) device found")
            
            # Check for output device
            output_device = sd.query_devices(kind='output')
            if output_device is None:
                raise AudioDeviceError("No output (speaker) device found")
            
            logger.debug(f"Input device: {input_device['name']}")
            logger.debug(f"Output device: {output_device['name']}")
            
        except Exception as e:
            if isinstance(e, AudioDeviceError):
                raise
            raise AudioDeviceError(f"Failed to query audio devices: {str(e)}")
    
    def start_recording(self, timeout_seconds: Optional[float] = None) -> None:
        """
        Start recording audio from the default microphone.
        
        Args:
            timeout_seconds: Maximum recording duration before timeout (None for no limit)
        
        Raises:
            AudioRecordingError: If recording is already in progress or fails to start.
            AudioDeviceError: If microphone is not accessible.
        """
        if self._recording:
            raise AudioRecordingError("Recording already in progress")
        
        try:
            self._audio_buffer = []
            self._recording = True
            self._recording_start_time = datetime.now()
            self._last_speech_time = None
            
            if timeout_seconds is not None:
                self._timeout_seconds = timeout_seconds
            
            logger.info(f"Starting audio recording (timeout: {self._timeout_seconds}s)...")
            
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
            raise AudioDeviceError(f"Microphone not accessible: {str(e)}")
        except Exception as e:
            self._recording = False
            self._stream = None
            logger.error(f"Unexpected error during recording start: {str(e)}")
            raise AudioRecordingError(f"Failed to start recording: {str(e)}")
    
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
    
    def stop_recording(self) -> Tuple[np.ndarray, int]:
        """
        Stop recording and return the captured audio data.
        
        Returns:
            Tuple of (audio_data, sample_rate) where audio_data is numpy array
        
        Raises:
            AudioRecordingError: If no recording is in progress.
        """
        if not self._recording:
            raise AudioRecordingError("No recording in progress")
        
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
                audio_data = np.array([], dtype=self.config.dtype)
            else:
                audio_data = np.concatenate(self._audio_buffer, axis=0)
            
            logger.info(f"Recording stopped. Captured {len(audio_data)} samples "
                       f"({len(audio_data) / self.config.sample_rate:.2f} seconds)")
            
            return audio_data, self.config.sample_rate
            
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
            raise AudioRecordingError(f"Failed to stop recording: {str(e)}")
    
    def play_audio(self, audio_data: np.ndarray, sample_rate: Optional[int] = None) -> None:
        """
        Play audio data through the default speaker.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate in Hz. If None, uses config sample rate.
        
        Raises:
            AudioPlaybackError: If playback fails.
            AudioDeviceError: If speaker is not accessible.
        """
        if sample_rate is None:
            sample_rate = self.config.sample_rate
        
        try:
            logger.info(f"Playing audio: {len(audio_data)} samples at {sample_rate}Hz")
            
            # Play audio and wait for completion
            sd.play(audio_data, sample_rate)
            sd.wait()
            
            logger.info("Audio playback completed")
            
        except sd.PortAudioError as e:
            logger.error(f"Failed to play audio: {str(e)}")
            raise AudioDeviceError(f"Speaker not accessible: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during playback: {str(e)}")
            raise AudioPlaybackError(f"Failed to play audio: {str(e)}")
    
    def check_user_timeout(self) -> Tuple[bool, float]:
        """
        Check if user has timed out (no response for too long).
        
        Returns:
            Tuple of (is_timeout, elapsed_seconds)
        """
        if not self._recording or self._recording_start_time is None:
            return False, 0.0
        
        elapsed = (datetime.now() - self._recording_start_time).total_seconds()
        is_timeout = elapsed >= self._timeout_seconds
        
        if is_timeout:
            logger.warning(f"User timeout detected: {elapsed:.1f}s elapsed")
        
        return is_timeout, elapsed
    
    def has_speech_activity(self, threshold: Optional[float] = None) -> bool:
        """
        Check if there is speech activity in the current buffer.
        
        Args:
            threshold: RMS threshold for speech detection
        
        Returns:
            True if speech detected, False otherwise
        """
        if not self._audio_buffer:
            return False
        
        if threshold is None:
            threshold = -40  # Default speech threshold in dB
        
        # Get recent audio
        audio_data = np.concatenate(self._audio_buffer[-10:], axis=0) if len(self._audio_buffer) >= 10 else np.concatenate(self._audio_buffer, axis=0)
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        if rms < 1e-10:
            return False
        
        db_level = 20 * np.log10(rms)
        has_speech = db_level > threshold
        
        if has_speech:
            self._last_speech_time = datetime.now()
        
        return has_speech
    
    def get_silence_duration(self) -> float:
        """
        Get duration of silence since last speech activity.
        
        Returns:
            Silence duration in seconds
        """
        if self._last_speech_time is None:
            # No speech detected yet
            if self._recording_start_time:
                return (datetime.now() - self._recording_start_time).total_seconds()
            return 0.0
        
        return (datetime.now() - self._last_speech_time).total_seconds()
    
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
        rms = np.sqrt(np.mean(recent_audio**2))
        
        # Avoid log(0) by adding small epsilon
        if rms < 1e-10:
            db_level = -100.0
        else:
            # Convert to dB scale
            db_level = 20 * np.log10(rms)
        
        is_silent = db_level < threshold
        
        if is_silent:
            logger.debug(f"Silence detected: {db_level:.2f}dB < {threshold}dB for {duration}s")
        
        return is_silent
    
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
            return np.mean(audio_data, axis=1)
        elif target_channels == 2 and current_channels == 1:
            # Mono to stereo: duplicate channel
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
