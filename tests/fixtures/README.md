# Test Fixtures

This directory contains test fixtures including sample audio files for testing the audio and speech systems.

## Audio Files

The following sample audio files are used in tests:

- `sample_audio_clear.wav` - Clear audio (440Hz sine wave, 2 seconds)
- `sample_audio_unclear.wav` - Noisy/unclear audio (random noise, 2 seconds)
- `sample_audio_silence.wav` - Silent audio (2 seconds of silence)
- `sample_audio_mixed.wav` - Mixed audio (1 second tone + 1 second silence)

## Generating Audio Files

To generate the sample audio files, run:

```bash
python generate_audio.py
```

This will create all required WAV files in this directory.

## Usage in Tests

These audio files are used by various test modules:

- `test_audio_system.py` - Testing audio playback and recording
- `test_stt_tts.py` - Testing speech-to-text with different audio qualities
- `test_end_to_end.py` - End-to-end integration tests

The fixtures are loaded using pytest fixtures defined in `conftest.py`.
