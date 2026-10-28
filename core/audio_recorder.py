import time
import wave
import threading
import webrtcvad
import pyaudio
from pathlib import Path
from typing import Callable, Optional, Tuple
from config import Config

def get_best_input_stream(p: pyaudio.PyAudio) -> Tuple[Optional[pyaudio.Stream], int, int]:
    """
    智能探测并尝试打开最适配的麦克风音频流。
    返回: (stream, channels, sample_rate)
    """
    # 1. 尝试默认设备
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
    后台常驻音频捕获与智能切片线程。
    具备硬件自适应与虚拟静默守护机制：在未插物理麦克风时保持稳定运行并守护系统。
    """
    def __init__(self, on_slice_ready: Callable[[str, float, float], None]):
        super().__init__(daemon=True)
        self.on_slice_ready = on_slice_ready
        self.running = False
        self.paused = False
        self.intercom_active = False # 对讲与播报隔离标记，激活时彻底屏蔽麦克风入库
        self._stop_event = threading.Event()
        
        # VAD 检测器
        self.vad = webrtcvad.Vad(Config.VAD_MODE)
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.is_virtual = False

    def run(self):
        self.running = True
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.stream, ch, rate = get_best_input_stream(self.pyaudio_instance)
        except Exception as e:
            self.stream = None

        if self.stream is None:
            self.is_virtual = True
            print("[AudioWorker] [提示] 当前未检测到已就绪的硬件麦克风输入，已开启后台虚拟守护监听模式。")
        else:
            print("[AudioWorker] 麦克风硬件音频采集已启动...")

        frames = []
        slice_start_time = time.time()
        continuous_silence_seconds = 0.0
        chunk_sec = Config.CHUNK_DURATION_MS / 1000.0
        chunk_bytes = int(Config.SAMPLE_RATE * chunk_sec * 2)  # 16-bit mono 对应字节数

        while not self._stop_event.is_set():
            if self.paused:
                time.sleep(0.1)
                slice_start_time = time.time()
                frames.clear()
                continuous_silence_seconds = 0.0
                continue

            if self.intercom_active:
                # 对讲或 TTS 播报期间：持续读取并清空硬件缓冲区，但绝不写入会议切片 frames！
                if not self.is_virtual and self.stream:
                    try:
                        self.stream.read(Config.CHUNK_SIZE, exception_on_overflow=False)
                    except Exception:
                        pass
                time.sleep(chunk_sec)
                continue

            if self.is_virtual:
                # 虚拟静默模式下维持节拍
                time.sleep(chunk_sec)
                data = b'\x00' * chunk_bytes
                is_speech = False
            else:
                try:
                    data = self.stream.read(Config.CHUNK_SIZE, exception_on_overflow=False)
                    try:
                        is_speech = self.vad.is_speech(data, Config.SAMPLE_RATE)
                    except Exception:
                        is_speech = False
                except Exception:
                    time.sleep(0.01)
                    continue

            frames.append(data)

            if is_speech:
                continuous_silence_seconds = 0.0
            else:
                continuous_silence_seconds += chunk_sec

            elapsed_seconds = time.time() - slice_start_time

            # 判定切片条件
            is_max_reached = elapsed_seconds >= Config.MAX_SLICE_SECONDS
            is_silence_cut = (elapsed_seconds >= Config.MIN_SILENCE_CUT_SECONDS) and (
                continuous_silence_seconds >= Config.SILENCE_DURATION_SECONDS
            )

            # 虚拟模式下不向转录队列产生无意义的全静音切片，避免浪费 API 调用
            if (is_max_reached or is_silence_cut) and len(frames) > 0:
                if not self.is_virtual and elapsed_seconds >= 5.0:
                    end_time = time.time()
                    wav_path = self._save_slice(frames)
                    if wav_path:
                        print(f"[AudioWorker] 产生切片: {wav_path} (时长: {elapsed_seconds:.1f}s)")
                        self.on_slice_ready(wav_path, slice_start_time, end_time)
                
                frames = []
                slice_start_time = time.time()
                continuous_silence_seconds = 0.0

        self._cleanup()

    def _save_slice(self, frames: list[bytes]) -> Optional[str]:
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"slice_{timestamp_str}_{int(time.time()*1000)%1000:03d}.wav"
        file_path = Config.RECORDINGS_DIR / filename
        try:
            with wave.open(str(file_path), "wb") as wf:
                wf.setnchannels(Config.CHANNELS)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(Config.SAMPLE_RATE)
                wf.writeframes(b"".join(frames))
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
        stream, _, _ = get_best_input_stream(p)
        chunk_sec = Config.CHUNK_DURATION_MS / 1000.0
        chunk_bytes = int(Config.SAMPLE_RATE * chunk_sec * 2)

        while self.is_recording:
            if stream:
                try:
                    data = stream.read(Config.CHUNK_SIZE, exception_on_overflow=False)
                    self.frames.append(data)
                except Exception:
                    time.sleep(0.01)
            else:
                time.sleep(chunk_sec)
                self.frames.append(b'\x00' * chunk_bytes)

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
