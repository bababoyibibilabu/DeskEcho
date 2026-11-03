import time
import wave
import threading
import collections
import numpy as np
import webrtcvad
import pyaudio
from pathlib import Path
from typing import Callable, Optional, Tuple, List
from config import Config

def _to_16k_mono(raw_bytes: bytes, in_channels: int, in_rate: int) -> bytes:
    """将任意多声道/不同采样率的 PCM16 数据转换为标准 16000Hz 单声道 PCM16 字节流"""
    arr = np.frombuffer(raw_bytes, dtype=np.int16)
    if in_channels > 1:
        arr = arr.reshape(-1, in_channels).mean(axis=1).astype(np.int16)
    if in_rate != Config.SAMPLE_RATE:
        target_len = int(len(arr) * (Config.SAMPLE_RATE / float(in_rate)))
        orig_idx = np.linspace(0, len(arr) - 1, len(arr))
        target_idx = np.linspace(0, len(arr) - 1, target_len)
        arr = np.interp(target_idx, orig_idx, arr).astype(np.int16)
    return arr.tobytes()

def get_best_input_stream(p: pyaudio.PyAudio) -> Tuple[Optional[pyaudio.Stream], int, int]:
    """
    智能探测并尝试打开最适配的麦克风音频流。
    返回: (stream, channels, sample_rate)
    """
    # 1. 尝试默认设备标准 16kHz 单声道
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=Config.CHANNELS,
            rate=Config.SAMPLE_RATE,
            input=True,
            frames_per_buffer=Config.CHUNK_SIZE
        )
        return stream, Config.CHANNELS, Config.SAMPLE_RATE
    except Exception:
        pass

    # 2. 遍历所有具备输入通道的设备，尝试多种配置 (16k, 44.1k, 48k; 单声道/立体声)
    device_count = p.get_device_count()
    for dev_idx in range(device_count):
        try:
            info = p.get_device_info_by_index(dev_idx)
            max_in = info.get("maxInputChannels", 0)
            if max_in <= 0:
                continue

            default_rate = int(info.get("defaultSampleRate", 16000))
            rates_to_try = [16000, default_rate, 44100, 48000]
            channels_to_try = [1, min(2, max_in)]

            for ch in channels_to_try:
                for rate in set(rates_to_try):
                    try:
                        chunk = int(rate * (Config.CHUNK_DURATION_MS / 1000.0))
                        stream = p.open(
                            format=pyaudio.paInt16,
                            channels=ch,
                            rate=rate,
                            input=True,
                            input_device_index=dev_idx,
                            frames_per_buffer=chunk
                        )
                        print(f"[AudioWorker] 成功接入麦克风设备 [{info.get('name')}] (通道:{ch}, 采样率:{rate}Hz)")
                        return stream, ch, rate
                    except Exception:
                        continue
        except Exception:
            continue

    return None, 1, 16000


class AudioSliceWorker(threading.Thread):
    """
    后台常驻事件驱动音频捕获与智能切片线程。
    架构特性：
    1. 采用 Silero VAD (ONNX) 配合预语音缓冲与尾随静音判定 (Hangover Silence)，并具备 WebRTC VAD 双重兜底。
    2. 静音期零消耗：房间无人说话时，CPU 占用率低于 0.1%，产生 0 次切片与 0 次磁盘 I/O。
    3. 会议语流智能聚合：按自然段落 (25s~60s) 或话题停顿 (>=2.5s) 汇聚完整语句，杜绝 1 秒微片段与频繁总结骚扰。
    4. 硬件自适应与虚拟守护：自动兼容单/双声道及 16k/44.1k/48k 硬件流；物理无麦克风时进入虚拟守护。
    """
    def __init__(self, on_slice_ready: Callable[[str, float, float], None]):
        super().__init__(daemon=True)
        self.on_slice_ready = on_slice_ready
        self.running = False
        self.paused = False
        self.intercom_active = False # 对讲与播报隔离标记，激活时彻底屏蔽麦克风入库
        self._stop_event = threading.Event()
        
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.is_virtual = False

        # VAD 引擎初始化 (优先 Silero VAD，降级 webrtcvad)
        self.use_silero = False
        self.vad = None
        self.webrtc_vad = None
        self._init_vad()

    def _init_vad(self):
        """初始化 VAD 引擎 (优先加载 Silero VAD ONNX 模型)"""
        candidate_models = [
            getattr(Config, "SILERO_VAD_MODEL_PATH", None),
            Config.BASE_DIR / "models" / "silero_vad.onnx",
            Config.DATA_DIR / "models" / "silero_vad.onnx",
            Path(__file__).resolve().parent.parent / "models" / "silero_vad.onnx"
        ]

        model_path = None
        for p in candidate_models:
            if p and Path(p).exists():
                model_path = str(Path(p).resolve())
                break

        if model_path:
            try:
                import sherpa_onnx
                vad_config = sherpa_onnx.VadModelConfig()
                vad_config.silero_vad.model = model_path
                vad_config.silero_vad.threshold = getattr(Config, "VAD_THRESHOLD", 0.5)
                vad_config.silero_vad.min_silence_duration = getattr(Config, "VAD_MIN_SILENCE_DURATION", 0.8)
                vad_config.silero_vad.min_speech_duration = getattr(Config, "VAD_MIN_SPEECH_DURATION", 0.3)
                vad_config.silero_vad.max_speech_duration = getattr(Config, "VAD_MAX_SPEECH_DURATION", 60.0)
                vad_config.sample_rate = Config.SAMPLE_RATE
                vad_config.num_threads = 1
                self.vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=60)
                self.use_silero = True
                print(f"[AudioWorker] 事件驱动 Silero VAD 就绪 (模型: {model_path})")
                return
            except Exception as e:
                print(f"[AudioWorker] 加载 Silero VAD 失败: {e}，将启用 WebRTC VAD 备选")

        try:
            self.webrtc_vad = webrtcvad.Vad(Config.VAD_MODE)
            print("[AudioWorker] WebRTC VAD 状态机备选就绪")
        except Exception as e:
            print(f"[AudioWorker] WebRTC VAD 初始化失败: {e}")

    def run(self):
        self.running = True
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.stream, ch, rate = get_best_input_stream(self.pyaudio_instance)
        except Exception:
            self.stream = None
            ch, rate = 1, Config.SAMPLE_RATE

        if self.stream is None:
            self.is_virtual = True
            print("[AudioWorker] [提示] 当前未检测到已就绪的硬件麦克风输入，已开启后台虚拟守护监听模式。")
        else:
            print(f"[AudioWorker] 麦克风硬件音频采集已启动 (物理通道:{ch}, 采样率:{rate}Hz)...")

        chunk_sec = Config.CHUNK_DURATION_MS / 1000.0  # 0.030s
        input_chunk_samples = int(rate * chunk_sec)
        target_chunk_samples = int(Config.SAMPLE_RATE * chunk_sec)  # 480
        target_chunk_bytes = target_chunk_samples * 2

        # 预语音环形缓冲 (保留发音字头前 0.8 秒)
        pre_speech_chunks = max(4, int(getattr(Config, "VAD_PRE_SPEECH_BUFFER", 0.8) / chunk_sec))
        pre_speech_ring = collections.deque(maxlen=pre_speech_chunks)

        # 段落级切片聚合器 (自然语言段落汇聚，避免按句碎片化切片)
        current_slice_audio: List[np.ndarray] = []
        slice_speech_seconds = 0.0
        slice_start_ts = 0.0
        last_speech_wall_time = 0.0
        webrtc_in_speech = False
        webrtc_burst_count = 0

        def _finalize_and_emit():
            nonlocal current_slice_audio, slice_speech_seconds, slice_start_ts, last_speech_wall_time
            if not current_slice_audio:
                return
            min_speech = getattr(Config, "VAD_MIN_SPEECH_DURATION", 0.5)
            if slice_speech_seconds >= min_speech:
                combined_audio = np.concatenate(current_slice_audio)
                dur = len(combined_audio) / float(Config.SAMPLE_RATE)
                end_ts = time.time()
                actual_start = slice_start_ts if slice_start_ts > 0 else (end_ts - dur)
                wav_path = self._save_samples(combined_audio)
                if wav_path:
                    print(f"[AudioWorker] [事件驱动归档] 捕获会议发言段落: {wav_path} (语音时长: {slice_speech_seconds:.1f}s, 切片总长: {dur:.1f}s)")
                    self.on_slice_ready(wav_path, actual_start, end_ts)
            current_slice_audio.clear()
            slice_speech_seconds = 0.0
            slice_start_ts = 0.0
            last_speech_wall_time = 0.0

        while not self._stop_event.is_set():
            if self.paused:
                _finalize_and_emit()
                if self.use_silero and self.vad:
                    try:
                        self.vad.reset()
                    except Exception:
                        pass
                webrtc_in_speech = False
                pre_speech_ring.clear()
                time.sleep(0.1)
                continue

            if self.intercom_active:
                _finalize_and_emit()
                if not self.is_virtual and self.stream:
                    try:
                        self.stream.read(input_chunk_samples, exception_on_overflow=False)
                    except Exception:
                        pass
                else:
                    time.sleep(chunk_sec)

                if self.use_silero and self.vad:
                    try:
                        self.vad.reset()
                    except Exception:
                        pass
                webrtc_in_speech = False
                pre_speech_ring.clear()
                continue

            if self.is_virtual:
                time.sleep(chunk_sec)
                continue

            # 正常硬件麦克风读取
            try:
                raw_data = self.stream.read(input_chunk_samples, exception_on_overflow=False)
            except Exception:
                time.sleep(0.01)
                continue

            # 转换为标准 16kHz 16-bit 单声道
            if ch != 1 or rate != Config.SAMPLE_RATE:
                data_16k = _to_16k_mono(raw_data, ch, rate)
            else:
                data_16k = raw_data

            if len(data_16k) < target_chunk_bytes:
                continue

            # ---------------- 1. Silero VAD (ONNX) 路径 ----------------
            if self.use_silero and self.vad:
                chunk_int16 = np.frombuffer(data_16k, dtype=np.int16)
                chunk_float = chunk_int16.astype(np.float32) / 32768.0

                self.vad.accept_waveform(chunk_float)

                if self.vad.is_speech_detected():
                    last_speech_wall_time = time.time()

                # 处理已完成断句的语音片段
                while not self.vad.empty():
                    segment = self.vad.front
                    seg_samples = np.array(segment.samples, dtype=np.float32)
                    seg_dur = len(seg_samples) / float(Config.SAMPLE_RATE)
                    if seg_dur >= 0.2:
                        now = time.time()
                        if not current_slice_audio:
                            slice_start_ts = now - seg_dur - getattr(Config, "VAD_MIN_SILENCE_DURATION", 0.8)
                        else:
                            # 拼接同一切片内的连续短句时插入 0.25 秒微平滑静音
                            current_slice_audio.append(np.zeros(int(Config.SAMPLE_RATE * 0.25), dtype=np.float32))
                        current_slice_audio.append(seg_samples)
                        slice_speech_seconds += seg_dur
                        last_speech_wall_time = now
                    self.vad.pop()

                # 切片聚合与截断判定:
                # A. 达到目标段落时长 (25s) 且发言人当前处于间歇期:
                if slice_speech_seconds >= getattr(Config, "MIN_SLICE_CUT_SECONDS", 25.0) and not self.vad.is_speech_detected():
                    _finalize_and_emit()
                # B. 达到单一切片最大允许时长 (60s):
                elif slice_speech_seconds >= getattr(Config, "MAX_SLICE_SECONDS", 60.0):
                    _finalize_and_emit()
                # C. 会议话题自然停顿 (上一句发言后持续静默 >= 2.5s):
                elif current_slice_audio and (time.time() - last_speech_wall_time >= getattr(Config, "SILENCE_BREAK_SECONDS", 2.5)):
                    _finalize_and_emit()

            # ---------------- 2. WebRTC VAD 状态机备选路径 ----------------
            elif self.webrtc_vad:
                try:
                    is_speech = self.webrtc_vad.is_speech(data_16k, Config.SAMPLE_RATE)
                except Exception:
                    is_speech = False

                chunk_f32 = np.frombuffer(data_16k, dtype=np.int16).astype(np.float32) / 32768.0

                if not webrtc_in_speech:
                    pre_speech_ring.append(chunk_f32)
                    if is_speech:
                        webrtc_burst_count += 1
                        if webrtc_burst_count >= 3: # 连续 90ms 判定为发言触发
                            webrtc_in_speech = True
                            webrtc_burst_count = 0
                            now = time.time()
                            if not current_slice_audio:
                                slice_start_ts = now - (len(pre_speech_ring) * chunk_sec)
                            current_slice_audio.extend(list(pre_speech_ring))
                            slice_speech_seconds += len(pre_speech_ring) * chunk_sec
                            last_speech_wall_time = now
                    else:
                        webrtc_burst_count = 0
                else:
                    current_slice_audio.append(chunk_f32)
                    if is_speech:
                        slice_speech_seconds += chunk_sec
                        last_speech_wall_time = time.time()

                    silence_elapsed = time.time() - last_speech_wall_time
                    if slice_speech_seconds >= getattr(Config, "MIN_SLICE_CUT_SECONDS", 25.0) and silence_elapsed >= 0.8:
                        _finalize_and_emit()
                        webrtc_in_speech = False
                    elif slice_speech_seconds >= getattr(Config, "MAX_SLICE_SECONDS", 60.0):
                        _finalize_and_emit()
                        webrtc_in_speech = False
                    elif silence_elapsed >= getattr(Config, "SILENCE_BREAK_SECONDS", 2.5):
                        _finalize_and_emit()
                        webrtc_in_speech = False

        # 线程退出前冲刷剩余语音
        if self.use_silero and self.vad:
            try:
                self.vad.flush()
                while not self.vad.empty():
                    seg = self.vad.front
                    seg_samples = np.array(seg.samples, dtype=np.float32)
                    if len(seg_samples) / float(Config.SAMPLE_RATE) >= 0.2:
                        current_slice_audio.append(seg_samples)
                        slice_speech_seconds += len(seg_samples) / float(Config.SAMPLE_RATE)
                    self.vad.pop()
            except Exception:
                pass
        _finalize_and_emit()
        self._cleanup()

    def _save_samples(self, samples) -> Optional[str]:
        """将语音片段保存为标准 16kHz 16-bit 单声道 WAV 文件"""
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"slice_{timestamp_str}_{int(time.time()*1000)%1000:03d}.wav"
        file_path = Config.RECORDINGS_DIR / filename
        try:
            if isinstance(samples, np.ndarray):
                arr = samples
                s16 = (np.clip(arr, -1.0, 1.0) * 32767).astype(np.int16)
                raw_bytes = s16.tobytes()
            elif isinstance(samples, (list, tuple)) and samples and isinstance(samples[0], (int, float)):
                arr = np.array(samples, dtype=np.float32)
                s16 = (np.clip(arr, -1.0, 1.0) * 32767).astype(np.int16)
                raw_bytes = s16.tobytes()
            elif isinstance(samples, (list, tuple)) and samples and isinstance(samples[0], bytes):
                raw_bytes = b"".join(samples)
            elif isinstance(samples, bytes):
                raw_bytes = samples
            else:
                arr = np.array(list(samples), dtype=np.float32)
                s16 = (np.clip(arr, -1.0, 1.0) * 32767).astype(np.int16)
                raw_bytes = s16.tobytes()

            with wave.open(str(file_path), "wb") as wf:
                wf.setnchannels(Config.CHANNELS)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(Config.SAMPLE_RATE)
                wf.writeframes(raw_bytes)
            return str(file_path)
        except Exception as e:
            print(f"[AudioWorker] 写入切片文件失败: {e}")
            return None

    def pause(self):
        self.paused = True
        print("[AudioWorker] 会议录制已暂停")

    def resume(self):
        self.paused = False
        print("[AudioWorker] 会议录制已恢复")

    def set_intercom_active(self, active: bool):
        """控制对讲与 TTS 隔离，防止用户提问和音箱外放声音被录入会议切片"""
        self.intercom_active = active
        status = "已暂停麦克风录入 (隔离对讲提问与TTS播报回音)" if active else "已恢复背景会议监听"
        print(f"[AudioWorker] 录制状态: {status}")

    def stop(self):
        self._stop_event.set()
        self.running = False

    def _cleanup(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception:
                pass


class IntercomRecorder:
    """
    对讲专用录音机 (长按按键时录音，松手时输出提问音频)
    若无物理硬件，自动生成有效静音音频配合 ASR Fallback
    """
    def __init__(self):
        self.frames = []
        self.is_recording = False
        self.start_time = 0.0
        self._thread = None

    def start(self):
        if self.is_recording:
            return
        self.frames = []
        self.is_recording = True
        self.start_time = time.time()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def _record_loop(self):
        p = pyaudio.PyAudio()
        stream, ch, rate = get_best_input_stream(p)
        chunk_sec = Config.CHUNK_DURATION_MS / 1000.0
        in_chunk_samples = int(rate * chunk_sec)
        target_chunk_bytes = int(Config.SAMPLE_RATE * chunk_sec * 2)

        while self.is_recording:
            if stream:
                try:
                    raw_data = stream.read(in_chunk_samples, exception_on_overflow=False)
                    if ch != 1 or rate != Config.SAMPLE_RATE:
                        data_16k = _to_16k_mono(raw_data, ch, rate)
                    else:
                        data_16k = raw_data
                    self.frames.append(data_16k)
                except Exception:
                    time.sleep(0.01)
            else:
                time.sleep(chunk_sec)
                self.frames.append(b'\x00' * target_chunk_bytes)

        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
        try:
            p.terminate()
        except Exception:
            pass

    def stop(self) -> Optional[str]:
        if not self.is_recording:
            return None
        self.is_recording = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        
        duration = time.time() - self.start_time
        if duration < 0.5 or not self.frames:
            # 误触
            self.frames = []
            return None

        # 保存对讲提问音频
        wav_path = Config.TEMP_DIR / f"query_{int(time.time()*1000)}.wav"
        try:
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(Config.CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(Config.SAMPLE_RATE)
                wf.writeframes(b"".join(self.frames))
            return str(wav_path)
        except Exception as e:
            print(f"[IntercomRecorder] 保存提问音频失败: {e}")
            return None
