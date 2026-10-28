import sys
import os
import time
import datetime
import threading
from typing import Optional

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from config import Config
from core.audio_recorder import AudioSliceWorker, IntercomRecorder
from core.asr_client import ASRClient
from core.llm_summarizer import LLMSummarizer
from core.knowledge_engine import MeetingStore
from core.rag_engine import RAGEngine
from core.tts_engine import TTSEngine
from ui.intercom_hotkey import IntercomHotkeyListener
from ui.main_window import MainWindow
from ui.tray_icon import TrayManager

class AppSignals(QObject):
    hotkey_pressed = pyqtSignal()
    hotkey_released = pyqtSignal(bool)
    slice_processed = pyqtSignal(str, str) # topic, time_str
    instant_ack = pyqtSignal(str)          # ack_audio_path
    stage_progress = pyqtSignal(int, str, str) # step, title, detail
    query_answered = pyqtSignal(str, str, str)  # query_text, answer_markdown, tts_audio_path

class DeskEchoApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.signals = AppSignals()

        # 核心引擎初始化
        self.store = MeetingStore()
        self.asr = ASRClient()
        self.summarizer = LLMSummarizer()
        self.rag = RAGEngine(self.store)
        self.tts = TTSEngine()

        # 音频与对讲组件
        self.audio_worker = AudioSliceWorker(on_slice_ready=self._on_audio_slice_ready)
        self.intercom_recorder = IntercomRecorder()

        # UI 组件 (完全集成至知识溯源控制台，取消右下角独立悬浮窗)
        self.main_window = MainWindow(self.store)
        self.tray = TrayManager()

        # 全局热键监听器
        self.hotkey_listener = IntercomHotkeyListener(
            on_press_cb=lambda: self.signals.hotkey_pressed.emit(),
            on_release_cb=lambda valid: self.signals.hotkey_released.emit(valid)
        )

        self._connect_signals()

    def _connect_signals(self):
        # 信号连接
        self.signals.hotkey_pressed.connect(self._handle_hotkey_pressed)
        self.signals.hotkey_released.connect(self._handle_hotkey_released)
        self.signals.slice_processed.connect(self._handle_slice_processed)
        
        # 阶段性即时反馈
        self.signals.instant_ack.connect(self._handle_instant_ack)
        self.signals.stage_progress.connect(self._handle_stage_progress)
        self.signals.query_answered.connect(self._handle_query_answered)

        # 文字提问 (直接汇聚至知识溯源主解答区)
        self.main_window.query_submitted.connect(self._process_text_query)

        # 录制开关与托盘联动
        self.main_window.record_toggled.connect(self._on_main_record_toggled)
        self.main_window.inject_demo_requested.connect(self._inject_demo_record)
        self.main_window.tts_playback_finished.connect(self._on_tts_finished)
        self.tray.toggle_record_signal.connect(self._on_tray_record_toggled)
        self.tray.show_main_signal.connect(self._show_main_window)
        self.tray.inject_demo_signal.connect(self._inject_demo_record)
        self.tray.quit_signal.connect(self.quit)

    def _on_tts_finished(self):
        # 语音播报结束，短暂缓冲 0.3 秒以衰减房间余音，随后恢复背景录制
        threading.Timer(0.3, lambda: self.audio_worker.set_intercom_active(False)).start()

    def start(self):
        key_display = Config.get_intercom_display_key()
        print("==================================================")
        print("  DeskEcho 桌面常驻会议记忆控制台正在启动...")
        print(f"  全局对讲热键: 长按 [{key_display}] 开始对讲，松开检索")
        print(f"  ASR 引擎: {Config.ASR_PROVIDER}")
        print(f"  LLM 模型: {Config.LLM_MODEL}")
        print("==================================================")

        self.audio_worker.start()
        self.hotkey_listener.start()
        self.main_window.showMaximized()

        self.tray.tray_icon.showMessage(
            "DeskEcho 桌面回响",
            f"已就绪！会议监听开启中，长按【{key_display}】可随时对讲提问。",
            self.tray.tray_icon.MessageIcon.Information,
            2500
        )

        return self.app.exec()

    # ---------------- 录制开关联动 ----------------
    def _on_main_record_toggled(self, is_active: bool):
        if is_active:
            self.audio_worker.resume()
        else:
            self.audio_worker.pause()
        self.tray.set_record_state(is_active)

    def _on_tray_record_toggled(self, is_active: bool):
        if is_active:
            self.audio_worker.resume()
        else:
            self.audio_worker.pause()
        self.main_window.set_record_state(is_active)

    # ---------------- 录音切片处理管道 ----------------
    def _on_audio_slice_ready(self, wav_path: str, start_ts: float, end_ts: float):
        threading.Thread(
            target=self._process_slice_pipeline,
            args=(wav_path, start_ts, end_ts),
            daemon=True
        ).start()

    def _process_slice_pipeline(self, wav_path: str, start_ts: float, end_ts: float):
        start_time_str = datetime.datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M:%S")
        end_time_str = datetime.datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d %H:%M:%S")
        slice_id = f"slice_{int(start_ts)}"

        print(f"[Pipeline] 开始处理切片 {slice_id} ({start_time_str} ~ {end_time_str})...")
        raw_text = self.asr.transcribe(wav_path)
        if not raw_text or not raw_text.strip():
            print(f"[Pipeline] 切片 {slice_id} 为静音或未识别到文本，跳过归档。")
            return

        print(f"[Pipeline] 切片识别文本: {raw_text[:60]}...")
        summary = self.summarizer.summarize(raw_text, start_time_str, end_time_str)

        self.store.insert_record(
            slice_id=slice_id,
            start_time=start_time_str,
            end_time=end_time_str,
            raw_text=raw_text,
            summary=summary,
            audio_path=wav_path
        )

        first_line = summary.split("\n")[0] if summary else "新会议片段已归档"
        self.signals.slice_processed.emit(first_line, start_time_str)

    def _handle_slice_processed(self, topic: str, time_str: str):
        self.main_window.refresh_records()
        self.tray.tray_icon.showMessage(
            "会议资产已归档",
            f"{time_str}\n{topic}",
            self.tray.tray_icon.MessageIcon.Information,
            2500
        )

    # ---------------- 全局热键与提问管道 ----------------
    def _handle_hotkey_pressed(self):
        # 1. 毫秒级优先打断当前正在进行的 TTS 语音播报！
        was_playing = self.main_window.stop_speaking()
        self._intercom_was_interrupting = was_playing

        # 2. 核心声学隔离：立即屏蔽背景录音，彻底防止将【右 Alt】提问语音录入背景会议切片！
        self.audio_worker.set_intercom_active(True)

        self.intercom_recorder.start()
        # 唤醒/展示主界面并在知识解答区顶部展示收音动效
        self._show_main_window()
        self.main_window.show_listening()

    def _handle_hotkey_released(self, is_valid: bool):
        wav_path = self.intercom_recorder.stop()
        
        # 如果时长 < 0.5 秒（属于点按触发）：
        if not is_valid or not wav_path:
            # 如果此前处于播报中，本次点按即为纯粹的“打断/静音”操作！
            if getattr(self, "_intercom_was_interrupting", False):
                self._intercom_was_interrupting = False
                self.main_window.show_interrupted_status()
                self.audio_worker.set_intercom_active(False)
                return
            self._intercom_was_interrupting = False
            self.main_window.reset_banner()
            self.audio_worker.set_intercom_active(False)
            return

        self._intercom_was_interrupting = False
        # 正常长按发问流程：毫秒级零延迟立即反馈：“稍等，正在检索”
        # 保持 audio_worker.set_intercom_active(True)，防止即时反馈和后续播报被录入会议切片！
        ack_audio = self.tts.get_ack_audio_path() or ""
        self.signals.instant_ack.emit(ack_audio)

        threading.Thread(
            target=self._process_audio_query,
            args=(wav_path,),
            daemon=True
        ).start()

    def _handle_instant_ack(self, ack_audio_path: str):
        self.main_window.show_instant_ack(ack_audio_path)
        self.main_window.search_status_lbl.setText("⏳ 稍等，正在检索...")

    def _handle_stage_progress(self, step: int, title: str, detail: str):
        self.main_window.show_stage_update(step, title, detail)
        if step == 0:
            self.main_window.search_status_lbl.setText("")
        else:
            self.main_window.search_status_lbl.setText(f"⚡ {title}")

    def _process_audio_query(self, wav_path: str):
        self.signals.stage_progress.emit(1, "识别语音中...", "🎧 正在听清您的提问内容...")
        query_text = self.asr.transcribe(wav_path)
        
        # 严格过滤：若用户未说话（静音或无有效文本），立即取消检索并恢复背景录音
        if not query_text or not query_text.strip() or query_text.strip() in ("未识别到语音输入", "未识别到有效语音", "None"):
            print("[Intercom] 未检测到有效语音提问 (静音或未开口)，取消检索并恢复背景录音。")
            self.signals.stage_progress.emit(0, "未检测到说话", "未检测到说话声音，请按住【右 Alt】说话后松开")
            self.audio_worker.set_intercom_active(False)
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except Exception:
                pass
            return

        self.signals.stage_progress.emit(2, "已听清提问", f"识别提问：<b>“{query_text}”</b><br><br>🔍 正在检索向量知识库与时间轴切片...")
        time.sleep(0.2)

        def on_rag_progress(title: str, detail: str):
            self.signals.stage_progress.emit(3, title, detail)

        result = self.rag.answer_query(query_text, on_progress=on_rag_progress)
        answer_markdown = result["answer"]
        spoken_text = result.get("spoken_text", "")

        def on_tts_ready(audio_path: str):
            self.signals.query_answered.emit(query_text, answer_markdown, audio_path)

        if Config.ENABLE_TTS and spoken_text:
            self.tts.speak_async(spoken_text, on_audio_ready=on_tts_ready)
            self.signals.query_answered.emit(query_text, answer_markdown, "")
        else:
            self.signals.query_answered.emit(query_text, answer_markdown, "")

    def _process_text_query(self, query_text: str):
        # 无论此前是否正在播报，新提问立即打断前一次播报
        self.main_window.stop_speaking()
        # 开启背景录音隔离，防止即时提示音及播报回音被录入会议切片
        self.audio_worker.set_intercom_active(True)
        ack_audio = self.tts.get_ack_audio_path() or ""
        self.signals.instant_ack.emit(ack_audio)

        def _worker():
            self.signals.stage_progress.emit(2, "正在检索", f"问题：<b>“{query_text}”</b><br><br>🔍 正在检索向量知识库与时间轴...")
            
            def on_rag_progress(title: str, detail: str):
                self.signals.stage_progress.emit(3, title, detail)

            result = self.rag.answer_query(query_text, on_progress=on_rag_progress)
            answer_markdown = result["answer"]
            spoken_text = result.get("spoken_text", "")

            def on_tts_ready(audio_path: str):
                self.signals.query_answered.emit(query_text, answer_markdown, audio_path)

            if Config.ENABLE_TTS and spoken_text:
                self.tts.speak_async(spoken_text, on_audio_ready=on_tts_ready)
                self.signals.query_answered.emit(query_text, answer_markdown, "")
            else:
                self.signals.query_answered.emit(query_text, answer_markdown, "")

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_query_answered(self, query_text: str, answer_markdown: str, audio_path: str):
        # 1. 自动同步提问文本至搜索框，方便提问人核对、复制或重新编辑
        if query_text and query_text != "未识别到语音输入":
            self.main_window.query_input.setText(query_text)

        # 2. 将提问内容以优雅的问答卡形式置于回答卡片顶部
        formatted_answer = f"> ❓ **语音提问**：{query_text}\n\n{answer_markdown}" if (query_text and query_text != "未识别到语音输入") else answer_markdown
        self.main_window.display_answer(formatted_answer, audio_path)

        # 3. 若无 TTS 音频播放，立即恢复背景会议录制；若有播放，由 MainWindow.tts_playback_finished 在播完后恢复
        if not audio_path or not os.path.exists(audio_path):
            self.audio_worker.set_intercom_active(False)

    # ---------------- 窗口控制 ----------------
    def _show_main_window(self):
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        self.main_window.showMaximized()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _inject_demo_record(self):
        now = datetime.datetime.now()
        t1 = (now - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        t2 = (now - datetime.timedelta(hours=1, minutes=45)).strftime("%Y-%m-%d %H:%M:%S")
        slice_id = f"demo_{int(time.time())}"
        raw_text = (
            "张总：关于 DeskEcho 桌面常驻助手的排期，我们必须在 10 月 28 号前跑通全链路。"
            "李工：目前音频切片采用 16kHz 16-bit PCM，满 5 分钟或者满 2 分钟加连续 3 秒静音自动切片切分入库。"
            "王总监：全局热键定在右 Alt，长按对讲，松开检索，误触时间阈值设为 0.5 秒。"
            "张总：好的，预算批复 5 万元，优先保证本地数据安全与检索极速响应。"
        )
        summary = (
            "1. 核心议题（Topic）：DeskEcho 桌面常驻助手 MVP 研发排期与架构定型。\n"
            "2. 决策与结论（Key Decisions）：热键采用右 Alt，误触阈值 0.5 秒；切片策略为满 5 分钟或满 2 分钟+3 秒静音；预算批复 5 万元。\n"
            "3. 待办事项（Action Items）：[李工] 完成音频切片与 VAD 录音通道；[团队] 10月28日前跑通全链路。\n"
            "4. 事实备忘（Key Facts）：采样率 16000Hz 单声道，预算 5 万元人民币。"
        )
        self.store.insert_record(slice_id, t1, t2, raw_text, summary)
        self.main_window.refresh_records()
        self.tray.tray_icon.showMessage("演示数据已注入", "已成功写入一段模拟会议记录，可直接在控制台检索或长按【右 Alt】提问！", self.tray.tray_icon.MessageIcon.Information, 2500)

    def quit(self):
        print("[DeskEcho] 正在退出应用...")
        self.audio_worker.stop()
        self.hotkey_listener.stop()
        self.app.quit()

if __name__ == "__main__":
    app_instance = DeskEchoApp()
    sys.exit(app_instance.start())
