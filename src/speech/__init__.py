"""
Speech module for text-to-speech and speech-to-text functionality.
"""
from .elevenlabs_tts import (
    ElevenLabsTTS,
    ElevenLabsTTSError,
    APIKeyError,
    QuotaExceededError,
    RateLimitError
)

__all__ = [
    "ElevenLabsTTS",
    "ElevenLabsTTSError",
    "APIKeyError",
    "QuotaExceededError",
    "RateLimitError"
]
