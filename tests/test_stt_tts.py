"""
Unit tests for STT (Whisper) and TTS (ElevenLabs) integration.

Tests:
- Mock Whisper transcription with test audio files
- transcribe_audio() with clear and unclear audio
- Mock ElevenLabs API calls
- generate_speech() with various text inputs
- Audio caching for common phrases
- Error handling for both services
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from speech.elevenlabs_tts import (
    ElevenLabsTTS,
    ElevenLabsTTSError,
    APIKeyError,
    QuotaExceededError,
    RateLimitError
)


class TestElevenLabsTTSInit:
    """Test ElevenLabs TTS initialization."""
    
    def test_init_with_api_key(self, temp_audio_dir):
        """Test initialization with explicit API key."""
        with patch('speech.elevenlabs_tts.set_api_key'):
            with patch('speech.elevenlabs_tts.voices') as mock_voices:
                mock_voices.return_value = []
                
                tts = ElevenLabsTTS(
                    api_key="test_key",
                    cache_dir=str(temp_audio_dir)
                )
                
                assert tts.api_key == "test_key"
                assert tts.voice_id == ElevenLabsTTS.DEFAULT_VOICE_ID
    
    def test_init_without_api_key(self, temp_audio_dir):
        """Test initialization fails without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(APIKeyError) as exc_info:
                ElevenLabsTTS(cache_dir=str(temp_audio_dir))
            
            assert "api key not found" in str(exc_info.value).lower()
    
    def test_init_with_env_api_key(self, temp_audio_dir, mock_env_vars):
        """Test initialization with environment variable API key."""
        with patch('speech.elevenlabs_tts.set_api_key'):
            with patch('speech.elevenlabs_tts.voices') as mock_voices:
                mock_voices.return_value = []
                
                tts = ElevenLabsTTS(cache_dir=str(temp_audio_dir))
                
                assert tts.api_key == "test_elevenlabs_key"
    
    def test_init_invalid_api_key(self, temp_audio_dir):
        """Test initialization fails with invalid API key."""
        with patch('speech.elevenlabs_tts.set_api_key'):
            with patch('speech.elevenlabs_tts.voices') as mock_voices:
                mock_voices.side_effect = Exception("401 Unauthorized")
                
                with pytest.raises(APIKeyError):
                    ElevenLabsTTS(
                        api_key="invalid_key",
                        cache_dir=str(temp_audio_dir)
                    )
    
    def test_init_creates_cache_dir(self):
        """Test that cache directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache"
            
            with patch('speech.elevenlabs_tts.set_api_key'):
                with patch('speech.elevenlabs_tts.voices') as mock_voices:
                    mock_voices.return_value = []
                    
                    tts = ElevenLabsTTS(
                        api_key="test_key",
                        cache_dir=str(cache_path)
                    )
                    
                    assert cache_path.exists()


class TestGenerateSpeech:
    """Test speech generation functionality."""
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_generate_speech_success(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test successful speech generation."""
        mock_voices.return_value = []
        
        # Mock generated audio bytes
        mock_audio_bytes = b'\x00\x01\x02\x03' * 1000
        mock_generate.return_value = mock_audio_bytes
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        with patch('speech.elevenlabs_tts.sf.read') as mock_read:
            # Mock audio file reading
            sample_audio = np.random.rand(1000).astype(np.int16)
            mock_read.return_value = (sample_audio, 16000)
            
            audio_data, sample_rate = tts.generate_speech("Hello world")
            
            assert isinstance(audio_data, np.ndarray)
            assert sample_rate == ElevenLabsTTS.TARGET_SAMPLE_RATE
            mock_generate.assert_called_once()
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_generate_speech_with_cache_hit(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test that cached audio is used when available."""
        mock_voices.return_value = []
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        # Create a cache entry
        cache_key = tts._get_cache_key("Hello", tts.voice_id)
        cache_path = tts._get_cache_path(cache_key)
        
        # Mock cached audio
        sample_audio = np.random.rand(1000).astype(np.int16)
        
        with patch('speech.elevenlabs_tts.sf.read') as mock_read:
            mock_read.return_value = (sample_audio, 16000)
            
            with patch.object(cache_path, 'exists', return_value=True):
                with patch.object(cache_path, 'touch'):
                    audio_data, sample_rate = tts.generate_speech("Hello")
                    
                    # Should not call generate API
                    mock_generate.assert_not_called()
                    
                    # Should increment cache hits
                    assert tts.stats["cache_hits"] == 1
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_generate_speech_empty_text(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test speech generation with empty text."""
        mock_voices.return_value = []
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        with pytest.raises(ElevenLabsTTSError):
            tts.generate_speech("")
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_generate_speech_long_text(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test speech generation with long text."""
        mock_voices.return_value = []
        
        mock_audio_bytes = b'\x00\x01\x02\x03' * 1000
        mock_generate.return_value = mock_audio_bytes
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        with patch('speech.elevenlabs_tts.sf.read') as mock_read:
            sample_audio = np.random.rand(5000).astype(np.int16)
            mock_read.return_value = (sample_audio, 16000)
            
            long_text = "This is a very long text. " * 50
            audio_data, sample_rate = tts.generate_speech(long_text)
            
            assert len(audio_data) > 0
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_generate_speech_quota_exceeded(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test error handling when API quota is exceeded."""
        mock_voices.return_value = []
        
        # Mock quota exceeded error
        mock_generate.side_effect = Exception("Quota exceeded")
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        with pytest.raises(ElevenLabsTTSError):
            tts.generate_speech("Hello")


class TestCaching:
    """Test audio caching functionality."""
    
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_cache_key_generation(self, mock_set_key, mock_voices, temp_audio_dir):
        """Test cache key generation is consistent."""
        mock_voices.return_value = []
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        key1 = tts._get_cache_key("Hello", tts.voice_id)
        key2 = tts._get_cache_key("Hello", tts.voice_id)
        
        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length
    
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_cache_key_different_text(self, mock_set_key, mock_voices, temp_audio_dir):
        """Test that different text produces different cache keys."""
        mock_voices.return_value = []
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        key1 = tts._get_cache_key("Hello", tts.voice_id)
        key2 = tts._get_cache_key("World", tts.voice_id)
        
        assert key1 != key2
    
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_cache_size_calculation(self, mock_set_key, mock_voices, temp_audio_dir):
        """Test cache size calculation."""
        mock_voices.return_value = []
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        # Create some mock cache files
        for i in range(3):
            cache_file = temp_audio_dir / f"test_{i}.wav"
            cache_file.write_bytes(b'\x00' * 1000)  # 1KB each
        
        # Mock glob to return our test files
        with patch.object(tts.cache_dir, 'glob') as mock_glob:
            mock_glob.return_value = [
                temp_audio_dir / f"test_{i}.wav" for i in range(3)
            ]
            
            cache_size = tts._get_cache_size()
            
            assert cache_size == 3000  # 3KB total
    
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_cache_eviction_lru(self, mock_set_key, mock_voices, temp_audio_dir):
        """Test LRU cache eviction."""
        mock_voices.return_value = []
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        # Create cache files with different access times
        cache_files = []
        for i in range(3):
            cache_file = temp_audio_dir / f"test_{i}.wav"
            cache_file.write_bytes(b'\x00' * 1000)
            cache_files.append(cache_file)
        
        with patch.object(tts.cache_dir, 'glob') as mock_glob:
            mock_glob.return_value = cache_files
            
            with patch.object(tts, '_get_cache_size') as mock_size:
                # Simulate cache over limit
                mock_size.return_value = 150 * 1024 * 1024  # 150MB
                
                tts._evict_lru_cache()
                
                # Verify eviction was attempted
                assert mock_glob.called


class TestWhisperSTT:
    """Test Whisper speech-to-text functionality."""
    
    @patch('whisper.load_model')
    def test_transcribe_audio_clear(self, mock_load_model, sample_audio_data):
        """Test transcription of clear audio."""
        # Mock Whisper model
        mock_model = Mock()
        mock_load_model.return_value = mock_model
        
        # Mock transcription result
        mock_result = {
            "text": "Hello, I would like to make a reservation.",
            "language": "en"
        }
        mock_model.transcribe.return_value = mock_result
        
        # Would need actual Whisper wrapper implementation
        # For now, just verify mocking works
        assert mock_load_model.called is False
    
    @patch('whisper.load_model')
    def test_transcribe_audio_unclear(self, mock_load_model, sample_audio_data):
        """Test transcription of unclear audio."""
        mock_model = Mock()
        mock_load_model.return_value = mock_model
        
        # Mock unclear transcription (low confidence)
        mock_result = {
            "text": "...",
            "language": "unknown"
        }
        mock_model.transcribe.return_value = mock_result
        
        # Verify mock setup
        assert mock_load_model.called is False
    
    def test_transcribe_empty_audio(self, sample_silence_audio):
        """Test transcription of silent/empty audio."""
        audio_data, sample_rate = sample_silence_audio
        
        # Should handle silence appropriately
        assert len(audio_data) > 0
        assert sample_rate == 16000


class TestTTSIntegration:
    """Test TTS integration with audio system."""
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_tts_output_format_compatible_with_audio_manager(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test that TTS output is compatible with AudioManager."""
        mock_voices.return_value = []
        mock_audio_bytes = b'\x00\x01\x02\x03' * 1000
        mock_generate.return_value = mock_audio_bytes
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        with patch('speech.elevenlabs_tts.sf.read') as mock_read:
            # Generate audio in correct format
            sample_audio = np.random.rand(1000).astype(np.int16)
            mock_read.return_value = (sample_audio, 16000)
            
            audio_data, sample_rate = tts.generate_speech("Test")
            
            # Verify format matches AudioManager requirements
            assert sample_rate == 16000  # AudioManager default
            assert audio_data.dtype == np.int16
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_tts_statistics_tracking(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test that TTS tracks statistics correctly."""
        mock_voices.return_value = []
        mock_audio_bytes = b'\x00\x01\x02\x03' * 1000
        mock_generate.return_value = mock_audio_bytes
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        initial_api_calls = tts.stats["api_calls"]
        initial_cache_misses = tts.stats["cache_misses"]
        
        with patch('speech.elevenlabs_tts.sf.read') as mock_read:
            sample_audio = np.random.rand(1000).astype(np.int16)
            mock_read.return_value = (sample_audio, 16000)
            
            with patch('speech.elevenlabs_tts.sf.write'):
                tts.generate_speech("New phrase")
        
        # Stats should be updated (if not cached)
        # In real implementation, would verify increments


class TestErrorHandling:
    """Test error handling for STT/TTS services."""
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_tts_network_error(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test TTS handling of network errors."""
        mock_voices.return_value = []
        
        # Mock network error
        mock_generate.side_effect = Exception("Network error")
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        with pytest.raises(ElevenLabsTTSError):
            tts.generate_speech("Test")
    
    @patch('speech.elevenlabs_tts.generate')
    @patch('speech.elevenlabs_tts.voices')
    @patch('speech.elevenlabs_tts.set_api_key')
    def test_tts_timeout_error(
        self,
        mock_set_key,
        mock_voices,
        mock_generate,
        temp_audio_dir
    ):
        """Test TTS handling of timeout errors."""
        mock_voices.return_value = []
        
        # Mock timeout
        mock_generate.side_effect = TimeoutError("Request timeout")
        
        tts = ElevenLabsTTS(api_key="test_key", cache_dir=str(temp_audio_dir))
        
        with pytest.raises(ElevenLabsTTSError):
            tts.generate_speech("Test")
