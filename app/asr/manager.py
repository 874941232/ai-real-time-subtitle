"""ASR manager: local + Aliyun + Baidu (国内服务).

Modes:
  - local: SenseVoice only (offline, unlimited free)
  - aliyun: Aliyun online only
  - baidu: Baidu online only (永久免费)
  - auto: try configured online first, fall back to local on failure
"""
import time
import threading
import numpy as np
from typing import Optional, Callable
from .base import ASREngine
from .sensevoice_engine import SenseVoiceEngine


def _build_aliyun_safe(cfg):
    try:
        from .aliyun_engine import AliyunEngine
        if cfg.aliyun_access_key_id and cfg.aliyun_access_key_secret and cfg.aliyun_appkey:
            return AliyunEngine(cfg.aliyun_access_key_id, cfg.aliyun_access_key_secret, cfg.aliyun_appkey)
    except Exception:
        pass
    return None


def _build_baidu_safe(cfg):
    try:
        from .baidu_engine import BaiduEngine
        if cfg.baidu_api_key and cfg.baidu_secret_key:
            return BaiduEngine(cfg.baidu_api_key, cfg.baidu_secret_key)
    except Exception:
        pass
    return None


class ASRManager:
    def __init__(self, asr_cfg):
        self.cfg = asr_cfg
        self._lock = threading.Lock()
        self._current: Optional[ASREngine] = None
        self._current_name: str = ""
        self._err_count = 0
        self._max_err = 3
        self._status_cb: Optional[Callable[[str], None]] = None

    def set_status_callback(self, cb: Callable[[str], None]) -> None:
        self._status_cb = cb

    def _emit(self, msg: str) -> None:
        if self._status_cb:
            try:
                self._status_cb(msg)
            except Exception:
                pass

    def _build_local(self) -> ASREngine:
        return SenseVoiceEngine()

    def _build_aliyun(self) -> Optional[ASREngine]:
        return _build_aliyun_safe(self.cfg)

    def _build_baidu(self) -> Optional[ASREngine]:
        return _build_baidu_safe(self.cfg)

    def _engine_for(self) -> ASREngine:
        with self._lock:
            if self.cfg.mode == "local":
                self._current = self._build_local()
                self._current_name = self._current.name
                self._emit(f"使用引擎: 本地 {self._current_name} (离线无限量)")
            elif self.cfg.mode == "aliyun":
                eng = self._build_aliyun()
                if eng is None:
                    self._emit("未配置阿里云 Key，自动切到本地")
                    self._current = self._build_local()
                else:
                    self._current = eng
                self._current_name = self._current.name
                self._emit(f"使用引擎: {self._current_name}")
            elif self.cfg.mode == "baidu":
                eng = self._build_baidu()
                if eng is None:
                    self._emit("未配置百度 Key，自动切到本地")
                    self._current = self._build_local()
                else:
                    self._current = eng
                self._current_name = self._current.name
                self._emit(f"使用引擎: {self._current_name}")
            else:  # auto: 优先百度(免费)，其次阿里云，最后本地
                eng = self._build_baidu()
                if eng is not None:
                    self._current = eng
                    self._emit(f"使用引擎: 百度在线 {self._current.name}")
                else:
                    eng = self._build_aliyun()
                    if eng is not None:
                        self._current = eng
                        self._emit(f"使用引擎: 阿里云在线 {self._current.name}")
                    else:
                        self._current = self._build_local()
                        self._emit(f"使用引擎: 本地 {self._current.name} (未配置在线服务)")
                self._current_name = self._current.name
            self._err_count = 0
            return self._current

    @property
    def current_name(self) -> str:
        return self._current_name

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        if self._current is None:
            self._engine_for()
        assert self._current is not None
        try:
            text = self._current.transcribe(audio, sample_rate, self.cfg.language)
            with self._lock:
                self._err_count = 0
            return text
        except Exception as e:
            with self._lock:
                self._err_count += 1
                failed_name = self._current_name
                if self.cfg.mode == "auto" and self._current_name not in ("local", "sensevoice") and self._err_count >= self._max_err:
                    self._emit(f"在线服务连续失败，切换到本地: {e}")
                    self._current = self._build_local()
                    self._current_name = self._current.name
                    self._err_count = 0
                    return ""
            self._emit(f"识别失败 ({failed_name}): {e}")
            return ""
