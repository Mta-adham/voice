"""
Audio configuration settings for the voice assistant system.
"""
from dataclasses import dataclass, field
=======
Audio configuration constants and settings.
"""
from dataclasses import dataclass

from typing import Literal


@dataclass
class AudioConfig:
    """
    Audio configuration for recording and playback.
    
    Attributes:
        sample_rate: Sample rate in Hz (16kHz recommended for speech)
        channels: Number of audio channels (1=mono, 2=stereo)
        bit_depth: Audio bit depth (16-bit standard for speech)
        dtype: NumPy data type for audio samples
        chunk_size: Number of frames per buffer
        silence_threshold: Silence detection threshold in dB
        silence_duration: Minimum silence duration in seconds to stop recording
        max_recording_duration: Maximum recording duration in seconds
        temp_dir: Directory for temporary audio files
    """
    sample_rate: int = 16000  # 16kHz recommended for speech recognition
    channels: int = 1  # Mono channel
    bit_depth: int = 16  # 16-bit depth
    dtype: Literal["int16", "float32"] = "int16"
    chunk_size: int = 1024  # Frames per buffer
    
    # Voice activity detection
    silence_threshold: float = -40.0  # dB
    silence_duration: float = 1.5  # seconds
    
    # Recording limits
    max_recording_duration: float = 300.0  # 5 minutes max
    
    # File management
    temp_dir: str = "temp_audio"
    
    def __post_init__(self):
        """Validate configuration values."""
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if self.channels not in (1, 2):
            raise ValueError("Channels must be 1 (mono) or 2 (stereo)")
        if self.bit_depth not in (16, 24, 32):
            raise ValueError("Bit depth must be 16, 24, or 32")
        if self.silence_threshold > 0:
            raise ValueError("Silence threshold must be negative (dB)")
        if self.silence_duration <= 0:
            raise ValueError("Silence duration must be positive")


# Default configuration instance
DEFAULT_CONFIG = AudioConfig()
