"""
Audio file handling for saving and loading audio files.
"""
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import os

from .config import AudioConfig, default_config
from .utils import normalize_audio, denormalize_audio


class AudioFileHandler:
    """
    Handler for saving and loading audio files in various formats.
    
    Supports WAV format natively via soundfile, with potential for other formats.
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize the audio file handler.
        
        Args:
            config: Audio configuration. If None, uses default config.
        """
        self.config = config or default_config
        
        # Create save directory if it doesn't exist
        self.save_path = Path(self.config.audio_save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        audio_data: np.ndarray,
        file_path: Optional[str] = None,
        sample_rate: Optional[int] = None,
        format: Optional[str] = None
    ) -> str:
        """
        Save audio data to a file.
        
        Args:
            audio_data: Audio data as numpy array
            file_path: Path to save file. If None, generates timestamped filename.
            sample_rate: Sample rate of audio. If None, uses config sample rate.
            format: File format ('wav', 'flac', 'ogg'). If None, uses config default.
            
        Returns:
            Path to saved file
        """
        sample_rate = sample_rate or self.config.sample_rate
        format = format or self.config.default_file_format
        
        # Generate filename if not provided
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = str(self.save_path / f"recording_{timestamp}.{format}")
        else:
            # Ensure file path has correct extension
            file_path = str(Path(file_path).with_suffix(f".{format}"))
        
        # Ensure parent directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Normalize audio to float32 for saving
        if audio_data.dtype != np.float32:
            audio_normalized = normalize_audio(audio_data)
        else:
            audio_normalized = audio_data
        
        # Reshape for correct number of channels
        if len(audio_normalized.shape) == 1 and self.config.channels > 1:
            audio_normalized = np.column_stack([audio_normalized] * self.config.channels)
        
        # Save audio file
        sf.write(
            file_path,
            audio_normalized,
            sample_rate,
            format=format.upper()
        )
        
        return file_path
    
    def load(
        self,
        file_path: str,
        target_sample_rate: Optional[int] = None,
        target_dtype: str = "float32"
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio data from a file.
        
        Args:
            file_path: Path to audio file
            target_sample_rate: Resample to this rate. If None, keeps original.
            target_dtype: Target data type for audio array
            
        Returns:
            Tuple of (audio_data, sample_rate)
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        # Load audio file
        audio_data, sample_rate = sf.read(file_path, dtype='float32')
        
        # Convert to mono if needed
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            if self.config.channels == 1:
                audio_data = audio_data.mean(axis=1)
        
        # Resample if requested
        if target_sample_rate and target_sample_rate != sample_rate:
            from .utils import resample_audio
            audio_data = resample_audio(audio_data, sample_rate, target_sample_rate)
            sample_rate = target_sample_rate
        
        # Convert to target dtype
        if target_dtype != "float32":
            audio_data = denormalize_audio(audio_data, target_dtype)
        
        return audio_data, sample_rate
    
    def get_audio_info(self, file_path: str) -> dict:
        """
        Get information about an audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with audio file information
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        info = sf.info(file_path)
        
        return {
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "duration": info.duration,
            "frames": info.frames,
            "format": info.format,
            "subtype": info.subtype,
        }
    
    def convert_format(
        self,
        input_path: str,
        output_path: str,
        target_format: str = "wav",
        target_sample_rate: Optional[int] = None
    ) -> str:
        """
        Convert audio file to different format.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to output audio file
            target_format: Target format ('wav', 'flac', 'ogg')
            target_sample_rate: Resample to this rate. If None, keeps original.
            
        Returns:
            Path to converted file
        """
        # Load audio
        audio_data, sample_rate = self.load(input_path, target_sample_rate)
        
        # Save in new format
        return self.save(
            audio_data,
            output_path,
            sample_rate,
            target_format
        )
    
    def list_recordings(self) -> list[dict]:
        """
        List all recordings in the save directory.
        
        Returns:
            List of dictionaries with recording information
        """
        recordings = []
        
        for file_path in self.save_path.glob("*.wav"):
            try:
                info = self.get_audio_info(str(file_path))
                info["file_path"] = str(file_path)
                info["file_name"] = file_path.name
                info["file_size"] = file_path.stat().st_size
                recordings.append(info)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        return recordings
    
    def delete_recording(self, file_path: str) -> bool:
        """
        Delete a recording file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            Path(file_path).unlink()
            return True
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
            return False
    
    def cleanup_old_recordings(self, days: int = 7) -> int:
        """
        Delete recordings older than specified days.
        
        Args:
            days: Delete recordings older than this many days
            
        Returns:
            Number of files deleted
        """
        import time
        
        current_time = time.time()
        max_age = days * 24 * 60 * 60  # Convert days to seconds
        deleted_count = 0
        
        for file_path in self.save_path.glob("*.wav"):
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age:
                if self.delete_recording(str(file_path)):
                    deleted_count += 1
        
        return deleted_count
