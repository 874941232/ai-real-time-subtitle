"""Configuration management - persists to config.ini next to the exe."""
import configparser
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional


def _exe_dir() -> Path:
    """Return directory of the running exe (or project root in dev)."""
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


CONFIG_PATH = _exe_dir() / "config.ini"


@dataclass
class ASRConfig:
    # mode: local = only SenseVoice (offline, unlimited free)
    #       aliyun = Aliyun online only
    #       baidu = Baidu online only (永久免费)
    #       auto = try online first, fall back to local on failure
    mode: str = "local"
    # Aliyun (国内, 有每日免费额度)
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""
    aliyun_appkey: str = ""
    # Baidu (国内, 永久免费)
    baidu_api_key: str = ""
    baidu_secret_key: str = ""
    local_model: str = "sensevoice"
    language: str = "zh"        # zh | en | auto


@dataclass
class UISubtitleConfig:
    font_family: str = "Microsoft YaHei"
    font_size: int = 28
    text_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    bg_color: str = "#80000000"   # 50% black
    opacity: float = 0.85
    position: str = "bottom"      # top | middle | bottom
    max_lines: int = 3


@dataclass
class AudioConfig:
    device_name: str = ""         # empty = default loopback
    sample_rate: int = 16000
    channels: int = 1
    chunk_seconds: float = 3.0    # how much audio per ASR request
    silence_threshold: float = 0.01  # RMS below this is treated as silence


@dataclass
class AppConfig:
    asr: ASRConfig = field(default_factory=ASRConfig)
    subtitle: UISubtitleConfig = field(default_factory=UISubtitleConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)


def load() -> AppConfig:
    cfg = AppConfig()
    if not CONFIG_PATH.exists():
        return cfg
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")

    def get(section, key, default=""):
        return parser.get(section, key, fallback=default)

    cfg.asr.mode = get("asr", "mode", cfg.asr.mode)
    cfg.asr.aliyun_access_key_id = get("asr", "aliyun_access_key_id", cfg.asr.aliyun_access_key_id)
    cfg.asr.aliyun_access_key_secret = get("asr", "aliyun_access_key_secret", cfg.asr.aliyun_access_key_secret)
    cfg.asr.aliyun_appkey = get("asr", "aliyun_appkey", cfg.asr.aliyun_appkey)
    cfg.asr.baidu_api_key = get("asr", "baidu_api_key", cfg.asr.baidu_api_key)
    cfg.asr.baidu_secret_key = get("asr", "baidu_secret_key", cfg.asr.baidu_secret_key)
    cfg.asr.local_model = get("asr", "local_model", cfg.asr.local_model)
    cfg.asr.language = get("asr", "language", cfg.asr.language)

    cfg.subtitle.font_family = get("subtitle", "font_family", cfg.subtitle.font_family)
    cfg.subtitle.font_size = int(get("subtitle", "font_size", str(cfg.subtitle.font_size)))
    cfg.subtitle.text_color = get("subtitle", "text_color", cfg.subtitle.text_color)
    cfg.subtitle.outline_color = get("subtitle", "outline_color", cfg.subtitle.outline_color)
    cfg.subtitle.bg_color = get("subtitle", "bg_color", cfg.subtitle.bg_color)
    cfg.subtitle.opacity = float(get("subtitle", "opacity", str(cfg.subtitle.opacity)))
    cfg.subtitle.position = get("subtitle", "position", cfg.subtitle.position)
    cfg.subtitle.max_lines = int(get("subtitle", "max_lines", str(cfg.subtitle.max_lines)))

    cfg.audio.device_name = get("audio", "device_name", cfg.audio.device_name)
    cfg.audio.sample_rate = int(get("audio", "sample_rate", str(cfg.audio.sample_rate)))
    cfg.audio.channels = int(get("audio", "channels", str(cfg.audio.channels)))
    cfg.audio.chunk_seconds = float(get("audio", "chunk_seconds", str(cfg.audio.chunk_seconds)))
    cfg.audio.silence_threshold = float(get("audio", "silence_threshold", str(cfg.audio.silence_threshold)))
    return cfg


def save(cfg: AppConfig) -> None:
    parser = configparser.ConfigParser()

    def put(section, key, val):
        if not parser.has_section(section):
            parser.add_section(section)
        parser.set(section, key, str(val))

    put("asr", "mode", cfg.asr.mode)
    put("asr", "aliyun_access_key_id", cfg.asr.aliyun_access_key_id)
    put("asr", "aliyun_access_key_secret", cfg.asr.aliyun_access_key_secret)
    put("asr", "aliyun_appkey", cfg.asr.aliyun_appkey)
    put("asr", "baidu_api_key", cfg.asr.baidu_api_key)
    put("asr", "baidu_secret_key", cfg.asr.baidu_secret_key)
    put("asr", "local_model", cfg.asr.local_model)
    put("asr", "language", cfg.asr.language)

    put("subtitle", "font_family", cfg.subtitle.font_family)
    put("subtitle", "font_size", cfg.subtitle.font_size)
    put("subtitle", "text_color", cfg.subtitle.text_color)
    put("subtitle", "outline_color", cfg.subtitle.outline_color)
    put("subtitle", "bg_color", cfg.subtitle.bg_color)
    put("subtitle", "opacity", cfg.subtitle.opacity)
    put("subtitle", "position", cfg.subtitle.position)
    put("subtitle", "max_lines", cfg.subtitle.max_lines)

    put("audio", "device_name", cfg.audio.device_name)
    put("audio", "sample_rate", cfg.audio.sample_rate)
    put("audio", "channels", cfg.audio.channels)
    put("audio", "chunk_seconds", cfg.audio.chunk_seconds)
    put("audio", "silence_threshold", cfg.audio.silence_threshold)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        parser.write(f)
