"""百度语音识别 - 短语音识别 API.

Docs: https://ai.baidu.com/ai-doc/SPEECH/Vk38lxily
使用 HTTP 接口，无需安装官方 SDK。
永久免费额度，适合长期使用。
"""
import base64
import hashlib
import json
import time
import urllib.parse
from typing import Optional

import numpy as np
import requests

from .base import ASREngine, _to_wav_bytes


class BaiduEngine(ASREngine):
    name = "baidu"
    # 百度短语音识别 API
    URL = "https://vop.baidu.com/server_api"
    # Token 获取接口
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"

    def __init__(self, api_key: str, secret_key: str):
        if not api_key or not secret_key:
            raise ValueError("百度 API Key 或 Secret Key 未配置")
        self.api_key = api_key
        self.secret_key = secret_key
        self._token: Optional[str] = None
        self._token_expire: float = 0

    def transcribe(self, audio: np.ndarray, sample_rate: int, language: str = "zh") -> str:
        wav_bytes = _to_wav_bytes(audio, sample_rate)
        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

        # 语言映射
        dev_pid = 1537  # 普通话(支持简单的英文识别)
        if language == "en":
            dev_pid = 1737  # 英文
        elif language in ("zh", "auto"):
            dev_pid = 1537

        params = {
            "dev_pid": dev_pid,
            "cuid": "ai_subtitle_tool",
            "asr_client_ip": "127.0.0.1",
            "token": self._get_token(),
            "speech": audio_b64,
            "len": len(wav_bytes),
        }
        headers = {"Content-Type": "application/json"}
        r = requests.post(self.URL, json=params, headers=headers, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"百度 ASR HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        err_no = data.get("err_no", -1)
        if err_no != 0:
            raise RuntimeError(f"百度 ASR 错误 {err_no}: {data.get('err_msg', '')}")
        results = data.get("result", [])
        if not results:
            return ""
        return results[0].strip()

    def _get_token(self) -> str:
        """获取 access_token，缓存到过期前。"""
        now = time.time()
        if self._token and now < self._token_expire - 60:
            return self._token

        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }
        url = self.TOKEN_URL + "?" + urllib.parse.urlencode(params)
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"百度获取 Token 失败: {r.status_code} {r.text[:200]}")
        data = r.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 2592000)
        if not token:
            raise RuntimeError(f"百度返回 Token 为空: {data}")
        self._token = token
        self._token_expire = now + expires_in
        return token
