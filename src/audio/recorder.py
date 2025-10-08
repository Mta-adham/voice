"""
Audio recording functionality for capturing microphone input.
"""
import numpy as np
import sounddevice as sd
from typing import Optional, Callable
import time
import threading
from queue import Queue

from .config import AudioConfig, default_config
from .utils import calculate_rms, detect_silence


class AudioRecorder:
    """
    Audio recorder for capturing microphone input.
    
    Supports both blocking (record until duration/silence) and streaming modes.
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize the audio recorder.
        
        Args:
            config: Audio configuration. If None, uses default config.
        """
        self.config = config or default_config
        self._recording = False
        self._audio_data: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: Queue = Queue()
        
    def record(
        self, 
        duration: Optional[float] = None,
        stop_on_silence: bool = True,
        callback: Optional[Callable[[np.ndarray], None]] = None
    ) -> np.ndarray:
        """
        Record audio from microphone (blocking mode).
        
        Args:
            duration: Recording duration in seconds. If None, records until silence
                     or max_recording_duration is reached.
            stop_on_silence: If True, stops recording after silence_duration seconds of silence
            callback: Optional callback function called with each audio chunk
            
        Returns:
            Recorded audio as numpy array
        """
        self._audio_data = []
        self._recording = True
        
        start_time = time.time()
        silence_start: Optional[float] = None
        
        max_duration = duration if duration is not None else self.config.max_recording_duration
        silence_samples = int(self.config.sample_rate * self.config.silence_duration)
        
        def audio_callback(indata, frames, time_info, status):
            """Callback function for audio stream."""
            if status:
                print(f"Recording status: {status}")
            
            # Copy audio data
            audio_chunk = indata.copy().flatten()
            self._audio_data.append(audio_chunk)
            
            # Call user callback if provided
            if callback:
                callback(audio_chunk)
        
        try:
            # Start recording stream
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.get_numpy_dtype(),
                blocksize=self.config.chunk_size,
                device=self.config.input_device,
                callback=audio_callback
            ):
                print("Recording started...")
                
                while self._recording:
                    elapsed = time.time() - start_time
                    
                    # Check max duration
                    if elapsed >= max_duration:
                        print(f"Max duration ({max_duration}s) reached")
                        break
                    
                    # Check for silence if enabled
                    if stop_on_silence and len(self._audio_data) > 0:
                        # Combine recent audio for silence detection
                        recent_audio = np.concatenate(self._audio_data)
                        
                        if detect_silence(
                            recent_audio, 
                            self.config.silence_threshold,
                            silence_samples
                        ):
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start >= self.config.silence_duration:
                                print(f"Silence detected for {self.config.silence_duration}s")
                                break
                        else:
                            silence_start = None
                    
                    # Small sleep to prevent busy waiting
                    time.sleep(0.1)
                
                print("Recording stopped")
        
        finally:
            self._recording = False
        
        # Combine all audio chunks
        if len(self._audio_data) > 0:
            return np.concatenate(self._audio_data)
        else:
            return np.array([], dtype=self.config.get_numpy_dtype())
    
    def start_streaming(
        self, 
        callback: Callable[[np.ndarray], None],
        buffer_size: int = 10
    ) -> None:
        """
        Start streaming audio from microphone (non-blocking mode).
        
        Args:
            callback: Callback function called with each audio chunk
            buffer_size: Maximum number of chunks to buffer
        """
        if self._recording:
            raise RuntimeError("Recording already in progress")
        
        self._recording = True
        self._audio_queue = Queue(maxsize=buffer_size)
        
        def audio_callback(indata, frames, time_info, status):
            """Callback for audio stream."""
            if status:
                print(f"Streaming status: {status}")
            
            audio_chunk = indata.copy().flatten()
            
            try:
                self._audio_queue.put_nowait(audio_chunk)
            except:
                # Queue full, skip this chunk
                pass
        
        def process_stream():
            """Process audio chunks from queue."""
            while self._recording:
                try:
                    audio_chunk = self._audio_queue.get(timeout=0.1)
                    callback(audio_chunk)
                except:
                    continue
        
        # Start audio stream
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.get_numpy_dtype(),
            blocksize=self.config.chunk_size,
            device=self.config.input_device,
            callback=audio_callback
        )
        self._stream.start()
        
        # Start processing thread
        self._process_thread = threading.Thread(target=process_stream, daemon=True)
        self._process_thread.start()
        
        print("Streaming started...")
    
    def stop_streaming(self) -> None:
        """Stop streaming audio."""
        if not self._recording:
            return
        
        self._recording = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        print("Streaming stopped")
    
    def stop(self) -> None:
        """Stop recording (for blocking mode)."""
        self._recording = False
    
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
    
    def get_audio_level(self) -> float:
        """
        Get current audio input level (RMS).
        
        Returns:
            Audio level (0.0 to 1.0)
        """
        if len(self._audio_data) == 0:
            return 0.0
        
        recent_audio = self._audio_data[-1] if len(self._audio_data) > 0 else np.array([])
        return calculate_rms(recent_audio)
