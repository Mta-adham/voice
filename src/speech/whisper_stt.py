"""
Whisper Speech-to-Text (STT) service with error handling.

This module provides speech-to-text functionality using OpenAI's Whisper model
with comprehensive error handling, silence detection, and audio quality checks.
"""
import os
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Union
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai package not installed. Whisper STT will not be available.")

try:
    import whisper
    WHISPER_LOCAL_AVAILABLE = True
except ImportError:
    WHISPER_LOCAL_AVAILABLE = False
    logger.debug("whisper package not installed. Local Whisper will not be available.")

from ..error_handling.exceptions import (
    STTError,
    APIKeyError,
    SilenceDetectedError,
    UnclearAudioError,
    AudioProcessingError,
)


class WhisperSTT:
    """
    Speech-to-Text service using OpenAI Whisper.
    
    Supports both:
    - OpenAI Whisper API (cloud, requires API key)
    - Local Whisper models (no API key needed)
    
    Features:
    - Automatic silence detection
    - Audio quality validation
    - Retry logic for transient failures
    - Fallback to local model if API fails
    - Comprehensive error handling
    
    Example:
        stt = WhisperSTT()
        text = stt.transcribe_file("recording.wav")
        # or
        text = stt.transcribe_audio(audio_data, sample_rate)
    """
    
    # Minimum audio duration to consider (seconds)
    MIN_AUDIO_DURATION = 0.3
    
    # Silence threshold (RMS amplitude)
    SILENCE_THRESHOLD = 0.01
    
    # Minimum confidence score to accept transcription
    MIN_CONFIDENCE = 0.5
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "base",
        use_api: bool = True,
        language: str = "en"
    ):
        """
        Initialize Whisper STT service.
        
        Args:
            api_key: OpenAI API key. If None, loads from OPENAI_API_KEY env var
            model: Whisper model size for local inference ("tiny", "base", "small", "medium", "large")
            use_api: Whether to use OpenAI API (True) or local model (False)
            language: Language code for transcription (default: "en")
            
        Raises:
            APIKeyError: If use_api=True and API key is not available
            ImportError: If required packages are not installed
        """
        self.language = language
        self.use_api = use_api
        self.local_model = None
        
        # Setup API-based Whisper
        if use_api:
            if not OPENAI_AVAILABLE:
                raise ImportError(
                    "openai package is required for API-based Whisper. "
                    "Install with: pip install openai"
                )
            
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise APIKeyError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                    "or pass api_key parameter.",
                    service="whisper"
                )
            
            # Set API key for openai library
            openai.api_key = self.api_key
            logger.info("WhisperSTT initialized with OpenAI API")
        
        # Setup local Whisper model as fallback
        else:
            if not WHISPER_LOCAL_AVAILABLE:
                raise ImportError(
                    "whisper package is required for local Whisper. "
                    "Install with: pip install openai-whisper"
                )
            
            logger.info(f"Loading local Whisper model: {model}")
            try:
                self.local_model = whisper.load_model(model)
                logger.info(f"WhisperSTT initialized with local {model} model")
            except Exception as e:
                raise STTError(
                    f"Failed to load local Whisper model: {str(e)}",
                    original_error=e
                )
    
    def _check_audio_quality(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> Tuple[bool, str]:
        """
        Check if audio has sufficient quality for transcription.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate in Hz
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check duration
        duration = len(audio_data) / sample_rate
        if duration < self.MIN_AUDIO_DURATION:
            return False, f"Audio too short: {duration:.2f}s"
        
        # Check for silence (low RMS)
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms < self.SILENCE_THRESHOLD:
            return False, f"Audio appears to be silence (RMS: {rms:.6f})"
        
        # Check for clipping
        max_amplitude = np.max(np.abs(audio_data))
        if max_amplitude > 0.99:
            logger.warning(f"Audio may be clipped (max amplitude: {max_amplitude:.2f})")
        
        return True, ""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError)) if OPENAI_AVAILABLE else retry_if_exception_type(Exception),
    )
    def _transcribe_with_api(self, audio_file_path: Path) -> str:
        """
        Transcribe audio using OpenAI Whisper API.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text
            
        Raises:
            STTError: If transcription fails
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                response = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=self.language,
                    response_format="text"
                )
            
            if isinstance(response, str):
                text = response
            else:
                text = response.text if hasattr(response, 'text') else str(response)
            
            return text.strip()
            
        except openai.AuthenticationError as e:
            raise APIKeyError(
                f"Whisper API authentication failed: {str(e)}",
                service="whisper"
            )
        except (openai.RateLimitError, openai.APITimeoutError) as e:
            # These will be retried by tenacity
            logger.warning(f"Whisper API error (will retry): {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Whisper API transcription failed: {str(e)}")
            raise STTError(
                f"Whisper API transcription failed: {str(e)}",
                original_error=e
            )
    
    def _transcribe_with_local_model(self, audio_file_path: Path) -> str:
        """
        Transcribe audio using local Whisper model.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text
            
        Raises:
            STTError: If transcription fails
        """
        if not self.local_model:
            raise STTError("Local Whisper model not loaded")
        
        try:
            result = self.local_model.transcribe(
                str(audio_file_path),
                language=self.language,
                fp16=False  # Use FP32 for CPU compatibility
            )
            
            text = result.get("text", "").strip()
            
            # Check confidence if available
            if "segments" in result and result["segments"]:
                avg_confidence = np.mean([
                    seg.get("confidence", 1.0)
                    for seg in result["segments"]
                ])
                
                if avg_confidence < self.MIN_CONFIDENCE:
                    logger.warning(f"Low transcription confidence: {avg_confidence:.2f}")
            
            return text
            
        except Exception as e:
            logger.error(f"Local Whisper transcription failed: {str(e)}")
            raise STTError(
                f"Local Whisper transcription failed: {str(e)}",
                original_error=e
            )
    
    def transcribe_file(self, audio_file_path: Union[str, Path]) -> str:
        """
        Transcribe audio from a file.
        
        Args:
            audio_file_path: Path to audio file (WAV, MP3, etc.)
            
        Returns:
            Transcribed text
            
        Raises:
            STTError: If transcription fails
            SilenceDetectedError: If audio is silent
            UnclearAudioError: If audio quality is poor
        """
        audio_file_path = Path(audio_file_path)
        
        if not audio_file_path.exists():
            raise STTError(f"Audio file not found: {audio_file_path}")
        
        logger.info(f"Transcribing audio file: {audio_file_path}")
        
        try:
            # Try API first if configured
            if self.use_api:
                try:
                    text = self._transcribe_with_api(audio_file_path)
                    logger.info(f"Transcription successful (API): '{text}'")
                    
                    # Check if transcription is empty or too short
                    if not text or len(text) < 2:
                        raise SilenceDetectedError()
                    
                    return text
                    
                except (STTError, APIKeyError) as e:
                    # If we have a local model, try it as fallback
                    if self.local_model:
                        logger.warning("API failed, falling back to local model")
                        text = self._transcribe_with_local_model(audio_file_path)
                        logger.info(f"Transcription successful (local): '{text}'")
                        
                        if not text or len(text) < 2:
                            raise SilenceDetectedError()
                        
                        return text
                    else:
                        raise
            
            # Use local model
            else:
                text = self._transcribe_with_local_model(audio_file_path)
                logger.info(f"Transcription successful (local): '{text}'")
                
                if not text or len(text) < 2:
                    raise SilenceDetectedError()
                
                return text
                
        except SilenceDetectedError:
            raise
        except STTError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {str(e)}")
            raise STTError(
                f"Transcription failed: {str(e)}",
                original_error=e
            )
    
    def transcribe_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        temp_dir: str = "cache/audio"
    ) -> str:
        """
        Transcribe audio from numpy array.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate in Hz
            temp_dir: Directory for temporary files
            
        Returns:
            Transcribed text
            
        Raises:
            STTError: If transcription fails
            SilenceDetectedError: If audio is silent
            UnclearAudioError: If audio quality is poor
            AudioProcessingError: If audio validation fails
        """
        # Validate audio quality
        is_valid, reason = self._check_audio_quality(audio_data, sample_rate)
        if not is_valid:
            logger.warning(f"Audio quality check failed: {reason}")
            if "silence" in reason.lower():
                raise SilenceDetectedError(context={"reason": reason})
            else:
                raise UnclearAudioError(context={"reason": reason})
        
        # Save audio to temporary file
        import soundfile as sf
        import tempfile
        
        temp_path = Path(temp_dir)
        temp_path.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.wav',
            dir=temp_path,
            delete=False
        ) as temp_file:
            temp_filepath = Path(temp_file.name)
        
        try:
            # Write audio to temporary file
            sf.write(temp_filepath, audio_data, sample_rate)
            
            # Transcribe
            text = self.transcribe_file(temp_filepath)
            
            return text
            
        finally:
            # Clean up temporary file
            try:
                if temp_filepath.exists():
                    temp_filepath.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_filepath}: {e}")
    
    def is_available(self) -> bool:
        """
        Check if STT service is available and working.
        
        Returns:
            True if service is available
        """
        if self.use_api:
            return OPENAI_AVAILABLE and self.api_key is not None
        else:
            return self.local_model is not None
    
    def __repr__(self) -> str:
        mode = "API" if self.use_api else "Local"
        return f"WhisperSTT(mode={mode}, language={self.language})"
