"""SenseVoice-Small ONNX 本地引擎 — 中文主力识别。

阿里达摩院开源，中文识别准确率远超 Whisper，模型仅 ~230MB。
使用 onnxruntime 推理，无需 torch/funasr 等重型依赖。

模型下载地址：https://www.modelscope.cn/models/iic/SenseVoice-Small-ONNX
首次运行时自动从 hf-mirror.com 或 modelscope 下载。
"""
import os
import json
import threading
import numpy as np
from pathlib import Path
from .base import ASREngine

# Default mirror for mainland China
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

MODEL_DIR_NAME = "SenseVoice-Small-ONNX"

REPO = "iic/SenseVoiceSmall-onnx"
BASE_URL = f"https://www.modelscope.cn/api/v1/models/{REPO}/repo"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _model_dir() -> Path:
    """Return the directory where the ONNX model files are stored.

    Priority:
    1. Next to the exe (for portable distribution)
    2. Next to the project source (for development)
    3. ModelScope cache directory
    """
    import sys
    # 1. Check next to the exe (frozen / pyinstaller)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        local = exe_dir / MODEL_DIR_NAME
        if (local / "model.onnx").exists():
            return local
    # 2. Check next to project source (development)
    project = Path(__file__).resolve().parents[3]
    local = project / MODEL_DIR_NAME
    if (local / "model.onnx").exists():
        return local
    # 3. Check ModelScope cache
    candidates = [
        Path.home() / ".cache" / "modelscope" / "hub" / "iic" / MODEL_DIR_NAME,
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            if (c / "model.onnx").exists():
                return c
            snaps = sorted([p for p in c.iterdir() if p.is_dir()])
            for snap in reversed(snaps):
                if (snap / "model.onnx").exists():
                    return snap
    return None


def _download_model() -> Path:
    """Download the SenseVoice ONNX model from ModelScope official repo.

    Downloads to the exe's directory (if frozen) or project root,
    so the model folder can be shared with colleagues.
    """
    import requests, sys

    # Determine download target: prefer exe dir (for distribution), then project dir
    if getattr(sys, "frozen", False):
        target = Path(sys.executable).parent / MODEL_DIR_NAME
    else:
        target = Path(__file__).resolve().parents[3] / MODEL_DIR_NAME
    target.mkdir(parents=True, exist_ok=True)

    REPO = "iic/SenseVoiceSmall-onnx"
    base_url = f"https://www.modelscope.cn/api/v1/models/{REPO}/repo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    files_map = [
        ("model_quant.onnx", "model.onnx"),
        ("tokens.json", "tokens.json"),
        ("config.yaml", "config.yaml"),
    ]

    # Try direct API download
    failed = []
    for repo_file, save_name in files_map:
        out = target / save_name
        if out.exists():
            continue
        url = f"{base_url}?Revision=master&FilePath={repo_file}"
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=120)
            if r.status_code == 200:
                with open(out, "wb") as fw:
                    for chunk in r.iter_content(chunk_size=8192):
                        fw.write(chunk)
            else:
                failed.append(repo_file)
        except Exception:
            failed.append(repo_file)

    # Convert tokens.json -> tokens.txt
    json_path = target / "tokens.json"
    txt_path = target / "tokens.txt"
    if json_path.exists() and not txt_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tokens = []
            if isinstance(data, dict):
                for k in sorted(data.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
                    tokens.append(str(data[k]))
            elif isinstance(data, list):
                tokens = [str(t) for t in data]
            with open(txt_path, "w", encoding="utf-8") as f:
                for t in tokens:
                    f.write(t + "\n")
        except Exception:
            pass

    # Convert config.yaml -> config.json
    yaml_path = target / "config.yaml"
    cfg_path = target / "config.json"
    if yaml_path.exists() and not cfg_path.exists():
        try:
            import yaml
            with open(yaml_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            lang_map = {}
            if isinstance(cfg, dict) and "model_conf" in cfg:
                lang_map = cfg["model_conf"].get("language", {})
            if not lang_map:
                lang_map = {"zh": 0, "en": 1, "yue": 2, "ja": 3, "ko": 4}
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"language": lang_map}, f, ensure_ascii=False, indent=2)
        except ImportError:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"language": {"zh": 0, "en": 1, "yue": 2, "ja": 3, "ko": 4}}, f)
        except Exception:
            pass

    # Fallback: use modelscope SDK
    if failed:
        try:
            from modelscope.hub.snapshot_download import snapshot_download
            sdk_dir = snapshot_download(REPO, cache_dir=str(target.parent.parent))
            sdk_path = Path(sdk_dir)
            for src_name, dst_name in files_map:
                src = sdk_path / src_name
                dst = target / dst_name
                if src.exists() and not dst.exists():
                    import shutil
                    shutil.copy2(str(src), str(dst))
        except Exception as e:
            raise RuntimeError(
                f"下载 SenseVoice 模型失败。请手动运行: python download_model.py\n"
                f"或直接安装 modelscope: pip install modelscope\n错误: {e}"
            )
    return target


def check_model_update() -> dict:
    """Check if a newer model version is available on ModelScope.

    Returns:
        dict with keys: 'has_update', 'local_size', 'remote_size', 'model_path'
    """
    import requests
    model_dir = _model_dir()
    if model_dir is None:
        return {"has_update": False, "local_size": 0, "remote_size": 0, "model_path": None}

    local_model = model_dir / "model.onnx"
    local_size = local_model.stat().st_size if local_model.exists() else 0

    try:
        url = f"{BASE_URL}?Revision=master&FilePath=model_quant.onnx"
        r = requests.head(url, headers=HEADERS, timeout=30)
        remote_size = int(r.headers.get("Content-Length", 0)) if r.status_code == 200 else 0
    except Exception:
        remote_size = 0

    has_update = remote_size > local_size if local_size > 0 else False

    return {
        "has_update": has_update,
        "local_size": local_size,
        "remote_size": remote_size,
        "model_path": str(model_dir),
    }


def update_model() -> bool:
    """Force download and update the model files.

    Returns:
        True if update succeeded, False otherwise.
    """
    import requests, sys, shutil

    if getattr(sys, "frozen", False):
        target = Path(sys.executable).parent / MODEL_DIR_NAME
    else:
        target = Path(__file__).resolve().parents[3] / MODEL_DIR_NAME

    files_map = [
        ("model_quant.onnx", "model.onnx"),
        ("tokens.json", "tokens.json"),
        ("config.yaml", "config.yaml"),
    ]

    try:
        for repo_file, save_name in files_map:
            out = target / save_name
            url = f"{BASE_URL}?Revision=master&FilePath={repo_file}"
            r = requests.get(url, headers=HEADERS, stream=True, timeout=120)
            if r.status_code == 200:
                with open(out, "wb") as fw:
                    for chunk in r.iter_content(chunk_size=8192):
                        fw.write(chunk)

        json_path = target / "tokens.json"
        txt_path = target / "tokens.txt"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tokens = []
            if isinstance(data, dict):
                for k in sorted(data.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
                    tokens.append(str(data[k]))
            elif isinstance(data, list):
                tokens = [str(t) for t in data]
            with open(txt_path, "w", encoding="utf-8") as f:
                for t in tokens:
                    f.write(t + "\n")

        yaml_path = target / "config.yaml"
        cfg_path = target / "config.json"
        if yaml_path.exists():
            try:
                import yaml
                with open(yaml_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                lang_map = {}
                if isinstance(cfg, dict) and "model_conf" in cfg:
                    lang_map = cfg["model_conf"].get("language", {})
                if not lang_map:
                    lang_map = {"zh": 0, "en": 1, "yue": 2, "ja": 3, "ko": 4}
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump({"language": lang_map}, f, ensure_ascii=False, indent=2)
            except ImportError:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump({"language": {"zh": 0, "en": 1, "yue": 2, "ja": 3, "ko": 4}}, f)

        return True
    except Exception as e:
        raise RuntimeError(f"更新模型失败: {e}")


class SenseVoiceEngine(ASREngine):
    name = "sensevoice"
    _instance_cache = {}
    _lock = threading.Lock()

    # Feature extraction config (from config.yaml)
    FS = 16000
    N_MELS = 80
    FRAME_LENGTH = 400   # 25ms @ 16kHz
    FRAME_SHIFT = 160    # 10ms @ 16kHz
    N_FFT = 512
    LFR_M = 7
    LFR_N = 6

    def __init__(self):
        self._mel_fb = None

    def _get_mel_filterbank(self):
        if self._mel_fb is not None:
            return self._mel_fb
        # Build mel filterbank [n_mels, n_fft//2+1]
        f_min = 0.0
        f_max = self.FS / 2.0
        mel_min = 2595.0 * np.log10(1.0 + f_min / 700.0)
        mel_max = 2595.0 * np.log10(1.0 + f_max / 700.0)
        mels = np.linspace(mel_min, mel_max, self.N_MELS + 2)
        freqs = 700.0 * (10.0 ** (mels / 2595.0) - 1.0)
        fft_freqs = np.linspace(0, self.FS / 2.0, self.N_FFT // 2 + 1)
        filters = np.zeros((self.N_MELS, self.N_FFT // 2 + 1))
        for i in range(self.N_MELS):
            left, center, right = freqs[i], freqs[i + 1], freqs[i + 2]
            for j, f in enumerate(fft_freqs):
                if left <= f <= center:
                    filters[i, j] = (f - left) / (center - left + 1e-10)
                elif center < f <= right:
                    filters[i, j] = (right - f) / (right - center + 1e-10)
        self._mel_fb = filters
        return filters

    def _extract_fbank(self, audio: np.ndarray) -> np.ndarray:
        """Extract 80-dim FBank features from 16kHz mono audio."""
        audio = audio.astype(np.float32)
        # 1. Pre-emphasis
        audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])
        # 2. Framing
        n_samples = len(audio)
        n_frames = 1 + (n_samples - self.FRAME_LENGTH) // self.FRAME_SHIFT
        if n_frames <= 0:
            n_frames = 1
        frames = np.zeros((n_frames, self.FRAME_LENGTH), dtype=np.float32)
        for i in range(n_frames):
            start = i * self.FRAME_SHIFT
            end = start + self.FRAME_LENGTH
            if end <= n_samples:
                frames[i] = audio[start:end]
            else:
                frames[i, :n_samples - start] = audio[start:]
        # 3. Hamming window
        window = 0.54 - 0.46 * np.cos(2.0 * np.pi * np.arange(self.FRAME_LENGTH) / (self.FRAME_LENGTH - 1))
        frames *= window
        # 4. FFT & power spectrum
        fft = np.fft.rfft(frames, n=self.N_FFT)
        power = np.abs(fft) ** 2
        # 5. Mel filterbank
        mel_fb = self._get_mel_filterbank()
        mel_spec = np.dot(power, mel_fb.T)
        # 6. Log
        fbank = np.log(mel_spec + 1e-10)
        return fbank

    def _apply_lfr(self, feats: np.ndarray) -> np.ndarray:
        """Apply LFR (Low Frame Rate): concat lfr_m frames, stride lfr_n."""
        T = feats.shape[0]
        if T < self.LFR_M:
            # Pad with zeros to reach minimum length
            pad = np.zeros((self.LFR_M - T, feats.shape[1]), dtype=np.float32)
            feats = np.vstack([feats, pad])
            T = self.LFR_M
        T_lfr = (T - self.LFR_M) // self.LFR_N + 1
        out = np.zeros((T_lfr, feats.shape[1] * self.LFR_M), dtype=np.float32)
        for i in range(T_lfr):
            start = i * self.LFR_N
            out[i] = feats[start:start + self.LFR_M].flatten()
        return out

    def _get_session(self):
        with SenseVoiceEngine._lock:
            if "session" in SenseVoiceEngine._instance_cache:
                return SenseVoiceEngine._instance_cache
            import onnxruntime as ort

            model_dir = _model_dir()
            if model_dir is None:
                model_dir = _download_model()

            onnx_path = model_dir / "model.onnx"
            if not onnx_path.exists():
                raise FileNotFoundError(f"SenseVoice ONNX 模型未找到: {onnx_path}")

            session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

            # Load tokens
            tokens_path = model_dir / "tokens.txt"
            token_list = []
            if tokens_path.exists():
                with open(tokens_path, "r", encoding="utf-8") as f:
                    for line in f:
                        token_list.append(line.strip())

            # Load config for language tokens
            config_path = model_dir / "config.json"
            lang_map = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    lang_map = cfg.get("language", {})

            SenseVoiceEngine._instance_cache = {
                "session": session,
                "tokens": token_list,
                "lang_map": lang_map,
            }
            return SenseVoiceEngine._instance_cache

    def transcribe(self, audio: np.ndarray, sample_rate: int, language: str = "zh") -> str:
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            try:
                import resampy
                audio = resampy.resample(audio, sample_rate, 16000)
            except ImportError:
                ratio = 16000.0 / sample_rate
                old_len = len(audio)
                new_len = int(old_len * ratio)
                indices = np.linspace(0, old_len - 1, new_len)
                audio = np.interp(indices, np.arange(old_len), audio).astype(np.float32)

        audio = audio.astype(np.float32)

        # Ensure minimum length (~0.5s at 16kHz)
        if len(audio) < 8000:
            audio = np.pad(audio, (0, 8000 - len(audio)))

        # Extract FBank + LFR features
        fbank = self._extract_fbank(audio)
        feats = self._apply_lfr(fbank)

        cache = self._get_session()
        session = cache["session"]
        tokens = cache["tokens"]
        lang_map = cache["lang_map"]

        # Language ID mapping
        lang_ids = {"auto": 0, "zh": 1, "en": 2, "yue": 3, "ja": 4, "ko": 5}
        lang_id = lang_ids.get(language, lang_ids.get("zh", 1))

        # Build inputs
        feeds = {
            "speech": feats[np.newaxis, :, :],           # [1, T, 560]
            "speech_lengths": np.array([feats.shape[0]], dtype=np.int32),  # [1]
            "language": np.array([lang_id], dtype=np.int32),               # [1]
            "textnorm": np.array([0], dtype=np.int32),   # 0=withitn (数字转阿拉伯数字)
        }

        outputs = session.run(None, feeds)
        logits = outputs[0]           # [1, T_out, vocab_size]
        out_lens = outputs[1]         # [1]

        # Decode CTC: argmax -> remove blanks and repeats
        ids = np.argmax(logits[0], axis=-1)
        seq_len = int(out_lens[0])
        ids = ids[:seq_len]

        # CTC blank token: typically vocab_size - 1 for ESPnet models
        vocab_size = len(tokens)
        blank_id = vocab_size - 1  # <|SPECIAL_TOKEN_35|> or similar

        prev_id = -1
        decoded_ids = []
        for idx in ids:
            if idx == blank_id:
                continue
            if idx != prev_id and idx < vocab_size:
                decoded_ids.append(idx)
            prev_id = idx

        text_parts = []
        for idx in decoded_ids:
            tok = tokens[idx] if idx < vocab_size else ""
            # Skip special tokens and <unk>
            if (not tok
                or tok == "<blank>"
                or tok == "<unk>"
                or tok == "<s>"
                or tok == "</s>"
                or tok.startswith("<|") and tok.endswith("|>")):
                continue
            text_parts.append(tok)

        text = "".join(text_parts).strip()
        # Remove any remaining special tokens / tags
        for tag in ["<|zh|>", "<|en|>", "<|yue|>", "<|ko|>", "<|ja|>", "<|auto|>", "<|NONE|>"]:
            text = text.replace(tag, "")
        # Defensive: remove <unk> if any still present
        text = text.replace("<unk>", "").strip()
        # Collapse multiple spaces
        import re
        text = re.sub(r"\s+", " ", text).strip()
        return text
