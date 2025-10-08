"""
Utility functions for audio processing and conversion.
"""
import numpy as np
from typing import Tuple
import sounddevice as sd


def bytes_to_numpy(audio_bytes: bytes, dtype: str = "int16", channels: int = 1) -> np.ndarray:
    """
    Convert raw audio bytes to numpy array.
    
    Args:
        audio_bytes: Raw audio bytes
        dtype: Data type of audio samples
        channels: Number of audio channels
        
    Returns:
        Numpy array of audio samples
    """
    audio_array = np.frombuffer(audio_bytes, dtype=dtype)
    if channels > 1:
        audio_array = audio_array.reshape(-1, channels)
    return audio_array


def numpy_to_bytes(audio_array: np.ndarray) -> bytes:
    """
    Convert numpy array to raw audio bytes.
    
    Args:
        audio_array: Numpy array of audio samples
        
    Returns:
        Raw audio bytes
    """
    return audio_array.tobytes()


def normalize_audio(audio_array: np.ndarray) -> np.ndarray:
    """
    Normalize audio array to range [-1.0, 1.0].
    
    Args:
        audio_array: Input audio array
        
    Returns:
        Normalized audio array as float32
    """
    audio_float = audio_array.astype(np.float32)
    
    # Normalize based on dtype
    if audio_array.dtype == np.int16:
        audio_float /= 32768.0
    elif audio_array.dtype == np.int32:
        audio_float /= 2147483648.0
    elif audio_array.dtype != np.float32:
        # Already float, normalize to [-1, 1] range
        max_val = np.abs(audio_float).max()
        if max_val > 0:
            audio_float /= max_val
    
    return audio_float


def denormalize_audio(audio_array: np.ndarray, target_dtype: str = "int16") -> np.ndarray:
    """
    Convert normalized float audio to integer format.
    
    Args:
        audio_array: Normalized audio array (range [-1.0, 1.0])
        target_dtype: Target data type ('int16' or 'int32')
        
    Returns:
        Audio array in target dtype
    """
    if target_dtype == "int16":
        return (audio_array * 32767).astype(np.int16)
    elif target_dtype == "int32":
        return (audio_array * 2147483647).astype(np.int32)
    else:
        return audio_array.astype(np.float32)


def resample_audio(
    audio_array: np.ndarray, 
    orig_sample_rate: int, 
    target_sample_rate: int
) -> np.ndarray:
    """
    Resample audio to a different sample rate.
    
    Args:
        audio_array: Input audio array
        orig_sample_rate: Original sample rate
        target_sample_rate: Target sample rate
        
    Returns:
        Resampled audio array
    """
    if orig_sample_rate == target_sample_rate:
        return audio_array
    
    # Calculate resampling ratio
    ratio = target_sample_rate / orig_sample_rate
    new_length = int(len(audio_array) * ratio)
    
    # Use linear interpolation for resampling
    original_indices = np.arange(len(audio_array))
    new_indices = np.linspace(0, len(audio_array) - 1, new_length)
    resampled = np.interp(new_indices, original_indices, audio_array)
    
    return resampled.astype(audio_array.dtype)


def calculate_rms(audio_array: np.ndarray) -> float:
    """
    Calculate Root Mean Square (RMS) amplitude of audio.
    
    Args:
        audio_array: Audio array
        
    Returns:
        RMS value (normalized to 0-1 range for int16)
    """
    if len(audio_array) == 0:
        return 0.0
    
    # Normalize to float if needed
    if audio_array.dtype in [np.int16, np.int32]:
        audio_float = normalize_audio(audio_array)
    else:
        audio_float = audio_array
    
    rms = np.sqrt(np.mean(audio_float ** 2))
    return float(rms)


def detect_silence(
    audio_array: np.ndarray, 
    threshold: float = 0.01, 
    min_duration_samples: int = 16000
) -> bool:
    """
    Detect if audio contains silence.
    
    Args:
        audio_array: Audio array to check
        threshold: RMS threshold below which audio is considered silent
        min_duration_samples: Minimum number of samples for silence detection
        
    Returns:
        True if audio is silent, False otherwise
    """
    if len(audio_array) < min_duration_samples:
        return False
    
    rms = calculate_rms(audio_array[-min_duration_samples:])
    return rms < threshold


def get_audio_devices() -> Tuple[list, list]:
    """
    Get available audio input and output devices.
    
    Returns:
        Tuple of (input_devices, output_devices) where each is a list of dicts
        with device information
    """
    devices = sd.query_devices()
    
    input_devices = []
    output_devices = []
    
    for i, device in enumerate(devices):
        device_info = {
            "index": i,
            "name": device["name"],
            "channels": device["max_input_channels"] if device["max_input_channels"] > 0 else device["max_output_channels"],
            "sample_rate": int(device["default_samplerate"])
        }
        
        if device["max_input_channels"] > 0:
            input_devices.append(device_info)
        if device["max_output_channels"] > 0:
            output_devices.append(device_info)
    
    return input_devices, output_devices


def print_audio_devices() -> None:
    """Print available audio devices to console."""
    input_devices, output_devices = get_audio_devices()
    
    print("=" * 60)
    print("AUDIO INPUT DEVICES")
    print("=" * 60)
    for device in input_devices:
        print(f"[{device['index']}] {device['name']}")
        print(f"    Channels: {device['channels']}, Sample Rate: {device['sample_rate']} Hz")
    
    print("\n" + "=" * 60)
    print("AUDIO OUTPUT DEVICES")
    print("=" * 60)
    for device in output_devices:
        print(f"[{device['index']}] {device['name']}")
        print(f"    Channels: {device['channels']}, Sample Rate: {device['sample_rate']} Hz")
    print()
