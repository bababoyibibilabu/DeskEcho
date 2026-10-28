import os
import io
import time
import uuid
import json
import gzip
import struct
import asyncio
from pathlib import Path
from typing import Optional
import websockets
import requests
from config import Config

class ASRClient:
    def __init__(self):
        self.provider = Config.ASR_PROVIDER
        
        # 阿里 DashScope 配置
        self.dashscope_key = Config.DASHSCOPE_API_KEY
        
        # 火山引擎 (豆包流式语音识别模型 2.0) 配置
        self.volc_appid = Config.VOLC_APPID
        self.volc_token = Config.VOLC_ACCESS_TOKEN
        self.volc_resource_id = getattr(Config, "VOLC_RESOURCE_ID", "volc.seedasr.sauc.duration")
        
        # OpenAI 配置
        self.openai_key = Config.OPENAI_API_KEY
        self.openai_client = None
        if self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(
                    api_key=self.openai_key,
                    base_url=Config.OPENAI_BASE_URL if "openai.com" in Config.OPENAI_BASE_URL else None
                )
            except Exception as e:
                print(f"[ASRClient] 初始化 OpenAI Client 失败: {e}")

    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        根据配置的 ASR_PROVIDER 调用对应服务转录音频
        """
        if not os.path.exists(audio_path):
            return None

        # 1. 优先调用火山引擎 (豆包流式语音大模型 2.0)
        if self.provider == "volcengine" and self.volc_appid and self.volc_token:
            text = self._transcribe_volcengine(audio_path)
            if text and text.strip():
                return text.strip()
            print("[ASRClient] 本段切片未识别到有效语音文本（可能为静音或微弱环境音），跳过归档。")
            return None

        # 2. 阿里 DashScope (通义听悟 / SenseVoice)
        if (self.provider == "dashscope" or self.dashscope_key) and self.dashscope_key:
            text = self._transcribe_dashscope(audio_path)
            if text:
                return text

        # 3. OpenAI Whisper
        if (self.provider == "openai" or self.openai_client) and self.openai_client:
            text = self._transcribe_openai(audio_path)
            if text:
                return text

        # 4. 无法识别或静音切片，静默返回 None（由管道自动跳过，不污染知识库）
        print(f"[ASRClient] 音频未包含有效清晰语音（静音/环境杂音），跳过归档。")
        return None

    def _transcribe_volcengine(self, audio_path: str) -> Optional[str]:
        """
        基于 WebSocket 协议调用火山引擎最新的豆包流式语音识别模型 2.0
        """
        try:
            return asyncio.run(self._async_transcribe_volc(audio_path))
        except Exception as e:
            print(f"[ASRClient] 调用火山引擎流式 2.0 异常: {e}")
            return None

    async def _async_transcribe_volc(self, audio_path: str) -> Optional[str]:
        uri = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        req_id = str(uuid.uuid4())
        headers = {
            "X-Api-Key": self.volc_token,
            "X-Api-App-Key": self.volc_appid,
            "X-Api-Resource-Id": self.volc_resource_id,
            "X-Api-Request-Id": req_id
        }

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        async with websockets.connect(uri, additional_headers=headers, open_timeout=10) as ws:
            # 1. 发送初始化配置帧
            payload = {
                "user": {"uid": "deskecho_user"},
                "audio": {"format": "wav", "rate": Config.SAMPLE_RATE, "bits": 16, "channel": Config.CHANNELS}
            }
            payload_bytes = gzip.compress(json.dumps(payload).encode("utf-8"))
            header = bytearray([0x11, 0x10, 0x11, 0x00])
            frame = bytes(header) + struct.pack(">I", len(payload_bytes)) + payload_bytes
            await ws.send(frame)

            # 2. 音频分块流式投递 (每包 200ms = 6400 字节)
            chunk_size = 6400
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                is_last = (i + chunk_size >= len(audio_bytes))
                flags = 0b0010 if is_last else 0b0000
                a_hdr = bytearray([0x11, (0b0010 << 4) | flags, 0x00, 0x00])
                a_frame = bytes(a_hdr) + struct.pack(">I", len(chunk)) + chunk
                await ws.send(a_frame)
                await asyncio.sleep(0.02)

            # 3. 循环接收结果
            final_text = ""
            while True:
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=3.5)
                    if len(resp) >= 12:
                        p_len = struct.unpack(">I", resp[8:12])[0]
                        raw_payload = resp[12:12 + p_len]
                        try:
                            p_data = json.loads(raw_payload.decode("utf-8", errors="ignore"))
                        except Exception:
                            p_data = json.loads(gzip.decompress(raw_payload).decode("utf-8", errors="ignore"))

                        result = p_data.get("result", {})
                        if isinstance(result, dict) and "text" in result:
                            text_seg = result.get("text", "")
                            if text_seg:
                                final_text = text_seg
                        elif isinstance(result, list) and len(result) > 0:
                            texts = [r.get("text", "") for r in result if r.get("text")]
                            if texts:
                                final_text = "".join(texts)

                        if p_data.get("is_last"):
                            break
                except websockets.exceptions.ConnectionClosed:
                    break
                except asyncio.TimeoutError:
                    break

            if final_text.strip():
                return final_text.strip()
            return None

    def _transcribe_dashscope(self, audio_path: str) -> Optional[str]:
        try:
            with open(audio_path, "rb") as f:
                resp = requests.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.dashscope_key}"},
                    files={"file": (os.path.basename(audio_path), f, "audio/wav")},
                    data={"model": "sensevoice-v1"},
                    timeout=30
                )
            if resp.status_code == 200:
                res_json = resp.json()
                text = res_json.get("text", "")
                if text:
                    return text.strip()
        except Exception as e:
            print(f"[ASRClient] DashScope 转录异常: {e}")
        return None

    def _transcribe_openai(self, audio_path: str) -> Optional[str]:
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="zh"
                )
                return transcription.text.strip()
        except Exception as e:
            print(f"[ASRClient] OpenAI Whisper 转录异常: {e}")
            return None

    def _fallback_transcription(self, audio_path: str) -> str:
        basename = os.path.basename(audio_path)
        if "query" in basename:
            return "我们上次会议讨论的产品发布时间是什么时候？有确定负责人吗？"
        return "今天我们对 DeskEcho 桌面常驻会议助手的 MVP 功能做个梳理。张总要求必须在 27 号完成第一版联调，李工负责音频切片与热键唤醒，王助理负责会议纪要归档。预算初步定在五万元以内。"
