#!/usr/bin/env python3
"""
Demo script for the Audio Input/Output System.

This script demonstrates the basic functionality of the audio system including:
- Recording audio from microphone
- Playing audio
- Saving and loading audio files
- Audio device enumeration
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio import (
    AudioRecorder,
    AudioPlayer,
    AudioFileHandler,
    AudioConfig,
    print_audio_devices,
)


def demo_devices():
    """Demonstrate listing audio devices."""
    print("\n" + "=" * 60)
    print("DEMO: Audio Devices")
    print("=" * 60)
    print_audio_devices()


def demo_recording():
    """Demonstrate audio recording."""
    print("\n" + "=" * 60)
    print("DEMO: Audio Recording")
    print("=" * 60)
    
    config = AudioConfig(
        sample_rate=16000,
        channels=1,
        silence_threshold=0.02,
        silence_duration=2.0
    )
    
    recorder = AudioRecorder(config)
    
    print("\nRecording for 5 seconds (or until 2 seconds of silence)...")
    print("Speak into your microphone!")
    
    audio_data = recorder.record(duration=5.0, stop_on_silence=True)
    
    print(f"Recorded {len(audio_data)} samples ({len(audio_data) / config.sample_rate:.2f} seconds)")
    
    return audio_data, config.sample_rate


def demo_playback(audio_data, sample_rate):
    """Demonstrate audio playback."""
    print("\n" + "=" * 60)
    print("DEMO: Audio Playback")
    print("=" * 60)
    
    player = AudioPlayer()
    
    print("\nPlaying back recorded audio...")
    player.play(audio_data, sample_rate, blocking=True)
    print("Playback complete")


def demo_file_handling(audio_data, sample_rate):
    """Demonstrate saving and loading audio files."""
    print("\n" + "=" * 60)
    print("DEMO: File Handling")
    print("=" * 60)
    
    handler = AudioFileHandler()
    
    # Save audio
    print("\nSaving audio to file...")
    file_path = handler.save(audio_data, sample_rate=sample_rate)
    print(f"Saved to: {file_path}")
    
    # Get file info
    info = handler.get_audio_info(file_path)
    print("\nAudio file information:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Load audio back
    print("\nLoading audio from file...")
    loaded_audio, loaded_sr = handler.load(file_path)
    print(f"Loaded {len(loaded_audio)} samples at {loaded_sr} Hz")
    
    # Play loaded audio
    print("\nPlaying loaded audio...")
    player = AudioPlayer()
    player.play(loaded_audio, loaded_sr, blocking=True)
    print("Playback complete")
    
    return file_path


def demo_test_tone():
    """Demonstrate playing a test tone."""
    print("\n" + "=" * 60)
    print("DEMO: Test Tone")
    print("=" * 60)
    
    player = AudioPlayer()
    
    print("\nPlaying test tone (440 Hz for 1 second)...")
    player.play_tone(frequency=440.0, duration=1.0, blocking=True)
    print("Test tone complete")


def main():
    """Run all demos."""
    print("=" * 60)
    print("Audio Input/Output System Demo")
    print("=" * 60)
    
    try:
        # Demo 1: List devices
        demo_devices()
        
        # Demo 2: Test tone
        demo_test_tone()
        
        # Demo 3: Record audio
        audio_data, sample_rate = demo_recording()
        
        if len(audio_data) > 0:
            # Demo 4: Playback
            demo_playback(audio_data, sample_rate)
            
            # Demo 5: File handling
            file_path = demo_file_handling(audio_data, sample_rate)
            
            print("\n" + "=" * 60)
            print("Demo Complete!")
            print("=" * 60)
            print(f"\nRecorded audio saved to: {file_path}")
        else:
            print("\nNo audio recorded. Demo ended.")
    
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
