"""
Unit tests for audio system.

Tests:
- Mock microphone input and speaker output
- start_recording() and stop_recording()
- play_audio() with sample audio data
- detect_silence() with various audio inputs
- Audio format conversions
- Resource cleanup
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sounddevice as sd

from audio.audio_manager import (
    AudioManager,
    AudioDeviceError,
    AudioRecordingError,
    AudioPlaybackError
)
from audio.config import AudioConfig


class TestAudioManagerInit:
    """Test AudioManager initialization."""
    
    @patch('audio.audio_manager.sd.query_devices')
    def test_init_with_default_config(self, mock_query_devices):
        """Test initialization with default configuration."""
        # Mock audio devices
        mock_query_devices.return_value = [
            {"name": "Mock Microphone", "max_input_channels": 1},
            {"name": "Mock Speaker", "max_output_channels": 2}
        ]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_input:
            mock_input.return_value = {"name": "Mock Mic"}
            
            with patch('audio.audio_manager.sd.query_devices') as mock_output:
                mock_output.return_value = {"name": "Mock Speaker"}
                
                manager = AudioManager()
                
                assert manager.config is not None
                assert not manager._recording
    
    @patch('audio.audio_manager.sd.query_devices')
    def test_init_with_custom_config(self, mock_query_devices):
        """Test initialization with custom configuration."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            config = AudioConfig(sample_rate=44100, channels=2)
            manager = AudioManager(config=config)
            
            assert manager.config.sample_rate == 44100
            assert manager.config.channels == 2
    
    @patch('audio.audio_manager.sd.query_devices')
    def test_init_no_audio_devices(self, mock_query_devices):
        """Test initialization fails when no audio devices are available."""
        mock_query_devices.return_value = None
        
        with pytest.raises(AudioDeviceError):
            AudioManager()
    
    @patch('audio.audio_manager.sd.query_devices')
    def test_init_no_input_device(self, mock_query_devices):
        """Test initialization fails when no input device is found."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_input:
            mock_input.side_effect = [None, {"name": "Output"}]
            
            with pytest.raises(AudioDeviceError) as exc_info:
                AudioManager()
            
            assert "input" in str(exc_info.value).lower()


class TestAudioRecording:
    """Test audio recording functionality."""
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.InputStream')
    def test_start_recording_success(self, mock_input_stream, mock_query_devices):
        """Test successful start of audio recording."""
        # Mock devices
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            # Mock input stream
            mock_stream = Mock()
            mock_input_stream.return_value = mock_stream
            
            manager = AudioManager()
            manager.start_recording()
            
            assert manager._recording is True
            mock_stream.start.assert_called_once()
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.InputStream')
    def test_start_recording_already_in_progress(self, mock_input_stream, mock_query_devices):
        """Test that starting recording when already recording raises error."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            mock_stream = Mock()
            mock_input_stream.return_value = mock_stream
            
            manager = AudioManager()
            manager.start_recording()
            
            with pytest.raises(AudioRecordingError) as exc_info:
                manager.start_recording()
            
            assert "already in progress" in str(exc_info.value).lower()
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.InputStream')
    def test_stop_recording_success(self, mock_input_stream, mock_query_devices):
        """Test successful stop of audio recording."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            mock_stream = Mock()
            mock_input_stream.return_value = mock_stream
            
            manager = AudioManager()
            manager.start_recording()
            
            # Simulate some audio data
            sample_data = np.random.rand(1000, 1).astype(np.float32)
            manager._audio_buffer.append(sample_data)
            
            audio_data, sample_rate = manager.stop_recording()
            
            assert manager._recording is False
            assert isinstance(audio_data, np.ndarray)
            assert sample_rate > 0
            mock_stream.stop.assert_called_once()
            mock_stream.close.assert_called_once()
    
    @patch('audio.audio_manager.sd.query_devices')
    def test_stop_recording_no_recording_in_progress(self, mock_query_devices):
        """Test that stopping when not recording raises error."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            manager = AudioManager()
            
            with pytest.raises(AudioRecordingError) as exc_info:
                manager.stop_recording()
            
            assert "no recording in progress" in str(exc_info.value).lower()
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.InputStream')
    def test_stop_recording_empty_buffer(self, mock_input_stream, mock_query_devices):
        """Test stopping recording with empty buffer."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            mock_stream = Mock()
            mock_input_stream.return_value = mock_stream
            
            manager = AudioManager()
            manager.start_recording()
            
            # Don't add any data to buffer
            audio_data, sample_rate = manager.stop_recording()
            
            assert len(audio_data) == 0
            assert sample_rate > 0


class TestAudioPlayback:
    """Test audio playback functionality."""
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.play')
    @patch('audio.audio_manager.sd.wait')
    def test_play_audio_success(self, mock_wait, mock_play, mock_query_devices):
        """Test successful audio playback."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            manager = AudioManager()
            
            # Create sample audio
            sample_rate = 16000
            audio_data = np.random.rand(1000).astype(np.float32)
            
            manager.play_audio(audio_data, sample_rate)
            
            mock_play.assert_called_once_with(audio_data, sample_rate)
            mock_wait.assert_called_once()
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.play')
    @patch('audio.audio_manager.sd.wait')
    def test_play_audio_default_sample_rate(self, mock_wait, mock_play, mock_query_devices):
        """Test audio playback with default sample rate."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            manager = AudioManager()
            audio_data = np.random.rand(1000).astype(np.float32)
            
            manager.play_audio(audio_data)
            
            # Should use config sample rate
            call_args = mock_play.call_args
            assert call_args[0][1] == manager.config.sample_rate
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.play')
    def test_play_audio_device_error(self, mock_play, mock_query_devices):
        """Test audio playback error handling."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            manager = AudioManager()
            
            # Mock playback error
            mock_play.side_effect = sd.PortAudioError("Device error")
            
            audio_data = np.random.rand(1000).astype(np.float32)
            
            with pytest.raises(AudioDeviceError):
                manager.play_audio(audio_data)


class TestSilenceDetection:
    """Test silence detection functionality."""
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.InputStream')
    def test_detect_silence_with_silence(self, mock_input_stream, mock_query_devices):
        """Test detecting actual silence."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            mock_stream = Mock()
            mock_input_stream.return_value = mock_stream
            
            manager = AudioManager()
            manager.start_recording()
            
            # Add silent audio data
            silent_data = np.zeros((1000, 1), dtype=np.float32)
            manager._audio_buffer.append(silent_data)
            
            # Should detect silence
            is_silent = manager.detect_silence(threshold=-60, duration=0.1)
            
            assert is_silent is True
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.InputStream')
    def test_detect_silence_with_audio(self, mock_input_stream, mock_query_devices):
        """Test detecting non-silent audio."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            mock_stream = Mock()
            mock_input_stream.return_value = mock_stream
            
            manager = AudioManager()
            manager.start_recording()
            
            # Add loud audio data
            loud_data = np.random.rand(1000, 1).astype(np.float32) * 0.5
            manager._audio_buffer.append(loud_data)
            
            # Should not detect silence
            is_silent = manager.detect_silence(threshold=-60, duration=0.1)
            
            assert is_silent is False


class TestContextManager:
    """Test AudioManager as context manager."""
    
    @patch('audio.audio_manager.sd.query_devices')
    def test_context_manager_enter_exit(self, mock_query_devices):
        """Test AudioManager can be used as context manager."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            with AudioManager() as manager:
                assert manager is not None
                assert isinstance(manager, AudioManager)
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.InputStream')
    def test_context_manager_cleanup(self, mock_input_stream, mock_query_devices):
        """Test that context manager properly cleans up resources."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            mock_stream = Mock()
            mock_input_stream.return_value = mock_stream
            
            with AudioManager() as manager:
                manager.start_recording()
            
            # Stream should be stopped and closed on exit
            mock_stream.stop.assert_called()
            mock_stream.close.assert_called()


class TestAudioFormatConversion:
    """Test audio format conversion functionality."""
    
    @patch('audio.audio_manager.sd.query_devices')
    def test_audio_data_format(self, mock_query_devices):
        """Test that recorded audio is in correct format."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            with patch('audio.audio_manager.sd.InputStream') as mock_stream_class:
                mock_stream = Mock()
                mock_stream_class.return_value = mock_stream
                
                manager = AudioManager()
                manager.start_recording()
                
                # Simulate recorded data
                sample_data = np.random.rand(1000, 1).astype(np.float32)
                manager._audio_buffer.append(sample_data)
                
                audio_data, sample_rate = manager.stop_recording()
                
                # Check format
                assert isinstance(audio_data, np.ndarray)
                assert audio_data.dtype == manager.config.dtype
                assert sample_rate == manager.config.sample_rate


class TestResourceManagement:
    """Test resource management and cleanup."""
    
    @patch('audio.audio_manager.sd.query_devices')
    def test_temp_directory_creation(self, mock_query_devices):
        """Test that temp directory is created."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            manager = AudioManager()
            
            assert manager._temp_dir.exists()
    
    @patch('audio.audio_manager.sd.query_devices')
    @patch('audio.audio_manager.sd.InputStream')
    def test_recording_state_management(self, mock_input_stream, mock_query_devices):
        """Test that recording state is properly managed."""
        mock_query_devices.return_value = [{"name": "Device"}]
        
        with patch('audio.audio_manager.sd.query_devices') as mock_dev:
            mock_dev.return_value = {"name": "Device"}
            
            mock_stream = Mock()
            mock_input_stream.return_value = mock_stream
            
            manager = AudioManager()
            
            assert manager._recording is False
            
            manager.start_recording()
            assert manager._recording is True
            
            manager.stop_recording()
            assert manager._recording is False
