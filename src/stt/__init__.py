"""
Speech-to-Text Module - Whisper transcription services.
"""

from .whisper_transcriber import (
    WhisperTranscriber,
    WhisperTranscriptionError,
    transcribe_audio
)

__all__ = [
    "WhisperTranscriber",
    "WhisperTranscriptionError",
    "transcribe_audio",
]
