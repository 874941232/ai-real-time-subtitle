"""Capture system audio using WASAPI loopback (Windows).

Why soundcard: it uses the native Windows WASAPI loopback API to capture
whatever is playing on the speaker output, without needing to enable
"Stereo Mix" in the control panel.
"""
import threading
import queue
import numpy as np
from typing import Optional, Callable, List


def list_loopback_devices() -> List[str]:
    """Return human-readable names of available loopback devices."""
    try:
        import soundcard as sc
        return [m.name for m in sc.all_microphones(include_loopback=True)]
    except Exception:
        return []


class SystemAudioCapture:
    """Captures system audio into fixed-size float32 numpy arrays at 16 kHz mono."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_seconds: float = 3.0,
        device_name: str = "",
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_seconds = chunk_seconds
        self.chunk_frames = int(sample_rate * chunk_seconds)
        self.device_name = device_name
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=32)
        self._on_error: Optional[Callable[[str], None]] = None

    def set_error_handler(self, cb: Callable[[str], None]) -> None:
        self._on_error = cb

    def _resolve_mic(self):
        import soundcard as sc
        if self.device_name:
            for m in sc.all_microphones(include_loopback=True):
                if m.name == self.device_name:
                    return m
        # Pick the first available loopback (speaker) mic
        loopbacks = [m for m in sc.all_microphones(include_loopback=True) if m.isloopback]
        if loopbacks:
            return loopbacks[0]
        # Fall back to default mic
        return sc.default_microphone()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def get_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Pull one chunk of audio. Returns None on stop."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _run(self) -> None:
        try:
            import soundcard as sc
            mic = self._resolve_mic()
            if mic is None:
                raise RuntimeError("未找到可用的音频输入设备")
            # soundcard uses blocking recorder; we slice in fixed frame windows
            block_frames = 1024
            buffer = np.zeros((0, self.channels), dtype="float32")

            with mic.recorder(samplerate=self.sample_rate, channels=self.channels,
                              blocksize=block_frames) as rec:
                while not self._stop.is_set():
                    data = rec.record(numframes=block_frames)
                    # data: float64 in [-1, 1], shape (n, channels)
                    if data.size == 0:
                        continue
                    if data.dtype != np.float32:
                        data = data.astype(np.float32)
                    if data.ndim == 1:
                        data = data.reshape(-1, 1)
                    buffer = np.concatenate([buffer, data], axis=0)
                    while buffer.shape[0] >= self.chunk_frames:
                        chunk, buffer = buffer[:self.chunk_frames], buffer[self.chunk_frames:]
                        chunk_mono = chunk[:, 0] if self.channels == 1 else chunk.mean(axis=1)
                        try:
                            self._queue.put_nowait(chunk_mono.copy())
                        except queue.Full:
                            # drop oldest to keep latency low
                            try:
                                self._queue.get_nowait()
                                self._queue.put_nowait(chunk_mono.copy())
                            except queue.Empty:
                                pass
        except Exception as e:
            if self._on_error:
                self._on_error(f"音频采集出错: {e}")
