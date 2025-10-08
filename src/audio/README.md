# Audio Input/Output System

A comprehensive audio recording and playback system for the restaurant booking voice assistant.

## Overview

This module provides all the necessary functionality for capturing audio from a microphone, playing audio through speakers, and managing audio files. It's built on top of `sounddevice` and `soundfile` libraries for reliable cross-platform audio handling.

## Features

- **Audio Recording**: Record audio from microphone with silence detection
- **Audio Playback**: Play audio with support for various formats
- **File Management**: Save and load audio files (WAV, FLAC, OGG)
- **Audio Processing**: Convert formats, resample, normalize audio
- **Device Management**: Query and select audio input/output devices
- **Configurable**: Flexible configuration for all audio parameters

## Components

### AudioConfig

Configuration class for audio operations.

```python
from audio import AudioConfig

config = AudioConfig(
    sample_rate=16000,      # 16 kHz for speech
    channels=1,              # Mono audio
    chunk_size=1024,         # Buffer size
    silence_threshold=0.01,  # Silence detection threshold
    silence_duration=2.0     # Stop after 2s of silence
)
```

### AudioRecorder

Record audio from microphone.

```python
from audio import AudioRecorder, AudioConfig

# Create recorder with custom config
config = AudioConfig(sample_rate=16000, channels=1)
recorder = AudioRecorder(config)

# Record for 5 seconds or until silence
audio_data = recorder.record(
    duration=5.0,
    stop_on_silence=True
)

# Streaming mode with callback
def on_audio_chunk(chunk):
    print(f"Received {len(chunk)} samples")

recorder.start_streaming(callback=on_audio_chunk)
# ... do other work ...
recorder.stop_streaming()
```

### AudioPlayer

Play audio through speakers.

```python
from audio import AudioPlayer
import numpy as np

player = AudioPlayer()

# Play audio array (blocking)
player.play(audio_data, sample_rate=16000, blocking=True)

# Play audio file
player.play_file("recording.wav", blocking=False)
player.wait()  # Wait for completion

# Play test tone
player.play_tone(frequency=440.0, duration=1.0)

# Stop playback
player.stop()
```

### AudioFileHandler

Save and load audio files.

```python
from audio import AudioFileHandler

handler = AudioFileHandler()

# Save audio (auto-generates timestamped filename)
file_path = handler.save(audio_data, sample_rate=16000)

# Save with specific filename
file_path = handler.save(
    audio_data,
    file_path="my_recording.wav",
    sample_rate=16000,
    format="wav"
)

# Load audio
audio_data, sample_rate = handler.load("recording.wav")

# Get audio file info
info = handler.get_audio_info("recording.wav")
print(f"Duration: {info['duration']} seconds")
print(f"Sample rate: {info['sample_rate']} Hz")

# List all recordings
recordings = handler.list_recordings()
for rec in recordings:
    print(f"{rec['file_name']}: {rec['duration']:.2f}s")

# Convert format
handler.convert_format(
    "recording.wav",
    "recording.flac",
    target_format="flac"
)

# Clean up old recordings
deleted = handler.cleanup_old_recordings(days=7)
```

## Utility Functions

```python
from audio import (
    normalize_audio,
    denormalize_audio,
    resample_audio,
    calculate_rms,
    detect_silence,
    get_audio_devices,
    print_audio_devices
)

# Normalize audio to float32 [-1.0, 1.0]
audio_float = normalize_audio(audio_int16)

# Convert back to int16
audio_int16 = denormalize_audio(audio_float, target_dtype="int16")

# Resample audio
audio_16k = resample_audio(audio_44k, orig_sample_rate=44100, target_sample_rate=16000)

# Calculate audio level
rms = calculate_rms(audio_data)
print(f"Audio level: {rms:.3f}")

# Detect silence
is_silent = detect_silence(audio_data, threshold=0.01)

# List audio devices
print_audio_devices()
input_devs, output_devs = get_audio_devices()
```

## Quick Start

### Basic Recording and Playback

```python
from audio import AudioRecorder, AudioPlayer

# Record audio
recorder = AudioRecorder()
print("Recording... (speak now)")
audio_data = recorder.record(duration=5.0)

# Play it back
player = AudioPlayer()
print("Playing back...")
player.play(audio_data, blocking=True)
```

### Record and Save

```python
from audio import AudioRecorder, AudioFileHandler

# Record
recorder = AudioRecorder()
audio_data = recorder.record(duration=5.0, stop_on_silence=True)

# Save
handler = AudioFileHandler()
file_path = handler.save(audio_data)
print(f"Saved to: {file_path}")
```

### Load and Play

```python
from audio import AudioFileHandler, AudioPlayer

# Load
handler = AudioFileHandler()
audio_data, sample_rate = handler.load("recording.wav")

# Play
player = AudioPlayer()
player.play(audio_data, sample_rate, blocking=True)
```

## Demo

Run the demo script to see all features in action:

```bash
python src/audio/demo.py
```

The demo will:
1. List available audio devices
2. Play a test tone
3. Record audio from your microphone
4. Play back the recording
5. Save the recording to a file
6. Load and play the saved file

## Configuration

### Environment Variables

Audio recordings are saved to the `audio_save_path` directory (default: `audio_recordings/`).

### Sample Rates

- **16000 Hz**: Recommended for speech recognition (balances quality and performance)
- **22050 Hz**: Good for general audio
- **44100 Hz**: CD quality (overkill for speech)
- **48000 Hz**: Professional audio

### Audio Formats

Supported formats via `soundfile`:
- **WAV**: Uncompressed, best for processing (default)
- **FLAC**: Lossless compression
- **OGG**: Lossy compression (requires additional setup)

### Silence Detection

Adjust silence detection parameters:

```python
config = AudioConfig(
    silence_threshold=0.01,  # Lower = more sensitive
    silence_duration=2.0,    # Seconds of silence before stopping
)
```

## Dependencies

- `sounddevice`: Audio I/O
- `soundfile`: Audio file reading/writing
- `numpy`: Audio data manipulation

All dependencies are listed in `requirements.txt`.

## Error Handling

```python
from audio import AudioRecorder

recorder = AudioRecorder()

try:
    audio_data = recorder.record(duration=5.0)
except RuntimeError as e:
    print(f"Recording error: {e}")
except KeyboardInterrupt:
    print("Recording cancelled")
    recorder.stop()
```

## Thread Safety

- `AudioRecorder` and `AudioPlayer` are NOT thread-safe
- Use separate instances for concurrent operations
- Streaming mode uses internal threads safely

## Performance Tips

1. **Chunk Size**: Larger chunks reduce CPU usage but increase latency
2. **Sample Rate**: Use 16kHz for speech (lower CPU usage)
3. **Channels**: Use mono (1 channel) for speech recognition
4. **Format**: Use int16 for lower memory usage, float32 for better processing

## Integration Example

```python
from audio import AudioRecorder, AudioFileHandler, AudioConfig

class VoiceAssistant:
    def __init__(self):
        self.config = AudioConfig(
            sample_rate=16000,
            channels=1,
            silence_threshold=0.02,
            silence_duration=1.5
        )
        self.recorder = AudioRecorder(self.config)
        self.file_handler = AudioFileHandler(self.config)
    
    def listen(self):
        """Record user speech."""
        print("Listening...")
        audio_data = self.recorder.record(
            duration=10.0,
            stop_on_silence=True
        )
        
        # Save recording
        file_path = self.file_handler.save(audio_data)
        return audio_data, file_path
    
    def process_audio(self, audio_data):
        """Process recorded audio (implement speech recognition here)."""
        # TODO: Add speech recognition
        pass
```

## Troubleshooting

### No Audio Devices Found

```bash
# Check if sounddevice can find devices
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Permission Errors

On some systems, you may need to grant microphone permissions to Python.

### PortAudio Errors

If you get PortAudio-related errors, you may need to install system audio libraries:

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev
```

**macOS:**
```bash
brew install portaudio
```

**Windows:**
PortAudio is included with the pyaudio/sounddevice packages.

### Recording Quality Issues

- Check microphone levels in system settings
- Adjust `silence_threshold` for your environment
- Increase `chunk_size` if audio is choppy
- Ensure correct audio device is selected

## License

Part of the Restaurant Booking Voice Assistant System.
