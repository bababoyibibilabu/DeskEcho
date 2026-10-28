import os
import sys
import math
import random
import datetime
import html
import re
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QUrl
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextBrowser, QFrame, QSplitter,
    QListWidget, QListWidgetItem, QGraphicsDropShadowEffect,
    QStackedWidget, QScrollArea, QGridLayout, QSizePolicy
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QPen, QLinearGradient
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from config import Config
from core.knowledge_engine import MeetingStore
from core.entity_dict import EMPLOYEES, COMPANY_INFO
from ui.audio_visualizer import AudioWaveVisualizer

class ModernBreathingSwitch(QPushButton):
    """
    Alma 风格的微胶囊呼吸状态开关
    - 活跃状态：深暗底座 + 柔和脉冲绿光光晕 + '🎙️ 实时环境倾听中 [开启]'
    - 暂停状态：静谧暗灰 + '⏸️ 环境倾听已暂停 [点击开启]'
    """
    toggled_state = pyqtSignal(bool)

    def __init__(self, checked: bool = True, parent=None):
        super().__init__(parent)
        self.is_active = checked
        self.setFixedHeight(44)
        self.setMinimumWidth(210)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._toggle)

        self.glow_radius = 5.0
        self.glow_direction = 1
        self.glow_alpha = 150

        self.timer = QTimer(self)
        self.timer.setInterval(35)
        self.timer.timeout.connect(self._animate_glow)
        self.timer.start()

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def _toggle(self):
        self.is_active = not self.is_active
        self.update()
        self.toggled_state.emit(self.is_active)

    def _animate_glow(self):
        if self.is_active:
            self.glow_radius += 0.28 * self.glow_direction
            if self.glow_radius >= 10.0:
                self.glow_direction = -1
            elif self.glow_radius <= 3.5:
                self.glow_direction = 1
            self.glow_alpha = int(80 + (self.glow_radius / 10.0) * 120)
            self.update()
        else:
            if self.glow_radius != 0:
                self.glow_radius = 0
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w, h = rect.width(), rect.height()

        # 胶囊底座
        if self.is_active:
            painter.setBrush(QBrush(QColor(16, 185, 129, 30)))
            painter.setPen(QPen(QColor(138, 198, 87, 180), 1.5))
        else:
            painter.setBrush(QBrush(QColor(245, 158, 11, 25)))
            painter.setPen(QPen(QColor(245, 158, 11, 120), 1.2))

        painter.drawRoundedRect(1, 1, w - 2, h - 2, 10, 10)

        # 呼吸光晕与中心核 (美好智能 鹦鹉绿 #8AC657 动态律动)
        dot_x = 16
        dot_y = h // 2
        core_r = 4.0

        if self.is_active:
            halo_color = QColor(138, 198, 87, int(self.glow_alpha * 0.5))
            painter.setBrush(QBrush(halo_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(dot_x - self.glow_radius), int(dot_y - self.glow_radius),
                                int(self.glow_radius * 2), int(self.glow_radius * 2))

            painter.setBrush(QBrush(QColor(138, 198, 87)))
            painter.drawEllipse(int(dot_x - core_r), int(dot_y - core_r), int(core_r * 2), int(core_r * 2))
        else:
            painter.setBrush(QBrush(QColor(245, 158, 11)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(dot_x - core_r), int(dot_y - core_r), int(core_r * 2), int(core_r * 2))

        # 文字说明 (精炼字数，适配侧栏宽度，确保开启与暂停均完整优雅展示)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_rect = rect.adjusted(30, 0, -6, 0)
        if self.is_active:
            painter.setPen(QColor(241, 245, 249))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "🎙️ 实时倾听中 [已开启]")
        else:
            painter.setPen(QColor(251, 191, 36))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "⏸️ 倾听已暂停 [点击恢复]")


class StreamTextDisplay(QTextBrowser):
    """
    Alma 风格的打字机流式输出渲染器 (富文本 Markdown 转换，支持多轮对话卡片连续追加)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history_turns = []
        self._full_text = ""
        self._current_index = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._stream_step)

    def clear_history(self):
        """清空历史追问卡片，恢复默认导引页"""
        self._timer.stop()
        self._history_turns.clear()
        self._full_text = ""
        self._current_index = 0
        self.setHtml(
            "<div style='color: #475569; text-align: center; padding-top: 100px; line-height: 1.8;'>"
            "💡 在上方输入问题回车，或长按 <b>右 Alt</b> 启动语音对讲 (免按 Fn，空格键右侧直达)<br>"
            "系统将自动完成 <b>Query Rewriting 意图蒸馏</b> 与 <b>Hybrid RAG 混合检索</b><br>"
            "并以<b>音视分离</b>策略给出结论播报与精准上下文溯源"
            "</div>"
        )

    def start_streaming(self, markdown_text: str, is_followup: bool = False):
        if not is_followup:
            self._history_turns.clear()
        else:
            # 追问时最多保留前序 2 轮卡片，防止界面过度冗长
            if len(self._history_turns) > 2:
                self._history_turns = self._history_turns[-2:]

        self._full_text = markdown_text
        self._current_index = 0
        self._timer.start()

    def _stream_step(self):
        if self._current_index < len(self._full_text):
            step_chunk = random.randint(2, 4)
            self._current_index = min(len(self._full_text), self._current_index + step_chunk)
            partial = self._full_text[:self._current_index]
            self._render_combined(partial, is_streaming=(self._current_index < len(self._full_text)))
        else:
            self._timer.stop()
            completed_turn_html = self._format_turn_html(self._full_text, is_streaming=False)
            self._history_turns.append(completed_turn_html)
            self._render_combined(self._full_text, is_streaming=False, use_cached_latest=True)

    def _render_combined(self, active_text: str, is_streaming: bool, use_cached_latest: bool = False):
        parts = []
        if use_cached_latest:
            for i, card_html in enumerate(self._history_turns):
                if i > 0:
                    parts.append(self._get_divider_html())
                parts.append(card_html)
        else:
            for i, card_html in enumerate(self._history_turns):
                if i > 0:
                    parts.append(self._get_divider_html())
                parts.append(card_html)
            if self._history_turns:
                parts.append(self._get_divider_html())
            parts.append(self._format_turn_html(active_text, is_streaming=is_streaming))

        html_body = f"""<div style="line-height: 1.6; color: #E2E8F0; font-size: 12.5px; font-family: 'Segoe UI', -apple-system, sans-serif;">{''.join(parts)}</div>"""
        self.setHtml(html_body)
        
        # 滚轮自动吸底跟随打字流
        sb = self.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _get_divider_html(self) -> str:
        return """
        <div style="margin: 18px 0 14px 0; border-top: 1px dashed rgba(38, 176, 228, 0.28); text-align: center;">
            <span style="background-color: #0A0C10; padding: 2px 12px; color: #8AC657; font-size: 10px; font-weight: bold; border-radius: 4px; border: 1px solid rgba(138, 198, 87, 0.3);">
                ⏱️ 连续追问上下文 · 上下文延续中
            </span>
        </div>
        """

    def _format_turn_html(self, text: str, is_streaming: bool) -> str:
        escaped = html.escape(text.strip())

        # 0. 重点渲染 > ❓ **连续追问**：或 > ❓ **语音提问**：或 **文字提问**
        def format_question(m):
            q_type = m.group(1).strip()
            content = m.group(2).strip()
            if "追问" in q_type:
                return (
                    f'<div style="background: rgba(138, 198, 87, 0.12); border-left: 3px solid #8AC657; border-radius: 6px; padding: 7px 12px; margin: 4px 0 8px 0;">'
                    f'<div style="color: #8AC657; font-weight: bold; font-size: 10px; margin-bottom: 2px;">⚡ 连续追问 (已继承上下文)</div>'
                    f'<div style="color: #FFFFFF; font-size: 13px; font-weight: 600;">“{content}”</div></div>'
                )
            else:
                return (
                    f'<div style="background: rgba(38, 176, 228, 0.12); border-left: 3px solid #26B0E4; border-radius: 6px; padding: 7px 12px; margin: 4px 0 8px 0;">'
                    f'<div style="color: #26B0E4; font-weight: bold; font-size: 10px; margin-bottom: 2px;">❓ 识别提问</div>'
                    f'<div style="color: #FFFFFF; font-size: 13px; font-weight: 600;">“{content}”</div></div>'
                )
        escaped = re.sub(r'&gt;\s*❓?\s*\*\*(语音提问|连续追问|文字提问)\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_question, escaped, flags=re.DOTALL)

        # 1. 重点渲染 > 🎙️ **结论播报**：为 美好智能 VI 风格三色渐变醒目标签卡
        def format_spoken(m):
            content = m.group(1).strip()
            return f'<div style="background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(19, 69, 157, 0.28), stop:0.55 rgba(38, 176, 228, 0.16), stop:1 rgba(138, 198, 87, 0.12)); border-left: 3px solid #26B0E4; border-radius: 6px; padding: 8px 14px; margin: 6px 0 10px 0;"><div style="color: #26B0E4; font-weight: bold; font-size: 10px; letter-spacing: 0.5px; margin-bottom: 3px;">🎙️ 结论播报 (TTS 极简朗读)</div><div style="color: #FFFFFF; font-size: 13px; font-weight: 600; line-height: 1.45;">{content}</div></div>'
        escaped = re.sub(r'&gt;\s*🎙️?\s*\*\*结论播报\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_spoken, escaped, flags=re.DOTALL)

        # 2. Markdown 强调与标题转换
        escaped = re.sub(r'###\s*(.+?)(?=\n|$)', r'<div style="color: #F8FAFC; font-size: 13.5px; font-weight: bold; margin: 12px 0 4px 0; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 3px;">\1</div>', escaped)
        escaped = re.sub(r'##\s*(.+?)(?=\n|$)', r'<div style="color: #FFFFFF; font-size: 14.5px; font-weight: bold; margin: 14px 0 6px 0;">\1</div>', escaped)
        escaped = re.sub(r'\*\*(.+?)\*\*', r'<b style="color: #FBBF24;">\1</b>', escaped)
        escaped = re.sub(r'`([^`]+)`', r'<code style="background-color: rgba(255,255,255,0.08); color: #26B0E4; padding: 2px 4px; border-radius: 4px; font-family: Cascadia Code, Consolas;">\1</code>', escaped)
        
        # 3. 严格清洗空行与换行 (彻底杜绝多余空白)
        escaped = re.sub(r'\n{3,}', '\n\n', escaped)
        escaped = escaped.strip()
        escaped = escaped.replace("\n", "<br>")
        escaped = re.sub(r'(?:<br>\s*)+(<div)', r'\1', escaped)
        escaped = re.sub(r'(</div>)(?:\s*<br>)+', r'\1', escaped)
        while escaped.startswith("<br>"):
            escaped = escaped[4:].strip()

        cursor = " <span style='color: #26B0E4; font-weight: bold; font-size: 13px;'>▌</span>" if is_streaming else ""
        return f"<div>{escaped}{cursor}</div>"


class IntercomBanner(QFrame):
    """
    知识溯源解答区域顶部的全局语音对讲与检索动效长条
    - 未唤醒 (Idle)：暗透磨砂胶囊，提示按住【右 Alt】对讲或文本检索
    - 收音中 (Listening)：红青极光边框 + 实时动态跳动声波 + “正在倾听语音提问...”
    - 检索中 (Processing)：海青科技光晕 + 阶段文字更新 (“稍等，正在检索... / 识别提问 / 混合检索”)
    - 播报中 (Speaking)：翡翠绿呼吸光晕 + 播报声波 + [🔇 打断播报] 按钮
    - 打断状态 (Interrupted)：柔灰提示 “🔇 播报已打断”
    """
    interrupted_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self.set_idle)

        self._setup_ui()
        self.set_idle()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # 状态徽章 (Pill Badge)
        self.badge_lbl = QLabel("🎙️ 右Alt 对讲")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.06);
            color: #94A3B8;
            font-size: 11px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 6px;
        """)
        layout.addWidget(self.badge_lbl)

        # 核心提示文案
        self.status_lbl = QLabel("长按【右 Alt】语音对讲提问 (松开检索) · 或在上方输入框检索")
        self.status_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        self.status_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.status_lbl, 1)

        # 实时动效声波频谱
        self.wave_vis = AudioWaveVisualizer()
        self.wave_vis.setFixedSize(70, 22)
        self.wave_vis.set_active(False)
        layout.addWidget(self.wave_vis)

        # 播报打断按钮 (默认隐藏)
        self.stop_btn = QPushButton("🔇 打断播报")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.4);
                color: #FCA5A5;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.28);
                color: #FFFFFF;
                border-color: #EF4444;
            }
        """)
        self.stop_btn.clicked.connect(self.interrupted_clicked.emit)
        self.stop_btn.hide()
        layout.addWidget(self.stop_btn)

    def set_idle(self):
        self._reset_timer.stop()
        self.stop_btn.hide()
        self.setStyleSheet("""
            IntercomBanner {
                background: rgba(15, 23, 42, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 8px;
            }
        """)
        self.badge_lbl.setText("🎙️ 右Alt 对讲")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.05);
            color: #64748B;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        self.status_lbl.setText("长按【右 Alt】随时语音对讲提问 (松开检索) · 免按 Fn / 支持空格或右 Alt 即刻打断播报")
        self.status_lbl.setStyleSheet("color: #64748B; font-size: 11.5px;")
        self.wave_vis.set_active(False)

    def set_listening(self):
        self._reset_timer.stop()
        self.stop_btn.hide()
        self.setStyleSheet("""
            IntercomBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(239, 68, 68, 0.18), stop:1 rgba(38, 176, 228, 0.12));
                border: 1.5px solid rgba(239, 68, 68, 0.6);
                border-radius: 8px;
            }
        """)
        self.badge_lbl.setText("🔴 正在收音")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(239, 68, 68, 0.25);
            color: #FCA5A5;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        self.status_lbl.setText("正在倾听您的提问... 请说话，松开【右 Alt】即刻检索历史会议")
        self.status_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold;")
        self.wave_vis.set_mode("listening")
        self.wave_vis.set_active(True)

    def set_ack(self):
        self._reset_timer.stop()
        self.stop_btn.hide()
        self.setStyleSheet("""
            IntercomBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(19, 69, 157, 0.25), stop:1 rgba(38, 176, 228, 0.15));
                border: 1.2px solid #26B0E4;
                border-radius: 8px;
            }
        """)
        self.badge_lbl.setText("⏳ 即时响应")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(38, 176, 228, 0.22);
            color: #26B0E4;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        self.status_lbl.setText("稍等，正在检索... 正在将语音对齐向量知识库")
        self.status_lbl.setStyleSheet("color: #81D4FA; font-size: 12px; font-weight: 600;")
        self.wave_vis.set_mode("default")
        self.wave_vis.set_active(True)

    def set_stage(self, step: int, title: str, detail: str):
        self._reset_timer.stop()
        self.stop_btn.hide()
        clean_detail = re.sub(r'<[^>]+>', '', detail).replace('\n', ' ')
        self.badge_lbl.setText(f"⚡ 步骤 {step}/3")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(38, 176, 228, 0.2);
            color: #26B0E4;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        self.status_lbl.setText(f"{title} · {clean_detail}")
        self.status_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        self.wave_vis.set_mode("default")
        self.wave_vis.set_active(True)

    def set_speaking(self):
        self._reset_timer.stop()
        self.stop_btn.show()
        self.setStyleSheet("""
            IntercomBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(16, 185, 129, 0.15), stop:1 rgba(138, 198, 87, 0.10));
                border: 1.2px solid #8AC657;
                border-radius: 8px;
            }
        """)
        self.badge_lbl.setText("🔊 结论播报")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(138, 198, 87, 0.22);
            color: #8AC657;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        self.status_lbl.setText("🎙️ 正在语音播报结论... (按右 Alt、按空格或点击右侧可随时打断)")
        self.status_lbl.setStyleSheet("color: #A5D6A7; font-size: 12px; font-weight: 500;")
        self.wave_vis.set_mode("speaking")
        self.wave_vis.set_active(True)

    def set_completed(self, focal_topic: str = "", is_followup: bool = False):
        self.stop_btn.hide()
        self.wave_vis.set_active(False)
        self.badge_lbl.setText("⚡ 连续就绪" if is_followup else "✅ 检索完成")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(38, 176, 228, 0.15);
            color: #81D4FA;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        if focal_topic:
            self.status_lbl.setText(f"回答已就绪 · 当前焦点「{focal_topic}」，长按【右 Alt】可针对该话题直接追问")
        else:
            self.status_lbl.setText("回答已就绪 · 长按【右 Alt】随时语音对讲追问")
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11.5px;")
        self._reset_timer.start(8000)

    def set_interrupted(self):
        self.stop_btn.hide()
        self.wave_vis.set_active(False)
        self.setStyleSheet("""
            IntercomBanner {
                background: rgba(30, 41, 59, 0.5);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
            }
        """)
        self.badge_lbl.setText("🔇 播报已打断")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(148, 163, 184, 0.15);
            color: #94A3B8;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        self.status_lbl.setText("语音播报已静音打断，完整解答与时间轴记录保留在下方")
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11.5px;")
        self._reset_timer.start(5000)

    def set_no_speech(self, hint: str = ""):
        self._reset_timer.stop()
        self.stop_btn.hide()
        self.wave_vis.set_active(False)
        self.setStyleSheet("""
            IntercomBanner {
                background: rgba(30, 41, 59, 0.45);
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 8px;
            }
        """)
        self.badge_lbl.setText("🎙️ 未听到说话")
        self.badge_lbl.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            color: #CBD5E1;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        msg = hint or "未听到提问声音，请按住【右 Alt】说话，松开即刻检索"
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11.5px;")
        self._reset_timer.start(3500)


class NavButton(QPushButton):
    """
    Alma 风格的侧边栏导航按钮 (激活状态带微光指示条与柔和高亮)
    """
    def __init__(self, icon_str: str, label_str: str, badge_str: str = "", parent=None):
        super().__init__(parent)
        self.icon_str = icon_str
        self.label_str = label_str
        self.badge_str = badge_str
        self.is_active = False

        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def set_badge(self, text: str):
        self.badge_str = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w, h = rect.width(), rect.height()

        # 背景与圆角 (美好智能 VI: 靛青底座 #13459D + 海青指示条 #26B0E4)
        if self.is_active:
            painter.setBrush(QBrush(QColor(19, 69, 157, 48))) # 靛青底座 #13459D
            painter.setPen(QPen(QColor(38, 176, 228, 130), 1.0)) # 海青边框 #26B0E4
            painter.drawRoundedRect(4, 2, w - 8, h - 4, 8, 8)

            # 左侧微光指示小条 (海青 #26B0E4)
            painter.setBrush(QBrush(QColor(38, 176, 228)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(7, 9, 3, h - 18, 1.5, 1.5)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # 图标与主文本
        painter.setFont(QFont("Segoe UI Emoji", 11))
        painter.setPen(QColor(255, 255, 255) if self.is_active else QColor(148, 163, 184))
        painter.drawText(16, 0, 24, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.icon_str)

        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium if not self.is_active else QFont.Weight.DemiBold))
        text_color = QColor(255, 255, 255) if self.is_active else QColor(203, 213, 225)
        painter.setPen(text_color)
        painter.drawText(44, 0, w - 90, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.label_str)

        # 右侧微型 Badge (美好智能 鹦鹉绿 #8AC657)
        if self.badge_str:
            badge_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(badge_font)
            badge_w = max(20, len(self.badge_str) * 7 + 10)
            badge_rect_x = w - badge_w - 12
            badge_rect_y = (h - 18) // 2

            bg_badge = QColor(19, 69, 157, 85) if self.is_active else QColor(255, 255, 255, 16)
            painter.setBrush(QBrush(bg_badge))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect_x, badge_rect_y, badge_w, 18, 9, 9)

            text_badge = QColor(138, 198, 87) if self.is_active else QColor(148, 163, 184)
            painter.setPen(text_badge)
            painter.drawText(badge_rect_x, badge_rect_y, badge_w, 18, Qt.AlignmentFlag.AlignCenter, self.badge_str)


class MainWindow(QMainWindow):
    record_toggled = pyqtSignal(bool)
    query_submitted = pyqtSignal(str)
    inject_demo_requested = pyqtSignal()
    tts_playback_finished = pyqtSignal()
    new_session_requested = pyqtSignal()

    def __init__(self, meeting_store: MeetingStore):
        super().__init__()
        self.store = meeting_store
        self.setWindowTitle("DeskEcho 桌面回响 · 企业常驻会议记忆空间")
        self.resize(1120, 740)
        self.setMinimumSize(960, 620)

        # 内置音频播放器与输出设备 (管理即时反馈与结论播报 TTS)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._init_ui()
        self._setup_timer()
        self.refresh_records()

    def _init_ui(self):
        # Alma 风格全局深邃 Obsidian 调色盘与极致流线型滚动条
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0A0C10;
            }
            QWidget {
                color: #E2E8F0;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
            }
            QFrame#card {
                background-color: #11141D;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 12px;
            }
            QFrame#sidebar {
                background-color: #07090D;
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
            /* 分割线全面隐形消隐，彻底消除白条 */
            QSplitter {
                background: transparent;
                border: none;
            }
            QSplitter::handle {
                background-color: transparent;
            }
            QSplitter::handle:horizontal {
                width: 6px;
                background-color: transparent;
            }
            QSplitter::handle:horizontal:hover {
                background-color: rgba(99, 102, 241, 0.4);
            }
            QSplitter::handle:vertical {
                height: 6px;
                background-color: transparent;
            }
            QSplitter::handle:vertical:hover {
                background-color: rgba(38, 176, 228, 0.4);
            }

            /* 美好智能 VI 品牌风格极简现代化垂直滚动条 */
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.16);
                border-radius: 3px;
                min-height: 28px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(38, 176, 228, 0.8);
            }
            QScrollBar::handle:vertical:pressed {
                background: #13459D;
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

            /* 美好智能 VI 品牌风格极简现代化水平滚动条 */
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 6px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255, 255, 255, 0.16);
                border-radius: 3px;
                min-width: 28px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(38, 176, 228, 0.8);
            }
            QScrollBar::handle:horizontal:pressed {
                background: #13459D;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: transparent;
                height: 0px;
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                border: none;
                background: transparent;
            }
            QScrollBar::corner {
                background: transparent;
            }

            /* 滚动视图全局透明背景适配 */
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_h_layout = QHBoxLayout(central_widget)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # 1. Alma 风格左侧导航 Rail
        self._build_sidebar(main_h_layout)

        # 2. 右侧主工作区 (Top Bar + Stacked Content)
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(14)

        # 顶部 Bar
        self._build_top_bar(content_layout)

        # 多视图切换区
        self.stack = QStackedWidget()
        self._build_page_ask(self.stack)       # Page 0: 对讲与即时问答
        self._build_page_memory(self.stack)    # Page 1: 会议记忆切片库
        self._build_page_roster(self.stack)    # Page 2: 企业通讯录与岗位
        self._build_page_settings(self.stack)  # Page 3: 引擎配置与硬件

        content_layout.addWidget(self.stack, 1)
        main_h_layout.addWidget(content_container, 1)

    # ---------------- 侧边栏构建 ----------------
    def _build_sidebar(self, parent_layout: QHBoxLayout):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 18, 14, 18)
        side_layout.setSpacing(8)

        # 品牌 Workspace 标识卡
        brand_card = QFrame()
        brand_card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
                padding: 4px;
            }
        """)
        brand_layout = QHBoxLayout(brand_card)
        brand_layout.setContentsMargins(10, 8, 10, 8)
        brand_layout.setSpacing(10)

        # 美好智能 VI 品牌 Logo Pill (靛青 #13459D -> 海青 #26B0E4 -> 鹦鹉绿 #8AC657 渐变)
        logo_icon = QLabel("美")
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setFixedSize(30, 30)
        logo_icon.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #13459D, stop:0.5 #26B0E4, stop:1 #8AC657);
            color: #FFFFFF;
            font-size: 15px;
            font-weight: 900;
            border-radius: 7px;
        """)

        brand_text_box = QVBoxLayout()
        brand_text_box.setSpacing(1)
        title_lbl = QLabel("美好智能")
        title_lbl.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;")
        sub_lbl = QLabel("BEAUTIFUL · DeskEcho")
        sub_lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #26B0E4; letter-spacing: 0.5px;")
        brand_text_box.addWidget(title_lbl)
        brand_text_box.addWidget(sub_lbl)

        brand_layout.addWidget(logo_icon)
        brand_layout.addLayout(brand_text_box)
        brand_layout.addStretch()

        side_layout.addWidget(brand_card)
        side_layout.addSpacing(12)

        # 导航分类标题
        nav_label = QLabel("WORKSPACE")
        nav_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748B; letter-spacing: 0.8px; padding-left: 6px;")
        side_layout.addWidget(nav_label)

        # 导航按钮集合
        self.nav_btns = []
        self.btn_ask = NavButton("⚡", "对讲与检索", "右Alt")
        self.btn_ask.clicked.connect(lambda: self._switch_nav(0))
        self.btn_ask.set_active(True)
        self.nav_btns.append(self.btn_ask)
        side_layout.addWidget(self.btn_ask)

        self.btn_memory = NavButton("🧠", "会议记忆库", "0")
        self.btn_memory.clicked.connect(lambda: self._switch_nav(1))
        self.nav_btns.append(self.btn_memory)
        side_layout.addWidget(self.btn_memory)

        self.btn_roster = NavButton("👥", "企业通讯录", "9人")
        self.btn_roster.clicked.connect(lambda: self._switch_nav(2))
        self.nav_btns.append(self.btn_roster)
        side_layout.addWidget(self.btn_roster)

        self.btn_settings = NavButton("⚙️", "引擎与状态", "DeepSeek")
        self.btn_settings.clicked.connect(lambda: self._switch_nav(3))
        self.nav_btns.append(self.btn_settings)
        side_layout.addWidget(self.btn_settings)

        side_layout.addStretch()

        # 声波频谱动效指示器 (置于开关正上方，视觉上完全联动一体)
        vis_container = QHBoxLayout()
        vis_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visualizer = AudioWaveVisualizer()
        self.visualizer.setFixedSize(110, 22)
        vis_container.addWidget(self.visualizer)
        side_layout.addLayout(vis_container)

        side_layout.addSpacing(3)

        # 底部常驻 VAD 录音呼吸胶囊
        self.record_switch = ModernBreathingSwitch(checked=True)
        self.record_switch.toggled_state.connect(self._on_switch_toggled)
        side_layout.addWidget(self.record_switch)

        # 热键小标签
        hotkey_tag = QLabel(f"长按 [{Config.get_intercom_display_key()}] 任意界面语音对讲")
        hotkey_tag.setStyleSheet("color: #64748B; font-size: 11px; text-align: center; padding-top: 4px; padding-left: 4px;")
        side_layout.addWidget(hotkey_tag)

        parent_layout.addWidget(sidebar)

    def _switch_nav(self, index: int):
        for i, btn in enumerate(self.nav_btns):
            btn.set_active(i == index)
        self.stack.setCurrentIndex(index)
        titles = ["对讲与即时检索", "会议记忆切片库", "企业组织通讯录", "系统引擎与状态"]
        self.breadcrumb_lbl.setText(f"DeskEcho / {titles[index]}")

    # ---------------- 顶部栏构建 ----------------
    def _build_top_bar(self, parent_layout: QVBoxLayout):
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        # 面包屑
        self.breadcrumb_lbl = QLabel("DeskEcho / 对讲与即时检索")
        self.breadcrumb_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #94A3B8;")
        top_bar.addWidget(self.breadcrumb_lbl)

        top_bar.addStretch()

        # 快捷刷新操作按钮 (移除开发演示期的 "注入示例" 冗余按钮，保留清新易懂的刷新)
        refresh_btn = QPushButton("🔄 刷新列表")
        refresh_btn.setToolTip("手动同步最新的会议切片与检索索引")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
                border-color: rgba(255, 255, 255, 0.18);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_records)
        top_bar.addWidget(refresh_btn)

        parent_layout.addLayout(top_bar)

    # ---------------- Page 0: 对讲与检索 ----------------
    def _build_page_ask(self, stack: QStackedWidget):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(14)

        # 美好智能 Command 风格检索栏
        cmd_card = QFrame()
        cmd_card.setObjectName("cmd_card")
        cmd_card.setStyleSheet("""
            QFrame#cmd_card {
                background-color: #111520;
                border: 1px solid rgba(38, 176, 228, 0.45);
                border-radius: 12px;
            }
        """)
        cmd_layout = QHBoxLayout(cmd_card)
        cmd_layout.setContentsMargins(14, 10, 14, 10)
        cmd_layout.setSpacing(10)

        search_icon = QLabel("⚡")
        search_icon.setStyleSheet("border: none; background: transparent; font-size: 16px; color: #26B0E4;")
        cmd_layout.addWidget(search_icon)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("提问会议记忆 (例如: 设计海报找谁？昨天讨论了什么？预算定了吗？)")
        self.query_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                font-size: 13px;
                color: #FFFFFF;
                padding: 4px;
            }
        """)
        self.query_input.returnPressed.connect(self._handle_query)
        cmd_layout.addWidget(self.query_input, 1)

        self.search_status_lbl = QLabel("")
        self.search_status_lbl.setStyleSheet("border: none; background: transparent; color: #8AC657; font-size: 11px; font-weight: 600;")
        cmd_layout.addWidget(self.search_status_lbl)

        # 快捷键标签
        shortcut_chip = QLabel("↵ Enter 检索")
        shortcut_chip.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            color: #94A3B8;
            border: none;
            border-radius: 4px;
            padding: 3px 7px;
            font-size: 10px;
            font-weight: bold;
        """)
        cmd_layout.addWidget(shortcut_chip)

        search_btn = QPushButton("检索记忆")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #13459D, stop:1 #26B0E4);
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                padding: 7px 18px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0E347A, stop:1 #1FA0D1);
            }
        """)
        search_btn.clicked.connect(self._handle_query)
        cmd_layout.addWidget(search_btn)

        page_layout.addWidget(cmd_card)

        # 工作区双栏分割 (左：溯源回答卡，右：实时会议流)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        # 左卡：回答区域
        ans_card = QFrame()
        ans_card.setObjectName("card")
        ans_layout = QVBoxLayout(ans_card)
        ans_layout.setContentsMargins(18, 16, 18, 16)
        ans_layout.setSpacing(10)

        ans_title_row = QHBoxLayout()
        ans_title = QLabel("💬 知识溯源解答")
        ans_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        ans_title_row.addWidget(ans_title)
        ans_title_row.addStretch()

        self.new_session_btn = QPushButton("🔄 开启新会话")
        self.new_session_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_session_btn.setToolTip("清空上下文，开启全新的独立话题")
        self.new_session_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #94A3B8;
                font-size: 11px;
                padding: 3px 8px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(38, 176, 228, 0.16);
                border-color: #26B0E4;
                color: #26B0E4;
            }
        """)
        self.new_session_btn.clicked.connect(self.clear_answer_session)
        ans_title_row.addWidget(self.new_session_btn)

        copy_btn = QPushButton("复制内容")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("background: transparent; border: none; color: #94A3B8; font-size: 11px;")
        copy_btn.clicked.connect(self._copy_answer_to_clipboard)
        ans_title_row.addWidget(copy_btn)
        ans_layout.addLayout(ans_title_row)

        # 重点：知识溯源解答区域最上方的全局语音对讲与检索动效长条
        self.intercom_banner = IntercomBanner(self)
        self.intercom_banner.interrupted_clicked.connect(self.stop_speaking)
        ans_layout.addWidget(self.intercom_banner)

        self.answer_browser = StreamTextDisplay()
        self.answer_browser.setOpenExternalLinks(True)
        self.answer_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #0A0C10;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 14px;
                color: #E2E8F0;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        self.answer_browser.setHtml(
            "<div style='color: #475569; text-align: center; padding-top: 100px; line-height: 1.8;'>"
            "💡 在上方输入问题回车，或长按 <b>右 Alt</b> 启动语音对讲 (免按 Fn，空格键右侧直达)<br>"
            "系统将自动完成 <b>Query Rewriting 意图蒸馏</b> 与 <b>Hybrid RAG 混合检索</b><br>"
            "并以<b>音视分离</b>策略给出结论播报与精准上下文溯源"
            "</div>"
        )
        ans_layout.addWidget(self.answer_browser, 1)
        splitter.addWidget(ans_card)

        # 右卡：近期切片资产动态流
        stream_card = QFrame()
        stream_card.setObjectName("card")
        stream_layout = QVBoxLayout(stream_card)
        stream_layout.setContentsMargins(16, 16, 16, 16)
        stream_layout.setSpacing(10)

        stream_title_row = QHBoxLayout()
        stream_title = QLabel("⏱️ 会议切片动态流")
        stream_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        stream_title_row.addWidget(stream_title)
        stream_title_row.addStretch()

        self.slice_count_badge = QLabel("0 段切片")
        self.slice_count_badge.setStyleSheet("color: #26B0E4; font-size: 11px; font-weight: bold;")
        stream_title_row.addWidget(self.slice_count_badge)
        stream_layout.addLayout(stream_title_row)

        self.slice_list = QListWidget()
        self.slice_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.slice_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.slice_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.slice_list.setStyleSheet("""
            QListWidget {
                background-color: #0A0C10;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 6px;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                background-color: #12151F;
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 8px;
                padding: 9px 12px;
                margin-bottom: 6px;
                color: #CBD5E1;
            }
            QListWidget::item:hover {
                background-color: #151D2C;
                border-color: rgba(38, 176, 228, 0.4);
            }
            QListWidget::item:selected {
                background-color: #12213A;
                border-color: #26B0E4;
                color: #FFFFFF;
            }
        """)
        self.slice_list.itemClicked.connect(self._on_slice_clicked)
        stream_layout.addWidget(self.slice_list, 1)

        splitter.addWidget(stream_card)
        splitter.setSizes([640, 320])

        page_layout.addWidget(splitter, 1)
        stack.addWidget(page)

    # ---------------- Page 1: 会议记忆库 (Memory Slices) ----------------
    def _build_page_memory(self, stack: QStackedWidget):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(12)

        # 顶部搜索与统计条
        header_card = QFrame()
        header_card.setObjectName("card")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(14, 10, 14, 10)

        self.mem_search_input = QLineEdit()
        self.mem_search_input.setPlaceholderText("在沉淀的切片纪要中快速搜索关键词 (如: 预算, Logo, 机器人)...")
        self.mem_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0A0C10;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #26B0E4;
            }
        """)
        self.mem_search_input.returnPressed.connect(self._search_memory_slices)
        h_layout.addWidget(self.mem_search_input, 1)

        mem_search_btn = QPushButton("筛选切片")
        mem_search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mem_search_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(19, 69, 157, 0.35);
                color: #26B0E4;
                border: 1px solid rgba(38, 176, 228, 0.45);
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #26B0E4;
                color: #FFFFFF;
            }
        """)
        mem_search_btn.clicked.connect(self._search_memory_slices)
        h_layout.addWidget(mem_search_btn)

        page_layout.addWidget(header_card)

        # 双栏切片检查器 (左：所有切片列表，右：结构化四象限卡片详情)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        # 列表
        self.mem_list = QListWidget()
        self.mem_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mem_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.mem_list.setStyleSheet("""
            QListWidget {
                background-color: #11141D;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 12px;
                padding: 10px;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                background-color: #0A0C10;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 8px;
                color: #CBD5E1;
            }
            QListWidget::item:hover {
                background-color: #151D2C;
                border-color: rgba(38, 176, 228, 0.4);
            }
            QListWidget::item:selected {
                background-color: #12213A;
                border-color: #26B0E4;
                color: #FFFFFF;
            }
        """)
        self.mem_list.currentRowChanged.connect(self._on_mem_item_selected)
        splitter.addWidget(self.mem_list)

        # 详情卡
        self.mem_detail_browser = QTextBrowser()
        self.mem_detail_browser.setOpenExternalLinks(True)
        self.mem_detail_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #11141D;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 12px;
                padding: 18px;
                color: #E2E8F0;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        self.mem_detail_browser.setHtml("<p style='color:#64748B; text-align:center; padding-top:120px;'>请在左侧选择一段会议切片查看完整结构化提取与原始语音转录。</p>")
        splitter.addWidget(self.mem_detail_browser)
        splitter.setSizes([340, 600])

        page_layout.addWidget(splitter, 1)
        stack.addWidget(page)

    # ---------------- Page 2: 企业通讯录 (Org Directory) ----------------
    def _build_page_roster(self, stack: QStackedWidget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid = QGridLayout(container)
        grid.setContentsMargins(4, 4, 14, 40)
        grid.setSpacing(12)

        # 美好智能 VI 品牌色谱：靛青 #13459D、海青 #26B0E4、鹦鹉绿 #8AC657 及其和声衍生色
        colors = ["#13459D", "#26B0E4", "#8AC657", "#1E60B8", "#17A2B8", "#6DAE3E", "#2C75D3", "#38BDF8", "#78B847"]

        for idx, emp in enumerate(EMPLOYEES):
            row = idx // 2
            col = idx % 2

            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(6)

            # 头像 + 姓名 + 岗位
            top_h = QHBoxLayout()
            avatar = QLabel(emp["name"][:1])
            avatar.setFixedSize(34, 34)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c = colors[idx % len(colors)]
            avatar.setStyleSheet(f"""
                background-color: {c};
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
            """)

            info_box = QVBoxLayout()
            info_box.setSpacing(1)
            name_lbl = QLabel(emp["name"])
            name_lbl.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #FFFFFF;")
            title_lbl = QLabel(emp["title"])
            title_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
            info_box.addWidget(name_lbl)
            info_box.addWidget(title_lbl)

            top_h.addWidget(avatar)
            top_h.addLayout(info_box)
            top_h.addStretch()

            # 别名标签
            aliases_str = " / ".join(emp.get("aliases", [])[:3])
            alias_badge = QLabel(f"音似: {aliases_str}")
            alias_badge.setStyleSheet("color: #64748B; font-size: 10px; background: rgba(255,255,255,0.04); padding: 3px 6px; border-radius: 4px;")
            top_h.addWidget(alias_badge)

            card_layout.addLayout(top_h)

            # 职责与技术栈
            duties_lbl = QLabel(f"📌 {emp['duties']}")
            duties_lbl.setWordWrap(True)
            duties_lbl.setStyleSheet("color: #CBD5E1; font-size: 11.5px; line-height: 1.4;")
            card_layout.addWidget(duties_lbl)

            tech_lbl = QLabel(f"⚡ 技术栈/方向: {emp.get('tech_stack', '通用业务')}")
            tech_lbl.setStyleSheet("color: #26B0E4; font-size: 11px;")
            card_layout.addWidget(tech_lbl)

            grid.addWidget(card, row, col)

        scroll.setWidget(container)
        stack.addWidget(scroll)

    # ---------------- Page 3: 引擎配置与状态 (Settings & Status) ----------------
    def _build_page_settings(self, stack: QStackedWidget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(4, 4, 12, 36)
        v_layout.setSpacing(14)

        # 引擎矩阵卡
        engine_card = QFrame()
        engine_card.setObjectName("card")
        e_layout = QVBoxLayout(engine_card)
        e_layout.setContentsMargins(20, 18, 20, 18)
        e_layout.setSpacing(12)

        e_title = QLabel("⚙️ DeskEcho AI 引擎与硬件通信栈 (MVP)")
        e_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        e_layout.addWidget(e_title)

        grid = QGridLayout()
        grid.setSpacing(12)

        items = [
            ("语音识别 (ASR)", f"火山引擎豆包流式 ASR 2.0 (WebSocket V3)\n资源位: {Config.VOLC_RESOURCE_ID}\n备选: 阿里 DashScope SenseVoice / Whisper", "#10B981"),
            ("大模型 (LLM / RAG)", f"DeepSeek V3 ({Config.LLM_MODEL})\n二层 Query Rewriting 意图改写\n音视分离极简播报 Prompt 引擎", "#6366F1"),
            ("语音合成 (TTS)", f"Edge-TTS (微软云原生高质量语音) / 火山豆包\n预加载实时 Ack 音效 (毫秒级响应)", "#06B6D4"),
            ("向量检索与本地存储", f"ChromaDB 持久化向量库 (HNSW)\nSQLite 结构化时间轴 (omni_data/records.db)\nJieba 中文双向倒排检索加权", "#F59E0B"),
            ("拾音与静音切片", "PyAudio 16kHz 16-bit Mono\nWebRTC VAD 智能静音探测 (Aggressiveness=2)\n无麦克风硬件自动切换虚拟静默守护", "#EC4899"),
            ("全局交互与对讲", f"pynput 全局底层热键监听 [{Config.INTERCOM_KEY}]\n支持长按对讲、释放检索 (<0.5s 防抖拦截)\nAlma 风格三态浮窗与动态波形", "#8B5CF6")
        ]

        for idx, (t, d, c) in enumerate(items):
            r = idx // 2
            col = idx % 2
            box = QFrame()
            box.setStyleSheet("background-color: #0A0C10; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px;")
            b_layout = QVBoxLayout(box)
            b_layout.setSpacing(4)
            lbl_t = QLabel(t)
            lbl_t.setStyleSheet(f"color: {c}; font-size: 12px; font-weight: bold;")
            lbl_d = QLabel(d)
            lbl_d.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.4;")
            lbl_d.setWordWrap(True)
            b_layout.addWidget(lbl_t)
            b_layout.addWidget(lbl_d)
            grid.addWidget(box, r, col)

        e_layout.addLayout(grid)
        v_layout.addWidget(engine_card)
        v_layout.addStretch()

        scroll.setWidget(container)
        stack.addWidget(scroll)

    # ---------------- 定时与刷新逻辑 ----------------
    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(8000)
        self.refresh_timer.timeout.connect(self.refresh_records)
        self.refresh_timer.start()

    def refresh_records(self):
        try:
            total_count = self.store.get_total_count() if hasattr(self.store, "get_total_count") else 0
            records = self.store.query_recent(limit=100)
            if total_count == 0:
                total_count = len(records)

            self.slice_list.clear()
            self.mem_list.clear()
            self.cached_records = records

            count_str = f"共 {total_count} 段切片"
            self.slice_count_badge.setText(count_str)
            self.btn_memory.set_badge(str(total_count))

            for rec in records:
                time_str = rec.get("start_time", "")
                if " " in time_str:
                    time_short = time_str.split(" ")[1][:5]
                else:
                    time_short = time_str[:5]

                summary = rec.get("summary", "")
                first_line = summary.split("\n")[0] if summary else "常驻录音切片"
                first_line = re.sub(r'^[\s\d\.\-、*#]*(?:核心议题|议题|Topic|【核心议题】|主题)(?:[（\(].*?[）\)])?[：:\s]*', '', first_line).strip()
                if not first_line:
                    first_line = "常规会议沟通讨论"

                # 动态流条目 (纯净时间 + 核心事件，超出自动省略)
                item = QListWidgetItem(f"⏱️ {time_short}  {first_line[:24]}")
                item.setToolTip(f"{time_str}\n{first_line}")
                item.setData(Qt.ItemDataRole.UserRole, rec)
                self.slice_list.addItem(item)

                # 记忆库条目
                mem_item = QListWidgetItem(f"📅 {time_str}\n   {first_line[:28]}")
                mem_item.setToolTip(f"{time_str}\n{first_line}")
                mem_item.setData(Qt.ItemDataRole.UserRole, rec)
                self.mem_list.addItem(mem_item)

            if records and self.mem_list.count() > 0:
                self.mem_list.setCurrentRow(0)

        except Exception as e:
            print(f"[MainWindow] 刷新记录失败: {e}")

    def _on_slice_clicked(self, item: QListWidgetItem):
        rec = item.data(Qt.ItemDataRole.UserRole)
        if rec:
            self._render_record_to_detail(rec, self.answer_browser)

    def _on_mem_item_selected(self, row: int):
        if row < 0 or not hasattr(self, "cached_records") or row >= len(self.cached_records):
            return
        rec = self.cached_records[row]
        self._render_record_to_detail(rec, self.mem_detail_browser)

    def _render_record_to_detail(self, rec: dict, browser: QTextBrowser):
        start_t = rec.get("start_time", "")
        end_t = rec.get("end_time", "")
        summary = rec.get("summary", "")
        raw_text = rec.get("raw_text", "")

        detail_html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; line-height: 1.6;">
            <div style="background-color: rgba(19, 69, 157, 0.22); border-left: 3px solid #26B0E4; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px;">
                <span style="color: #26B0E4; font-weight: bold; font-size: 11px;">会议切片区间</span><br>
                <span style="color: #FFFFFF; font-size: 13px; font-weight: 600;">{start_t} 至 {end_t}</span>
            </div>

            <div style="color: #F8FAFC; font-size: 14px; font-weight: bold; margin-bottom: 6px;">📋 结构化纪要提取</div>
            <div style="background-color: #0A0C10; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px; color: #CBD5E1; font-size: 12px; white-space: pre-wrap; margin-bottom: 14px;">
{summary}
            </div>

            <div style="color: #F8FAFC; font-size: 14px; font-weight: bold; margin-bottom: 6px;">🎙️ 原始语音对话转录</div>
            <div style="background-color: #0A0C10; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px; color: #94A3B8; font-size: 12px; line-height: 1.5; white-space: pre-wrap;">
{raw_text}
            </div>
        </div>
        """
        browser.setHtml(detail_html)

    def _search_memory_slices(self):
        kw = self.mem_search_input.text().strip()
        if not kw:
            self.refresh_records()
            return

        matched = self.store.query_by_keywords([kw], limit=100)
        self.mem_list.clear()
        self.cached_records = matched
        for rec in matched:
            time_str = rec.get("start_time", "")
            summary = rec.get("summary", "")
            first_line = summary.split("\n")[0] if summary else "匹配切片"
            item = QListWidgetItem(f"📅 {time_str}\n   🔍 {first_line[:28]}")
            item.setData(Qt.ItemDataRole.UserRole, rec)
            self.mem_list.addItem(item)

        if matched:
            self.mem_list.setCurrentRow(0)
        else:
            self.mem_detail_browser.setHtml(f"<p style='color:#64748B; text-align:center; padding-top:100px;'>未检索到与 <b>“{kw}”</b> 相关的会议切片。</p>")

    def _handle_query(self):
        text = self.query_input.text().strip()
        if text:
            self.query_submitted.emit(text)

    def _copy_answer_to_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        text = self.answer_browser.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.search_status_lbl.setText("✓ 已复制到剪贴板")
            QTimer.singleShot(2000, lambda: self.search_status_lbl.setText(""))

    def _on_switch_toggled(self, active: bool):
        self.visualizer.set_active(active)
        self.record_toggled.emit(active)

    def set_record_state(self, active: bool):
        self.record_switch.set_active(active)
        self.visualizer.set_active(active)

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            if hasattr(self, "intercom_banner") and "播报" in self.intercom_banner.badge_lbl.text():
                self.intercom_banner.set_completed()
            self.tts_playback_finished.emit()

    def is_playing(self) -> bool:
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def stop_speaking(self) -> bool:
        if self.is_playing():
            self.player.stop()
            self.intercom_banner.set_interrupted()
            self.tts_playback_finished.emit()
            return True
        return False

    def show_listening(self):
        self.intercom_banner.set_listening()

    def show_instant_ack(self, ack_audio_path: str = ""):
        self.intercom_banner.set_ack()
        if ack_audio_path and os.path.exists(ack_audio_path):
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(ack_audio_path)))
            self.player.play()

    def show_stage_update(self, step: int, title: str, detail: str):
        if step == 0:
            self.search_status_lbl.setText("")
            self.intercom_banner.set_no_speech(detail)
        else:
            self.intercom_banner.set_stage(step, title, detail)

    def clear_answer_session(self):
        """清空当前问答界面和会话上下文"""
        self.answer_browser.clear_history()
        self.intercom_banner.set_idle()
        self.new_session_requested.emit()

    def display_answer(self, markdown_text: str, audio_path: str = "", is_followup: bool = False, focal_topic: str = ""):
        self.search_status_lbl.setText("")
        self.answer_browser.start_streaming(markdown_text, is_followup=is_followup)
        if audio_path and os.path.exists(audio_path):
            self.intercom_banner.set_speaking()
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(audio_path)))
            self.player.play()
        else:
            self.intercom_banner.set_completed(focal_topic=focal_topic, is_followup=is_followup)

    def show_interrupted_status(self):
        self.intercom_banner.set_interrupted()

    def reset_banner(self):
        self.intercom_banner.set_idle()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.is_playing():
                self.stop_speaking()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """点击窗口右上角 X 号时，静默最小化到系统右下角托盘，保持后台守护与【右 Alt】对讲"""
        event.ignore()
        self.hide()
