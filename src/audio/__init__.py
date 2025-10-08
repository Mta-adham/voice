"""
Audio Input/Output System for voice assistant.

This module provides comprehensive audio recording, playback, and file handling
capabilities for the restaurant booking voice assistant system.

Main Components:
- AudioRecorder: Record audio from microphone
- AudioPlayer: Play audio through speakers
- AudioFileHandler: Save and load audio files
- AudioConfig: Configuration for audio operations
- Utility functions: Audio processing and format conversion
"""

from .config import AudioConfig, default_config
from .recorder import AudioRecorder
from .player import AudioPlayer
from .file_handler import AudioFileHandler
from .utils import (
    bytes_to_numpy,
    numpy_to_bytes,
    normalize_audio,
    denormalize_audio,
    resample_audio,
    calculate_rms,
    detect_silence,
    get_audio_devices,
    print_audio_devices,
)

__all__ = [
    # Configuration
    "AudioConfig",
    "default_config",
    # Core classes
    "AudioRecorder",
    "AudioPlayer",
    "AudioFileHandler",
    # Utility functions
    "bytes_to_numpy",
    "numpy_to_bytes",
    "normalize_audio",
    "denormalize_audio",
    "resample_audio",
    "calculate_rms",
    "detect_silence",
    "get_audio_devices",
    "print_audio_devices",
]

__version__ = "1.0.0"
