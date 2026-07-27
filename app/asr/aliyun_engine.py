"""阿里云语音识别 - 一句话识别 HTTP API.

Docs: https://help.aliyun.com/zh/isis/icon-speech-recognition
OpenAPI: nls-filetrans / 语音识别 (SpeechRecognition)
这里使用较简单的「一句话识别」POP API: aliyun-python-sdk-core 方式。
为了避免引入官方 SDK 的依赖，我们用 requests + HMAC-SHA1 签名。
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import uuid
from datetime import datetime, timezone

import numpy as np
import requests

from .base import ASREngine, _to_wav_bytes


class AliyunEngine(ASREngine):
    name = "aliyun"
    # 智能语音交互 一句话识别 POP endpoint
    URL = "https://nls-gateway.aliyuncs.com/stream/v1/asr"

    def __init__(self, access_key_id: str, access_key_secret: str, appkey: str):
        if not access_key_id or not access_key_secret or not appkey:
            raise ValueError("阿里云 AccessKey ID/Secret 或 Appkey 未配置")
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.appkey = appkey

    def transcribe(self, audio: np.ndarray, sample_rate: int, language: str = "zh") -> str:
        wav_bytes = _to_wav_bytes(audio, sample_rate)
        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

        url = f"{self.URL}?appkey={self.appkey}"
        headers = {
            "X-NLS-Token": self._get_token(),
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(wav_bytes)),
        }
        # 也可以直接传二进制 wav，这里用更稳定的 token 方式
        r = requests.post(url, data=wav_bytes, headers=headers, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"阿里云 ASR HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        status = data.get("status", -1)
        if status != 20000000:
            raise RuntimeError(f"阿里云 ASR 错误 {status}: {data.get('message', '')}")
        result = data.get("result", "")
        return result.strip()

    def _get_token(self) -> str:
        """Build a temporary access token via the POP token interface."""
        # 构造AssumeRole或CreateToken方式需要STS，这里简单使用签名版本1获取token。
        # 阿里云智能语音一句话识别也可以用「长期AccessKey签名」方式。
        # 为简单可靠，使用官方 STS AssumeRole 需要的接口较复杂；
        # 实际上更推荐安装 alibabacloud-nls-java-sdk，Python 端我们使用
        # 阿里云 POP OpenAPI 通用签名访问 CreateToken。
        params = {
            "Format": "JSON",
            "Version": "2019-02-28",
            "AccessKeyId": self.access_key_id,
            "SignatureMethod": "HMAC-SHA1",
            "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "SignatureVersion": "1.0",
            "SignatureNonce": str(uuid.uuid4()),
            "Action": "CreateToken",
            "RegionId": "cn-shanghai",
        }
        sorted_params = sorted(params.items())
        canonical = urllib.parse.urlencode(sorted_params, safe="*")
        string_to_sign = f"GET&%2F&{urllib.parse.quote(canonical, safe='')}"
        key = f"{self.access_key_secret}&"
        signature = base64.b64encode(
            hmac.new(key.encode(), string_to_sign.encode(), hashlib.sha1).digest()
        ).decode()
        params["Signature"] = signature
        url = "https://nls-meta.cn-shanghai.aliyuncs.com/?" + urllib.parse.urlencode(params)
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"阿里云获取 Token 失败: {r.status_code} {r.text[:200]}")
        token = r.json().get("Token", {}).get("Id")
        if not token:
            raise RuntimeError("阿里云返回 Token 为空")
        return token
