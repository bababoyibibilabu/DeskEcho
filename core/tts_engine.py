import os
import re
import uuid
import time
import base64
import asyncio
import threading
from pathlib import Path
from typing import Optional, Callable
import requests
import edge_tts
from config import Config

class TTSEngine:
    """
    多引擎自适应语音合成播报 (TTS Engine)
    - 优先支持：火山引擎豆包语音大模型 TTS (自然度极高、拟真情感)
    - 免费备选：微软 Edge-TTS (免配置免 Key，极速稳定)
    - 角色分离：会议内部结论采用【沉稳男声】，全网通识科普采用【知性女声】，听觉显著区分来源
    """
    def __init__(self):
        self.provider = Config.TTS_PROVIDER
        self.voice = Config.TTS_VOICE
        self.enabled = Config.ENABLE_TTS
        
        # 火山引擎参数
        self.volc_appid = Config.VOLC_APPID
        self.volc_token = Config.VOLC_ACCESS_TOKEN
        self.volc_voice_type = Config.VOLC_TTS_VOICE_TYPE
        self.volc_cluster = Config.VOLC_TTS_CLUSTER

        self.ack_audio_path = Config.DATA_DIR / "assets" / "ack.mp3"
        self._ensure_ack_cached()

    def _ensure_ack_cached(self):
        """确保预热的即时响应音频存在"""
        if not self.ack_audio_path.exists():
            def _gen():
                try:
                    self.ack_audio_path.parent.mkdir(parents=True, exist_ok=True)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    communicate = edge_tts.Communicate("稍等，正在检索", "zh-CN-YunxiNeural")
                    loop.run_until_complete(communicate.save(str(self.ack_audio_path)))
                    loop.close()
                except Exception as e:
                    print(f"[TTSEngine] 预缓存即时回复音频失败: {e}")
            threading.Thread(target=_gen, daemon=True).start()

    def get_ack_audio_path(self) -> Optional[str]:
        if self.enabled and self.ack_audio_path.exists():
            return str(self.ack_audio_path)
        return None

    def clean_text_for_tts(self, text: str) -> str:
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        cleaned = re.sub(r'[\*#_`~>|-]', '', cleaned)
        cleaned = re.sub(r'\n+', '，', cleaned)
        if len(cleaned) > 220:
            cleaned = cleaned[:220] + "，详细内容请查看屏幕卡片。"
        return cleaned.strip()

    def speak_async(self, text: str, on_audio_ready: Callable[[str], None], mode: str = "MEETING"):
        if not self.enabled:
            return

        plain_text = self.clean_text_for_tts(text)
        if not plain_text:
            return

        is_general = (str(mode).upper() == "GENERAL")
        edge_voice = Config.TTS_VOICE_GENERAL if is_general else Config.TTS_VOICE_MEETING
        volc_voice = Config.VOLC_TTS_VOICE_GENERAL if is_general else Config.VOLC_TTS_VOICE_MEETING

        def _worker():
            # 1. 若配置了火山引擎 TTS，优先尝试火山豆包 TTS
            if self.provider == "volcengine" and self.volc_appid and self.volc_token:
                volc_path = self._synthesize_volcengine(plain_text, voice_type=volc_voice)
                if volc_path:
                    on_audio_ready(volc_path)
                    return
                print("[TTSEngine] 火山豆包 TTS 未返回有效音频，自动平滑切换至 Edge-TTS...")

            # 2. 默认 / 备选 Edge-TTS (会议沉稳男声 vs 全网科普知性女声)
            edge_path = self._synthesize_edge_tts(plain_text, voice=edge_voice)
            if edge_path:
                on_audio_ready(edge_path)

        threading.Thread(target=_worker, daemon=True).start()

    def _synthesize_volcengine(self, text: str, voice_type: Optional[str] = None) -> Optional[str]:
        """
        调用火山引擎豆包语音合成 API (HTTP 极速模式)
        """
        try:
            url = "https://openspeech.bytedance.com/api/v1/tts"
            headers = {
                "Authorization": f"Bearer; {self.volc_token}",
                "Content-Type": "application/json"
            }
            v_type = voice_type or self.volc_voice_type
            payload = {
                "app": {
                    "appid": self.volc_appid,
                    "token": self.volc_token,
                    "cluster": self.volc_cluster
                },
                "user": {
                    "uid": "deskecho_client"
                },
                "audio": {
                    "voice_type": v_type,
                    "encoding": "mp3",
                    "speed_ratio": 1.0,
                    "volume_ratio": 1.0,
                    "pitch_ratio": 1.0
                },
                "request": {
                    "reqid": str(uuid.uuid4()),
                    "text": text,
                    "text_type": "plain",
                    "operation": "query"
                }
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                resp_json = resp.json()
                if resp_json.get("code") == 3000 and "data" in resp_json:
                    audio_b64 = resp_json["data"]
                    out_path = Config.TEMP_DIR / f"tts_volc_{int(time.time()*1000)}.mp3"
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(audio_b64))
                    return str(out_path)
                else:
                    print(f"[TTSEngine] 火山 TTS 提示: {resp_json.get('message')}")
        except Exception as e:
            print(f"[TTSEngine] 火山 TTS 异常: {e}")
        return None

    def _synthesize_edge_tts(self, text: str, voice: Optional[str] = None) -> Optional[str]:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            output_path = Config.TEMP_DIR / f"tts_edge_{int(time.time()*1000)}.mp3"
            v = voice or self.voice
            communicate = edge_tts.Communicate(text, v)
            loop.run_until_complete(communicate.save(str(output_path)))
            loop.close()
            if output_path.exists():
                return str(output_path)
        except Exception as e:
            print(f"[TTSEngine] Edge-TTS 合成异常: {e}")
        return None
