"""Abstract ASR engine interface."""
from abc import ABC, abstractmethod
import io
import struct
import numpy as np


class ASREngine(ABC):
    name: str = "base"

    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int, language: str = "zh") -> str:
        """Synchronously transcribe one chunk of float32 mono audio in [-1, 1].

        Return an empty string if the audio is silent or no speech detected.
        Raise on transport errors so the manager can mark this engine unhealthy.
        """
        raise NotImplementedError


def _to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Convert float32 numpy array in [-1, 1] to 16-bit PCM WAV bytes."""
    if audio.dtype != np.int16:
        audio = np.clip(audio, -1.0, 1.0)
        audio = (audio * 32767).astype(np.int16)
    buf = io.BytesIO()
    n_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * n_channels * bits_per_sample // 8
    block_align = n_channels * bits_per_sample // 8
    data_size = len(audio) * 2
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))
    buf.write(struct.pack("<H", 1))
    buf.write(struct.pack("<H", n_channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", byte_rate))
    buf.write(struct.pack("<H", block_align))
    buf.write(struct.pack("<H", bits_per_sample))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(audio.tobytes())
    return buf.getvalue()
