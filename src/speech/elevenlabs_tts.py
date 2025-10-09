"""
ElevenLabs Text-to-Speech Integration.

This module provides text-to-speech functionality using the ElevenLabs API
with caching, retry logic, fallback TTS options, and audio format conversion
for AudioManager compatibility.
"""
import hashlib
import os
import time
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import soundfile as sf
from elevenlabs import generate, voices, set_api_key, Voice, VoiceSettings
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import fallback TTS libraries
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logger.warning("pyttsx3 not available for fallback TTS")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not available for fallback TTS")


class ElevenLabsTTSError(Exception):
    """Base exception for ElevenLabs TTS errors."""
    pass


class APIKeyError(ElevenLabsTTSError):
    """Raised when API key is invalid or missing."""
    pass


class QuotaExceededError(ElevenLabsTTSError):
    """Raised when API quota is exceeded."""
    pass


class RateLimitError(ElevenLabsTTSError):
    """Raised when API rate limit is hit."""
    pass


class ElevenLabsTTS:
    """
    Text-to-Speech service using ElevenLabs API.
    
    Features:
    - Natural-sounding speech generation
    - Local caching of generated audio to reduce API calls
    - Automatic retry with exponential backoff for rate limits
    - Audio format conversion to match AudioManager requirements (16kHz mono 16-bit PCM)
    - LRU cache management with 100MB size limit
    
    Example:
        tts = ElevenLabsTTS()
        audio_data, sample_rate = tts.generate_speech("Hello, welcome to our restaurant!")
        # Use with AudioManager
        audio_manager.play_audio(audio_data, sample_rate)
    """
    
    # Default voice ID for Rachel (professional, friendly female voice)
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    
    # Audio output specifications (matching AudioManager requirements)
    TARGET_SAMPLE_RATE = 16000  # 16kHz
    TARGET_CHANNELS = 1  # Mono
    TARGET_DTYPE = np.int16  # 16-bit
    
    # Cache settings
    MAX_CACHE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        cache_dir: str = "cache/audio"
    ):
        """
        Initialize ElevenLabs TTS service.
        
        Args:
            api_key: ElevenLabs API key. If None, loads from ELEVENLABS_API_KEY env var.
            voice_id: Voice ID to use. If None, uses DEFAULT_VOICE_ID (Rachel).
            cache_dir: Directory for audio cache storage.
        
        Raises:
            APIKeyError: If API key is not provided and not found in environment.
        """
        # Load API key
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise APIKeyError(
                "ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Set API key for elevenlabs library
        set_api_key(self.api_key)
        
        # Voice configuration
        self.voice_id = voice_id or self.DEFAULT_VOICE_ID
        
        # Cache directory setup
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache metadata file for LRU tracking
        self.cache_metadata_file = self.cache_dir / ".cache_metadata.txt"
        
        # Statistics
        self.stats = {
            "api_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0
        }
        
        logger.info(
            f"ElevenLabsTTS initialized with voice_id={self.voice_id}, "
            f"cache_dir={self.cache_dir}"
        )
        
        # Validate API key by testing connection
        try:
            self._validate_api_key()
        except Exception as e:
            logger.error(f"Failed to validate API key: {str(e)}")
            raise APIKeyError(f"Invalid API key: {str(e)}")
    
    def _validate_api_key(self) -> None:
        """
        Validate API key by making a test request.
        
        Raises:
            APIKeyError: If API key is invalid.
        """
        try:
            # Try to fetch available voices as a validation check
            _ = voices()
            logger.debug("API key validated successfully")
        except Exception as e:
            error_msg = str(e).lower()
            if "401" in error_msg or "unauthorized" in error_msg or "invalid" in error_msg:
                raise APIKeyError("Invalid API key")
            elif "quota" in error_msg or "exceeded" in error_msg:
                raise QuotaExceededError("API quota exceeded")
            else:
                raise APIKeyError(f"API key validation failed: {str(e)}")
    
    def _get_cache_key(self, text: str, voice_id: str) -> str:
        """
        Generate cache key from text and voice_id using MD5 hash.
        
        Args:
            text: Input text
            voice_id: Voice ID used
        
        Returns:
            MD5 hash string
        """
        content = f"{text}:{voice_id}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get full path to cached audio file."""
        return self.cache_dir / f"{cache_key}.wav"
    
    def _get_cache_size(self) -> int:
        """
        Calculate total size of cache directory in bytes.
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        for file in self.cache_dir.glob("*.wav"):
            try:
                total_size += file.stat().st_size
            except OSError:
                continue
        return total_size
    
    def _evict_lru_cache(self) -> None:
        """
        Evict least recently used cache entries until under size limit.
        Uses file access time for LRU determination.
        """
        cache_files = list(self.cache_dir.glob("*.wav"))
        if not cache_files:
            return
        
        # Sort by access time (oldest first)
        cache_files.sort(key=lambda f: f.stat().st_atime)
        
        current_size = self._get_cache_size()
        
        for file in cache_files:
            if current_size <= self.MAX_CACHE_SIZE_BYTES:
                break
            
            try:
                file_size = file.stat().st_size
                file.unlink()
                current_size -= file_size
                logger.debug(f"Evicted cache file: {file.name} ({file_size} bytes)")
            except OSError as e:
                logger.warning(f"Failed to evict cache file {file.name}: {str(e)}")
        
        logger.info(
            f"Cache eviction complete. Current size: {current_size / (1024*1024):.2f}MB"
        )
    
    def _load_from_cache(self, cache_key: str) -> Optional[Tuple[np.ndarray, int]]:
        """
        Load audio from cache if available.
        
        Args:
            cache_key: Cache key (MD5 hash)
        
        Returns:
            Tuple of (audio_data, sample_rate) if found, None otherwise
        """
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            # Update access time for LRU
            cache_path.touch()
            
            # Load audio
            audio_data, sample_rate = sf.read(cache_path)
            
            # Convert to int16 if needed
            if audio_data.dtype != self.TARGET_DTYPE:
                audio_data = self._convert_to_int16(audio_data)
            
            logger.debug(f"Cache hit: {cache_key}")
            self.stats["cache_hits"] += 1
            
            return audio_data, sample_rate
            
        except Exception as e:
            logger.warning(f"Failed to load from cache {cache_key}: {str(e)}")
            # Delete corrupted cache file
            try:
                cache_path.unlink()
            except OSError:
                pass
            return None
    
    def _save_to_cache(
        self,
        cache_key: str,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> None:
        """
        Save audio to cache.
        
        Args:
            cache_key: Cache key (MD5 hash)
            audio_data: Audio data to cache
            sample_rate: Sample rate
        """
        try:
            cache_path = self._get_cache_path(cache_key)
            
            # Save audio as WAV
            sf.write(cache_path, audio_data, sample_rate)
            
            logger.debug(f"Saved to cache: {cache_key}")
            
            # Check cache size and evict if necessary
            cache_size = self._get_cache_size()
            if cache_size > self.MAX_CACHE_SIZE_BYTES:
                logger.info(
                    f"Cache size ({cache_size / (1024*1024):.2f}MB) "
                    f"exceeds limit ({self.MAX_CACHE_SIZE_BYTES / (1024*1024):.2f}MB)"
                )
                self._evict_lru_cache()
        
        except Exception as e:
            logger.warning(f"Failed to save to cache {cache_key}: {str(e)}")
    
    def _convert_to_int16(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Convert audio data to int16 format.
        
        Args:
            audio_data: Input audio data
        
        Returns:
            Audio data in int16 format
        """
        if audio_data.dtype == np.int16:
            return audio_data
        
        # Assuming input is float32 in range [-1.0, 1.0]
        if audio_data.dtype in (np.float32, np.float64):
            # Clip and convert to int16 range
            audio_data = np.clip(audio_data, -1.0, 1.0)
            audio_data = (audio_data * 32767).astype(np.int16)
            return audio_data
        
        # For other types, try direct conversion
        return audio_data.astype(np.int16)
    
    def _convert_audio_format(
        self,
        audio_data: np.ndarray,
        original_rate: int
    ) -> Tuple[np.ndarray, int]:
        """
        Convert audio to target format (16kHz, mono, int16).
        
        Args:
            audio_data: Input audio data
            original_rate: Original sample rate
        
        Returns:
            Tuple of (converted_audio_data, target_sample_rate)
        """
        # Convert to mono if stereo
        if audio_data.ndim == 2:
            audio_data = np.mean(audio_data, axis=1)
            logger.debug("Converted stereo to mono")
        
        # Resample if needed
        if original_rate != self.TARGET_SAMPLE_RATE:
            logger.debug(f"Resampling from {original_rate}Hz to {self.TARGET_SAMPLE_RATE}Hz")
            
            # Calculate resampling ratio
            ratio = self.TARGET_SAMPLE_RATE / original_rate
            new_length = int(len(audio_data) * ratio)
            
            # Linear interpolation resampling
            indices = np.linspace(0, len(audio_data) - 1, new_length)
            audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data)
        
        # Convert to int16
        audio_data = self._convert_to_int16(audio_data)
        
        return audio_data, self.TARGET_SAMPLE_RATE
    
    @retry(
        retry=retry_if_exception_type((RateLimitError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING")
    )
    def _call_api(self, text: str, voice_id: str) -> bytes:
        """
        Call ElevenLabs API with retry logic.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use
        
        Returns:
            Audio bytes
        
        Raises:
            RateLimitError: If rate limit is hit
            QuotaExceededError: If quota is exceeded
            ElevenLabsTTSError: For other API errors
        """
        try:
            logger.debug(f"Calling ElevenLabs API: text_length={len(text)}, voice_id={voice_id}")
            
            # Generate speech with optimized settings for restaurant context
            audio_bytes = generate(
                text=text,
                voice=Voice(
                    voice_id=voice_id,
                    settings=VoiceSettings(
                        stability=0.5,  # Balanced stability for natural conversation
                        similarity_boost=0.75,  # Good voice similarity
                        style=0.0,  # Neutral style
                        use_speaker_boost=True  # Enhanced clarity
                    )
                ),
                model="eleven_monolingual_v1"  # Fast, high-quality English model
            )
            
            self.stats["api_calls"] += 1
            logger.info(f"API call successful. Text length: {len(text)} characters")
            
            return audio_bytes
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Parse error type
            if "rate limit" in error_msg or "429" in error_msg:
                logger.warning("Rate limit hit, will retry with backoff")
                self.stats["errors"] += 1
                raise RateLimitError("API rate limit exceeded")
            
            elif "quota" in error_msg or "exceeded" in error_msg:
                logger.error("API quota exceeded")
                self.stats["errors"] += 1
                raise QuotaExceededError("API quota exceeded. Check your ElevenLabs account.")
            
            elif "401" in error_msg or "unauthorized" in error_msg or "invalid" in error_msg:
                logger.error("Invalid API key")
                self.stats["errors"] += 1
                raise APIKeyError("Invalid API key")
            
            elif "network" in error_msg or "connection" in error_msg:
                logger.warning("Network error, will retry")
                self.stats["errors"] += 1
                raise ConnectionError(f"Network error: {str(e)}")
            
            else:
                logger.error(f"API call failed: {str(e)}")
                self.stats["errors"] += 1
                raise ElevenLabsTTSError(f"Failed to generate speech: {str(e)}")
    
    def generate_speech(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Generate speech from text using ElevenLabs API.
        
        This method checks the cache first, and only calls the API if needed.
        Generated audio is automatically converted to AudioManager-compatible format
        (16kHz, mono, 16-bit PCM).
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use. If None, uses default voice.
        
        Returns:
            Tuple of (audio_data, sample_rate) as numpy array and int
            Ready for use with AudioManager.play_audio()
        
        Raises:
            APIKeyError: If API key is invalid
            QuotaExceededError: If API quota is exceeded
            RateLimitError: If rate limit is exceeded (after retries)
            ElevenLabsTTSError: For other errors
        
        Example:
            >>> tts = ElevenLabsTTS()
            >>> audio_data, sample_rate = tts.generate_speech("Welcome to our restaurant!")
            >>> audio_manager.play_audio(audio_data, sample_rate)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Use default voice if not specified
        voice_id = voice_id or self.voice_id
        
        # Generate cache key
        cache_key = self._get_cache_key(text, voice_id)
        
        # Check cache first
        cached_audio = self._load_from_cache(cache_key)
        if cached_audio is not None:
            logger.info(f"Using cached audio for text: '{text[:50]}...'")
            return cached_audio
        
        # Cache miss - call API
        logger.info(f"Cache miss. Generating speech for text: '{text[:50]}...'")
        self.stats["cache_misses"] += 1
        
        try:
            # Call API with retry logic
            audio_bytes = self._call_api(text, voice_id)
            
            # Save raw audio to temp file for processing
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(audio_bytes)
            
            try:
                # Load audio from temp file
                audio_data, original_rate = sf.read(temp_path)
                
                # Convert to target format (16kHz, mono, int16)
                audio_data, sample_rate = self._convert_audio_format(audio_data, original_rate)
                
                # Save to cache
                self._save_to_cache(cache_key, audio_data, sample_rate)
                
                logger.info(
                    f"Speech generated successfully: {len(audio_data)} samples, "
                    f"{sample_rate}Hz, {len(audio_data)/sample_rate:.2f}s duration"
                )
                
                return audio_data, sample_rate
                
            finally:
                # Clean up temp file
                try:
                    temp_path.unlink()
                except OSError:
                    pass
        
        except (APIKeyError, QuotaExceededError, RateLimitError):
            # Re-raise known errors
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error generating speech: {str(e)}")
            raise ElevenLabsTTSError(f"Failed to generate speech: {str(e)}")
    
    def get_stats(self) -> dict:
        """
        Get usage statistics.
        
        Returns:
            Dictionary with statistics including API calls, cache hits/misses, errors
        """
        cache_size = self._get_cache_size()
        cache_file_count = len(list(self.cache_dir.glob("*.wav")))
        
        return {
            **self.stats,
            "cache_size_mb": cache_size / (1024 * 1024),
            "cache_file_count": cache_file_count,
            "cache_hit_rate": (
                self.stats["cache_hits"] / 
                (self.stats["cache_hits"] + self.stats["cache_misses"])
                if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0
                else 0.0
            )
        }
    
    def clear_cache(self) -> None:
        """Clear all cached audio files."""
        try:
            for file in self.cache_dir.glob("*.wav"):
                file.unlink()
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
            raise ElevenLabsTTSError(f"Failed to clear cache: {str(e)}")


# ============================================================================
# Fallback TTS Implementation
# ============================================================================

class FallbackTTS:
    """
    Fallback Text-to-Speech service using pyttsx3 (offline) or gTTS (online).
    
    This is used when ElevenLabs API is unavailable. It provides basic TTS
    functionality to ensure the conversation can continue even with degraded quality.
    """
    
    TARGET_SAMPLE_RATE = 16000  # Match ElevenLabs
    TARGET_CHANNELS = 1  # Mono
    TARGET_DTYPE = np.int16
    
    def __init__(self, use_gtts: bool = False):
        """
        Initialize fallback TTS.
        
        Args:
            use_gtts: If True, use gTTS (online). If False, use pyttsx3 (offline).
        """
        self.use_gtts = use_gtts
        self.provider = "gtts" if use_gtts else "pyttsx3"
        
        logger.warning(f"Using fallback TTS provider: {self.provider}")
        
        if not use_gtts:
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
                # Set properties for better quality
                self.engine.setProperty('rate', 150)  # Speaking rate
                self.engine.setProperty('volume', 1.0)  # Volume
            except Exception as e:
                logger.error(f"Failed to initialize pyttsx3: {e}")
                self.engine = None
    
    def generate_speech(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Generate speech using fallback TTS.
        
        Args:
            text: Text to convert to speech
            voice_id: Ignored for fallback TTS
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            ElevenLabsTTSError: If generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        logger.info(f"Generating fallback TTS for text: '{text[:50]}...'")
        
        try:
            if self.use_gtts:
                return self._generate_with_gtts(text)
            else:
                return self._generate_with_pyttsx3(text)
        except Exception as e:
            logger.error(f"Fallback TTS generation failed: {e}")
            raise ElevenLabsTTSError(f"Fallback TTS failed: {str(e)}")
    
    def _generate_with_gtts(self, text: str) -> Tuple[np.ndarray, int]:
        """Generate speech using gTTS (Google Text-to-Speech)."""
        try:
            from gtts import gTTS
            import tempfile
            
            # Generate speech
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                tts.save(str(temp_path))
            
            try:
                # Load audio
                audio_data, original_rate = sf.read(temp_path)
                
                # Convert to target format
                if audio_data.ndim == 2:
                    audio_data = np.mean(audio_data, axis=1)
                
                # Resample if needed
                if original_rate != self.TARGET_SAMPLE_RATE:
                    ratio = self.TARGET_SAMPLE_RATE / original_rate
                    new_length = int(len(audio_data) * ratio)
                    indices = np.linspace(0, len(audio_data) - 1, new_length)
                    audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data)
                
                # Convert to int16
                if audio_data.dtype in (np.float32, np.float64):
                    audio_data = np.clip(audio_data, -1.0, 1.0)
                    audio_data = (audio_data * 32767).astype(np.int16)
                
                logger.info(f"gTTS generation successful: {len(audio_data)} samples")
                return audio_data, self.TARGET_SAMPLE_RATE
                
            finally:
                # Clean up temp file
                try:
                    temp_path.unlink()
                except OSError:
                    pass
                    
        except ImportError:
            raise ElevenLabsTTSError(
                "gTTS not installed. Install with: pip install gtts"
            )
        except Exception as e:
            raise ElevenLabsTTSError(f"gTTS generation failed: {str(e)}")
    
    def _generate_with_pyttsx3(self, text: str) -> Tuple[np.ndarray, int]:
        """Generate speech using pyttsx3 (offline TTS)."""
        try:
            import tempfile
            
            if self.engine is None:
                raise ElevenLabsTTSError("pyttsx3 engine not initialized")
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            try:
                # Generate speech
                self.engine.save_to_file(text, str(temp_path))
                self.engine.runAndWait()
                
                # Load audio
                audio_data, original_rate = sf.read(temp_path)
                
                # Convert to target format
                if audio_data.ndim == 2:
                    audio_data = np.mean(audio_data, axis=1)
                
                # Resample if needed
                if original_rate != self.TARGET_SAMPLE_RATE:
                    ratio = self.TARGET_SAMPLE_RATE / original_rate
                    new_length = int(len(audio_data) * ratio)
                    indices = np.linspace(0, len(audio_data) - 1, new_length)
                    audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data)
                
                # Convert to int16
                if audio_data.dtype in (np.float32, np.float64):
                    audio_data = np.clip(audio_data, -1.0, 1.0)
                    audio_data = (audio_data * 32767).astype(np.int16)
                
                logger.info(f"pyttsx3 generation successful: {len(audio_data)} samples")
                return audio_data, self.TARGET_SAMPLE_RATE
                
            finally:
                # Clean up temp file
                try:
                    temp_path.unlink()
                except OSError:
                    pass
                    
        except ImportError:
            raise ElevenLabsTTSError(
                "pyttsx3 not installed. Install with: pip install pyttsx3"
            )
        except Exception as e:
            raise ElevenLabsTTSError(f"pyttsx3 generation failed: {str(e)}")


# ============================================================================
# Unified TTS with Automatic Fallback
# ============================================================================

class TTSWithFallback:
    """
    Unified TTS service that automatically falls back to alternative providers.
    
    Tries ElevenLabs first, then falls back to gTTS or pyttsx3 if unavailable.
    This ensures the conversation can continue even if the primary TTS fails.
    """
    
    def __init__(
        self,
        elevenlabs_api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        cache_dir: str = "cache/audio",
        enable_fallback: bool = True,
        prefer_gtts: bool = True
    ):
        """
        Initialize TTS with fallback.
        
        Args:
            elevenlabs_api_key: ElevenLabs API key
            voice_id: ElevenLabs voice ID
            cache_dir: Cache directory for audio files
            enable_fallback: Whether to enable fallback TTS
            prefer_gtts: If True, prefer gTTS over pyttsx3 for fallback
        """
        self.enable_fallback = enable_fallback
        self.prefer_gtts = prefer_gtts
        self.primary_tts = None
        self.fallback_tts = None
        self.using_fallback = False
        
        # Try to initialize ElevenLabs
        try:
            self.primary_tts = ElevenLabsTTS(
                api_key=elevenlabs_api_key,
                voice_id=voice_id,
                cache_dir=cache_dir
            )
            logger.info("ElevenLabs TTS initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize ElevenLabs TTS: {e}")
            if enable_fallback:
                logger.info("Will use fallback TTS from the start")
                self.using_fallback = True
            else:
                raise
        
        # Initialize fallback if enabled
        if enable_fallback:
            try:
                self.fallback_tts = FallbackTTS(use_gtts=prefer_gtts)
                logger.info(f"Fallback TTS initialized: {self.fallback_tts.provider}")
            except Exception as e:
                logger.warning(f"Failed to initialize fallback TTS: {e}")
                # Try the other fallback option
                try:
                    self.fallback_tts = FallbackTTS(use_gtts=not prefer_gtts)
                    logger.info(f"Alternative fallback TTS initialized: {self.fallback_tts.provider}")
                except Exception as e2:
                    logger.error(f"All fallback TTS options failed: {e2}")
                    self.fallback_tts = None
    
    def generate_speech(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Generate speech with automatic fallback.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID (only used for ElevenLabs)
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            ElevenLabsTTSError: If all TTS providers fail
        """
        # Try primary TTS first (if not already using fallback)
        if self.primary_tts and not self.using_fallback:
            try:
                return self.primary_tts.generate_speech(text, voice_id)
            except (QuotaExceededError, APIKeyError) as e:
                # These errors are not recoverable, switch to fallback permanently
                logger.error(f"ElevenLabs TTS failure: {e}. Switching to fallback permanently.")
                self.using_fallback = True
                
                if not self.enable_fallback or not self.fallback_tts:
                    raise
            except (RateLimitError, ElevenLabsTTSError) as e:
                # These errors might be temporary, try fallback for this request
                logger.warning(f"ElevenLabs TTS error: {e}. Using fallback for this request.")
                
                if not self.enable_fallback or not self.fallback_tts:
                    raise
        
        # Use fallback TTS
        if self.fallback_tts:
            try:
                logger.info("Using fallback TTS")
                return self.fallback_tts.generate_speech(text)
            except Exception as e:
                logger.error(f"Fallback TTS also failed: {e}")
                raise ElevenLabsTTSError(
                    f"All TTS providers failed. Primary: disabled/failed, Fallback: {str(e)}"
                )
        
        raise ElevenLabsTTSError("No TTS provider available")
    
    def get_current_provider(self) -> str:
        """Get name of current TTS provider being used."""
        if self.using_fallback and self.fallback_tts:
            return self.fallback_tts.provider
        elif self.primary_tts:
            return "elevenlabs"
        else:
            return "none"
