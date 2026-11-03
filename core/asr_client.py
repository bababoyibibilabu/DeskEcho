import os
import io
import re
import time
import uuid
import json
import gzip
import struct
import asyncio
import threading
from pathlib import Path
from typing import Optional, Callable, Tuple
import websockets
import requests
import numpy as np
from config import Config

class ASRStatus:
    OK = "ok"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"

class ASRClient:
    def __init__(self):
        self.provider = getattr(Config, "ASR_PROVIDER", "sensevoice").lower().strip()
        
        # 本地离线 SenseVoice 引擎
        self._sensevoice_lock = threading.Lock()
        self._sensevoice_recognizer = None
        self._init_local_recognizer()

        # 阿里 DashScope 配置
        self.dashscope_key = Config.DASHSCOPE_API_KEY
        
        # 火山引擎 (豆包流式语音识别模型 2.0) 配置 (保留在代码层作为次选备选通道)
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

    def _init_local_recognizer(self):
        """初始化本地离线 SenseVoice-Small 识别引擎 (基于 sherpa-onnx)"""
        candidate_dirs = [
            getattr(Config, "SENSEVOICE_MODEL_DIR", None),
            Config.BASE_DIR / "models" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17",
            Config.DATA_DIR / "models" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17",
            Path(__file__).resolve().parent.parent / "models" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
        ]

        model_path = None
        tokens_path = None
        for d in candidate_dirs:
            if not d:
                continue
            p = Path(d)
            if p.exists():
                m_int8 = p / "model.int8.onnx"
                m_fp32 = p / "model.onnx"
                tok = p / "tokens.txt"
                if (m_int8.exists() or m_fp32.exists()) and tok.exists():
                    model_path = str(m_int8 if m_int8.exists() else m_fp32)
                    tokens_path = str(tok)
                    break

        if not model_path or not tokens_path:
            return

        try:
            import sherpa_onnx
            num_threads = max(1, getattr(Config, "ASR_NUM_THREADS", 2))
            self._sensevoice_recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_path,
                tokens=tokens_path,
                num_threads=num_threads,
                use_itn=True
            )
            print(f"[ASRClient] 本地离线 SenseVoice-Small ASR 引擎就绪 (INT8 量化, 线程数: {num_threads})")
        except Exception as e:
            print(f"[ASRClient] 加载本地 SenseVoice-Small 失败: {e}")
            self._sensevoice_recognizer = None

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
        轻量级快速健康探测
        本地引擎检测模型权重完整性；云端引擎检测 Token 与额度
        """
        if self.provider in ("sensevoice", "local"):
            if self._sensevoice_recognizer is None:
                self._init_local_recognizer()
            if self._sensevoice_recognizer is not None:
                self._update_status(ASRStatus.OK, "")
                return True, "本地离线高精识别引擎就绪 (SenseVoice-Small)"
            else:
                err = "未检测到本地 SenseVoice 模型文件，请检查 models/ 目录"
                self._update_status(ASRStatus.ERROR, err)
                return False, err

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

    @staticmethod
    def _clean_sensevoice_text(text: str) -> str:
        """剥离 SenseVoice 附带的情感事件标记并过滤无效幻觉"""
        if not text:
            return ""
        # 剥离诸如 <|zh|>, <|NEUTRAL|>, <|Speech|>, <|woitn|> 等特殊标记
        cleaned = re.sub(r"<\|.*?\|>", "", text).strip()
        
        # 过滤模型在近静音/微弱底噪下的已知幻觉词
        if cleaned in ("\uadf8.", "\uadf8", "\uc5b4.", "\uc5b4", "\uc74c.", "\uc74c"):
            return ""

        # 确保含有有效语义内容 (汉字、日文假名、英文、数字)
        has_content = any(
            ('\u4e00' <= ch <= '\u9fff') or
            ('\u3040' <= ch <= '\u30ff') or
            ('a' <= ch.lower() <= 'z') or
            ('0' <= ch <= '9')
            for ch in cleaned
        )
        if not has_content:
            return ""
        return cleaned

    def _transcribe_sensevoice(self, audio_path: str) -> Optional[str]:
        """使用本地 SenseVoice-Small ONNX 引擎转录音频"""
        if not self._sensevoice_recognizer:
            self._init_local_recognizer()
        if not self._sensevoice_recognizer:
            raise RuntimeError("本地 SenseVoice 模型未就绪或未找到权重文件")

        import soundfile as sf
        audio, sr = sf.read(audio_path, dtype="float32")
        if len(audio) == 0:
            return None

        # 针对立体声输入做单声道合并降维
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        if not audio.flags.c_contiguous:
            audio = np.ascontiguousarray(audio, dtype=np.float32)

        # 静音/微弱底噪过滤，避免模型产生无意义字符
        max_amp = float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0
        if max_amp < 0.005:
            return None

        # sherpa-onnx OfflineRecognizer 在底层支持跨 Stream 并发解码
        stream = self._sensevoice_recognizer.create_stream()
        stream.accept_waveform(sr, audio)
        self._sensevoice_recognizer.decode_stream(stream)
        raw_text = stream.result.text

        cleaned = self._clean_sensevoice_text(raw_text)
        if cleaned:
            return cleaned
        return None

    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        根据配置的 ASR_PROVIDER 调用对应服务转录音频
        默认: 本地 SenseVoice-Small；代码层保留火山/DashScope 作为备选
        """
        if not os.path.exists(audio_path):
            return None

        # 1. 默认主引擎: 本地离线 SenseVoice-Small (100% 免费、完全离线、低耗快速)
        if self.provider in ("sensevoice", "local", "offline", ""):
            try:
                text = self._transcribe_sensevoice(audio_path)
                self._update_status(ASRStatus.OK, "")
                if text and text.strip():
                    return text.strip()
                return None
            except Exception as e:
                err_msg = str(e)
                print(f"[ASRClient] 本地 SenseVoice 识别异常: {err_msg}")
                # 平滑回退策略: 若本地引擎异常且配置了火山引擎备选，自动平滑回退
                if self.volc_appid and self.volc_token:
                    print("[ASRClient] 正在尝试平滑回退至火山引擎备选通道...")
                    try:
                        v_text = self._transcribe_volcengine(audio_path)
                        if v_text and v_text.strip():
                            return v_text.strip()
                        return None
                    except Exception as ve:
                        print(f"[ASRClient] 火山引擎备选通道同样失败: {ve}")
                elif self.dashscope_key:
                    print("[ASRClient] 正在尝试平滑回退至 DashScope 备选通道...")
                    try:
                        d_text = self._transcribe_dashscope(audio_path)
                        if d_text and d_text.strip():
                            return d_text.strip()
                        return None
                    except Exception as de:
                        print(f"[ASRClient] DashScope 备选通道同样失败: {de}")
                self._update_status(ASRStatus.ERROR, err_msg)
                return None

        # 2. 火山引擎 (豆包流式语音大模型 2.0，代码层保留次选)
        elif self.provider == "volcengine":
            if self.volc_appid and self.volc_token:
                try:
                    text = self._transcribe_volcengine(audio_path)
                    if text and text.strip():
                        self._update_status(ASRStatus.OK, "")
                        return text.strip()
                    self._update_status(ASRStatus.OK, "")
                    return None
                except Exception as e:
                    err_msg = str(e)
                    print(f"[ASRClient] 火山引擎 ASR 调用异常: {err_msg}")
                    self._update_status(ASRStatus.ERROR, err_msg)
                    return None
            else:
                self._update_status(ASRStatus.UNCONFIGURED, "未配置火山引擎凭证")
                return None

        # 3. 阿里 DashScope (通义听悟 / SenseVoice API 备选)
        elif self.provider == "dashscope":
            if self.dashscope_key:
                try:
                    text = self._transcribe_dashscope(audio_path)
                    if text:
                        self._update_status(ASRStatus.OK, "")
                        return text
                except Exception as e:
                    self._update_status(ASRStatus.ERROR, f"DashScope 异常: {e}")
                    return None
            else:
                self._update_status(ASRStatus.UNCONFIGURED, "未配置 DashScope API Key")
                return None

        # 4. OpenAI Whisper
        elif self.provider == "openai":
            if self.openai_client:
                try:
                    text = self._transcribe_openai(audio_path)
                    if text:
                        self._update_status(ASRStatus.OK, "")
                        return text
                except Exception as e:
                    self._update_status(ASRStatus.ERROR, f"OpenAI 异常: {e}")
                    return None
            else:
                self._update_status(ASRStatus.UNCONFIGURED, "未配置 OpenAI API Key")
                return None

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
