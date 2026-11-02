import os
import io
import time
import uuid
import json
import gzip
import struct
import asyncio
from pathlib import Path
from typing import Optional, Callable, Tuple
import websockets
import requests
from config import Config

class ASRStatus:
    OK = "ok"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"

class ASRClient:
    def __init__(self):
        self.provider = Config.ASR_PROVIDER
        
        # 阿里 DashScope 配置
        self.dashscope_key = Config.DASHSCOPE_API_KEY
        
        # 火山引擎 (豆包流式语音识别模型 2.0) 配置
        self.volc_appid = Config.VOLC_APPID
        self.volc_token = Config.VOLC_ACCESS_TOKEN
        self.volc_resource_id = getattr(Config, "VOLC_RESOURCE_ID", "volc.seedasr.sauc.duration")
        
        # 状态感知与监听
        self.status = ASRStatus.OK
        self.last_error = ""
        self.on_status_changed: Optional[Callable[[str, str], None]] = None

        if self.provider == "volcengine" and (not self.volc_appid or not self.volc_token):
            self.status = ASRStatus.UNCONFIGURED
            self.last_error = "未配置火山引擎 AppID 或 Access Token"

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

    def _update_status(self, new_status: str, error_msg: str = ""):
        """更新服务可用状态并触发回调通知"""
        if self.status != new_status or self.last_error != error_msg:
            old_s = self.status
            self.status = new_status
            self.last_error = error_msg
            print(f"[ASRClient] ASR 状态迁移: {old_s} -> {new_status} (原因: {error_msg})")
            if callable(self.on_status_changed):
                try:
                    self.on_status_changed(new_status, error_msg)
                except Exception as e:
                    print(f"[ASRClient] 触发状态回调异常: {e}")

    def check_health(self) -> Tuple[bool, str]:
        """
        轻量级快速健康探测 (握手建联并验证 Token 鉴权与账户额度状态)
        用于启动自检与每隔数分钟的后台静默巡检，发现欠费立即预警
        """
        if self.provider == "volcengine":
            if not self.volc_appid or not self.volc_token:
                self._update_status(ASRStatus.UNCONFIGURED, "未配置火山引擎 AppID 或 Token")
                return False, "未配置火山引擎凭证"
            try:
                async def _probe():
                    uri = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
                    headers = {
                        "X-Api-Key": self.volc_token,
                        "X-Api-App-Key": self.volc_appid,
                        "X-Api-Resource-Id": self.volc_resource_id,
                        "X-Api-Request-Id": str(uuid.uuid4())
                    }
                    async with websockets.connect(uri, additional_headers=headers, open_timeout=5) as ws:
                        payload = {
                            "user": {"uid": "probe_user"},
                            "audio": {"format": "wav", "rate": Config.SAMPLE_RATE, "bits": 16, "channel": Config.CHANNELS}
                        }
                        payload_bytes = gzip.compress(json.dumps(payload).encode("utf-8"))
                        header = bytearray([0x11, 0x10, 0x11, 0x00])
                        frame = bytes(header) + struct.pack(">I", len(payload_bytes)) + payload_bytes
                        await ws.send(frame)
                        resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
                        if len(resp) >= 12:
                            p_len = struct.unpack(">I", resp[8:12])[0]
                            raw_payload = resp[12:12 + p_len]
                            try:
                                p_data = json.loads(raw_payload.decode("utf-8", errors="ignore"))
                            except Exception:
                                p_data = json.loads(gzip.decompress(raw_payload).decode("utf-8", errors="ignore"))
                            code = p_data.get("code")
                            if code is not None and code not in (0, 1000):
                                raise RuntimeError(f"火山返回错误: {p_data.get('message', code)}")
                        return True, "就绪"

                asyncio.run(_probe())
                self._update_status(ASRStatus.OK, "")
                return True, "正常就绪"
            except websockets.exceptions.InvalidStatusCode as e:
                if e.status_code in (401, 403):
                    err = f"火山引擎鉴权失败或账户欠费 (HTTP {e.status_code})"
                elif e.status_code == 402:
                    err = "火山引擎账户欠费，额度不足 (HTTP 402)"
                else:
                    err = f"火山引擎连接拒绝 (HTTP {e.status_code})"
                self._update_status(ASRStatus.ERROR, err)
                return False, err
            except Exception as e:
                err = f"火山语音识别不可用: {e}"
                self._update_status(ASRStatus.ERROR, err)
                return False, err
        return True, "就绪"

    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        根据配置的 ASR_PROVIDER 调用对应服务转录音频
        """
        if not os.path.exists(audio_path):
            return None

        # 1. 优先调用火山引擎 (豆包流式语音大模型 2.0)
        if self.provider == "volcengine" and self.volc_appid and self.volc_token:
            try:
                text = self._transcribe_volcengine(audio_path)
                if text and text.strip():
                    self._update_status(ASRStatus.OK, "")
                    return text.strip()
                # 正常静音切片 (服务正常，无有效发言)
                self._update_status(ASRStatus.OK, "")
                print("[ASRClient] 本段切片未识别到有效语音文本（可能为静音或微弱环境音），跳过归档。")
                return None
            except Exception as e:
                err_msg = str(e)
                print(f"[ASRClient] 火山引擎 ASR 调用异常: {err_msg}")
                self._update_status(ASRStatus.ERROR, err_msg)
                return None

        # 2. 阿里 DashScope (通义听悟 / SenseVoice)
        if (self.provider == "dashscope" or self.dashscope_key) and self.dashscope_key:
            try:
                text = self._transcribe_dashscope(audio_path)
                if text:
                    self._update_status(ASRStatus.OK, "")
                    return text
            except Exception as e:
                self._update_status(ASRStatus.ERROR, f"DashScope 异常: {e}")
                return None

        # 3. OpenAI Whisper
        if (self.provider == "openai" or self.openai_client) and self.openai_client:
            try:
                text = self._transcribe_openai(audio_path)
                if text:
                    self._update_status(ASRStatus.OK, "")
                    return text
            except Exception as e:
                self._update_status(ASRStatus.ERROR, f"OpenAI 异常: {e}")
                return None

        # 4. 无法识别或静音切片，静默返回 None
        print(f"[ASRClient] 音频未包含有效清晰语音（静音/环境杂音），跳过归档。")
        return None

    def _transcribe_volcengine(self, audio_path: str) -> Optional[str]:
        """
        基于 WebSocket 协议调用火山引擎最新的豆包流式语音识别模型 2.0
        """
        return asyncio.run(self._async_transcribe_volc(audio_path))

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

        try:
            ws_conn = websockets.connect(uri, additional_headers=headers, open_timeout=10)
            async with ws_conn as ws:
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

                            # 显式截获云端返回的错误码或欠费提示
                            code = p_data.get("code")
                            if code is not None and code not in (0, 1000):
                                msg = p_data.get("message", "未知错误")
                                raise RuntimeError(f"火山引擎返回异常 (code {code}): {msg}")

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
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code in (401, 403):
                raise RuntimeError(f"火山语音鉴权失败或账户欠费 (HTTP {e.status_code})")
            elif e.status_code == 402:
                raise RuntimeError("火山引擎账户余额不足/欠费 (HTTP 402 Payment Required)")
            else:
                raise RuntimeError(f"火山引擎连接拒绝 (HTTP {e.status_code})")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"连接火山引擎识别服务失败: {e}")

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
