# Audio Input/Output System

## Overview

The Audio Input/Output System is a foundational component of the restaurant booking voice assistant that provides comprehensive audio recording, playback, and file management capabilities. This system serves as the infrastructure layer for speech recognition and text-to-speech functionality.

## Implementation Status

✅ **COMPLETE** - All components implemented and ready for use

## Architecture

The audio system is organized into modular components located in `src/audio/`:

```
src/audio/
├── __init__.py          # Main module exports
├── config.py            # Configuration management
├── recorder.py          # Audio recording from microphone
├── player.py            # Audio playback
├── file_handler.py      # File I/O operations
├── utils.py             # Audio processing utilities
├── demo.py              # Demonstration script
└── README.md            # Detailed documentation
```

## Core Components

### 1. AudioConfig (`config.py`)

Configuration dataclass for all audio operations:
- Sample rate (default: 16 kHz for speech)
- Number of channels (mono/stereo)
- Buffer/chunk size
- Silence detection parameters
- Recording limits
- File format preferences

### 2. AudioRecorder (`recorder.py`)

Microphone input handling with two modes:

**Blocking Mode:**
- Record for fixed duration
- Stop on silence detection
- Return complete audio array

**Streaming Mode:**
- Continuous recording with callbacks
- Real-time processing support
- Non-blocking operation

**Features:**
- Configurable silence detection
- Audio level monitoring
- Maximum recording duration limits
- Clean resource management

### 3. AudioPlayer (`player.py`)

Audio output/playback functionality:
- Play audio arrays
- Play audio files
- Blocking and non-blocking modes
- Test tone generation
- Playback control (stop, wait)

**Features:**
- Automatic format conversion
- Channel handling (mono/stereo)
- Thread-safe playback
- Volume control support

### 4. AudioFileHandler (`file_handler.py`)

File management and persistence:
- Save audio to WAV/FLAC/OGG formats
- Load audio from files
- Automatic timestamped filenames
- Format conversion
- File metadata retrieval

**Management Features:**
- List all recordings
- Delete recordings
- Cleanup old recordings
- Get audio file information

### 5. Audio Utilities (`utils.py`)

Audio processing and conversion functions:
- Format conversion (bytes ↔ numpy)
- Audio normalization/denormalization
- Resampling
- RMS (audio level) calculation
- Silence detection
- Device enumeration

## Usage Examples

### Basic Recording

```python
from audio import AudioRecorder

recorder = AudioRecorder()
audio_data = recorder.record(duration=5.0, stop_on_silence=True)
```

### Basic Playback

```python
from audio import AudioPlayer

player = AudioPlayer()
player.play(audio_data, sample_rate=16000, blocking=True)
```

### Save and Load

```python
from audio import AudioFileHandler

handler = AudioFileHandler()

# Save
file_path = handler.save(audio_data, sample_rate=16000)

# Load
audio_data, sample_rate = handler.load(file_path)
```

### Custom Configuration

```python
from audio import AudioRecorder, AudioConfig

config = AudioConfig(
    sample_rate=16000,
    channels=1,
    silence_threshold=0.02,
    silence_duration=2.0
)

recorder = AudioRecorder(config)
```

## Technical Specifications

### Audio Parameters

- **Sample Rate**: 16000 Hz (optimized for speech)
- **Channels**: 1 (mono) for speech, 2 (stereo) optional
- **Format**: int16 (2 bytes) or float32 (4 bytes)
- **Chunk Size**: 1024 frames (configurable)

### Supported File Formats

- **WAV**: Uncompressed (default, best compatibility)
- **FLAC**: Lossless compression
- **OGG**: Lossy compression (optional)

### Dependencies

- `sounddevice`: Cross-platform audio I/O
- `soundfile`: Audio file reading/writing
- `numpy`: Audio data manipulation

All dependencies are specified in `requirements.txt`.

## Key Features

### 1. Silence Detection

Automatically stops recording after detecting silence:
- Configurable RMS threshold
- Configurable silence duration
- Prevents unnecessary long recordings

### 2. Device Management

Query and select audio devices:
```python
from audio import print_audio_devices, get_audio_devices

print_audio_devices()  # List all devices
input_devs, output_devs = get_audio_devices()
```

### 3. Format Flexibility

Automatic format conversion:
- Between int16, int32, float32
- Between mono and stereo
- Between different sample rates

### 4. Resource Management

- Automatic cleanup of audio streams
- Context manager support via with statements
- Thread-safe operations
- Proper error handling

## Integration Points

This audio system provides the foundation for:

1. **Speech-to-Text**: Record user speech for transcription
2. **Text-to-Speech**: Play synthesized speech responses
3. **Audio Feedback**: Play confirmation tones and sounds
4. **Call Recording**: Save conversation history

## Testing

Run the demo script to verify the system:

```bash
python src/audio/demo.py
```

The demo performs:
1. Device enumeration
2. Test tone playback
3. Audio recording
4. Playback of recording
5. File save/load operations

## Performance Considerations

### Optimal Settings for Speech

```python
config = AudioConfig(
    sample_rate=16000,    # Good balance for speech
    channels=1,           # Mono sufficient for speech
    chunk_size=1024,      # Low latency
    format="int16"        # Lower memory usage
)
```

### Low Latency Settings

```python
config = AudioConfig(
    chunk_size=512,       # Smaller chunks = lower latency
    sample_rate=16000     # Lower rate = less processing
)
```

### High Quality Settings

```python
config = AudioConfig(
    sample_rate=44100,    # CD quality
    channels=2,           # Stereo
    format="float32"      # Better precision
)
```

## Error Handling

The system provides clear error messages for:
- Missing audio devices
- Permission issues
- File I/O errors
- Invalid audio data
- Configuration errors

Example:
```python
try:
    recorder = AudioRecorder()
    audio_data = recorder.record(duration=5.0)
except RuntimeError as e:
    print(f"Recording failed: {e}")
except KeyboardInterrupt:
    recorder.stop()
```

## Future Enhancements

Potential additions (not in current scope):
- Real-time audio effects
- Noise reduction/filtering
- Voice activity detection (VAD)
- Audio compression options
- Network audio streaming
- Multi-channel recording

## Documentation

- **Module README**: `src/audio/README.md` - Comprehensive API documentation
- **Demo Script**: `src/audio/demo.py` - Interactive examples
- **This Document**: Architecture and integration overview

## Compatibility

- **OS Support**: Windows, macOS, Linux (via sounddevice)
- **Python Version**: 3.10+
- **Audio Backends**: PortAudio (cross-platform)

## Status Summary

| Component | Status | Description |
|-----------|--------|-------------|
| AudioConfig | ✅ Complete | Configuration management |
| AudioRecorder | ✅ Complete | Microphone input with silence detection |
| AudioPlayer | ✅ Complete | Audio playback and test tones |
| AudioFileHandler | ✅ Complete | File save/load/management |
| Utilities | ✅ Complete | Audio processing functions |
| Documentation | ✅ Complete | README and examples |
| Demo | ✅ Complete | Interactive demonstration |

## Next Steps

With the Audio Input/Output System complete, the next components to implement are:

1. **Speech-to-Text Integration**: Use the recorder to capture speech and transcribe it
2. **Text-to-Speech System**: Use ElevenLabs to generate speech and play it back
3. **Voice Assistant Logic**: Combine audio I/O with LLM for conversational interface

The audio system is now ready to support these higher-level components.
