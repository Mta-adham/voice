"""
TTS fallback system with multiple providers.

This module provides a robust TTS system that attempts ElevenLabs first,
then falls back to pyttsx3 or gTTS if ElevenLabs fails.
"""
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import soundfile as sf
from loguru import logger

from ..error_handling.exceptions import TTSError
from ..error_handling.handlers import graceful_degradation


class TTSService:
    """
    Unified TTS service with automatic fallback support.
    
    Tries providers in order:
    1. ElevenLabs (primary - highest quality)
    2. gTTS (Google Text-to-Speech - good quality, requires internet)
    3. pyttsx3 (offline fallback - basic quality)
    """
    
    def __init__(
        self,
        elevenlabs_api_key: Optional[str] = None,
        cache_dir: str = "cache/audio"
    ):
        """
        Initialize TTS service with fallback support.
        
        Args:
            elevenlabs_api_key: ElevenLabs API key (optional)
            cache_dir: Directory for caching audio files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ElevenLabs if API key available
        self.elevenlabs_tts = None
        self.elevenlabs_available = False
        
        if elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY"):
            try:
                from .elevenlabs_tts import ElevenLabsTTS
                self.elevenlabs_tts = ElevenLabsTTS(
                    api_key=elevenlabs_api_key,
                    cache_dir=str(cache_dir)
                )
                self.elevenlabs_available = True
                logger.info("ElevenLabs TTS initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize ElevenLabs TTS: {e}")
                self.elevenlabs_available = False
        
        # Initialize fallback providers
        self._init_fallback_providers()
        
        # Statistics
        self.stats = {
            "elevenlabs_success": 0,
            "elevenlabs_failure": 0,
            "gtts_success": 0,
            "gtts_failure": 0,
            "pyttsx3_success": 0,
            "pyttsx3_failure": 0
        }
    
    def _init_fallback_providers(self) -> None:
        """Initialize fallback TTS providers."""
        # Check gTTS availability
        self.gtts_available = False
        try:
            import gtts
            self.gtts_available = True
            logger.info("gTTS fallback available")
        except ImportError:
            logger.warning("gTTS not available (pip install gtts)")
        
        # Check pyttsx3 availability
        self.pyttsx3_available = False
        try:
            import pyttsx3
            # Test initialization
            engine = pyttsx3.init()
            engine.stop()
            self.pyttsx3_available = True
            logger.info("pyttsx3 fallback available")
        except Exception as e:
            logger.warning(f"pyttsx3 not available: {e}")
    
    def _generate_with_elevenlabs(self, text: str) -> Tuple[np.ndarray, int]:
        """
        Generate speech using ElevenLabs.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            TTSError: If generation fails
        """
        if not self.elevenlabs_available or not self.elevenlabs_tts:
            raise TTSError(
                "ElevenLabs TTS not available",
                provider="elevenlabs",
                fallback_available=True
            )
        
        try:
            audio_data, sample_rate = self.elevenlabs_tts.generate_speech(text)
            self.stats["elevenlabs_success"] += 1
            logger.info(f"ElevenLabs TTS generated {len(audio_data)} samples")
            return audio_data, sample_rate
        except Exception as e:
            self.stats["elevenlabs_failure"] += 1
            logger.error(f"ElevenLabs TTS failed: {e}")
            raise TTSError(
                f"ElevenLabs TTS failed: {str(e)}",
                provider="elevenlabs",
                original_error=e,
                fallback_available=True
            )
    
    def _generate_with_gtts(self, text: str) -> Tuple[np.ndarray, int]:
        """
        Generate speech using gTTS (Google Text-to-Speech).
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            TTSError: If generation fails
        """
        if not self.gtts_available:
            raise TTSError(
                "gTTS not available",
                provider="gtts",
                fallback_available=self.pyttsx3_available
            )
        
        try:
            from gtts import gTTS
            import subprocess
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3:
                temp_mp3_path = temp_mp3.name
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
            
            try:
                # Generate MP3 using gTTS
                tts = gTTS(text=text, lang='en', slow=False)
                tts.save(temp_mp3_path)
                
                # Convert MP3 to WAV using ffmpeg or pydub
                try:
                    # Try ffmpeg first (faster)
                    subprocess.run(
                        ["ffmpeg", "-i", temp_mp3_path, "-ar", "16000", "-ac", "1", temp_wav_path],
                        check=True,
                        capture_output=True
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback to pydub if ffmpeg not available
                    try:
                        from pydub import AudioSegment
                        audio = AudioSegment.from_mp3(temp_mp3_path)
                        audio = audio.set_frame_rate(16000).set_channels(1)
                        audio.export(temp_wav_path, format="wav")
                    except ImportError:
                        raise TTSError(
                            "Cannot convert MP3 to WAV. Install ffmpeg or pydub.",
                            provider="gtts",
                            fallback_available=self.pyttsx3_available
                        )
                
                # Load WAV file
                audio_data, sample_rate = sf.read(temp_wav_path)
                
                # Convert to int16 if needed
                if audio_data.dtype != np.int16:
                    audio_data = (audio_data * 32767).astype(np.int16)
                
                self.stats["gtts_success"] += 1
                logger.info(f"gTTS generated {len(audio_data)} samples")
                return audio_data, sample_rate
                
            finally:
                # Clean up temporary files
                try:
                    os.unlink(temp_mp3_path)
                    os.unlink(temp_wav_path)
                except OSError:
                    pass
        
        except Exception as e:
            self.stats["gtts_failure"] += 1
            logger.error(f"gTTS failed: {e}")
            raise TTSError(
                f"gTTS failed: {str(e)}",
                provider="gtts",
                original_error=e,
                fallback_available=self.pyttsx3_available
            )
    
    def _generate_with_pyttsx3(self, text: str) -> Tuple[np.ndarray, int]:
        """
        Generate speech using pyttsx3 (offline TTS).
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            TTSError: If generation fails
        """
        if not self.pyttsx3_available:
            raise TTSError(
                "pyttsx3 not available",
                provider="pyttsx3",
                fallback_available=False
            )
        
        try:
            import pyttsx3
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
            
            try:
                # Initialize pyttsx3 engine
                engine = pyttsx3.init()
                
                # Configure voice properties
                engine.setProperty('rate', 150)  # Speed of speech
                engine.setProperty('volume', 1.0)  # Volume (0.0 to 1.0)
                
                # Save to file
                engine.save_to_file(text, temp_wav_path)
                engine.runAndWait()
                
                # Load WAV file
                audio_data, sample_rate = sf.read(temp_wav_path)
                
                # Resample to 16kHz if needed
                if sample_rate != 16000:
                    try:
                        import librosa
                        audio_data = librosa.resample(
                            audio_data.astype(np.float32),
                            orig_sr=sample_rate,
                            target_sr=16000
                        )
                        sample_rate = 16000
                    except ImportError:
                        logger.warning("librosa not available, keeping original sample rate")
                
                # Convert to int16 if needed
                if audio_data.dtype != np.int16:
                    audio_data = (audio_data * 32767).astype(np.int16)
                
                self.stats["pyttsx3_success"] += 1
                logger.info(f"pyttsx3 generated {len(audio_data)} samples")
                return audio_data, sample_rate
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_wav_path)
                except OSError:
                    pass
        
        except Exception as e:
            self.stats["pyttsx3_failure"] += 1
            logger.error(f"pyttsx3 failed: {e}")
            raise TTSError(
                f"pyttsx3 failed: {str(e)}",
                provider="pyttsx3",
                original_error=e,
                fallback_available=False
            )
    
    def generate_speech(
        self,
        text: str,
        prefer_quality: bool = True
    ) -> Tuple[np.ndarray, int]:
        """
        Generate speech with automatic fallback.
        
        Tries providers in order until one succeeds:
        1. ElevenLabs (if available and prefer_quality=True)
        2. gTTS
        3. pyttsx3
        
        Args:
            text: Text to convert to speech
            prefer_quality: If True, try ElevenLabs first. If False, skip to gTTS.
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            TTSError: If all providers fail
        """
        errors = []
        
        # Try ElevenLabs first if preferred and available
        if prefer_quality and self.elevenlabs_available:
            try:
                return self._generate_with_elevenlabs(text)
            except TTSError as e:
                logger.warning(f"ElevenLabs failed, trying fallback: {e}")
                errors.append(("elevenlabs", e))
        
        # Try gTTS
        if self.gtts_available:
            try:
                return self._generate_with_gtts(text)
            except TTSError as e:
                logger.warning(f"gTTS failed, trying fallback: {e}")
                errors.append(("gtts", e))
        
        # Try pyttsx3 as last resort
        if self.pyttsx3_available:
            try:
                return self._generate_with_pyttsx3(text)
            except TTSError as e:
                logger.error(f"pyttsx3 (last fallback) failed: {e}")
                errors.append(("pyttsx3", e))
        
        # All providers failed
        error_summary = ", ".join([f"{provider}: {str(error)}" for provider, error in errors])
        raise TTSError(
            f"All TTS providers failed: {error_summary}",
            provider="all",
            fallback_available=False
        )
    
    def get_stats(self) -> dict:
        """Get TTS usage statistics."""
        return self.stats.copy()
