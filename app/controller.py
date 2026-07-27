"""Controller: orchestrates audio capture -> ASR -> UI.

Runs a worker thread that pulls audio chunks, skips silent ones, calls the
ASR manager, and emits Qt signals on result.
"""
import threading
import time
import re
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from app.core.audio_capture import SystemAudioCapture
from app.asr.manager import ASRManager


class SubtitleController(QObject):
    status_changed = pyqtSignal(str)
    text_ready = pyqtSignal(str)         # final consolidated text (triggers scroll)
    partial_text = pyqtSignal(str)       # in-progress line (no scroll)
    engine_changed = pyqtSignal(str)

    MAX_SENTENCES = 3

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._capture = SystemAudioCapture(
            sample_rate=cfg.audio.sample_rate,
            channels=cfg.audio.channels,
            chunk_seconds=cfg.audio.chunk_seconds,
            device_name=cfg.audio.device_name,
        )
        self._capture.set_error_handler(self._on_audio_error)

        self.asr = ASRManager(cfg.asr)
        self.asr.set_status_callback(self._on_status)
        self.asr._engine_for()

        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._running = False
        self._sentences: list[str] = []    # list of completed sentences
        self._last_emitted = ""
        self._consecutive_silent = 0
        self._last_text = ""               # last chunk's text for dedup
        self._max_sentences = 20           # soft cap; window decides display count

    # ----- public -----
    @property
    def running(self) -> bool:
        return self._running

    @property
    def current_engine_name(self) -> str:
        return self.asr.current_name or "未启动"

    def update_config(self, cfg) -> None:
        was_running = self._running
        if was_running:
            self.stop()
        self.cfg = cfg
        self._capture = SystemAudioCapture(
            sample_rate=cfg.audio.sample_rate,
            channels=cfg.audio.channels,
            chunk_seconds=cfg.audio.chunk_seconds,
            device_name=cfg.audio.device_name,
        )
        self._capture.set_error_handler(self._on_audio_error)
        self.asr = ASRManager(cfg.asr)
        self.asr.set_status_callback(self._on_status)
        self.asr._engine_for()
        self.engine_changed.emit(self.asr.current_name or "未启动")
        if was_running:
            self.start()

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._sentences = []
        self._last_emitted = ""
        self._last_text = ""
        self._capture.start()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()
        self._running = True
        self._on_status(f"开始监听，设备={self._capture.device_name or '默认回采'}, 块={self._capture.chunk_seconds}s")
        self.engine_changed.emit(self.asr.current_name)

    def stop(self) -> None:
        if not self._running:
            return
        self._stop.set()
        self._capture.stop()
        if self._worker:
            self._worker.join(timeout=2.0)
            self._worker = None
        self._running = False
        self._on_status("已停止。")

    # ----- internals -----
    def _on_status(self, msg: str) -> None:
        self.status_changed.emit(msg)

    def _on_audio_error(self, msg: str) -> None:
        self._on_status(msg)
        self._running = False

    def _is_silent(self, audio: np.ndarray) -> bool:
        if audio.size == 0:
            return True
        rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
        return rms < self.cfg.audio.silence_threshold

    def _run(self) -> None:
        sr = self.cfg.audio.sample_rate
        self._consecutive_silent = 0
        while not self._stop.is_set():
            chunk = self._capture.get_chunk(timeout=0.5)
            if chunk is None:
                continue
            if self._is_silent(chunk):
                self._consecutive_silent += 1
                if self._consecutive_silent > 6 and self._sentences:
                    self._sentences = []
                    self._last_emitted = ""
                    self._last_text = ""
                    self.partial_text.emit("")
                    self.text_ready.emit("")
                continue
            self._consecutive_silent = 0
            try:
                text = self.asr.transcribe(chunk, sr)
            except Exception as e:
                self._on_status(f"识别异常: {e}")
                continue
            text = (text or "").strip()
            if not text:
                continue

            # Skip if identical to last chunk (avoid duplicate scrolling)
            if text == self._last_text:
                self.partial_text.emit(text)
                continue
            self._last_text = text

            # Show as partial immediately
            self.partial_text.emit(text)

            # Split new text into sentences and append
            new_parts = [s.strip() for s in re.split(r'(?<=[。！？!?\n])', text) if s.strip()]
            if not new_parts:
                new_parts = [text]

            # Append all new sentences
            for part in new_parts:
                # Skip if same as last sentence already in list
                if self._sentences and self._sentences[-1] == part:
                    continue
                self._sentences.append(part)

            # Keep only last _max_sentences (soft cap; display is window-driven)
            if len(self._sentences) > self._max_sentences:
                self._sentences = self._sentences[-self._max_sentences:]

            display = "\n".join(self._sentences)
            if display != self._last_emitted:
                self._last_emitted = display
                self.text_ready.emit(display)
