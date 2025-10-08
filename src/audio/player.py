"""
Audio playback functionality for playing audio through speakers.
"""
import numpy as np
import sounddevice as sd
from typing import Optional
import threading
import time

from .config import AudioConfig, default_config
from .utils import normalize_audio


class AudioPlayer:
    """
    Audio player for playing audio through speakers/headphones.
    
    Supports both blocking and non-blocking playback modes.
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize the audio player.
        
        Args:
            config: Audio configuration. If None, uses default config.
        """
        self.config = config or default_config
        self._playing = False
        self._stream: Optional[sd.OutputStream] = None
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def play(
        self, 
        audio_data: np.ndarray,
        sample_rate: Optional[int] = None,
        blocking: bool = True
    ) -> None:
        """
        Play audio data.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of audio. If None, uses config sample rate.
            blocking: If True, blocks until playback is complete
        """
        if self._playing:
            raise RuntimeError("Already playing audio")
        
        sample_rate = sample_rate or self.config.sample_rate
        
        # Ensure audio is in correct format
        if audio_data.dtype != np.float32:
            audio_data = normalize_audio(audio_data)
        
        # Reshape to correct number of channels if needed
        if len(audio_data.shape) == 1 and self.config.channels > 1:
            # Duplicate mono to stereo if needed
            audio_data = np.column_stack([audio_data] * self.config.channels)
        elif len(audio_data.shape) == 2 and audio_data.shape[1] != self.config.channels:
            # Handle channel mismatch
            if self.config.channels == 1:
                # Convert to mono by averaging channels
                audio_data = audio_data.mean(axis=1)
            else:
                # Duplicate single channel to required channels
                audio_data = np.column_stack([audio_data[:, 0]] * self.config.channels)
        
        self._playing = True
        self._stop_event.clear()
        
        if blocking:
            self._play_blocking(audio_data, sample_rate)
        else:
            self._playback_thread = threading.Thread(
                target=self._play_blocking,
                args=(audio_data, sample_rate),
                daemon=True
            )
            self._playback_thread.start()
    
    def _play_blocking(self, audio_data: np.ndarray, sample_rate: int) -> None:
        """
        Internal method for blocking playback.
        
        Args:
            audio_data: Audio data as numpy array (float32)
            sample_rate: Sample rate of audio
        """
        try:
            sd.play(
                audio_data,
                samplerate=sample_rate,
                device=self.config.output_device,
                blocking=False
            )
            
            # Wait for playback to complete or stop signal
            while sd.get_stream().active and not self._stop_event.is_set():
                time.sleep(0.01)
            
            # Stop if requested
            if self._stop_event.is_set():
                sd.stop()
        
        finally:
            self._playing = False
    
    def play_file(
        self, 
        file_path: str,
        blocking: bool = True
    ) -> None:
        """
        Play audio from a file.
        
        Args:
            file_path: Path to audio file
            blocking: If True, blocks until playback is complete
        """
        # Import here to avoid circular dependency
        from .file_handler import AudioFileHandler
        
        handler = AudioFileHandler(self.config)
        audio_data, sample_rate = handler.load(file_path)
        self.play(audio_data, sample_rate, blocking)
    
    def stop(self) -> None:
        """Stop audio playback."""
        if not self._playing:
            return
        
        self._stop_event.set()
        sd.stop()
        
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1.0)
        
        self._playing = False
    
    def is_playing(self) -> bool:
        """Check if currently playing audio."""
        return self._playing
    
    def wait(self, timeout: Optional[float] = None) -> None:
        """
        Wait for playback to complete.
        
        Args:
            timeout: Maximum time to wait in seconds. None means wait indefinitely.
        """
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=timeout)
    
    def play_tone(
        self,
        frequency: float = 440.0,
        duration: float = 0.5,
        blocking: bool = True
    ) -> None:
        """
        Play a simple sine wave tone.
        
        Args:
            frequency: Tone frequency in Hz
            duration: Duration in seconds
            blocking: If True, blocks until playback is complete
        """
        sample_rate = self.config.sample_rate
        num_samples = int(sample_rate * duration)
        
        # Generate sine wave
        t = np.linspace(0, duration, num_samples, False)
        tone = np.sin(2 * np.pi * frequency * t)
        
        # Apply fade in/out to avoid clicks
        fade_samples = int(sample_rate * 0.01)  # 10ms fade
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        
        tone[:fade_samples] *= fade_in
        tone[-fade_samples:] *= fade_out
        
        # Reduce volume
        tone *= 0.3
        
        self.play(tone.astype(np.float32), sample_rate, blocking)
    
    def test_audio(self) -> None:
        """Play a test tone to verify audio output is working."""
        print("Playing test tone (440 Hz, 1 second)...")
        self.play_tone(440.0, 1.0, blocking=True)
        print("Test tone complete")
