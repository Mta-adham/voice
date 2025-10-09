"""
Generate sample audio files for testing.

Creates:
- sample_audio_clear.wav: Clear speech simulation (440Hz sine wave)
- sample_audio_unclear.wav: Unclear/noisy audio
- sample_audio_silence.wav: Silent audio
"""
import numpy as np
import soundfile as sf
from pathlib import Path


def generate_clear_audio(duration=2.0, sample_rate=16000):
    """
    Generate clear audio (sine wave at 440Hz).
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Generate 440Hz sine wave (musical note A)
    audio_data = np.sin(2 * np.pi * 440 * t)
    
    # Convert to int16 format
    audio_data = (audio_data * 32767 * 0.8).astype(np.int16)
    
    return audio_data, sample_rate


def generate_unclear_audio(duration=2.0, sample_rate=16000):
    """
    Generate unclear/noisy audio.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    # Generate random noise
    audio_data = np.random.randn(int(sample_rate * duration))
    
    # Scale to reasonable amplitude
    audio_data = (audio_data * 5000).astype(np.int16)
    
    return audio_data, sample_rate


def generate_silence(duration=2.0, sample_rate=16000):
    """
    Generate silent audio.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    audio_data = np.zeros(int(sample_rate * duration), dtype=np.int16)
    
    return audio_data, sample_rate


def generate_mixed_audio(duration=2.0, sample_rate=16000):
    """
    Generate audio with speech followed by silence.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    # First half: sine wave
    half_duration = duration / 2
    t = np.linspace(0, half_duration, int(sample_rate * half_duration))
    audio_1 = np.sin(2 * np.pi * 440 * t) * 0.8
    
    # Second half: silence
    audio_2 = np.zeros(int(sample_rate * half_duration))
    
    # Concatenate
    audio_data = np.concatenate([audio_1, audio_2])
    audio_data = (audio_data * 32767).astype(np.int16)
    
    return audio_data, sample_rate


def main():
    """Generate all sample audio files."""
    fixtures_dir = Path(__file__).parent
    
    print("Generating sample audio files...")
    
    # Generate clear audio
    clear_audio, sr = generate_clear_audio(duration=2.0)
    sf.write(fixtures_dir / "sample_audio_clear.wav", clear_audio, sr)
    print(f"✓ Created sample_audio_clear.wav ({len(clear_audio)} samples, {sr}Hz)")
    
    # Generate unclear audio
    unclear_audio, sr = generate_unclear_audio(duration=2.0)
    sf.write(fixtures_dir / "sample_audio_unclear.wav", unclear_audio, sr)
    print(f"✓ Created sample_audio_unclear.wav ({len(unclear_audio)} samples, {sr}Hz)")
    
    # Generate silence
    silence_audio, sr = generate_silence(duration=2.0)
    sf.write(fixtures_dir / "sample_audio_silence.wav", silence_audio, sr)
    print(f"✓ Created sample_audio_silence.wav ({len(silence_audio)} samples, {sr}Hz)")
    
    # Generate mixed audio
    mixed_audio, sr = generate_mixed_audio(duration=2.0)
    sf.write(fixtures_dir / "sample_audio_mixed.wav", mixed_audio, sr)
    print(f"✓ Created sample_audio_mixed.wav ({len(mixed_audio)} samples, {sr}Hz)")
    
    print("\nAll sample audio files generated successfully!")


if __name__ == "__main__":
    main()
