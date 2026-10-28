import os
import math
import random
import html
import re
from PyQt6.QtCore import Qt, QPoint, QUrl, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QLineEdit, QPushButton, QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QPen, QLinearGradient
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class HUDStreamBrowser(QTextBrowser):
    """
    HUD 内带打字机流式输出动效的内容区 (Alma 风格渲染)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self._current_index = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._stream_step)

    def start_streaming(self, markdown_text: str):
        self._full_text = markdown_text
        self._current_index = 0
        self._timer.start()

    def _stream_step(self):
        if self._current_index < len(self._full_text):
            step_chunk = random.randint(2, 4)
            self._current_index = min(len(self._full_text), self._current_index + step_chunk)
            self._render(self._full_text[:self._current_index], is_streaming=True)
        else:
            self._timer.stop()
            self._render(self._full_text, is_streaming=False)

    def _render(self, text: str, is_streaming: bool):
        escaped = html.escape(text.strip())

        # 0. 重点渲染 > ❓ **语音提问**：
        def format_question(m):
            content = m.group(1).strip()
            return f'<div style="background: rgba(38, 176, 228, 0.12); border-left: 3px solid #26B0E4; border-radius: 6px; padding: 6px 11px; margin: 4px 0 6px 0;"><div style="color: #26B0E4; font-weight: bold; font-size: 10px; margin-bottom: 2px;">❓ 识别提问</div><div style="color: #FFFFFF; font-size: 13px; font-weight: 600;">“{content}”</div></div>'
        escaped = re.sub(r'&gt;\s*❓?\s*\*\*语音提问\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_question, escaped, flags=re.DOTALL)

        # 重点渲染结论播报 (美好智能 VI: 靛青 #13459D -> 海青 #26B0E4 -> 鹦鹉绿 #8AC657)
        def format_spoken(m):
            content = m.group(1).strip()
            return f'<div style="background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(19, 69, 157, 0.28), stop:0.55 rgba(38, 176, 228, 0.16), stop:1 rgba(138, 198, 87, 0.12)); border-left: 3px solid #26B0E4; border-radius: 6px; padding: 8px 12px; margin: 6px 0 8px 0;"><div style="color: #26B0E4; font-weight: bold; font-size: 10px; letter-spacing: 0.5px; margin-bottom: 2px;">🎙️ 结论播报 (TTS 极简朗读)</div><div style="color: #FFFFFF; font-size: 13px; font-weight: 600; line-height: 1.45;">{content}</div></div>'
        escaped = re.sub(r'&gt;\s*🎙️?\s*\*\*结论播报\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_spoken, escaped, flags=re.DOTALL)

        escaped = re.sub(r'###\s*(.+?)(?=\n|$)', r'<div style="color: #F8FAFC; font-size: 13px; font-weight: bold; margin: 10px 0 4px 0; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 3px;">\1</div>', escaped)
        escaped = re.sub(r'##\s*(.+?)(?=\n|$)', r'<div style="color: #FFFFFF; font-size: 14px; font-weight: bold; margin: 12px 0 6px 0;">\1</div>', escaped)
        escaped = re.sub(r'\*\*(.+?)\*\*', r'<b style="color: #FBBF24;">\1</b>', escaped)
        escaped = re.sub(r'`([^`]+)`', r'<code style="background-color: rgba(255,255,255,0.08); color: #26B0E4; padding: 2px 4px; border-radius: 4px; font-family: Cascadia Code, Consolas;">\1</code>', escaped)

        # 清理多余空行与换行
        escaped = re.sub(r'\n{3,}', '\n\n', escaped)
        escaped = escaped.strip()
        escaped = escaped.replace("\n", "<br>")
        escaped = re.sub(r'(?:<br>\s*)+(<div)', r'\1', escaped)
        escaped = re.sub(r'(</div>)(?:\s*<br>)+', r'\1', escaped)
        while escaped.startswith("<br>"):
            escaped = escaped[4:].strip()

        cursor = " <span style='color: #26B0E4; font-weight: bold;'>▌</span>" if is_streaming else ""

        self.setHtml(f"<div style='color: #F3F4F6; line-height: 1.6; font-size: 12.5px; font-family: Segoe UI, sans-serif;'>{escaped}{cursor}</div>")


class StageProgressBar(QWidget):
    """
    Alma 风格三段式胶囊进度指示器
    Step 1: 识别提问 -> Step 2: 匹配切片 -> Step 3: 归纳溯源
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self.current_step = 1

    def set_step(self, step: int):
        self.current_step = step
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w, h = rect.width(), rect.height()
        steps = ["1. 听清提问", "2. 检索切片", "3. 归纳溯源"]
        seg_w = w / 3.0

        for i, text in enumerate(steps):
            x = i * seg_w
            is_active = (i + 1) <= self.current_step
            is_current = (i + 1) == self.current_step

            if is_current:
                bg = QColor(38, 176, 228, 200) # 美好智能 海青 #26B0E4
                border_pen = QPen(QColor(138, 198, 87, 220), 1.0) # 鹦鹉绿 #8AC657
            elif is_active:
                bg = QColor(19, 69, 157, 160) # 靛青 #13459D
                border_pen = Qt.PenStyle.NoPen
            else:
                bg = QColor(15, 23, 42, 100)
                border_pen = Qt.PenStyle.NoPen

            painter.setBrush(QBrush(bg))
            painter.setPen(border_pen)
            painter.drawRoundedRect(int(x + 2), 1, int(seg_w - 4), h - 2, 4, 4)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold if is_current else QFont.Weight.Normal))
            text_color = QColor(255, 255, 255) if is_active else QColor(100, 116, 139)
            painter.setPen(text_color)
            painter.drawText(int(x + 2), 1, int(seg_w - 4), h - 2, Qt.AlignmentFlag.AlignCenter, text)


class HUDWindow(QWidget):
    query_submitted = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._init_ui()
        self._position_window()

    def _init_ui(self):
        self.setFixedSize(500, 400)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 外层卡片 (Alma 风格深黑透明磨砂)
        self.card = QFrame()
        self.card.setObjectName("cardFrame")
        self.card.setStyleSheet("""
            QFrame#cardFrame {
                background-color: rgba(10, 12, 17, 0.96);
                border: 1px solid rgba(38, 176, 228, 0.35);
                border-top: 2px solid #26B0E4;
                border-radius: 14px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 220))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # 1. 顶部 Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #10B981; font-size: 13px;")

        self.title_label = QLabel("DeskEcho")
        self.title_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: bold;")

        self.status_text = QLabel("长按【右 Alt】对讲")
        self.status_text.setStyleSheet("color: #94A3B8; font-size: 11px;")

        header_layout.addWidget(self.status_dot)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.status_text)

        self.stop_btn = QPushButton("⏹ 打断")
        self.stop_btn.setToolTip("打断当前语音播报 (也可按右 Alt 或空格打断)")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.2);
                color: #FCA5A5;
                border: 1px solid rgba(239, 68, 68, 0.45);
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.4);
                color: #FFFFFF;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_speaking)
        self.stop_btn.hide()
        header_layout.addWidget(self.stop_btn)

        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                font-size: 11px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)
        card_layout.addLayout(header_layout)

        # 2. 三段式检索进度条
        self.stage_progress = StageProgressBar()
        card_layout.addWidget(self.stage_progress)

        # 3. 核心内容流式浏览器
        self.content_browser = HUDStreamBrowser()
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(6, 8, 12, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                color: #E2E8F0;
                font-size: 12.5px;
                padding: 12px;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.18);
                border-radius: 2px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(38, 176, 228, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
                width: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                border: none;
                background: transparent;
            }
        """)
        self.content_browser.setHtml(
            "<div style='color: #64748B; padding-top: 55px; text-align: center; line-height: 1.8;'>"
            "长按 <b>右 Alt</b> 启动语音对讲，松开即刻检索历史会议<br>"
            "<span style='font-size: 11px;'>系统将通过 DeepSeek 意图改写与混合 RAG 提炼答复</span>"
            "</div>"
        )
        card_layout.addWidget(self.content_browser, 1)

        # 4. 底部输入与提问框 (Alma Command Palette 风格)
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background-color: #0D1017;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(8, 4, 8, 4)
        input_layout.setSpacing(6)

        icon_hint = QLabel("⚡")
        icon_hint.setStyleSheet("font-size: 13px; color: #26B0E4;")
        input_layout.addWidget(icon_hint)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("文字提问历史会议...")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #F8FAFC;
                font-size: 12px;
                padding: 4px;
            }
        """)
        self.input_edit.returnPressed.connect(self._on_text_submitted)
        input_layout.addWidget(self.input_edit, 1)

        send_btn = QPushButton("提问")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #13459D, stop:1 #26B0E4);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0E347A, stop:1 #1FA0D1);
            }
        """)
        send_btn.clicked.connect(self._on_text_submitted)
        input_layout.addWidget(send_btn)

        card_layout.addWidget(input_container)
        main_layout.addWidget(self.card)

    def _position_window(self):
        screen = self.screen().availableGeometry()
        x = screen.right() - self.width() - 24
        y = screen.bottom() - self.height() - 24
        self.move(x, y)

    def is_playing(self) -> bool:
        """检测当前是否正在播放语音"""
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def stop_speaking(self) -> bool:
        """立即打断并停止当前语音播报，返回此前是否正在播放"""
        if self.is_playing():
            self.player.stop()
            if hasattr(self, "stop_btn"):
                self.stop_btn.hide()
            self.status_dot.setStyleSheet("color: #64748B; font-size: 13px;")
            self.status_text.setText("🔇 播报已打断")
            return True
        return False

    def show_interrupted_status(self):
        """点按右 Alt 打断播报后的状态反馈，保留解答卡片内容供阅读"""
        self.status_dot.setStyleSheet("color: #94A3B8; font-size: 13px;")
        self.status_text.setText("🔇 播报已打断 (按 Esc 关闭)")
        if hasattr(self, "stop_btn"):
            self.stop_btn.hide()

    def _on_playback_state_changed(self, state):
        """播放器状态自然改变时的事件回调"""
        if state == QMediaPlayer.PlaybackState.StoppedState:
            if hasattr(self, "stop_btn"):
                self.stop_btn.hide()
            if "播报中" in self.status_text.text():
                self.status_text.setText("回答完毕")
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            if hasattr(self, "stop_btn"):
                self.stop_btn.show()

    def hide(self):
        """隐藏窗口时静默停止当前音频"""
        self.stop_speaking()
        super().hide()

    def show_listening(self):
        """按下右 Alt 麦克风开始收音"""
        self.status_dot.setStyleSheet("color: #EF4444; font-size: 13px;")
        self.status_text.setText("正在收音... (松开【右 Alt】检索)")
        if hasattr(self, "stop_btn"):
            self.stop_btn.hide()
        self.stage_progress.set_step(1)
        self.content_browser.setHtml(
            "<div style='color: #26B0E4; padding-top: 40px; text-align: center; font-size: 14px;'>"
            "<span style='font-size: 26px;'>🎙</span><br><br>"
            "<b>正在倾听您的提问...</b><br><br>"
            "<span style='color: #94A3B8; font-size: 12px;'>说出您的问题，松开按键即刻检索历史会议</span>"
            "</div>"
        )
        self.show()
        self.raise_()
        self.activateWindow()

    def show_instant_ack(self, ack_audio_path: str = ""):
        """松开右 Alt 瞬间毫秒级零延迟立即反馈"""
        self.status_dot.setStyleSheet("color: #8AC657; font-size: 13px;")
        self.status_text.setText("稍等，正在检索...")
        self.stage_progress.set_step(1)

        self.content_browser.setHtml(
            "<div style='padding-top: 36px; text-align: center;'>"
            "<div style='font-size: 17px; color: #26B0E4; font-weight: bold;'>⏳ 稍等，正在检索...</div>"
            "<div style='margin-top: 14px; color: #94A3B8; font-size: 12px;'>🎧 正在将提问转化为文字并对齐记忆切片...</div>"
            "</div>"
        )
        self.show()
        self.raise_()

        if ack_audio_path and os.path.exists(ack_audio_path):
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(ack_audio_path)))
            self.player.play()

    def show_stage_update(self, step: int, stage_title: str, detail_text: str):
        """阶段性进度更新"""
        self.status_dot.setStyleSheet("color: #26B0E4; font-size: 13px;")
        self.status_text.setText(stage_title)
        self.stage_progress.set_step(step)

        self.content_browser.setHtml(
            f"<div style='padding-top: 36px; text-align: center;'>"
            f"<div style='font-size: 15px; color: #8AC657; font-weight: bold;'>{stage_title}</div>"
            f"<div style='margin-top: 14px; color: #E2E8F0; font-size: 12.5px; line-height: 1.6;'>{detail_text}</div>"
            f"</div>"
        )
        self.show()
        self.raise_()

    def show_answer(self, markdown_answer: str, audio_path: str = ""):
        """完成所有检索，展示答案并播放合成语音"""
        self.status_dot.setStyleSheet("color: #8AC657; font-size: 13px;")
        self.stage_progress.set_step(3)
        self.content_browser.start_streaming(markdown_answer)
        self.show()
        self.raise_()

        if audio_path and os.path.exists(audio_path):
            self.status_text.setText("🔊 播报中 (按右 Alt 打断)")
            if hasattr(self, "stop_btn"):
                self.stop_btn.show()
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(audio_path)))
            self.player.play()
        else:
            self.status_text.setText("回答完毕")
            if hasattr(self, "stop_btn"):
                self.stop_btn.hide()

    def _on_text_submitted(self):
        text = self.input_edit.text().strip()
        if text:
            self.stop_speaking()
            self.input_edit.clear()
            self.query_submitted.emit(text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.stop_speaking()
            self.hide()
        elif event.key() == Qt.Key.Key_Space:
            # 空格键也可以打断正在播放的语音
            if self.is_playing():
                self.stop_speaking()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
