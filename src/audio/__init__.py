"""
Audio package - Audio recording, playback, and processing utilities.
"""
from .audio_manager import AudioManager
from .config import AudioConfig

__all__ = [
    "AudioManager",
    "AudioConfig",
]
