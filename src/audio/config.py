"""
Audio configuration settings for the voice assistant system.
"""
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class AudioConfig:
    """
    Configuration for audio input/output operations.
    
    Attributes:
        sample_rate: Audio sample rate in Hz (16000 Hz is standard for speech)
        channels: Number of audio channels (1 for mono, 2 for stereo)
        chunk_size: Number of frames per buffer (affects latency and processing)
        format: Audio format bit depth
        input_device: Input device index (None for default)
        output_device: Output device index (None for default)
        silence_threshold: Amplitude threshold for silence detection (0-1)
        silence_duration: Duration of silence in seconds to stop recording
    """
    # Recording settings
    sample_rate: int = 16000  # 16 kHz is standard for speech recognition
    channels: int = 1  # Mono audio
    chunk_size: int = 1024  # Frames per buffer
    format: Literal["int16", "int32", "float32"] = "int16"
    
    # Device settings
    input_device: int | None = None  # None = use default
    output_device: int | None = None  # None = use default
    
    # Recording behavior
    silence_threshold: float = 0.01  # Amplitude threshold for silence (0-1)
    silence_duration: float = 2.0  # Seconds of silence before stopping
    max_recording_duration: float = 30.0  # Maximum recording length in seconds
    
    # File settings
    default_file_format: str = "wav"
    audio_save_path: str = "audio_recordings"
    
    def get_numpy_dtype(self) -> str:
        """Get the corresponding numpy dtype for the audio format."""
        dtype_map = {
            "int16": "int16",
            "int32": "int32",
            "float32": "float32",
        }
        return dtype_map[self.format]
    
    def get_bytes_per_sample(self) -> int:
        """Get the number of bytes per audio sample."""
        bytes_map = {
            "int16": 2,
            "int32": 4,
            "float32": 4,
        }
        return bytes_map[self.format]


# Default global configuration
default_config = AudioConfig()
