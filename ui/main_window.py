import os
import sys
import math
import random
import datetime
import html
import re
import json
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QUrl, QMetaObject
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextBrowser, QFrame, QSplitter,
    QListWidget, QListWidgetItem, QGraphicsDropShadowEffect,
    QStackedWidget, QScrollArea, QGridLayout, QSizePolicy, QMenu,
    QMessageBox, QCheckBox, QComboBox, QProxyStyle, QStyle, QApplication
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QBrush, QPen, QLinearGradient, QFontMetrics
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class NoFocusRectStyle(QProxyStyle):
    """全局禁用 Windows 原生粗糙的虚线焦点框 (PE_FrameFocusRect)"""
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)

from config import Config
from version import APP_VERSION, APP_NAME, RELEASE_DATE
from core.knowledge_engine import MeetingStore, assess_slice_utility
from core.entity_dict import EMPLOYEES, COMPANY_INFO, get_dynamic_employee_profile
from core.updater import AutoUpdateWorker, UpdateChecker
from ui.audio_visualizer import AudioWaveVisualizer
from ui.theme_manager import ThemeManager, ThemeType
from ui.components.icons import get_symbol_icon, get_symbol_pixmap, get_flower_logo_icon, get_flower_logo_pixmap
from ui.components.modern_dialog import ModernDialog
from ui.components.border_beam import BorderBeamContainer
from ui.components.modern_combobox import ModernComboBox, get_modern_combobox_style
from ui.styles import (
    get_cmd_card_style, get_ans_card_style, get_answer_browser_style,
    get_top_version_style, get_theme_btn_style, get_intercom_banner_style,
    get_mem_list_style, get_mem_detail_style
)

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

        tm = ThemeManager.get_instance()
        is_light = tm.is_light()
        colors = tm.get_colors()

        # 胶囊底座
        if self.is_active:
            if is_light:
                painter.setBrush(QBrush(QColor(22, 163, 74, 18)))
                painter.setPen(QPen(QColor(22, 163, 74, 160), 1.2))
            else:
                painter.setBrush(QBrush(QColor(16, 185, 129, 30)))
                painter.setPen(QPen(QColor(138, 198, 87, 180), 1.2))
        else:
            painter.setBrush(QBrush(QColor(245, 158, 11, 20)))
            painter.setPen(QPen(QColor(245, 158, 11, 120), 1.2))

        painter.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)

        # 状态指示圆点
        dot_x = 16
        dot_y = h // 2
        core_r = 4.0

        if self.is_active:
            active_color = QColor(colors["brand_success"])
            halo_color = QColor(active_color.red(), active_color.green(), active_color.blue(), int(self.glow_alpha * 0.45))
            painter.setBrush(QBrush(halo_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(dot_x - self.glow_radius), int(dot_y - self.glow_radius),
                                int(self.glow_radius * 2), int(self.glow_radius * 2))

            painter.setBrush(QBrush(active_color))
            painter.drawEllipse(int(dot_x - core_r), int(dot_y - core_r), int(core_r * 2), int(core_r * 2))
        else:
            painter.setBrush(QBrush(QColor(245, 158, 11)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(dot_x - core_r), int(dot_y - core_r), int(core_r * 2), int(core_r * 2))

        # 文字说明 (自适应双主题对比度)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_rect = rect.adjusted(30, 0, -6, 0)
        if self.is_active:
            painter.setPen(QColor(colors["text_primary"]))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "实时倾听中 [已开启]")
        else:
            pause_color = QColor("#D97706" if is_light else "#FBBF24")
            painter.setPen(pause_color)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "倾听已暂停 [点击恢复]")


class StreamTextDisplay(QTextBrowser):
    """
    Alma 风格的打字机流式输出渲染器 (富文本 Markdown 转换，支持多轮对话卡片连续追加)
    """
    streaming_started = pyqtSignal()
    streaming_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history_turns = []
        self._full_text = ""
        self._current_index = 0
        self._is_streaming = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._stream_step)

    def is_streaming(self) -> bool:
        return self._is_streaming

    def clear_history(self):
        """清空历史追问卡片，恢复默认导引页 (立足用户视角，呈现具体可行动示例，无机械模版套话)"""
        self._timer.stop()
        self._is_streaming = False
        self._history_turns.clear()
        self._full_text = ""
        self._current_index = 0
        self.streaming_finished.emit()
        is_light = ThemeManager.get_instance().is_light()

        title_color = "#0F172A" if is_light else "#F8FAFC"
        key_bg = "#E2E8F0" if is_light else "rgba(38, 176, 228, 0.15)"
        key_color = "#0284C7" if is_light else "#38BDF8"
        key_border = "#CBD5E1" if is_light else "rgba(38, 176, 228, 0.4)"
        body_color = "#334155" if is_light else "#94A3B8"
        sub_color = "#64748B" if is_light else "#64748B"
        pill_bg = "#FFFFFF" if is_light else "#121622"
        pill_border = "#E2E8F0" if is_light else "rgba(255, 255, 255, 0.08)"
        quote_c = "#475569" if is_light else "#CBD5E1"

        self.setHtml(f"""
            <div style="text-align: center; padding-top: 75px; font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif;">
                <div style="font-size: 16px; font-weight: 700; color: {title_color}; margin-bottom: 8px;">
                    随时唤醒企业会议记忆
                </div>
                <div style="font-size: 13px; color: {body_color}; margin-bottom: 22px; line-height: 1.6;">
                    长按 <span style="background-color: {key_bg}; color: {key_color}; padding: 2px 7px; border-radius: 4px; font-size: 12px; font-weight: 600; border: 1px solid {key_border};">右 Alt</span> 语音对讲，或在上方直接输入问题
                </div>
                <div style="display: inline-block; text-align: left; background: {pill_bg}; border: 1px solid {pill_border}; border-radius: 10px; padding: 14px 22px; line-height: 1.85;">
                    <div style="font-size: 11px; font-weight: 600; color: {sub_color}; margin-bottom: 4px;">例如你可以询问：</div>
                    <div style="font-size: 12.5px; color: {quote_c};">“昨天下午的会议主要讨论了什么？”</div>
                    <div style="font-size: 12.5px; color: {quote_c};">“杨年新最近主导负责哪些业务推进？”</div>
                    <div style="font-size: 12.5px; color: {quote_c};">“关于机器人后端接口规范，定下来了吗？”</div>
                </div>
            </div>
        """)

    def load_history_session(self, turns: list):
        """一次性加载整场历史会话的所有问答卡片"""
        self._timer.stop()
        self._history_turns.clear()
        self._full_text = ""
        self._current_index = 0

        if not turns:
            self.clear_history()
            return

        for i, t in enumerate(turns):
            user_q = t.get("user_query", "").strip()
            markdown_body = t.get("detailed_markdown", "").strip()
            is_follow = (i > 0)
            q_label = "连续追问" if is_follow else "语音提问"
            if user_q and not markdown_body.startswith("> **"):
                full_card_text = f"> **{q_label}**：{user_q}\n\n{markdown_body}"
            else:
                full_card_text = markdown_body
            card_html = self._format_turn_html(full_card_text, is_streaming=False)
            self._history_turns.append(card_html)

        self._render_combined("", is_streaming=False, use_cached_latest=True)

    def start_streaming(self, markdown_text: str, is_followup: bool = False):
        if not is_followup:
            self._history_turns.clear()
        else:
            # 追问时最多保留前序 2 轮卡片，防止界面过度冗长
            if len(self._history_turns) > 2:
                self._history_turns = self._history_turns[-2:]

        self._full_text = markdown_text
        self._current_index = 0
        self._is_streaming = True
        self.streaming_started.emit()
        self._timer.start()

    def _stream_step(self):
        if self._current_index < len(self._full_text):
            step_chunk = random.randint(2, 4)
            self._current_index = min(len(self._full_text), self._current_index + step_chunk)
            partial = self._full_text[:self._current_index]
            self._render_combined(partial, is_streaming=(self._current_index < len(self._full_text)))
        else:
            self._timer.stop()
            self._is_streaming = False
            self.streaming_finished.emit()
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

        is_light = ThemeManager.get_instance().is_light()
        body_color = "#0F172A" if is_light else "#E2E8F0"
        html_body = f"""<div style="line-height: 1.6; color: {body_color}; font-size: 12.5px; font-family: -apple-system, 'Segoe UI', sans-serif;">{''.join(parts)}</div>"""
        self.setHtml(html_body)
        
        # 滚轮自动吸底跟随打字流
        sb = self.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _get_divider_html(self) -> str:
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            return """
            <div style="margin: 18px 0 14px 0; border-top: 1px dashed rgba(2, 132, 199, 0.25); text-align: center;">
                <span style="background-color: #F8FAFC; padding: 2px 12px; color: #16A34A; font-size: 10px; font-weight: bold; border-radius: 4px; border: 1px solid rgba(22, 163, 74, 0.3);">
                    连续追问上下文 · 上下文延续中
                </span>
            </div>
            """
        return """
        <div style="margin: 18px 0 14px 0; border-top: 1px dashed rgba(38, 176, 228, 0.28); text-align: center;">
            <span style="background-color: #0A0C10; padding: 2px 12px; color: #8AC657; font-size: 10px; font-weight: bold; border-radius: 4px; border: 1px solid rgba(138, 198, 87, 0.3);">
                连续追问上下文 · 上下文延续中
            </span>
        </div>
        """

    def _format_turn_html(self, text: str, is_streaming: bool) -> str:
        # 清除任何历史残留或外部携带的静态 Emoji
        text = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]', '', text)
        escaped = html.escape(text.strip())
        is_light = ThemeManager.get_instance().is_light()

        # 0. 重点渲染 > **连续追问**：或 > **语音提问**：或 **文字提问** (无 Emoji)
        def format_question(m):
            q_type = m.group(1).strip()
            content = m.group(2).strip()
            text_c = "#0F172A" if is_light else "#FFFFFF"
            if "追问" in q_type:
                bg = "rgba(22, 163, 74, 0.08)" if is_light else "rgba(138, 198, 87, 0.10)"
                border_c = "rgba(22, 163, 74, 0.3)" if is_light else "rgba(138, 198, 87, 0.35)"
                title_c = "#16A34A" if is_light else "#8AC657"
                return (
                    f'<div style="background: {bg}; border: 1px solid {border_c}; border-radius: 6px; padding: 8px 12px; margin: 4px 0 8px 0;">'
                    f'<div style="color: {title_c}; font-weight: bold; font-size: 10.5px; margin-bottom: 2px;">连续追问 (已继承上下文)</div>'
                    f'<div style="color: {text_c}; font-size: 13px; font-weight: 600;">“{content}”</div></div>'
                )
            else:
                bg = "rgba(2, 132, 199, 0.06)" if is_light else "rgba(38, 176, 228, 0.08)"
                border_c = "rgba(2, 132, 199, 0.25)" if is_light else "rgba(38, 176, 228, 0.3)"
                title_c = "#0284C7" if is_light else "#38BDF8"
                return (
                    f'<div style="background: {bg}; border: 1px solid {border_c}; border-radius: 6px; padding: 8px 12px; margin: 4px 0 8px 0;">'
                    f'<div style="color: {title_c}; font-weight: bold; font-size: 10.5px; margin-bottom: 2px;">识别提问</div>'
                    f'<div style="color: {text_c}; font-size: 13px; font-weight: 600;">“{content}”</div></div>'
                )
        escaped = re.sub(r'&gt;\s*❓?\s*\*\*(语音提问|连续追问|文字提问)\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_question, escaped, flags=re.DOTALL)

        # 0.4 重点渲染 > **敏捷自进化工单**：
        def format_instruction_pill(m):
            info = m.group(1).strip()
            bg = "rgba(245, 158, 11, 0.08)" if is_light else "rgba(245, 158, 11, 0.14)"
            border_c = "rgba(217, 119, 6, 0.3)" if is_light else "rgba(245, 158, 11, 0.35)"
            title_c = "#D97706" if is_light else "#FBBF24"
            desc_c = "#334155" if is_light else "#94A3B8"
            return (
                f'<div style="background: {bg}; border: 1px solid {border_c}; border-radius: 6px; padding: 6px 12px; margin: 4px 0 8px 0;">'
                f'<span style="color: {title_c}; font-weight: bold; font-size: 11px;">敏捷自进化工单已立项</span>'
                f'<span style="color: {desc_c}; font-size: 11px; margin-left: 8px;">{info}</span></div>'
            )
        escaped = re.sub(r'&gt;\s*🚀?\s*\*\*敏捷自进化工单\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_instruction_pill, escaped, flags=re.DOTALL)

        # 0.5 重点渲染 > **全网通用知识解答**：
        def format_general_badge(m):
            content = m.group(1).strip()
            if is_light:
                return (
                    f'<div style="background: rgba(147, 51, 234, 0.06); border: 1px solid rgba(147, 51, 234, 0.25); border-radius: 6px; padding: 8px 12px; margin: 6px 0 10px 0;">'
                    f'<div style="color: #9333EA; font-weight: bold; font-size: 10.5px; margin-bottom: 3px; letter-spacing: 0.5px;">'
                    f'全网通用知识解答 (非企业内部会议决策依据)</div>'
                    f'<div style="color: #0F172A; font-size: 12px; line-height: 1.5;">{content}</div></div>'
                )
            return (
                f'<div style="background: rgba(139, 92, 246, 0.12); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 6px; padding: 8px 12px; margin: 6px 0 10px 0;">'
                f'<div style="color: #C084FC; font-weight: bold; font-size: 10.5px; margin-bottom: 3px; letter-spacing: 0.5px;">'
                f'全网通用知识解答 (非企业内部会议决策依据)</div>'
                f'<div style="color: #E2E8F0; font-size: 12px; line-height: 1.5;">{content}</div></div>'
            )
        escaped = re.sub(r'&gt;\s*🌐?\s*\*\*全网通用知识解答\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_general_badge, escaped, flags=re.DOTALL)

        # 1. 重点渲染 > **结论播报**：或 > **架构师响应**：
        def format_spoken(m):
            tag = m.group(1).strip()
            content = m.group(2).strip()
            text_c = "#0F172A" if is_light else "#FFFFFF"
            if "架构师" in tag:
                bg = "rgba(245, 158, 11, 0.08)" if is_light else "rgba(245, 158, 11, 0.16)"
                border_c = "rgba(217, 119, 6, 0.3)" if is_light else "rgba(245, 158, 11, 0.35)"
                title_c = "#D97706" if is_light else "#FBBF24"
                return (
                    f'<div style="background: {bg}; border: 1px solid {border_c}; border-radius: 6px; padding: 8px 14px; margin: 6px 0 10px 0;">'
                    f'<div style="color: {title_c}; font-weight: bold; font-size: 10.5px; letter-spacing: 0.5px; margin-bottom: 3px;">架构师响应 (已录入自进化队列)</div>'
                    f'<div style="color: {text_c}; font-size: 13px; font-weight: 600; line-height: 1.45;">{content}</div></div>'
                )
            if is_light:
                return (
                    f'<div style="background: rgba(2, 132, 199, 0.06); border: 1px solid rgba(2, 132, 199, 0.22); border-radius: 6px; padding: 8px 14px; margin: 6px 0 10px 0;">'
                    f'<div style="color: #0284C7; font-weight: bold; font-size: 10.5px; letter-spacing: 0.5px; margin-bottom: 3px;">结论播报 (TTS 极简朗读)</div>'
                    f'<div style="color: #0F172A; font-size: 13px; font-weight: 600; line-height: 1.45;">{content}</div></div>'
                )
            return (
                f'<div style="background: rgba(38, 176, 228, 0.10); border: 1px solid rgba(38, 176, 228, 0.28); border-radius: 6px; padding: 8px 14px; margin: 6px 0 10px 0;">'
                f'<div style="color: #26B0E4; font-weight: bold; font-size: 10.5px; letter-spacing: 0.5px; margin-bottom: 3px;">结论播报 (TTS 极简朗读)</div>'
                f'<div style="color: #FFFFFF; font-size: 13px; font-weight: 600; line-height: 1.45;">{content}</div></div>'
            )
        escaped = re.sub(r'&gt;\s*🎙️?\s*\*\*(结论播报|架构师响应)\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_spoken, escaped, flags=re.DOTALL)

        # 1.5 渲染 > **自动流转**：提示卡
        def format_tip(m):
            content = m.group(1).strip()
            bg = "rgba(0, 0, 0, 0.03)" if is_light else "rgba(255, 255, 255, 0.04)"
            border = "#E2E8F0" if is_light else "rgba(255, 255, 255, 0.08)"
            tip_c = "#475569" if is_light else "#94A3B8"
            return f'<div style="background: {bg}; border: 1px solid {border}; border-radius: 6px; padding: 6px 12px; margin: 8px 0; color: {tip_c}; font-size: 11px;"><b>自动流转说明</b>：{content}</div>'
        escaped = re.sub(r'&gt;\s*💡?\s*\*\*(?:自动流转|提示)\*\*[：:]\s*(.+?)(?=(?:\n\n|\n&lt;|\n#|$))', format_tip, escaped, flags=re.DOTALL)

        # 2. Markdown 强调与标题转换
        if is_light:
            escaped = re.sub(r'###\s*(.+?)(?=\n|$)', r'<div style="color: #0F172A; font-size: 13.5px; font-weight: bold; margin: 12px 0 4px 0; border-bottom: 1px solid #E2E8F0; padding-bottom: 3px;">\1</div>', escaped)
            escaped = re.sub(r'##\s*(.+?)(?=\n|$)', r'<div style="color: #0F172A; font-size: 14.5px; font-weight: bold; margin: 14px 0 6px 0;">\1</div>', escaped)
            escaped = re.sub(r'\*\*(.+?)\*\*', r'<b style="color: #D97706;">\1</b>', escaped)
            escaped = re.sub(r'`([^`]+)`', r'<code style="background-color: #F1F5F9; color: #0284C7; padding: 2px 4px; border-radius: 4px; font-family: Cascadia Code, Consolas;">\1</code>', escaped)
        else:
            escaped = re.sub(r'###\s*(.+?)(?=\n|$)', r'<div style="color: #F8FAFC; font-size: 13.5px; font-weight: bold; margin: 12px 0 4px 0; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 3px;">\1</div>', escaped)
            escaped = re.sub(r'##\s*(.+?)(?=\n|$)', r'<div style="color: #FFFFFF; font-size: 14.5px; font-weight: bold; margin: 14px 0 6px 0;">\1</div>', escaped)
            escaped = re.sub(r'\*\*(.+?)\*\*', r'<b style="color: #FBBF24;">\1</b>', escaped)
            escaped = re.sub(r'`([^`]+)`', r'<code style="background-color: rgba(255,255,255,0.08); color: #26B0E4; padding: 2px 4px; border-radius: 4px; font-family: Cascadia Code, Consolas;">\1</code>', escaped)
        
        # 3. 严格清洗空行与换行
        escaped = re.sub(r'\n{3,}', '\n\n', escaped)
        escaped = escaped.strip()
        escaped = escaped.replace("\n", "<br>")
        escaped = re.sub(r'(?:<br>\s*)+(<div)', r'\1', escaped)
        escaped = re.sub(r'(</div>)(?:\s*<br>)+', r'\1', escaped)
        while escaped.startswith("<br>"):
            escaped = escaped[4:].strip()

        cursor = f" <span style='color: {'#0284C7' if is_light else '#26B0E4'}; font-weight: bold; font-size: 13px;'>▌</span>" if is_streaming else ""
        return f"<div>{escaped}{cursor}</div>"


class IntercomBanner(QFrame):
    """
    知识溯源解答区域顶部的全局语音对讲与检索动效长条 (双主题无缝适配，矢量微标，无 Emoji)
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
        self.badge_lbl = QLabel("右Alt 对讲")
        layout.addWidget(self.badge_lbl)

        # 核心提示文案 (高对比度深色文本)
        self.status_lbl = QLabel("长按【右 Alt】语音对讲提问 (松开检索) · 或在上方输入框检索")
        self.status_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.status_lbl, 1)

        # 实时动效声波频谱
        self.wave_vis = AudioWaveVisualizer()
        self.wave_vis.setFixedSize(70, 22)
        self.wave_vis.set_active(False)
        layout.addWidget(self.wave_vis)

        # 播报打断按钮 (默认隐藏)
        self.stop_btn = QPushButton("打断播报")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self.interrupted_clicked.emit)
        self.stop_btn.hide()
        layout.addWidget(self.stop_btn)

    def set_idle(self):
        self._reset_timer.stop()
        self.stop_btn.hide()
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            self.setStyleSheet("""
                IntercomBanner {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("右Alt 对讲")
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(2, 132, 199, 0.08);
                color: #0284C7;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 5px;
                border: 1px solid rgba(2, 132, 199, 0.25);
            """)
            self.status_lbl.setText("长按【右 Alt】随时语音对讲提问 (松开检索) · 免按 Fn / 支持空格或右 Alt 即刻打断播报")
            self.status_lbl.setStyleSheet("color: #334155; font-size: 11.5px; font-weight: 500;")
        else:
            self.setStyleSheet("""
                IntercomBanner {
                    background: rgba(15, 23, 42, 0.65);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("右Alt 对讲")
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(38, 176, 228, 0.15);
                color: #38BDF8;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
                border: 1px solid rgba(38, 176, 228, 0.35);
            """)
            self.status_lbl.setText("长按【右 Alt】随时语音对讲提问 (松开检索) · 免按 Fn / 支持空格或右 Alt 即刻打断播报")
            self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11.5px;")
        self.wave_vis.set_active(False)

    def set_listening(self):
        self._reset_timer.stop()
        self.stop_btn.hide()
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            self.setStyleSheet("""
                IntercomBanner {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(239, 68, 68, 0.08), stop:1 rgba(2, 132, 199, 0.05));
                    border: 1.5px solid #EF4444;
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("正在收音")
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.15);
                color: #DC2626;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
                border: 1px solid #EF4444;
            """)
            self.status_lbl.setText("正在倾听您的提问... 请说话，松开【右 Alt】即刻检索历史会议")
            self.status_lbl.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 700;")
        else:
            self.setStyleSheet("""
                IntercomBanner {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(239, 68, 68, 0.22), stop:1 rgba(38, 176, 228, 0.14));
                    border: 1.5px solid rgba(239, 68, 68, 0.7);
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("正在收音")
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.25);
                color: #FCA5A5;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
            """)
            self.status_lbl.setText("正在倾听您的提问... 请说话，松开【右 Alt】即刻检索历史会议")
            self.status_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold;")
        self.wave_vis.set_mode("listening")
        self.wave_vis.set_active(True)

    def set_ack(self):
        self._reset_timer.stop()
        self.stop_btn.hide()
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            self.setStyleSheet("""
                IntercomBanner {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(2, 132, 199, 0.08), stop:1 rgba(22, 163, 74, 0.05));
                    border: 1.5px solid #0284C7;
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("即时响应")
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(2, 132, 199, 0.15);
                color: #0284C7;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
                border: 1px solid #0284C7;
            """)
            self.status_lbl.setText("稍等，正在检索... 正在将语音对齐向量知识库")
            self.status_lbl.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 600;")
        else:
            self.setStyleSheet("""
                IntercomBanner {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(19, 69, 157, 0.28), stop:1 rgba(38, 176, 228, 0.18));
                    border: 1.2px solid #26B0E4;
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("即时响应")
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(38, 176, 228, 0.22);
                color: #26B0E4;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
            """)
            self.status_lbl.setText("稍等，正在检索... 正在将语音对齐向量知识库")
            self.status_lbl.setStyleSheet("color: #81D4FA; font-size: 12px; font-weight: 600;")
        self.wave_vis.set_mode("default")
        self.wave_vis.set_active(True)

    def set_stage(self, step: int, title: str, detail: str):
        self._reset_timer.stop()
        self.stop_btn.hide()
        is_light = ThemeManager.get_instance().is_light()
        clean_detail = re.sub(r'<[^>]+>', '', detail).replace('\n', ' ')
        self.badge_lbl.setText(f"步骤 {step}/3")
        if is_light:
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(2, 132, 199, 0.12);
                color: #0284C7;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
                border: 1px solid #0284C7;
            """)
            self.status_lbl.setText(f"{title} · {clean_detail}")
            self.status_lbl.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 500;")
        else:
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(38, 176, 228, 0.2);
                color: #26B0E4;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
            """)
            self.status_lbl.setText(f"{title} · {clean_detail}")
            self.status_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        self.wave_vis.set_mode("default")
        self.wave_vis.set_active(True)

    def set_speaking(self):
        self._reset_timer.stop()
        self.stop_btn.show()
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            self.setStyleSheet("""
                IntercomBanner {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(22, 163, 74, 0.08), stop:1 rgba(2, 132, 199, 0.05));
                    border: 1.5px solid #16A34A;
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("结论播报")
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(22, 163, 74, 0.15);
                color: #16A34A;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
                border: 1px solid #16A34A;
            """)
            self.status_lbl.setText("正在语音播报结论... (按右 Alt、按空格或点击右侧可随时打断)")
            self.status_lbl.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 600;")
            self.stop_btn.setIcon(get_symbol_icon("volume_off", color="#DC2626", size=13))
            self.stop_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(239, 68, 68, 0.10);
                    border: 1px solid #EF4444;
                    color: #DC2626;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #EF4444;
                    color: #FFFFFF;
                }
            """)
        else:
            self.setStyleSheet("""
                IntercomBanner {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(16, 185, 129, 0.18), stop:1 rgba(138, 198, 87, 0.12));
                    border: 1.2px solid #8AC657;
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("结论播报")
            self.badge_lbl.setStyleSheet("""
                background-color: rgba(138, 198, 87, 0.22);
                color: #8AC657;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 5px;
            """)
            self.status_lbl.setText("正在语音播报结论... (按右 Alt、按空格或点击右侧可随时打断)")
            self.status_lbl.setStyleSheet("color: #A5D6A7; font-size: 12px; font-weight: 500;")
            self.stop_btn.setIcon(get_symbol_icon("volume_off", color="#FCA5A5", size=13))
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
        self.wave_vis.set_mode("speaking")
        self.wave_vis.set_active(True)

    def set_completed(self, focal_topic: str = "", is_followup: bool = False, response_mode: str = "MEETING"):
        self.stop_btn.hide()
        self.wave_vis.set_active(False)
        is_light = ThemeManager.get_instance().is_light()

        if is_light:
            self.setStyleSheet("""
                IntercomBanner {
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
            """)
            if response_mode == "INSTRUCTION":
                self.badge_lbl.setText("敏捷自进化工单")
                self.badge_lbl.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); color: #D97706; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px; border: 1px solid #F59E0B;")
                self.status_lbl.setText("改进需求已立项归档 · 架构师角色已响应，后台智能体即将自动执行更新")
                self.status_lbl.setStyleSheet("color: #92400E; font-size: 11.5px; font-weight: 500;")
            elif response_mode == "GENERAL":
                self.badge_lbl.setText("全网通用常识")
                self.badge_lbl.setStyleSheet("background-color: rgba(147, 51, 234, 0.12); color: #9333EA; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px; border: 1px solid #9333EA;")
                self.status_lbl.setText("未检索到内部会议记录 · 已自动降级为全网通用大模型知识解答")
                self.status_lbl.setStyleSheet("color: #6B21A8; font-size: 11.5px; font-weight: 500;")
            else:
                self.badge_lbl.setText("连续就绪" if is_followup else "会议精准溯源")
                self.badge_lbl.setStyleSheet("background-color: rgba(2, 132, 199, 0.10); color: #0284C7; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px; border: 1px solid #0284C7;")
                if focal_topic:
                    self.status_lbl.setText(f"回答已就绪 · 当前焦点「{focal_topic}」，长按【右 Alt】可针对该话题直接追问")
                else:
                    self.status_lbl.setText("回答已就绪，已定位历史会议切片上下文")
                self.status_lbl.setStyleSheet("color: #334155; font-size: 11.5px; font-weight: 500;")
        else:
            self.setStyleSheet("""
                IntercomBanner {
                    background: rgba(15, 23, 42, 0.65);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
            """)
            if response_mode == "INSTRUCTION":
                self.badge_lbl.setText("敏捷自进化工单")
                self.badge_lbl.setStyleSheet("background-color: rgba(245, 158, 11, 0.22); color: #FBBF24; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px;")
                self.status_lbl.setText("改进需求已立项归档 · 架构师角色已响应，后台智能体即将自动执行更新")
                self.status_lbl.setStyleSheet("color: #FDE68A; font-size: 11.5px;")
            elif response_mode == "GENERAL":
                self.badge_lbl.setText("全网通用常识")
                self.badge_lbl.setStyleSheet("background-color: rgba(139, 92, 246, 0.22); color: #C084FC; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px;")
                self.status_lbl.setText("未检索到内部会议记录 · 已自动降级为全网通用大模型知识解答")
                self.status_lbl.setStyleSheet("color: #D8B4FE; font-size: 11.5px;")
            else:
                self.badge_lbl.setText("连续就绪" if is_followup else "会议精准溯源")
                self.badge_lbl.setStyleSheet("background-color: rgba(38, 176, 228, 0.15); color: #81D4FA; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px;")
                if focal_topic:
                    self.status_lbl.setText(f"回答已就绪 · 当前焦点「{focal_topic}」，长按【右 Alt】可针对该话题直接追问")
                else:
                    self.status_lbl.setText("回答已就绪，已定位历史会议切片上下文")
                self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11.5px;")
        self._reset_timer.start(8000)

    def set_interrupted(self):
        self.stop_btn.hide()
        self.wave_vis.set_active(False)
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            self.setStyleSheet("""
                IntercomBanner {
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("播报已打断")
            self.badge_lbl.setStyleSheet("background-color: #E2E8F0; color: #475569; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px;")
            self.status_lbl.setText("语音播报已静音打断，完整解答与时间轴记录保留在下方")
            self.status_lbl.setStyleSheet("color: #475569; font-size: 11.5px;")
        else:
            self.setStyleSheet("""
                IntercomBanner {
                    background: rgba(30, 41, 59, 0.5);
                    border: 1px solid rgba(148, 163, 184, 0.2);
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("播报已打断")
            self.badge_lbl.setStyleSheet("background-color: rgba(148, 163, 184, 0.15); color: #94A3B8; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px;")
            self.status_lbl.setText("语音播报已静音打断，完整解答与时间轴记录保留在下方")
            self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11.5px;")
        self._reset_timer.start(5000)

    def set_no_speech(self, hint: str = ""):
        self._reset_timer.stop()
        self.stop_btn.hide()
        self.wave_vis.set_active(False)
        is_light = ThemeManager.get_instance().is_light()
        msg = hint or "未听到提问声音，请按住【右 Alt】说话，松开即刻检索"
        if is_light:
            self.setStyleSheet("""
                IntercomBanner {
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("未听到说话")
            self.badge_lbl.setStyleSheet("background-color: #E2E8F0; color: #475569; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px;")
            self.status_lbl.setText(msg)
            self.status_lbl.setStyleSheet("color: #475569; font-size: 11.5px;")
        else:
            self.setStyleSheet("""
                IntercomBanner {
                    background: rgba(30, 41, 59, 0.45);
                    border: 1px solid rgba(148, 163, 184, 0.25);
                    border-radius: 8px;
                }
            """)
            self.badge_lbl.setText("未听到说话")
            self.badge_lbl.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #CBD5E1; font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 5px;")
            self.status_lbl.setText(msg)
            self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11.5px;")
        self._reset_timer.start(3500)


class CollapsibleSessionMenu(QWidget):
    """
    左侧边栏常驻的会话历史可折叠菜单 (Alma Obsidian 风格)
    - 顶行：【📜 会话历史】+ 展开/折叠指示箭头 + 计数徽章 + 右侧小【+】开启新会话按钮 (气泡提示: '新会话')
    - 默认状态：折叠 (向下展开列表默认隐藏)
    - 点击顶行：向下平滑展开/收起历史会话列表
    - 展开列表：显示最近问答历史主题与轮次，支持点击回溯会话、右键删除
    """
    session_selected = pyqtSignal(str)       # session_id
    new_chat_clicked = pyqtSignal()
    session_deleted = pyqtSignal(str)        # session_id

    def __init__(self, meeting_store: MeetingStore, parent=None):
        super().__init__(parent)
        self.store = meeting_store
        self.is_expanded = False
        self._active_session_id = ""
        self._all_sessions = []
        self._setup_ui()
        self.refresh_sessions()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # 1. 顶行常驻条 (可点击展开/收起，右侧为小 + 按钮)
        self.header_frame = QFrame()
        self.header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        h_layout = QHBoxLayout(self.header_frame)
        h_layout.setContentsMargins(10, 8, 8, 8)
        h_layout.setSpacing(6)

        self.icon_lbl = QLabel()
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        h_layout.addWidget(self.icon_lbl)

        self.title_lbl = QLabel("会话历史")
        h_layout.addWidget(self.title_lbl)

        self.count_badge = QLabel("0")
        h_layout.addWidget(self.count_badge)

        self.arrow_lbl = QLabel("▸")
        h_layout.addWidget(self.arrow_lbl)

        h_layout.addStretch()

        # 开启新会话小 + 按钮 (带气泡提示 "新会话")
        self.new_btn = QPushButton()
        self.new_btn.setFixedSize(22, 22)
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.setToolTip("新会话")
        self.new_btn.clicked.connect(self._on_new_btn_clicked)
        h_layout.addWidget(self.new_btn)

        self.header_frame.mousePressEvent = self._on_header_clicked
        main_layout.addWidget(self.header_frame)

        # 2. 向下展开的会话列表容器 (默认折叠隐藏)
        self.body_container = QWidget()
        self.body_container.setVisible(False)
        body_layout = QVBoxLayout(self.body_container)
        body_layout.setContentsMargins(4, 2, 4, 2)
        body_layout.setSpacing(4)

        # 搜索框 (紧凑型，无 Emoji)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("快速筛选话题...")
        self.search_input.textChanged.connect(self._filter_sessions)
        body_layout.addWidget(self.search_input)

        # 会话列表
        self.list_widget = QListWidget()
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setMaximumHeight(260)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        body_layout.addWidget(self.list_widget)

        main_layout.addWidget(self.body_container)
        self.apply_theme()

    def apply_theme(self):
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            self.header_frame.setStyleSheet("""
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: #F8FAFC;
                    border-color: #0284C7;
                }
            """)
            self.icon_lbl.setPixmap(get_symbol_pixmap("history", color="#0284C7", size=15))
            self.title_lbl.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 600; background: transparent; border: none;")
            self.count_badge.setStyleSheet("color: #64748B; font-size: 10px; background: #F1F5F9; padding: 1px 5px; border-radius: 4px; border: none;")
            self.arrow_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold; background: transparent; border: none;")
            self.new_btn.setIcon(get_symbol_icon("add", color="#0284C7", size=13))
            self.new_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(2, 132, 199, 0.08);
                    border: 1px solid rgba(2, 132, 199, 0.3);
                    border-radius: 5px;
                    padding: 0;
                }
                QPushButton:hover {
                    background: rgba(2, 132, 199, 0.18);
                    border-color: #0284C7;
                }
            """)
            self.search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    color: #0F172A;
                }
                QLineEdit:focus {
                    border-color: #0284C7;
                }
            """)
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    padding: 4px;
                    outline: none;
                }
                QListWidget::item {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                    padding: 6px 8px;
                    margin-bottom: 4px;
                    color: #1E293B;
                    font-size: 11px;
                }
                QListWidget::item:hover {
                    background-color: #F1F5F9;
                    border-color: #0284C7;
                    color: #0F172A;
                }
                QListWidget::item:selected {
                    background-color: rgba(2, 132, 199, 0.10);
                    border-color: #0284C7;
                    color: #0284C7;
                    font-weight: 600;
                }
            """)
        else:
            self.header_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.06);
                    border-color: rgba(38, 176, 228, 0.35);
                }
            """)
            self.icon_lbl.setPixmap(get_symbol_pixmap("history", color="#26B0E4", size=15))
            self.title_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: 600; background: transparent; border: none;")
            self.count_badge.setStyleSheet("color: #94A3B8; font-size: 10px; background: rgba(255, 255, 255, 0.06); padding: 1px 5px; border-radius: 4px; border: none;")
            self.arrow_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold; background: transparent; border: none;")
            self.new_btn.setIcon(get_symbol_icon("add", color="#38BDF8", size=13))
            self.new_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(38, 176, 228, 0.15);
                    border: 1px solid rgba(38, 176, 228, 0.35);
                    border-radius: 5px;
                    padding: 0;
                }
                QPushButton:hover {
                    background: rgba(38, 176, 228, 0.35);
                    border-color: #26B0E4;
                }
            """)
            self.search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #0A0D15;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    color: #FFFFFF;
                }
                QLineEdit:focus {
                    border-color: #26B0E4;
                }
            """)
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #0C0F17;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                    padding: 4px;
                    outline: none;
                }
                QListWidget::item {
                    background-color: #121624;
                    border: 1px solid rgba(255, 255, 255, 0.04);
                    border-radius: 6px;
                    padding: 6px 8px;
                    margin-bottom: 4px;
                    color: #CBD5E1;
                    font-size: 11px;
                }
                QListWidget::item:hover {
                    background-color: #162032;
                    border-color: rgba(38, 176, 228, 0.4);
                    color: #FFFFFF;
                }
                QListWidget::item:selected {
                    background-color: #132742;
                    border-color: #26B0E4;
                    color: #38BDF8;
                }
            """)

    def _on_header_clicked(self, event):
        child = self.header_frame.childAt(event.pos())
        if child == self.new_btn:
            return
        self.toggle_expanded()

    def _on_new_btn_clicked(self):
        self.new_chat_clicked.emit()

    def collapse(self):
        self.is_expanded = False
        self.body_container.setVisible(False)
        self.arrow_lbl.setText("▸")

    def expand(self):
        self.is_expanded = True
        self.body_container.setVisible(True)
        self.arrow_lbl.setText("▾")
        self.refresh_sessions()

    def toggle_expanded(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def set_active_session(self, session_id: str):
        self._active_session_id = session_id
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            sid = item.data(Qt.ItemDataRole.UserRole)
            if sid == session_id:
                self.list_widget.setCurrentItem(item)
                break

    def refresh_sessions(self):
        try:
            self._all_sessions = self.store.get_all_sessions(limit=60)
        except Exception as e:
            print(f"[CollapsibleSessionMenu] 加载会话列表失败: {e}")
            self._all_sessions = []
        self.count_badge.setText(str(len(self._all_sessions)))
        self._render_items(self._all_sessions)

    def _filter_sessions(self, text: str):
        query = text.strip().lower()
        if not query:
            self._render_items(self._all_sessions)
            return
        filtered = [
            s for s in self._all_sessions
            if query in s.get("title", "").lower()
        ]
        self._render_items(filtered)

    def _render_items(self, sessions):
        self.list_widget.clear()
        if not sessions:
            empty_item = QListWidgetItem("暂无历史问答记录")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_widget.addItem(empty_item)
            return

        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        for s in sessions:
            sid = s["id"]
            title = s.get("title") or "未命名会话"
            turn_count = s.get("turn_count", 1)
            updated_at = s.get("updated_at", "")

            date_part = updated_at.split(" ")[0] if " " in updated_at else updated_at
            time_part = updated_at.split(" ")[1][:5] if " " in updated_at else ""
            if date_part == today_str:
                group_tag = f"今天 {time_part}"
            elif date_part == yesterday_str:
                group_tag = f"昨天 {time_part}"
            else:
                group_tag = f"{date_part}"

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, sid)
            item_text = f"{title}\n    {group_tag} · {turn_count} 轮"
            item.setText(item_text)
            self.list_widget.addItem(item)
            if sid == self._active_session_id:
                item.setSelected(True)

    def _on_item_clicked(self, item: QListWidgetItem):
        sid = item.data(Qt.ItemDataRole.UserRole)
        if sid:
            self._active_session_id = sid
            self.session_selected.emit(sid)

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        sid = item.data(Qt.ItemDataRole.UserRole)
        if not sid:
            return

        is_light = ThemeManager.get_instance().is_light()
        menu = QMenu(self)
        if is_light:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    color: #0F172A;
                    font-size: 11px;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    border-radius: 4px;
                }
            """)
        else:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #121724;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    color: #E2E8F0;
                    font-size: 11px;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background-color: #EF4444;
                    color: #FFFFFF;
                    border-radius: 4px;
                }
            """)
        del_action = menu.addAction("删除此会话")
        del_action.setIcon(get_symbol_icon("delete_forever", color="#DC2626" if is_light else "#EF4444", size=14))
        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if action == del_action:
            if ModernDialog.confirm_danger(
                self,
                title="删除会话记录",
                message="确定删除此场历史会话记录吗？",
                detail="删除后该会话的问答上下文记录将被清空，但不会影响知识库底层的会议切片资产。",
                confirm_text="删除会话"
            ):
                try:
                    self.store.delete_session(sid)
                    self.session_deleted.emit(sid)
                    self.refresh_sessions()
                except Exception as e:
                    print(f"[CollapsibleSessionMenu] 删除会话失败: {e}")

# 兼容别名
SessionDrawer = CollapsibleSessionMenu


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

        tm = ThemeManager.get_instance()
        is_light = tm.is_light()
        colors = tm.get_colors()

        # 背景与圆角 (美好智能 VI 规范)
        if self.is_active:
            if is_light:
                painter.setBrush(QBrush(QColor(2, 132, 199, 20)))
                painter.setPen(QPen(QColor(2, 132, 199, 140), 1.0))
            else:
                painter.setBrush(QBrush(QColor(19, 69, 157, 48)))
                painter.setPen(QPen(QColor(38, 176, 228, 130), 1.0))
            painter.drawRoundedRect(4, 2, w - 8, h - 4, 8, 8)

            # 左侧微光指示小条
            painter.setBrush(QBrush(QColor(colors["brand_accent"])))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(7, 9, 3, h - 18, 1.5, 1.5)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # 绘制 Google Material Symbols 矢量图标 (彻底替代系统 Emoji)
        icon_c = colors["brand_accent"] if self.is_active else colors["text_muted"]
        icon_pix = get_symbol_pixmap(self.icon_str, color=icon_c, size=18)
        painter.drawPixmap(16, (h - 18) // 2, icon_pix)

        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold if self.is_active else QFont.Weight.Medium))
        text_color = QColor(colors["text_primary"] if self.is_active else colors["text_secondary"])
        painter.setPen(text_color)
        painter.drawText(44, 0, w - 90, h, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.label_str)

        # 右侧微型 Badge
        if self.badge_str:
            badge_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(badge_font)
            badge_w = max(20, len(self.badge_str) * 7 + 10)
            badge_rect_x = w - badge_w - 12
            badge_rect_y = (h - 18) // 2

            if is_light:
                bg_badge = QColor(2, 132, 199, 25) if self.is_active else QColor(15, 23, 42, 12)
                text_badge = QColor(2, 132, 199) if self.is_active else QColor(100, 116, 139)
            else:
                bg_badge = QColor(19, 69, 157, 85) if self.is_active else QColor(255, 255, 255, 16)
                text_badge = QColor(138, 198, 87) if self.is_active else QColor(148, 163, 184)

            painter.setBrush(QBrush(bg_badge))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect_x, badge_rect_y, badge_w, 18, 9, 9)

            painter.setPen(text_badge)
            painter.drawText(badge_rect_x, badge_rect_y, badge_w, 18, Qt.AlignmentFlag.AlignCenter, self.badge_str)


class ExpandableEmployeeCard(QFrame):
    """
    可点击展开的企业成员动态画像卡片 (Alma Obsidian 风格)
    - 折叠状态：头像、姓名职务、音似别名、会议关联数、最新主导动态核心摘要（随会议库动态沉淀）
    - 展开状态：平滑呈现该成员关联的历史会议时间、讨论议题、负责决策与详细发言摘要
    - 支持一键快捷检索该成员全部会议决议与发言
    """
    search_requested = pyqtSignal(str)

    def __init__(self, emp: dict, store: MeetingStore, color: str = "#26B0E4", parent=None):
        super().__init__(parent)
        self.emp = emp
        self.store = store
        self.brand_color = color
        self.is_expanded = False
        self.is_departed = (emp.get("status") == "departed")

        self.setObjectName("emp_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 主纵向布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 12, 14, 12)
        self.main_layout.setSpacing(8)

        # 1. 顶部 Header：头像 + 姓名职务 + 关联会议徽章 + 展开指示
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # 头像 (若已离职使用沉稳暗灰色调)
        avatar_bg = "#475569" if self.is_departed else self.brand_color
        self.avatar_lbl = QLabel(emp["name"][:1])
        self.avatar_lbl.setFixedSize(36, 36)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_lbl.setStyleSheet(f"""
            background-color: {avatar_bg};
            color: #FFFFFF;
            font-size: 15px;
            font-weight: bold;
            border-radius: 8px;
        """)
        header_layout.addWidget(self.avatar_lbl)

        # 姓名 + 职务
        info_box = QVBoxLayout()
        info_box.setSpacing(1)
        self.name_lbl = QLabel(emp["name"])
        self.name_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.title_lbl = QLabel(emp["title"])
        self.title_lbl.setStyleSheet("font-size: 11px;")
        info_box.addWidget(self.name_lbl)
        info_box.addWidget(self.title_lbl)
        header_layout.addLayout(info_box)

        header_layout.addStretch()

        # 右侧操作与徽章区
        right_box = QVBoxLayout()
        right_box.setSpacing(3)
        right_box.setAlignment(Qt.AlignmentFlag.AlignRight)

        # 离职状态徽章
        if self.is_departed:
            self.status_badge = QLabel("已离职 · 档案留存")
            self.status_badge.setStyleSheet("color: #94A3B8; font-size: 9.5px; background: rgba(148, 163, 184, 0.12); border: 1px solid rgba(148, 163, 184, 0.25); padding: 2px 6px; border-radius: 4px; font-weight: 600;")
            right_box.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignRight)

        # 关联会议计数徽章
        self.meeting_badge = QLabel("关联 0 场会议")
        self.meeting_badge.setStyleSheet("color: #64748B; font-size: 10px; background: rgba(0,0,0,0.04); padding: 2px 7px; border-radius: 4px; font-weight: 500;")
        right_box.addWidget(self.meeting_badge, alignment=Qt.AlignmentFlag.AlignRight)

        # 展开/收起指示器
        self.toggle_lbl = QLabel("▾ 展开履历")
        self.toggle_lbl.setStyleSheet("font-size: 10.5px; font-weight: 600; padding-right: 2px;")
        right_box.addWidget(self.toggle_lbl, alignment=Qt.AlignmentFlag.AlignRight)

        header_layout.addLayout(right_box)
        self.main_layout.addLayout(header_layout)

        # 2. 别名与称谓标签 (音似提示)
        aliases = emp.get("aliases", [])
        if aliases:
            aliases_str = " / ".join(aliases[:4])
            alias_badge = QLabel(f"称谓纠错: {aliases_str}")
            alias_badge.setStyleSheet("color: #64748B; font-size: 10px; background: rgba(0,0,0,0.02); padding: 2px 6px; border-radius: 4px;")
            self.main_layout.addWidget(alias_badge)

        # 3. 基础职责描述
        self.duties_lbl = QLabel(emp.get('duties', ''))
        self.duties_lbl.setWordWrap(True)
        self.duties_lbl.setStyleSheet("font-size: 11.5px; line-height: 1.4;")
        self.main_layout.addWidget(self.duties_lbl)

        # 4. 核心动态高亮胶囊 (动态从会议切片库提取)
        self.highlight_box = QFrame()
        hl_layout = QVBoxLayout(self.highlight_box)
        hl_layout.setContentsMargins(8, 6, 8, 6)
        hl_layout.setSpacing(3)

        self.hl_title_lbl = QLabel("最近主导与会议动态")
        self.hl_title_lbl.setStyleSheet("font-size: 10.5px; font-weight: bold;")
        self.hl_content_lbl = QLabel("正在同步会议记忆中台...")
        self.hl_content_lbl.setWordWrap(True)
        self.hl_content_lbl.setStyleSheet("font-size: 11px; line-height: 1.35;")
        hl_layout.addWidget(self.hl_title_lbl)
        hl_layout.addWidget(self.hl_content_lbl)
        self.main_layout.addWidget(self.highlight_box)

        # 5. 技术栈与专业方向
        self.tech_lbl = QLabel(f"业务方向/技术栈: {emp.get('tech_stack', '通用业务')}")
        self.tech_lbl.setStyleSheet("color: #64748B; font-size: 10.5px;")
        self.main_layout.addWidget(self.tech_lbl)

        # 6. 展开详细档案容器 (初始折叠)
        self.detail_container = QWidget()
        self.detail_container.setVisible(False)
        self.detail_layout = QVBoxLayout(self.detail_container)
        self.detail_layout.setContentsMargins(0, 6, 0, 0)
        self.detail_layout.setSpacing(8)

        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: rgba(148, 163, 184, 0.15); max-height: 1px;")
        self.detail_layout.addWidget(divider)

        # 详细档案小标题
        footprint_title = QLabel("动态会议足迹与履历档案 (实时沉淀自中台记忆)")
        footprint_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.detail_layout.addWidget(footprint_title)

        # 动态切片时间轴列表容器
        self.timeline_widget = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_widget)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(6)
        self.detail_layout.addWidget(self.timeline_widget)

        # 快捷检索按钮 (Material Symbol 矢量图标，无 Emoji)
        is_light = ThemeManager.get_instance().is_light()
        self.query_btn = QPushButton(f"检索关于 {emp['name']} 的全部会议决议与发言")
        self.query_btn.setIcon(get_symbol_icon("search", color="#0284C7" if is_light else "#38BDF8", size=13))
        self.query_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.query_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(2, 132, 199, 0.08);
                    color: #0284C7;
                    border: 1px solid rgba(2, 132, 199, 0.3);
                    border-radius: 6px;
                    padding: 7px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(2, 132, 199, 0.18);
                    color: #0369A1;
                }
            """)
        else:
            self.query_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(38, 176, 228, 0.12);
                    color: #38BDF8;
                    border: 1px solid rgba(38, 176, 228, 0.35);
                    border-radius: 6px;
                    padding: 7px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(38, 176, 228, 0.25);
                    color: #FFFFFF;
                    border-color: #26B0E4;
                }
            """)
        self.query_btn.clicked.connect(self._on_search_clicked)
        self.detail_layout.addWidget(self.query_btn)

        self.main_layout.addWidget(self.detail_container)

        # 初始化刷新动态档案
        self.refresh_profile()
        self._apply_style(hover=False)

    def _apply_style(self, hover: bool = False):
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            if self.is_departed:
                border_c = "#CBD5E1" if hover else "#E2E8F0"
                self.setStyleSheet(f"""
                    QFrame#emp_card {{
                        background-color: #F8FAFC;
                        border: 1px dashed {border_c};
                        border-radius: 10px;
                    }}
                """)
            else:
                border_c = "#0284C7" if (self.is_expanded or hover) else "#E2E8F0"
                bg_c = "#F8FAFC" if hover else "#FFFFFF"
                self.setStyleSheet(f"""
                    QFrame#emp_card {{
                        background-color: {bg_c};
                        border: 1px solid {border_c};
                        border-radius: 10px;
                    }}
                """)
            self.name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A;")
            self.title_lbl.setStyleSheet("font-size: 11px; color: #475569;")
            self.duties_lbl.setStyleSheet("color: #334155; font-size: 11.5px; line-height: 1.4;")
            self.toggle_lbl.setStyleSheet("color: #0284C7; font-size: 10.5px; font-weight: 600; padding-right: 2px;")
        else:
            if self.is_departed:
                border_c = "rgba(148, 163, 184, 0.45)" if self.is_expanded else ("rgba(148, 163, 184, 0.35)" if hover else "rgba(255, 255, 255, 0.09)")
                self.setStyleSheet(f"""
                    QFrame#emp_card {{
                        background-color: #121522;
                        border: 1px dashed {border_c};
                        border-radius: 10px;
                    }}
                """)
            else:
                border_c = "rgba(38, 176, 228, 0.55)" if self.is_expanded else ("rgba(38, 176, 228, 0.4)" if hover else "rgba(255, 255, 255, 0.08)")
                bg_c = "#141724" if self.is_expanded else ("#151928" if hover else "#12151F")
                self.setStyleSheet(f"""
                    QFrame#emp_card {{
                        background-color: {bg_c};
                        border: 1px solid {border_c};
                        border-radius: 10px;
                    }}
                """)
            self.name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
            self.title_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
            self.duties_lbl.setStyleSheet("color: #CBD5E1; font-size: 11.5px; line-height: 1.4;")
            self.toggle_lbl.setStyleSheet("color: #26B0E4; font-size: 10.5px; font-weight: 600; padding-right: 2px;")

    def enterEvent(self, event):
        if not self.is_expanded:
            self._apply_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_expanded:
            self._apply_style(hover=False)
        super().leaveEvent(event)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.detail_container.setVisible(self.is_expanded)
        self.toggle_lbl.setText("▴ 收起履历" if self.is_expanded else "▾ 展开履历")
        self._apply_style(hover=False)

    def mousePressEvent(self, event):
        child = self.childAt(event.pos())
        if isinstance(child, QPushButton):
            super().mousePressEvent(event)
            return
        self.toggle_expand()
        super().mousePressEvent(event)

    def _on_search_clicked(self):
        action_word = "历史会议决议、交接与发言" if self.is_departed else "发言、决策与负责事项"
        self.search_requested.emit(f"关于{self.emp['name']}在过往会议中的{action_word}")

    def refresh_profile(self):
        """从 store 动态反查该成员的最新会议切片并重新计算画像"""
        is_light = ThemeManager.get_instance().is_light()
        profile = get_dynamic_employee_profile(self.store, self.emp)
        m_count = profile.get("meeting_count", 0)

        # 1. 更新关联会议计数 Badge (无 Emoji)
        if m_count > 0:
            prefix = "历史关联" if self.is_departed else "关联"
            self.meeting_badge.setText(f"{prefix} {m_count} 场会议")
            badge_color = "#64748B" if self.is_departed else ("#0284C7" if is_light else "#26B0E4")
            badge_bg = "rgba(100,116,139,0.10)" if self.is_departed else ("rgba(2,132,199,0.10)" if is_light else "rgba(38,176,228,0.12)")
            badge_bd = "rgba(100,116,139,0.25)" if self.is_departed else ("rgba(2,132,199,0.25)" if is_light else "rgba(38,176,228,0.25)")
            self.meeting_badge.setStyleSheet(
                f"color: {badge_color}; font-size: 10px; background: {badge_bg}; "
                f"border: 1px solid {badge_bd}; padding: 2px 7px; border-radius: 4px; font-weight: 600;"
            )
        else:
            self.meeting_badge.setText("暂无关联会议")
            self.meeting_badge.setStyleSheet(
                "color: #94A3B8; font-size: 10px; background: rgba(0,0,0,0.03); "
                "border: 1px solid rgba(0,0,0,0.05); padding: 2px 7px; border-radius: 4px;"
            )

        # 2. 更新最新主导与动态高亮胶囊 (无 Emoji)
        core_hl = profile.get("core_highlight", "")
        core_hl = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]', '', core_hl)
        if self.is_departed:
            self.hl_title_lbl.setText("历史主导与交接决策" if m_count > 0 else "离职交接与历史档案留存")
            self.hl_title_lbl.setStyleSheet("color: #64748B; font-size: 10.5px; font-weight: bold;")
            self.highlight_box.setStyleSheet(f"""
                QFrame {{
                    background: {'rgba(100, 116, 139, 0.06)' if is_light else 'rgba(100, 116, 139, 0.12)'};
                    border: 1px solid {'#CBD5E1' if is_light else 'rgba(255, 255, 255, 0.1)'};
                    border-radius: 6px;
                    padding: 7px 10px;
                }}
            """)
        elif m_count > 0:
            self.hl_title_lbl.setText("最近主导与会议决策")
            self.hl_title_lbl.setStyleSheet(f"color: {'#0284C7' if is_light else '#26B0E4'}; font-size: 10.5px; font-weight: bold;")
            self.highlight_box.setStyleSheet(f"""
                QFrame {{
                    background: {'rgba(2, 132, 199, 0.05)' if is_light else 'rgba(38, 176, 228, 0.07)'};
                    border: 1px solid {'rgba(2, 132, 199, 0.22)' if is_light else 'rgba(38, 176, 228, 0.25)'};
                    border-radius: 6px;
                    padding: 7px 10px;
                }}
            """)
        else:
            self.hl_title_lbl.setText("现阶段核心职责与关注")
            self.hl_title_lbl.setStyleSheet(f"color: {'#16A34A' if is_light else '#8AC657'}; font-size: 10.5px; font-weight: bold;")
            self.highlight_box.setStyleSheet(f"""
                QFrame {{
                    background: {'rgba(22, 163, 74, 0.05)' if is_light else 'rgba(138, 198, 87, 0.07)'};
                    border: 1px solid {'rgba(22, 163, 74, 0.22)' if is_light else 'rgba(138, 198, 87, 0.25)'};
                    border-radius: 6px;
                    padding: 7px 10px;
                }}
            """)
        self.hl_content_lbl.setText(core_hl)
        self.hl_content_lbl.setStyleSheet(f"color: {'#1E293B' if is_light else '#E2E8F0'}; font-size: 11px; line-height: 1.35;")

        # 3. 清理并重新填充详细时间轴切片 (无 Emoji)
        while self.timeline_layout.count() > 0:
            child = self.timeline_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        actions = profile.get("actions", [])
        if actions:
            for act in actions:
                item_frame = QFrame()
                if is_light:
                    item_frame.setStyleSheet("""
                        QFrame {
                            background: #F8FAFC;
                            border: 1px solid #E2E8F0;
                            border-left: 2.5px solid #0284C7;
                            border-radius: 6px;
                            padding: 7px 9px;
                        }
                    """)
                else:
                    item_frame.setStyleSheet("""
                        QFrame {
                            background: rgba(255, 255, 255, 0.03);
                            border: 1px solid rgba(255, 255, 255, 0.06);
                            border-left: 2px solid #26B0E4;
                            border-radius: 6px;
                            padding: 7px 9px;
                        }
                    """)
                item_layout = QVBoxLayout(item_frame)
                item_layout.setContentsMargins(8, 6, 8, 6)
                item_layout.setSpacing(4)

                topic_str = act.get('topic', '常规议题')
                header_lbl = QLabel(f"{act.get('time', '近期')} · 【{topic_str}】")
                header_lbl.setWordWrap(True)
                header_lbl.setStyleSheet(f"color: {'#0284C7' if is_light else '#38BDF8'}; font-size: 11px; font-weight: bold;")
                item_layout.addWidget(header_lbl)

                points = act.get("points", [])
                if points:
                    for pt in points:
                        clean_pt = pt
                        for emo in ["✅", "📌", "📝", "🎙️", "💬"]:
                            clean_pt = clean_pt.replace(emo, "").strip()
                        pt_lbl = QLabel(f"• {clean_pt}")
                        pt_lbl.setWordWrap(True)
                        pt_lbl.setStyleSheet(f"color: {'#334155' if is_light else '#CBD5E1'}; font-size: 11px; line-height: 1.4; padding-left: 2px;")
                        item_layout.addWidget(pt_lbl)
                elif act.get("highlight"):
                    clean_hl = act.get('highlight', '')
                    for emo in ["✅", "📌", "📝", "🎙️", "💬"]:
                        clean_hl = clean_hl.replace(emo, "").strip()
                    desc_lbl = QLabel(clean_hl)
                    desc_lbl.setWordWrap(True)
                    desc_lbl.setStyleSheet(f"color: {'#334155' if is_light else '#E2E8F0'}; font-size: 11px; line-height: 1.35;")
                    item_layout.addWidget(desc_lbl)

                self.timeline_layout.addWidget(item_frame)
        else:
            no_act_lbl = QLabel("暂无直接关联的历史会议切片。后续会议讨论中若提及或由其发言，系统将自动汇总沉淀于此。")
            no_act_lbl.setWordWrap(True)
            no_act_lbl.setStyleSheet("color: #94A3B8; font-size: 10.5px; font-style: italic; padding: 4px;")
            self.timeline_layout.addWidget(no_act_lbl)


class ElidedLabel(QLabel):
    """
    单行自适应省略号文本组件：
    严格固定单行显示，末尾自适应添加 '...'，彻底杜绝文字折行、挤压或纵向截断
    """
    def __init__(self, text: str = "", color: str = "#CBD5E1", font_size: float = 11, font_weight: int = 400, parent=None):
        super().__init__(text, parent)
        self.full_text = text
        self.text_color = color
        self.font_size = font_size
        self.font_weight = font_weight
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def setText(self, text: str):
        self.full_text = text
        super().setText(text)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        f = self.font()
        if self.font_size:
            f.setPointSizeF(self.font_size)
        f.setWeight(QFont.Weight(self.font_weight))
        painter.setFont(f)
        metrics = QFontMetrics(f)
        avail_w = max(10, self.width() - 2)
        elided = metrics.elidedText(self.full_text, Qt.TextElideMode.ElideRight, avail_w)
        painter.setPen(QColor(self.text_color))
        painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), elided)


class TrashSliceItemWidget(QWidget):
    """
    或许没用记忆列表单项组件
    第 1 行：时间戳 + 右侧【恢复】按钮
    第 2 行：AI 研判理由红底标签 (单行展示)
    第 3 行：议题提炼文本 (固定单行白字，末尾自动 ...，右侧有完整详情)
    """
    def __init__(self, rec: dict, list_item: QListWidgetItem, list_widget: QListWidget, on_restore_callback, parent=None):
        super().__init__(parent)
        self.rec = rec
        self.list_item = list_item
        self.list_widget = list_widget
        self.on_restore_callback = on_restore_callback
        self.setStyleSheet("background: transparent;")

        time_str = rec.get("start_time", "")
        summary = rec.get("summary", "")
        first_line = summary.split("\n")[0] if summary else "常驻录音切片"
        first_line = re.sub(r'^[\s\d\.\-、*#]*(?:核心议题|议题|Topic|【核心议题】|主题)(?:[（\(].*?[）\)])?[：:\s]*', '', first_line).strip() or "常规沟通"
        reason = rec.get("trash_reason", "次要碎片")

        self.setToolTip(f"【AI 研判理由】: {reason}\n【切片时间】: {time_str}\n【切片完整纪要】:\n{summary}")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 4, 6, 4)
        root_layout.setSpacing(4)

        # 第 1 行：时间戳 + 恢复按钮
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lbl_time = QLabel(time_str)
        lbl_time.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold;")
        lbl_time.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row1.addWidget(lbl_time, 1)

        is_light = ThemeManager.get_instance().is_light()
        self.btn_useful = QPushButton("恢复")
        self.btn_useful.setIcon(get_symbol_icon("check_circle", color="#0284C7" if is_light else "#38BDF8", size=12))
        self.btn_useful.setIconSize(QSize(12, 12))
        self.btn_useful.setToolTip("将此切片判定为有用并恢复为正式会议资产 (消除误判)")
        self.btn_useful.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_useful.setFixedSize(58, 22)
        if is_light:
            self.btn_useful.setStyleSheet("""
                QPushButton {
                    background: rgba(2, 132, 199, 0.08);
                    color: #0284C7;
                    border: 1px solid rgba(2, 132, 199, 0.35);
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0 4px;
                }
                QPushButton:hover {
                    background: #0284C7;
                    color: #FFFFFF;
                }
            """)
        else:
            self.btn_useful.setStyleSheet("""
                QPushButton {
                    background: rgba(38, 176, 228, 0.16);
                    color: #26B0E4;
                    border: 1px solid rgba(38, 176, 228, 0.45);
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0 4px;
                }
                QPushButton:hover {
                    background: #26B0E4;
                    color: #FFFFFF;
                }
            """)
        self.btn_useful.clicked.connect(self._handle_restore)
        row1.addWidget(self.btn_useful, 0)
        root_layout.addLayout(row1)

        # 第 2 行：AI 研判理由 (红底胶囊单行展示)
        reason_frame = QFrame()
        reason_frame.setStyleSheet("background: rgba(239, 68, 68, 0.10); border-radius: 3px;")
        r_layout = QHBoxLayout(reason_frame)
        r_layout.setContentsMargins(5, 1, 5, 1)
        lbl_reason = ElidedLabel(f"研判原因：{reason}", color="#DC2626" if is_light else "#FCA5A5", font_size=10, font_weight=500)
        lbl_reason.setFixedHeight(16)
        r_layout.addWidget(lbl_reason)
        root_layout.addWidget(reason_frame)

        # 第 3 行：切片提炼白字部分 (严格固定单行，末尾自动 ...)
        self.lbl_title = ElidedLabel(first_line, color="#1E293B" if is_light else "#E2E8F0", font_size=11, font_weight=400)
        self.lbl_title.setFixedHeight(18)
        root_layout.addWidget(self.lbl_title)

    def _handle_restore(self):
        if self.on_restore_callback:
            self.on_restore_callback(self.rec)

    def mousePressEvent(self, event):
        child = self.childAt(event.pos())
        if child == self.btn_useful:
            super().mousePressEvent(event)
            return
        if self.list_widget and self.list_item:
            self.list_widget.setCurrentItem(self.list_item)
            super().mousePressEvent(event)
        if child == self.btn_useful:
            super().mousePressEvent(event)
            return
        if self.list_widget and self.list_item:
            self.list_widget.setCurrentItem(self.list_item)
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    record_toggled = pyqtSignal(bool)
    query_submitted = pyqtSignal(str)
    inject_demo_requested = pyqtSignal()
    tts_playback_finished = pyqtSignal()
    new_session_requested = pyqtSignal()
    session_switched = pyqtSignal(str)

    def __init__(self, meeting_store: MeetingStore):
        super().__init__()
        app = QApplication.instance()
        if app and not isinstance(app.style(), NoFocusRectStyle):
            app.setStyle(NoFocusRectStyle(app.style()))

        self.store = meeting_store
        self.setWindowTitle("DeskEcho 桌面回响 · 企业常驻会议记忆空间")
        self.setWindowIcon(get_flower_logo_icon(64))
        self.resize(1120, 740)
        self.setMinimumSize(960, 620)

        # 内置音频播放器与输出设备 (管理即时反馈与结论播报 TTS)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._init_ui()
        self._apply_current_theme()
        ThemeManager.get_instance().theme_changed.connect(self._apply_current_theme)
        self._setup_timer()
        self.refresh_records()
        self.clear_answer_session()

    def _init_ui(self):
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
        self._build_page_update(self.stack)    # Page 4: 软件发版与自动更新

        content_layout.addWidget(self.stack, 1)
        main_h_layout.addWidget(content_container, 1)

        # 底部简约状态栏 (不使用系统默认灰底框，简洁优雅，无过度动效)
        self._build_clean_status_bar()

    # ---------------- 侧边栏构建 ----------------
    def _build_sidebar(self, parent_layout: QHBoxLayout):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 18, 14, 18)
        side_layout.setSpacing(8)

        # 品牌 Workspace 标识区 (无多余嵌套外框，纯粹通透的品牌 Header)
        self.brand_card = QFrame()
        self.brand_card.setObjectName("brand_card")
        self.brand_card.setStyleSheet("background: transparent; border: none;")
        brand_layout = QHBoxLayout(self.brand_card)
        brand_layout.setContentsMargins(4, 2, 4, 10)
        brand_layout.setSpacing(10)

        # 美好智能品牌 Flower Logo (色卡花朵衍生变体)
        self.logo_icon = QLabel()
        self.logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_icon.setFixedSize(32, 32)
        self.logo_icon.setPixmap(get_flower_logo_pixmap(30))
        self.logo_icon.setStyleSheet("background: transparent; border: none;")

        brand_text_box = QVBoxLayout()
        brand_text_box.setSpacing(1)
        self.brand_title_lbl = QLabel("DeskEcho")
        self.brand_title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;")
        self.brand_sub_lbl = QLabel("美好智能")
        self.brand_sub_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #26B0E4; letter-spacing: 0.5px;")
        brand_text_box.addWidget(self.brand_title_lbl)
        brand_text_box.addWidget(self.brand_sub_lbl)

        brand_layout.addWidget(self.logo_icon)
        brand_layout.addLayout(brand_text_box)
        brand_layout.addStretch()

        side_layout.addWidget(self.brand_card)
        side_layout.addSpacing(6)

        # 1. 对讲与检索常驻主菜单项
        self.nav_btns = []
        self.btn_ask = NavButton("bolt", "对讲与检索", "右Alt")
        self.btn_ask.clicked.connect(lambda: self._switch_nav(0))
        self.btn_ask.set_active(True)
        self.nav_btns.append(self.btn_ask)
        side_layout.addWidget(self.btn_ask)

        side_layout.addSpacing(4)

        # 2. 会话历史常驻菜单 (默认折叠，点击向下展开，右侧带小 + 按钮，气泡提示 "新会话")
        self.session_menu = CollapsibleSessionMenu(self.store, parent=self)
        self.session_menu.session_selected.connect(self._on_history_session_selected)
        self.session_menu.new_chat_clicked.connect(self.clear_answer_session)
        self.session_menu.session_deleted.connect(self._on_history_session_deleted)
        self.session_drawer = self.session_menu  # 保持兼容引用
        side_layout.addWidget(self.session_menu)

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

        # 底部栏：左侧热键小标签 + 右下角小齿轮设置项按钮
        bottom_footer_layout = QHBoxLayout()
        bottom_footer_layout.setContentsMargins(4, 4, 4, 0)
        bottom_footer_layout.setSpacing(6)

        self.hotkey_tag = QLabel(f"长按 [{Config.get_intercom_display_key()}] 语音对讲")
        self.hotkey_tag.setStyleSheet("color: #64748B; font-size: 10.5px;")
        bottom_footer_layout.addWidget(self.hotkey_tag, 1)

        # 右下角小齿轮按钮 (设置项入口，矢量图标)
        self.btn_gear = QPushButton()
        self.btn_gear.setToolTip("设置中心 (企业通讯录 / 会议切片档案 / 引擎状态)")
        self.btn_gear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gear.setFixedSize(26, 26)
        self._update_gear_button_style(active=False)
        self.btn_gear.clicked.connect(self._toggle_settings_view)
        bottom_footer_layout.addWidget(self.btn_gear)

        side_layout.addLayout(bottom_footer_layout)

        parent_layout.addWidget(sidebar)

    def _update_gear_button_style(self, active: bool = False):
        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            if active:
                self.btn_gear.setIcon(get_symbol_icon("settings", color="#0284C7", size=15))
                self.btn_gear.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(2, 132, 199, 0.12);
                        border: 1px solid #0284C7;
                        border-radius: 6px;
                    }
                """)
            else:
                self.btn_gear.setIcon(get_symbol_icon("settings", color="#64748B", size=15))
                self.btn_gear.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #F1F5F9;
                        border-color: #0284C7;
                    }
                """)
        else:
            if active:
                self.btn_gear.setIcon(get_symbol_icon("settings", color="#38BDF8", size=15))
                self.btn_gear.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(38, 176, 228, 0.25);
                        border: 1px solid #26B0E4;
                        border-radius: 6px;
                    }
                """)
            else:
                self.btn_gear.setIcon(get_symbol_icon("settings", color="#94A3B8", size=15))
                self.btn_gear.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.04);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: rgba(38, 176, 228, 0.18);
                        border-color: #26B0E4;
                    }
                """)

    def _toggle_settings_view(self):
        """点击右下角小齿轮，切换到设置中心（默认展示企业通讯录）或切回对讲"""
        current = self.stack.currentIndex()
        if current in (1, 2, 3):
            self._switch_nav(0)
        else:
            target = getattr(self, "_last_settings_tab", 2)
            self._switch_nav(target)

    def _switch_nav(self, index: int):
        self.btn_ask.set_active(index == 0)
        self._update_gear_button_style(active=(index in (1, 2, 3, 4)))
        if index in (1, 2, 3, 4):
            self._last_settings_tab = index

        self.stack.setCurrentIndex(index)
        titles = ["对讲与即时检索", "会议记忆切片库", "企业组织通讯录", "系统引擎与状态", "软件发版与自动更新"]

        # 切换顶栏模式：Page 0 显示简洁面包屑，Page 1/2/3/4 显示设置分段子导航
        if index == 0:
            self.breadcrumb_lbl.setText("对讲与即时检索")
            if hasattr(self, 'settings_tab_bar'):
                self.settings_tab_bar.setVisible(False)
        else:
            self.breadcrumb_lbl.setText("设置中心")
            if hasattr(self, 'settings_tab_bar'):
                self.settings_tab_bar.setVisible(True)
            self._update_settings_sub_tab_styles(index)

        # 若从其他页面切换至会议记忆库且存在待更新的新切片，立即平滑呈现
        if index == 1 and getattr(self, "_has_pending_update", False):
            self._apply_pending_slice_update()

        if index == 2 and hasattr(self, "refresh_roster"):
            self.refresh_roster()

    def _update_settings_sub_tab_styles(self, active_index: int):
        if not hasattr(self, 'sub_btn_roster'):
            return
        is_light = ThemeManager.get_instance().is_light()
        idx_map = {
            2: (self.sub_btn_roster, "group"),
            1: (self.sub_btn_memory, "article"),
            3: (self.sub_btn_engine, "tune"),
            4: (self.sub_btn_update, "rocket_launch")
        }
        for idx, (btn, icon_name) in idx_map.items():
            btn.setFixedHeight(30)
            btn.setIconSize(QSize(14, 14))
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if idx == active_index:
                if is_light:
                    btn.setIcon(get_symbol_icon(icon_name, color="#0284C7", size=14))
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(2, 132, 199, 0.12);
                            color: #0284C7;
                            border: 1px solid #0284C7;
                            border-radius: 6px;
                            padding: 0px 12px;
                            font-size: 11px;
                            font-weight: 600;
                            outline: none;
                        }
                    """)
                else:
                    btn.setIcon(get_symbol_icon(icon_name, color="#38BDF8", size=14))
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(38, 176, 228, 0.22);
                            color: #FFFFFF;
                            border: 1px solid #26B0E4;
                            border-radius: 6px;
                            padding: 0px 12px;
                            font-size: 11px;
                            font-weight: 600;
                            outline: none;
                        }
                    """)
            else:
                if is_light:
                    btn.setIcon(get_symbol_icon(icon_name, color="#475569", size=14))
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #FFFFFF;
                            color: #475569;
                            border: 1px solid #CBD5E1;
                            border-radius: 6px;
                            padding: 0px 12px;
                            font-size: 11px;
                            font-weight: 600;
                            outline: none;
                        }
                        QPushButton:hover {
                            background-color: #F1F5F9;
                            color: #0F172A;
                            border-color: #94A3B8;
                        }
                    """)
                else:
                    btn.setIcon(get_symbol_icon(icon_name, color="#94A3B8", size=14))
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(255, 255, 255, 0.04);
                            color: #94A3B8;
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 6px;
                            padding: 0px 12px;
                            font-size: 11px;
                            font-weight: 600;
                            outline: none;
                        }
                        QPushButton:hover {
                            background-color: rgba(255, 255, 255, 0.08);
                            color: #E2E8F0;
                            border-color: rgba(255, 255, 255, 0.16);
                        }
                    """)

        if hasattr(self, 'sub_btn_back'):
            self.sub_btn_back.setFixedHeight(30)
            self.sub_btn_back.setIcon(get_symbol_icon("arrow_back", color="#0284C7" if is_light else "#38BDF8", size=14))
            self.sub_btn_back.setIconSize(QSize(14, 14))
            self.sub_btn_back.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if is_light:
                self.sub_btn_back.setStyleSheet("""
                    QPushButton {
                        background: rgba(2, 132, 199, 0.08);
                        color: #0284C7;
                        border: 1px solid rgba(2, 132, 199, 0.3);
                        border-radius: 6px;
                        padding: 0px 12px;
                        font-size: 11px;
                        font-weight: 600;
                        outline: none;
                    }
                    QPushButton:hover {
                        background: rgba(2, 132, 199, 0.16);
                        color: #0369A1;
                        border-color: #0284C7;
                    }
                """)
            else:
                self.sub_btn_back.setStyleSheet("""
                    QPushButton {
                        background: rgba(38, 176, 228, 0.15);
                        color: #38BDF8;
                        border: 1px solid rgba(38, 176, 228, 0.4);
                        border-radius: 6px;
                        padding: 0px 12px;
                        font-size: 11px;
                        font-weight: 600;
                        outline: none;
                    }
                    QPushButton:hover {
                        background: rgba(38, 176, 228, 0.3);
                        color: #FFFFFF;
                        border-color: #26B0E4;
                    }
                """)

    # ---------------- 顶部栏构建 ----------------
    def _build_top_bar(self, parent_layout: QVBoxLayout):
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        top_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 面包屑 (自然清晰，去除机械冗余前缀)
        self.breadcrumb_lbl = QLabel("对讲与即时检索")
        self.breadcrumb_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #94A3B8;")
        self.breadcrumb_lbl.setFixedHeight(30)
        self.breadcrumb_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        top_bar.addWidget(self.breadcrumb_lbl)

        # 设置中心分段子导航栏 (在 Page 1, 2, 3, 4 时呈现)
        self.settings_tab_bar = QWidget()
        self.settings_tab_bar.setVisible(False)
        self.settings_tab_bar.setFixedHeight(30)
        tab_layout = QHBoxLayout(self.settings_tab_bar)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(6)
        tab_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        is_light = ThemeManager.get_instance().is_light()
        self.sub_btn_roster = QPushButton(f"企业通讯录 ({len(EMPLOYEES)}人)")
        self.sub_btn_memory = QPushButton("会议记忆库")
        self.sub_btn_engine = QPushButton("系统引擎状态")
        self.sub_btn_update = QPushButton("软件更新")
        self.sub_btn_back = QPushButton("返回对讲")

        for btn in (self.sub_btn_roster, self.sub_btn_memory, self.sub_btn_engine, self.sub_btn_update, self.sub_btn_back):
            btn.setFixedHeight(30)
            btn.setIconSize(QSize(14, 14))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.sub_btn_roster.setIcon(get_symbol_icon("group", color="#0284C7" if is_light else "#38BDF8", size=14))
        self.sub_btn_memory.setIcon(get_symbol_icon("article", color="#0284C7" if is_light else "#38BDF8", size=14))
        self.sub_btn_engine.setIcon(get_symbol_icon("tune", color="#0284C7" if is_light else "#38BDF8", size=14))
        self.sub_btn_update.setIcon(get_symbol_icon("rocket_launch", color="#0284C7" if is_light else "#38BDF8", size=14))
        self.sub_btn_back.setIcon(get_symbol_icon("arrow_back", color="#0284C7" if is_light else "#38BDF8", size=14))

        self.sub_btn_roster.clicked.connect(lambda: self._switch_nav(2))
        self.sub_btn_memory.clicked.connect(lambda: self._switch_nav(1))
        self.sub_btn_engine.clicked.connect(lambda: self._switch_nav(3))
        self.sub_btn_update.clicked.connect(lambda: self._switch_nav(4))
        self.sub_btn_back.clicked.connect(lambda: self._switch_nav(0))

        tab_layout.addWidget(self.sub_btn_roster)
        tab_layout.addWidget(self.sub_btn_memory)
        tab_layout.addWidget(self.sub_btn_engine)
        tab_layout.addWidget(self.sub_btn_update)
        tab_layout.addSpacing(6)
        tab_layout.addWidget(self.sub_btn_back)

        top_bar.addWidget(self.settings_tab_bar)
        top_bar.addStretch()

        # 主题切换按钮 (月亮/太阳小图标，置于版本号左侧一点点)
        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(30, 30)
        self.theme_btn.setIconSize(QSize(16, 16))
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._on_toggle_theme)
        top_bar.addWidget(self.theme_btn)
        top_bar.addSpacing(4)

        # 常驻版本与更新入口 (任何页面均可点击查看发版详情)
        self.top_version_btn = QPushButton(f"v{APP_VERSION}")
        self.top_version_btn.setFixedHeight(30)
        self.top_version_btn.setIconSize(QSize(13, 13))
        self.top_version_btn.setIcon(get_symbol_icon("rocket_launch", color="#0284C7" if is_light else "#38BDF8", size=13))
        self.top_version_btn.setToolTip(f"当前版本 v{APP_VERSION} · 点击打开软件更新与发版管理中心")
        self.top_version_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_version_btn.clicked.connect(lambda: self._switch_nav(4))
        top_bar.addWidget(self.top_version_btn)

        parent_layout.addLayout(top_bar)

    # ---------------- Page 0: 对讲与检索 ----------------
    def _build_page_ask(self, stack: QStackedWidget):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(14)

        is_light = ThemeManager.get_instance().is_light()

        # 美好智能 Command 风格检索栏
        self.cmd_card = QFrame()
        self.cmd_card.setObjectName("cmd_card")
        cmd_layout = QHBoxLayout(self.cmd_card)
        cmd_layout.setContentsMargins(14, 10, 14, 10)
        cmd_layout.setSpacing(10)

        self.search_icon_lbl = QLabel()
        self.search_icon_lbl.setStyleSheet("border: none; background: transparent;")
        self.search_icon_lbl.setPixmap(get_symbol_pixmap("search", color="#0284C7" if is_light else "#26B0E4", size=18))
        cmd_layout.addWidget(self.search_icon_lbl)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("提问会议记忆 (例如: 设计海报找谁？昨天讨论了什么？预算定了吗？)")
        self.query_input.returnPressed.connect(self._handle_query)
        self.query_input.textChanged.connect(lambda: self.search_status_lbl.setText(""))
        cmd_layout.addWidget(self.query_input, 1)

        self.search_status_lbl = QLabel("")
        self.search_status_lbl.setStyleSheet("border: none; background: transparent; color: #8AC657; font-size: 11px; font-weight: 600;")
        cmd_layout.addWidget(self.search_status_lbl)

        # 快捷键标签
        shortcut_chip = QLabel("Enter 检索")
        shortcut_chip.setStyleSheet("""
            background-color: rgba(148, 163, 184, 0.12);
            color: #64748B;
            border: none;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 10.5px;
            font-weight: 600;
        """)
        cmd_layout.addWidget(shortcut_chip)

        search_btn = QPushButton("检索知识库")
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

        page_layout.addWidget(self.cmd_card)

        # 知识溯源解答主卡 (集成微动效 BorderBeam 呼吸边框容器)
        self.ans_card = BorderBeamContainer(border_radius=12)
        self.ans_card.setObjectName("ans_card")
        ans_layout = QVBoxLayout(self.ans_card)
        ans_layout.setContentsMargins(18, 16, 18, 16)
        ans_layout.setSpacing(10)

        ans_title_row = QHBoxLayout()
        ans_title_row.setSpacing(8)

        self.ans_title_icon = QLabel()
        self.ans_title_icon.setStyleSheet("border: none; background: transparent;")
        self.ans_title_icon.setPixmap(get_symbol_pixmap("chat", color="#0284C7" if is_light else "#26B0E4", size=16))
        ans_title_row.addWidget(self.ans_title_icon)

        self.ans_title = QLabel("知识溯源解答")
        self.ans_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        ans_title_row.addWidget(self.ans_title)
        ans_title_row.addStretch()

        # 今日新增会议切片状态胶囊 (位于“复制内容”左侧)
        self.today_slice_badge = QFrame()
        self.today_slice_badge.setFixedHeight(26)
        today_badge_layout = QHBoxLayout(self.today_slice_badge)
        today_badge_layout.setContentsMargins(8, 0, 10, 0)
        today_badge_layout.setSpacing(5)
        today_badge_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.today_slice_icon = QLabel()
        self.today_slice_icon.setStyleSheet("border: none; background: transparent;")
        self.today_slice_icon.setPixmap(get_symbol_pixmap("auto_awesome", color="#0284C7" if is_light else "#38BDF8", size=13))
        today_badge_layout.addWidget(self.today_slice_icon)

        self.today_slice_lbl = QLabel("今日已新增")
        self.today_slice_lbl.setStyleSheet("font-size: 11px; font-weight: 500; border: none; background: transparent;")
        today_badge_layout.addWidget(self.today_slice_lbl)

        self.today_slice_num = QLabel("0")
        self.today_slice_num.setFixedHeight(18)
        self.today_slice_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        today_badge_layout.addWidget(self.today_slice_num)

        self.today_slice_suffix = QLabel("条记忆")
        self.today_slice_suffix.setStyleSheet("font-size: 11px; font-weight: 500; border: none; background: transparent;")
        today_badge_layout.addWidget(self.today_slice_suffix)

        ans_title_row.addWidget(self.today_slice_badge)
        ans_title_row.addSpacing(6)

        self.copy_btn = QPushButton("复制内容")
        self.copy_btn.setIcon(get_symbol_icon("content_copy", color="#64748B" if is_light else "#94A3B8", size=13))
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setStyleSheet("background: transparent; border: none; color: #94A3B8; font-size: 11px;")
        self.copy_btn.clicked.connect(self._copy_answer_to_clipboard)
        ans_title_row.addWidget(self.copy_btn)
        ans_layout.addLayout(ans_title_row)

        # 全局语音对讲与检索动效长条
        self.intercom_banner = IntercomBanner(self)
        self.intercom_banner.interrupted_clicked.connect(self.stop_speaking)
        ans_layout.addWidget(self.intercom_banner)

        # 核心解答文本区域 (独占全宽，纯净无内嵌冗余边框)
        self.answer_browser = StreamTextDisplay()
        self.answer_browser.setOpenExternalLinks(True)
        self.answer_browser.clear_history()
        self.answer_browser.streaming_started.connect(self.ans_card.start_beam)
        self.answer_browser.streaming_finished.connect(self._on_output_finished)
        ans_layout.addWidget(self.answer_browser, 1)

        page_layout.addWidget(self.ans_card, 1)
        stack.addWidget(page)

        # 保持内部虚拟控件，保证 refresh_records 逻辑安全运行
        self.slice_list = QListWidget()
        self.slice_count_badge = QLabel("0 段切片")

    # ---------------- Page 1: 会议记忆库 (Memory Slices) ----------------
    def _build_page_memory(self, stack: QStackedWidget):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)

        self.current_mem_mode = "normal"  # "normal" 或 "trash"
        self.cached_normal_records = []
        self.cached_trash_records = []
        self.current_selected_record = None

        # 1. 顶部模式切换与搜索条
        is_light = ThemeManager.get_instance().is_light()
        self.mem_header_card = QFrame()
        self.mem_header_card.setObjectName("mem_header_card")
        if is_light:
            self.mem_header_card.setStyleSheet("""
                QFrame#mem_header_card {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 10px;
                }
            """)
        else:
            self.mem_header_card.setStyleSheet("""
                QFrame#mem_header_card {
                    background-color: #11141D;
                    border: 1px solid rgba(255, 255, 255, 0.07);
                    border-radius: 10px;
                }
            """)
        h_layout = QHBoxLayout(self.mem_header_card)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(10)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 两个菜单入口：正式切片 vs 或许没用 (矢量图标，无 Emoji)
        self.btn_mem_normal = QPushButton("正式会议记忆 (0)")
        self.btn_mem_normal.setFixedHeight(32)
        self.btn_mem_normal.setIconSize(QSize(14, 14))
        self.btn_mem_normal.setIcon(get_symbol_icon("article", color="#0284C7" if is_light else "#38BDF8", size=14))

        self.btn_mem_trash = QPushButton("或许没用 (0)")
        self.btn_mem_trash.setFixedHeight(32)
        self.btn_mem_trash.setIconSize(QSize(14, 14))
        self.btn_mem_trash.setIcon(get_symbol_icon("delete", color="#64748B" if is_light else "#94A3B8", size=14))

        for b in (self.btn_mem_normal, self.btn_mem_trash):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_mem_normal.clicked.connect(lambda: self._switch_mem_mode("normal"))
        self.btn_mem_trash.clicked.connect(lambda: self._switch_mem_mode("trash"))

        h_layout.addWidget(self.btn_mem_normal)
        h_layout.addWidget(self.btn_mem_trash)
        h_layout.addSpacing(10)

        self.mem_search_input = QLineEdit()
        self.mem_search_input.setFixedHeight(32)
        self.mem_search_input.setPlaceholderText("在当前会议记忆中快速搜索关键词 (如: 预算, Logo, 机器人)...")
        if is_light:
            self.mem_search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 0px 12px;
                    font-size: 12px;
                    color: #0F172A;
                }
                QLineEdit:focus {
                    border-color: #0284C7;
                }
            """)
        else:
            self.mem_search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #0A0C10;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 0px 12px;
                    font-size: 12px;
                    color: #FFFFFF;
                }
                QLineEdit:focus {
                    border-color: #26B0E4;
                }
            """)
        self.mem_search_input.returnPressed.connect(self._search_memory_slices)
        h_layout.addWidget(self.mem_search_input, 1)

        self.mem_search_btn = QPushButton("筛选记忆")
        self.mem_search_btn.setFixedHeight(32)
        self.mem_search_btn.setIconSize(QSize(14, 14))
        self.mem_search_btn.setIcon(get_symbol_icon("search", color="#0284C7" if is_light else "#26B0E4", size=14))
        self.mem_search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.mem_search_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(2, 132, 199, 0.08);
                    color: #0284C7;
                    border: 1px solid rgba(2, 132, 199, 0.35);
                    border-radius: 8px;
                    padding: 0px 16px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0284C7;
                    color: #FFFFFF;
                }
            """)
        else:
            self.mem_search_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(19, 69, 157, 0.35);
                    color: #26B0E4;
                    border: 1px solid rgba(38, 176, 228, 0.45);
                    border-radius: 8px;
                    padding: 0px 16px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #26B0E4;
                    color: #FFFFFF;
                }
            """)
        self.mem_search_btn.clicked.connect(self._search_memory_slices)
        h_layout.addWidget(self.mem_search_btn)

        page_layout.addWidget(self.mem_header_card)

        # 2. “或许没用”次要记忆 AI 研判提醒与一键清理横幅 (默认隐藏，仅在 trash 模式显示，克制无视觉污染)
        self.trash_banner = QFrame()
        self.trash_banner.setObjectName("trash_banner")
        self.trash_banner.setVisible(False)
        if is_light:
            self.trash_banner.setStyleSheet("""
                QFrame#trash_banner {
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
            """)
        else:
            self.trash_banner.setStyleSheet("""
                QFrame#trash_banner {
                    background: #11141D;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
            """)
        trash_b_layout = QHBoxLayout(self.trash_banner)
        trash_b_layout.setContentsMargins(12, 8, 12, 8)
        trash_b_layout.setSpacing(12)
        trash_b_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.trash_tip_lbl = QLabel("AI 研判：以下切片多为开场寒暄、试音或无决议的次要内容，可安全清理以释放检索空间。")
        self.trash_tip_lbl.setWordWrap(True)
        self.trash_tip_lbl.setStyleSheet(f"color: {'#64748B' if is_light else '#94A3B8'}; font-size: 11px; font-weight: 500;")
        trash_b_layout.addWidget(self.trash_tip_lbl, 1)

        self.btn_clean_all_trash = QPushButton("清空次要记忆")
        self.btn_clean_all_trash.setFixedHeight(30)
        self.btn_clean_all_trash.setIconSize(QSize(14, 14))
        self.btn_clean_all_trash.setIcon(get_symbol_icon("delete_sweep", color="#64748B" if is_light else "#94A3B8", size=14))
        self.btn_clean_all_trash.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.btn_clean_all_trash.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #475569;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 0px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #FEE2E2;
                    color: #DC2626;
                    border-color: #FCA5A5;
                }
            """)
        else:
            self.btn_clean_all_trash.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 0px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 0.2);
                    color: #FCA5A5;
                    border-color: #EF4444;
                }
            """)
        self.btn_clean_all_trash.clicked.connect(self._clean_all_trash_slices)
        trash_b_layout.addWidget(self.btn_clean_all_trash)

        page_layout.addWidget(self.trash_banner)

        # 3. 双栏切片检查器 (左：切片列表，右：结构化四象限卡片详情与专属删除操作)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        # 左栏：容器 (新切片静默浮动提示胶囊 + 切片列表)
        left_container = QWidget()
        left_container.setMinimumWidth(300)
        left_container.setMaximumWidth(420)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.new_slice_pill = QPushButton("收到新会议切片已归档 · 点击置顶查看")
        self.new_slice_pill.setIcon(get_symbol_icon("article", color="#0284C7" if is_light else "#38BDF8", size=13))
        self.new_slice_pill.setVisible(False)
        self.new_slice_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.new_slice_pill.setStyleSheet("""
                QPushButton {
                    background: rgba(2, 132, 199, 0.12);
                    color: #0284C7;
                    border: 1px solid #0284C7;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 11.5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #0284C7;
                    color: #FFFFFF;
                }
            """)
        else:
            self.new_slice_pill.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(38, 176, 228, 0.25), stop:1 rgba(99, 102, 241, 0.25));
                    color: #38BDF8;
                    border: 1px solid #26B0E4;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 11.5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #26B0E4;
                    color: #FFFFFF;
                    border: 1px solid #38BDF8;
                }
            """)
        self.new_slice_pill.clicked.connect(self._apply_pending_slice_update)
        left_layout.addWidget(self.new_slice_pill)

        # 列表 (自适应 Light / Dark 主题)
        self.mem_list = QListWidget()
        self.mem_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mem_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.mem_list.setStyleSheet(get_mem_list_style(is_light))
        self.mem_list.currentRowChanged.connect(self._on_mem_item_selected)
        self.mem_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mem_list.customContextMenuRequested.connect(self._show_mem_list_context_menu)
        self.mem_list.verticalScrollBar().valueChanged.connect(self._on_mem_scroll_changed)
        left_layout.addWidget(self.mem_list, 1)

        splitter.addWidget(left_container)

        # 右栏容器：详情卡 + 顶部专属操作栏 (次要记忆专属删除按钮)
        right_detail_container = QWidget()
        right_layout = QVBoxLayout(right_detail_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # 次要记忆详情顶部的删除与原因栏 (仅 trash 模式显示，克制素雅风格)
        self.trash_detail_action_bar = QFrame()
        self.trash_detail_action_bar.setObjectName("trash_detail_action_bar")
        self.trash_detail_action_bar.setVisible(False)
        if is_light:
            self.trash_detail_action_bar.setStyleSheet("""
                QFrame#trash_detail_action_bar {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    padding: 6px 10px;
                }
            """)
        else:
            self.trash_detail_action_bar.setStyleSheet("""
                QFrame#trash_detail_action_bar {
                    background-color: #11141D;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 6px 10px;
                }
            """)
        t_action_layout = QHBoxLayout(self.trash_detail_action_bar)
        t_action_layout.setContentsMargins(8, 4, 8, 4)
        t_action_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.trash_reason_lbl = QLabel("AI 研判理由：无实质性决策且无落地待办推进")
        self.trash_reason_lbl.setStyleSheet(f"color: {'#64748B' if is_light else '#94A3B8'}; font-size: 11px; font-weight: 500;")
        t_action_layout.addWidget(self.trash_reason_lbl, 1)

        self.btn_restore_curr_slice = QPushButton("恢复为正式资产")
        self.btn_restore_curr_slice.setFixedHeight(30)
        self.btn_restore_curr_slice.setIconSize(QSize(14, 14))
        self.btn_restore_curr_slice.setIcon(get_symbol_icon("check_circle", color="#0284C7" if is_light else "#38BDF8", size=14))
        self.btn_restore_curr_slice.setToolTip("将此切片恢复为正式会议资产，杜绝 AI 误判")
        self.btn_restore_curr_slice.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.btn_restore_curr_slice.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF;
                    color: #0284C7;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 0px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: rgba(2, 132, 199, 0.08);
                    border-color: #0284C7;
                }
            """)
        else:
            self.btn_restore_curr_slice.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #38BDF8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 0px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: rgba(56, 189, 248, 0.15);
                    border-color: #38BDF8;
                }
            """)
        self.btn_restore_curr_slice.clicked.connect(lambda: self._restore_slice_useful(self.current_selected_record))
        t_action_layout.addWidget(self.btn_restore_curr_slice)

        self.btn_delete_curr_slice = QPushButton("删除此切片")
        self.btn_delete_curr_slice.setFixedHeight(30)
        self.btn_delete_curr_slice.setIconSize(QSize(14, 14))
        self.btn_delete_curr_slice.setIcon(get_symbol_icon("delete", color="#64748B" if is_light else "#94A3B8", size=14))
        self.btn_delete_curr_slice.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.btn_delete_curr_slice.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF;
                    color: #64748B;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 0px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #FEE2E2;
                    color: #DC2626;
                    border-color: #FCA5A5;
                }
            """)
        else:
            self.btn_delete_curr_slice.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 0px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: rgba(239, 68, 68, 0.2);
                    color: #FCA5A5;
                    border-color: #EF4444;
                }
            """)
        self.btn_delete_curr_slice.clicked.connect(self._delete_current_selected_slice)
        t_action_layout.addWidget(self.btn_delete_curr_slice)
        right_layout.addWidget(self.trash_detail_action_bar)

        # 详情文本区
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
        right_layout.addWidget(self.mem_detail_browser, 1)

        splitter.addWidget(right_detail_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 680])

        page_layout.addWidget(splitter, 1)
        stack.addWidget(page)
        self._update_mem_tab_styles()

    def _switch_mem_mode(self, mode: str):
        """切换正式切片资产 vs 或许没用次要记忆"""
        if self.current_mem_mode == mode:
            return
        self.current_mem_mode = mode
        self.current_selected_record = None
        self._update_mem_tab_styles()
        self.trash_banner.setVisible(mode == "trash")
        self.trash_detail_action_bar.setVisible(False)
        if hasattr(self, "new_slice_pill"):
            self.new_slice_pill.setVisible(False)
        self._has_pending_update = False
        self._render_mem_list(preserve_selection=False)

    def _apply_pending_slice_update(self):
        """平滑应用积压的待更新切片，置顶显示最新会议内容"""
        if hasattr(self, "new_slice_pill"):
            self.new_slice_pill.setVisible(False)
        self._has_pending_update = False
        self._render_mem_list(preserve_selection=False)
        if self.mem_list.count() > 0:
            self.mem_list.setCurrentRow(0)
        self.mem_list.verticalScrollBar().setValue(0)

    def _on_mem_scroll_changed(self, val: int):
        """当操作员主动滚回顶部且有待更新的新切片时，自动平滑合并并隐藏胶囊"""
        if val == 0 and getattr(self, "_has_pending_update", False):
            self._apply_pending_slice_update()

    def _update_mem_tab_styles(self):
        if not hasattr(self, 'btn_mem_normal'):
            return
        self.btn_mem_normal.setFixedHeight(32)
        self.btn_mem_normal.setIconSize(QSize(14, 14))
        self.btn_mem_normal.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_mem_trash.setFixedHeight(32)
        self.btn_mem_trash.setIconSize(QSize(14, 14))
        self.btn_mem_trash.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        is_light = ThemeManager.get_instance().is_light()
        if is_light:
            if self.current_mem_mode == "normal":
                self.btn_mem_normal.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(2, 132, 199, 0.12);
                        color: #0284C7;
                        border: 1px solid #0284C7;
                        border-radius: 8px;
                        padding: 0px 14px;
                        font-size: 12px;
                        font-weight: 600;
                        outline: none;
                    }
                """)
                self.btn_mem_trash.setStyleSheet("""
                    QPushButton {
                        background-color: #F1F5F9;
                        color: #64748B;
                        border: 1px solid #CBD5E1;
                        border-radius: 8px;
                        padding: 0px 14px;
                        font-size: 12px;
                        font-weight: 600;
                        outline: none;
                    }
                    QPushButton:hover {
                        background-color: rgba(239, 68, 68, 0.08);
                        border-color: rgba(239, 68, 68, 0.35);
                        color: #DC2626;
                    }
                """)
            else:
                self.btn_mem_normal.setStyleSheet("""
                    QPushButton {
                        background-color: #F1F5F9;
                        color: #64748B;
                        border: 1px solid #CBD5E1;
                        border-radius: 8px;
                        padding: 0px 14px;
                        font-size: 12px;
                        font-weight: 600;
                        outline: none;
                    }
                    QPushButton:hover {
                        background-color: rgba(2, 132, 199, 0.08);
                        border-color: #0284C7;
                        color: #0284C7;
                    }
                """)
                self.btn_mem_trash.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(239, 68, 68, 0.12);
                        color: #DC2626;
                        border: 1px solid #EF4444;
                        border-radius: 8px;
                        padding: 0px 14px;
                        font-size: 12px;
                        font-weight: 600;
                        outline: none;
                    }
                """)
        else:
            if self.current_mem_mode == "normal":
                self.btn_mem_normal.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(38, 176, 228, 0.22);
                        color: #FFFFFF;
                        border: 1px solid #26B0E4;
                        border-radius: 8px;
                        padding: 0px 14px;
                        font-size: 12px;
                        font-weight: 600;
                        outline: none;
                    }
                """)
                self.btn_mem_trash.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.04);
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 8px;
                        padding: 0px 14px;
                        font-size: 12px;
                        font-weight: 600;
                        outline: none;
                    }
                    QPushButton:hover {
                        background-color: rgba(239, 68, 68, 0.15);
                        border-color: rgba(239, 68, 68, 0.35);
                        color: #FCA5A5;
                    }
                """)
            else:
                self.btn_mem_normal.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.04);
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 8px;
                        padding: 0px 14px;
                        font-size: 12px;
                        font-weight: 600;
                        outline: none;
                    }
                    QPushButton:hover {
                        background-color: rgba(38, 176, 228, 0.15);
                        border-color: #26B0E4;
                        color: #38BDF8;
                    }
                """)
                self.btn_mem_trash.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(239, 68, 68, 0.22);
                        color: #FECACA;
                        border: 1px solid #EF4444;
                        border-radius: 8px;
                        padding: 0px 14px;
                        font-size: 12px;
                        font-weight: 600;
                        outline: none;
                    }
                """)

    # ---------------- Page 2: 企业通讯录 (Org Directory) ----------------
    def _build_page_roster(self, stack: QStackedWidget):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(16, 12, 16, 16)
        page_layout.setSpacing(10)

        # 1. 顶部操作与筛选栏
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)
        filter_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        is_light = ThemeManager.get_instance().is_light()

        self.roster_search_input = QLineEdit()
        self.roster_search_input.setFixedHeight(32)
        self.roster_search_input.setPlaceholderText("快速筛选成员姓名、职务、职责或技能关键词...")
        if is_light:
            self.roster_search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 0px 14px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border-color: #0284C7;
                }
            """)
        else:
            self.roster_search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #12151F;
                    color: #FFFFFF;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 0px 14px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border-color: #26B0E4;
                    background-color: #161A28;
                }
            """)
        self.roster_search_input.textChanged.connect(self._filter_roster_cards)
        filter_bar.addWidget(self.roster_search_input, 1)

        active_emps = [e for e in EMPLOYEES if e.get("status") != "departed"]
        departed_emps = [e for e in EMPLOYEES if e.get("status") == "departed"]

        if len(departed_emps) > 0:
            self.roster_stat_lbl = QLabel(f"在职成员 {len(active_emps)} 位 · 归档离职 {len(departed_emps)} 位 · 会议画像全量留存")
        else:
            self.roster_stat_lbl = QLabel(f"共收录 {len(active_emps)} 位组织核心成员 · 实时关联中台会议动态画像")
        self.roster_stat_lbl.setFixedHeight(32)
        self.roster_stat_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.roster_stat_lbl.setStyleSheet(f"color: {'#16A34A' if is_light else '#8AC657'}; font-size: 11px; font-weight: 600; padding: 0 4px;")
        filter_bar.addWidget(self.roster_stat_lbl)

        self.refresh_roster_btn = QPushButton("刷新画像")
        self.refresh_roster_btn.setFixedHeight(32)
        self.refresh_roster_btn.setIconSize(QSize(14, 14))
        self.refresh_roster_btn.setIcon(get_symbol_icon("history", color="#0284C7" if is_light else "#CBD5E1", size=14))
        self.refresh_roster_btn.setToolTip("重新从会议记忆中台反查提取最新的成员参与决议与动态")
        self.refresh_roster_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.refresh_roster_btn.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 0px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #F1F5F9;
                    border-color: #0284C7;
                    color: #0284C7;
                }
            """)
        else:
            self.refresh_roster_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #CBD5E1;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    padding: 0px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                    color: #FFFFFF;
                    border-color: #26B0E4;
                }
            """)
        self.refresh_roster_btn.clicked.connect(self.refresh_roster)
        filter_bar.addWidget(self.refresh_roster_btn)

        page_layout.addLayout(filter_bar)

        # 2. 滚动区域与双列瀑布流容器
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

        cards_container = QWidget()
        cards_container.setStyleSheet("background: transparent;")
        cards_vbox = QVBoxLayout(cards_container)
        cards_vbox.setContentsMargins(0, 0, 8, 20)
        cards_vbox.setSpacing(14)
        cards_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 在职成员双列容器
        active_container = QWidget()
        active_columns_layout = QHBoxLayout(active_container)
        active_columns_layout.setContentsMargins(0, 0, 0, 0)
        active_columns_layout.setSpacing(12)
        active_columns_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.col_left = QVBoxLayout()
        self.col_left.setSpacing(12)
        self.col_left.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.col_right = QVBoxLayout()
        self.col_right.setSpacing(12)
        self.col_right.setAlignment(Qt.AlignmentFlag.AlignTop)

        active_columns_layout.addLayout(self.col_left, 1)
        active_columns_layout.addLayout(self.col_right, 1)
        cards_vbox.addWidget(active_container)

        # 美好智能 VI 品牌色谱
        colors = ["#13459D", "#26B0E4", "#8AC657", "#1E60B8", "#17A2B8", "#6DAE3E", "#2C75D3", "#38BDF8", "#78B847"]

        self.employee_cards = []
        self.active_cards = []
        self.departed_cards = []

        # 填充在职成员卡片
        for idx, emp in enumerate(active_emps):
            c = colors[idx % len(colors)]
            card = ExpandableEmployeeCard(emp, self.store, color=c)
            card.search_requested.connect(self._on_roster_search_requested)
            self.employee_cards.append(card)
            self.active_cards.append(card)

            if idx % 2 == 0:
                self.col_left.addWidget(card)
            else:
                self.col_right.addWidget(card)

        # 3. 已离职成员折叠区分隔与展开栏 (直接折叠收起，信息留存)
        self.departed_toggle_btn = QPushButton(f"已离职成员归档 ({len(departed_emps)} 人)  ▾ 点击展开历史沉淀档案")
        self.departed_toggle_btn.setIcon(get_symbol_icon("apartment", color="#64748B", size=13))
        self.departed_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.departed_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F8FAFC;
                    color: #64748B;
                    border: 1px dashed #CBD5E1;
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 11.5px;
                    font-weight: 600;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    color: #0F172A;
                    border-color: #94A3B8;
                }
            """)
        else:
            self.departed_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.02);
                    color: #94A3B8;
                    border: 1px dashed rgba(255, 255, 255, 0.12);
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 11.5px;
                    font-weight: 600;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: #E2E8F0;
                    border-color: rgba(38, 176, 228, 0.3);
                }
            """)
        self.departed_toggle_btn.clicked.connect(self._toggle_departed_section)
        self.departed_toggle_btn.setVisible(len(departed_emps) > 0)
        cards_vbox.addWidget(self.departed_toggle_btn)

        # 4. 已离职成员卡片容器 (默认折叠隐藏)
        self.departed_container = QWidget()
        self.departed_expanded = False
        self.departed_container.setVisible(False)
        dep_columns_layout = QHBoxLayout(self.departed_container)
        dep_columns_layout.setContentsMargins(0, 2, 0, 0)
        dep_columns_layout.setSpacing(12)
        dep_columns_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.col_dep_left = QVBoxLayout()
        self.col_dep_left.setSpacing(12)
        self.col_dep_left.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.col_dep_right = QVBoxLayout()
        self.col_dep_right.setSpacing(12)
        self.col_dep_right.setAlignment(Qt.AlignmentFlag.AlignTop)

        dep_columns_layout.addLayout(self.col_dep_left, 1)
        dep_columns_layout.addLayout(self.col_dep_right, 1)

        # 填充已离职成员卡片
        for idx, emp in enumerate(departed_emps):
            card = ExpandableEmployeeCard(emp, self.store, color="#475569")
            card.search_requested.connect(self._on_roster_search_requested)
            self.employee_cards.append(card)
            self.departed_cards.append(card)

            if idx % 2 == 0:
                self.col_dep_left.addWidget(card)
            else:
                self.col_dep_right.addWidget(card)

        cards_vbox.addWidget(self.departed_container)

        scroll.setWidget(cards_container)
        page_layout.addWidget(scroll, 1)
        stack.addWidget(page)

    def _toggle_departed_section(self):
        """展开或折叠已离职成员历史档案"""
        self.departed_expanded = not getattr(self, "departed_expanded", False)
        self.departed_container.setVisible(self.departed_expanded)
        dep_count = len(self.departed_cards)
        is_light = ThemeManager.get_instance().is_light()
        if self.departed_expanded:
            self.departed_toggle_btn.setText(f"已离职成员归档 ({dep_count} 人)  ▴ 点击收起历史归档")
            if is_light:
                self.departed_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(2, 132, 199, 0.06);
                        color: #0284C7;
                        border: 1px solid rgba(2, 132, 199, 0.3);
                        border-radius: 8px;
                        padding: 10px 14px;
                        font-size: 11.5px;
                        font-weight: 600;
                        text-align: left;
                    }
                """)
            else:
                self.departed_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(38, 176, 228, 0.05);
                        color: #26B0E4;
                        border: 1px solid rgba(38, 176, 228, 0.25);
                        border-radius: 8px;
                        padding: 10px 14px;
                        font-size: 11.5px;
                        font-weight: 600;
                        text-align: left;
                    }
                """)
        else:
            self.departed_toggle_btn.setText(f"已离职成员归档 ({dep_count} 人)  ▾ 点击展开历史沉淀档案")
            if is_light:
                self.departed_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F8FAFC;
                        color: #64748B;
                        border: 1px dashed #CBD5E1;
                        border-radius: 8px;
                        padding: 10px 14px;
                        font-size: 11.5px;
                        font-weight: 600;
                        text-align: left;
                    }
                """)
            else:
                self.departed_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.02);
                        color: #94A3B8;
                        border: 1px dashed rgba(255, 255, 255, 0.12);
                        border-radius: 8px;
                        padding: 10px 14px;
                        font-size: 11.5px;
                        font-weight: 600;
                        text-align: left;
                    }
                """)

    def _on_roster_search_requested(self, query: str):
        """卡片内一键点击检索发起跳转对讲搜索"""
        self._switch_nav(0)
        self.query_input.setText(query)
        self._handle_query()

    def _filter_roster_cards(self, text: str):
        """实时响应通讯录搜索过滤"""
        kw = text.strip().lower()
        matched_count = 0
        departed_matched = 0
        for card in self.employee_cards:
            emp = card.emp
            is_match = (
                not kw or
                kw in emp.get("name", "").lower() or
                kw in emp.get("title", "").lower() or
                kw in emp.get("duties", "").lower() or
                kw in emp.get("tech_stack", "").lower() or
                any(kw in a.lower() for a in emp.get("aliases", []))
            )
            card.setVisible(is_match)
            if is_match:
                matched_count += 1
                if getattr(card, "is_departed", False):
                    departed_matched += 1

        active_count = len(self.active_cards)
        dep_total = len(self.departed_cards)

        if kw:
            self.roster_stat_lbl.setText(f"筛选出 {matched_count} 位成员 (共 {len(EMPLOYEES)} 位)")
            if departed_matched > 0:
                self.departed_container.setVisible(True)
                self.departed_expanded = True
                self.departed_toggle_btn.setText(f"已离职成员归档 (包含 {departed_matched} 位搜索命中)  ▴ 已自动展开")
            else:
                self.departed_container.setVisible(False)
                self.departed_expanded = False
                self.departed_toggle_btn.setText(f"已离职成员归档 ({dep_total} 人)  ▾ 点击展开历史沉淀档案")
        else:
            if dep_total > 0:
                self.roster_stat_lbl.setText(f"在职成员 {active_count} 位 · 归档离职 {dep_total} 位 · 会议画像全量留存")
                self.departed_toggle_btn.setVisible(True)
            else:
                self.roster_stat_lbl.setText(f"共收录 {active_count} 位组织核心成员 · 实时关联中台会议动态画像")
                self.departed_toggle_btn.setVisible(False)
            self.departed_container.setVisible(False)
            self.departed_expanded = False
            self.departed_toggle_btn.setText(f"已离职成员归档 ({dep_total} 人)  ▾ 点击展开历史沉淀档案")

    def refresh_roster(self):
        """刷新所有成员卡片的动态画像与最新会议关联"""
        if hasattr(self, "employee_cards"):
            for card in self.employee_cards:
                card.refresh_profile()

    # ---------------- Page 3: 引擎配置与系统设置 (Settings Center) ----------------
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

        is_light = ThemeManager.get_instance().is_light()

        # 页面标题区
        header_box = QVBoxLayout()
        header_box.setSpacing(3)
        self.settings_page_title = QLabel("系统设置与引擎配置")
        self.settings_page_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        self.settings_page_desc = QLabel("集中管理大模型 API 密钥、语音识别凭据、多角色 TTS 播报音色与系统交互热键")
        self.settings_page_desc.setStyleSheet(f"font-size: 11.5px; color: {'#64748B' if is_light else '#94A3B8'};")
        header_box.addWidget(self.settings_page_title)
        header_box.addWidget(self.settings_page_desc)
        v_layout.addLayout(header_box)

        # ---------------- 卡片 1: 语音合成 (TTS) 与多角色播报 ----------------
        self.card_tts = QFrame()
        self.card_tts.setObjectName("settings_card")
        tts_layout = QVBoxLayout(self.card_tts)
        tts_layout.setContentsMargins(18, 16, 18, 16)
        tts_layout.setSpacing(10)

        tts_title_row = QHBoxLayout()
        self.tts_icon = QLabel()
        self.tts_icon.setPixmap(get_symbol_pixmap("volume_up", color="#0284C7" if is_light else "#38BDF8", size=16))
        self.tts_lbl = QLabel("语音合成 (TTS) 与角色播报")
        self.tts_lbl.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        tts_title_row.addWidget(self.tts_icon)
        tts_title_row.addWidget(self.tts_lbl)
        tts_title_row.addStretch()

        self.chk_enable_tts = QCheckBox("启用即时语音合成朗读")
        self.chk_enable_tts.setChecked(Config.ENABLE_TTS)
        tts_title_row.addWidget(self.chk_enable_tts)
        tts_layout.addLayout(tts_title_row)

        tts_grid = QGridLayout()
        tts_grid.setSpacing(10)

        tts_grid.addWidget(QLabel("TTS 引擎提供商:"), 0, 0)
        self.combo_tts_provider = ModernComboBox()
        self.combo_tts_provider.addItem("微软 Edge-TTS (云原生免 Key 高音质)", "edge-tts")
        self.combo_tts_provider.addItem("火山引擎豆包语音大模型 (拟真拟态)", "volcengine")
        if Config.TTS_PROVIDER == "volcengine":
            self.combo_tts_provider.setCurrentIndex(1)
        else:
            self.combo_tts_provider.setCurrentIndex(0)
        tts_grid.addWidget(self.combo_tts_provider, 0, 1)

        tts_grid.addWidget(QLabel("会议结论播报角色:"), 1, 0)
        self.combo_voice_meeting = ModernComboBox()
        meeting_voices = [
            ("云希 (自然男声 · 严肃严谨 · 默认)", "zh-CN-YunxiNeural"),
            ("晓晓 (知性女声 · 温暖亲和)", "zh-CN-XiaoxiaoNeural"),
            ("云扬 (播音男声 · 沉稳专业)", "zh-CN-YunyangNeural"),
            ("云健 (干练男声 · 敏捷有力)", "zh-CN-YunjianNeural"),
        ]
        for name, vid in meeting_voices:
            self.combo_voice_meeting.addItem(name, vid)
        curr_mv = Config.TTS_VOICE_MEETING
        mv_idx = next((i for i, (_, vid) in enumerate(meeting_voices) if vid == curr_mv), 0)
        self.combo_voice_meeting.setCurrentIndex(mv_idx)
        tts_grid.addWidget(self.combo_voice_meeting, 1, 1)

        tts_grid.addWidget(QLabel("全网科普通识角色:"), 2, 0)
        self.combo_voice_general = ModernComboBox()
        general_voices = [
            ("晓晓 (知性女声 · 温暖亲和 · 默认)", "zh-CN-XiaoxiaoNeural"),
            ("云希 (自然男声 · 严肃严谨)", "zh-CN-YunxiNeural"),
            ("云扬 (播音男声 · 沉稳专业)", "zh-CN-YunyangNeural"),
            ("云健 (干练男声 · 敏捷有力)", "zh-CN-YunjianNeural"),
        ]
        for name, vid in general_voices:
            self.combo_voice_general.addItem(name, vid)
        curr_gv = Config.TTS_VOICE_GENERAL
        gv_idx = next((i for i, (_, vid) in enumerate(general_voices) if vid == curr_gv), 0)
        self.combo_voice_general.setCurrentIndex(gv_idx)
        tts_grid.addWidget(self.combo_voice_general, 2, 1)

        tts_grid.addWidget(QLabel("敏捷指令架构角色:"), 3, 0)
        self.combo_voice_instruction = ModernComboBox()
        instruction_voices = [
            ("云健 (干练男声 · 敏捷有力 · 默认)", "zh-CN-YunjianNeural"),
            ("云扬 (播音男声 · 沉稳专业)", "zh-CN-YunyangNeural"),
            ("云希 (自然男声 · 严肃严谨)", "zh-CN-YunxiNeural"),
            ("晓晓 (知性女声 · 温暖亲和)", "zh-CN-XiaoxiaoNeural"),
        ]
        for name, vid in instruction_voices:
            self.combo_voice_instruction.addItem(name, vid)
        curr_iv = Config.TTS_VOICE_INSTRUCTION
        iv_idx = next((i for i, (_, vid) in enumerate(instruction_voices) if vid == curr_iv), 0)
        self.combo_voice_instruction.setCurrentIndex(iv_idx)
        tts_grid.addWidget(self.combo_voice_instruction, 3, 1)

        tts_layout.addLayout(tts_grid)

        preview_row = QHBoxLayout()
        preview_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.btn_preview_tts = QPushButton("试听当前会议音色")
        self.btn_preview_tts.setFixedHeight(32)
        self.btn_preview_tts.setIconSize(QSize(14, 14))
        self.btn_preview_tts.setIcon(get_symbol_icon("play_arrow", color="#0284C7" if is_light else "#38BDF8", size=14))
        self.btn_preview_tts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview_tts.clicked.connect(self._preview_tts)
        preview_row.addWidget(self.btn_preview_tts)
        preview_row.addStretch()
        tts_layout.addLayout(preview_row)

        v_layout.addWidget(self.card_tts)

        # ---------------- 卡片 2: 大模型 (LLM / RAG) API 配置 ----------------
        self.card_llm = QFrame()
        self.card_llm.setObjectName("settings_card")
        llm_layout = QVBoxLayout(self.card_llm)
        llm_layout.setContentsMargins(18, 16, 18, 16)
        llm_layout.setSpacing(10)

        llm_title_row = QHBoxLayout()
        self.llm_icon = QLabel()
        self.llm_icon.setPixmap(get_symbol_pixmap("psychology", color="#0284C7" if is_light else "#38BDF8", size=16))
        self.llm_lbl = QLabel("大模型 (LLM / RAG) 密钥与接口配置")
        self.llm_lbl.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        llm_title_row.addWidget(self.llm_icon)
        llm_title_row.addWidget(self.llm_lbl)
        llm_title_row.addStretch()
        llm_layout.addLayout(llm_title_row)

        llm_grid = QGridLayout()
        llm_grid.setSpacing(10)

        llm_grid.addWidget(QLabel("API Key (密钥):"), 0, 0)
        llm_key_box = QHBoxLayout()
        self.input_llm_key = QLineEdit()
        self.input_llm_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_llm_key.setText(Config.OPENAI_API_KEY)
        self.input_llm_key.setPlaceholderText("填入 OpenAI / DeepSeek / 智谱等兼容 API Key...")
        llm_key_box.addWidget(self.input_llm_key, 1)

        self.btn_toggle_llm_key = QPushButton()
        self.btn_toggle_llm_key.setIcon(get_symbol_icon("visibility", color="#64748B" if is_light else "#94A3B8", size=14))
        self.btn_toggle_llm_key.setToolTip("显示/隐藏密钥明文")
        self.btn_toggle_llm_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_llm_key.clicked.connect(self._toggle_llm_key_visibility)
        llm_key_box.addWidget(self.btn_toggle_llm_key)
        llm_grid.addLayout(llm_key_box, 0, 1)

        llm_grid.addWidget(QLabel("接口地址 (Base URL):"), 1, 0)
        self.input_llm_url = QLineEdit()
        self.input_llm_url.setText(Config.OPENAI_BASE_URL)
        self.input_llm_url.setPlaceholderText("https://open.bigmodel.cn/api/coding/paas/v4 或 https://api.deepseek.com/v1")
        llm_grid.addWidget(self.input_llm_url, 1, 1)

        llm_grid.addWidget(QLabel("模型名称 (Model):"), 2, 0)
        self.input_llm_model = QLineEdit()
        self.input_llm_model.setText(Config.LLM_MODEL)
        self.input_llm_model.setPlaceholderText("glm-4-flash / deepseek-chat / qwen-plus")
        llm_grid.addWidget(self.input_llm_model, 2, 1)

        llm_layout.addLayout(llm_grid)
        v_layout.addWidget(self.card_llm)

        # ---------------- 卡片 3: 语音识别 (ASR) 与采集配置 ----------------
        self.card_asr = QFrame()
        self.card_asr.setObjectName("settings_card")
        asr_layout = QVBoxLayout(self.card_asr)
        asr_layout.setContentsMargins(18, 16, 18, 16)
        asr_layout.setSpacing(10)

        asr_title_row = QHBoxLayout()
        self.asr_icon = QLabel()
        self.asr_icon.setPixmap(get_symbol_pixmap("graphic_eq", color="#0284C7" if is_light else "#38BDF8", size=16))
        self.asr_lbl = QLabel("语音识别 (ASR) 与采集设置")
        self.asr_lbl.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        asr_title_row.addWidget(self.asr_icon)
        asr_title_row.addWidget(self.asr_lbl)
        asr_title_row.addStretch()
        asr_layout.addLayout(asr_title_row)

        asr_grid = QGridLayout()
        asr_grid.setSpacing(10)

        asr_grid.addWidget(QLabel("ASR 引擎提供商:"), 0, 0)
        self.combo_asr_provider = ModernComboBox()
        self.combo_asr_provider.addItem("火山引擎 (Volcengine 豆包流式 ASR 2.0)", "volcengine")
        self.combo_asr_provider.addItem("阿里通义听悟 (DashScope SenseVoice)", "dashscope")
        if Config.ASR_PROVIDER == "dashscope":
            self.combo_asr_provider.setCurrentIndex(1)
        else:
            self.combo_asr_provider.setCurrentIndex(0)
        asr_grid.addWidget(self.combo_asr_provider, 0, 1)

        asr_grid.addWidget(QLabel("火山 AppID:"), 1, 0)
        self.input_volc_appid = QLineEdit()
        self.input_volc_appid.setText(Config.VOLC_APPID)
        self.input_volc_appid.setPlaceholderText("火山引擎控制台生成的 AppID")
        asr_grid.addWidget(self.input_volc_appid, 1, 1)

        asr_grid.addWidget(QLabel("火山 Access Token:"), 2, 0)
        self.input_volc_token = QLineEdit()
        self.input_volc_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_volc_token.setText(Config.VOLC_ACCESS_TOKEN)
        self.input_volc_token.setPlaceholderText("火山引擎 WebSocket 访问令牌 Access Token")
        asr_grid.addWidget(self.input_volc_token, 2, 1)

        asr_grid.addWidget(QLabel("火山 Resource ID:"), 3, 0)
        self.input_volc_resource = QLineEdit()
        self.input_volc_resource.setText(Config.VOLC_RESOURCE_ID)
        self.input_volc_resource.setPlaceholderText("默认 volc.seedasr.sauc.duration")
        asr_grid.addWidget(self.input_volc_resource, 3, 1)

        asr_layout.addLayout(asr_grid)
        v_layout.addWidget(self.card_asr)

        # ---------------- 卡片 4: 对讲热键与静音切片 ----------------
        self.card_intercom = QFrame()
        self.card_intercom.setObjectName("settings_card")
        intercom_layout = QVBoxLayout(self.card_intercom)
        intercom_layout.setContentsMargins(18, 16, 18, 16)
        intercom_layout.setSpacing(10)

        intercom_title_row = QHBoxLayout()
        self.intercom_icon = QLabel()
        self.intercom_icon.setPixmap(get_symbol_pixmap("keyboard", color="#0284C7" if is_light else "#38BDF8", size=16))
        self.intercom_lbl = QLabel("全局对讲热键与静音探测")
        self.intercom_lbl.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        intercom_title_row.addWidget(self.intercom_icon)
        intercom_title_row.addWidget(self.intercom_lbl)
        intercom_title_row.addStretch()
        intercom_layout.addLayout(intercom_title_row)

        intercom_grid = QGridLayout()
        intercom_grid.setSpacing(10)

        intercom_grid.addWidget(QLabel("对讲全局热键:"), 0, 0)
        self.combo_intercom_key = ModernComboBox()
        hotkeys = [
            ("右 Alt (Alt_R · 推荐，单键免组合，高频最顺手)", "Alt_R"),
            ("左 Alt (Alt_L)", "Alt_L"),
            ("Ctrl + Space (空格组合键)", "Ctrl+Space"),
            ("F2 (功能键)", "F2"),
        ]
        for name, val in hotkeys:
            self.combo_intercom_key.addItem(name, val)
        curr_k = Config.INTERCOM_KEY
        k_idx = next((i for i, (_, val) in enumerate(hotkeys) if val.lower() == curr_k.lower()), 0)
        self.combo_intercom_key.setCurrentIndex(k_idx)
        intercom_grid.addWidget(self.combo_intercom_key, 0, 1)

        intercom_grid.addWidget(QLabel("静音分段灵敏度:"), 1, 0)
        self.vad_hint_lbl = QLabel("WebRTC VAD 探测模式 2 (平衡模式：兼顾办公室背景噪音过滤与清晰人声捕捉)")
        self.vad_hint_lbl.setStyleSheet(f"color: {'#64748B' if is_light else '#94A3B8'}; font-size: 11.5px;")
        intercom_grid.addWidget(self.vad_hint_lbl, 1, 1)

        intercom_layout.addLayout(intercom_grid)
        v_layout.addWidget(self.card_intercom)

        # ---------------- 卡片 5: 企业扩展插槽 (Modular Extension Slots) ----------------
        self.card_ext = QFrame()
        self.card_ext.setObjectName("settings_card")
        ext_layout = QVBoxLayout(self.card_ext)
        ext_layout.setContentsMargins(18, 16, 18, 16)
        ext_layout.setSpacing(10)

        ext_title_row = QHBoxLayout()
        self.ext_icon = QLabel()
        self.ext_icon.setPixmap(get_symbol_pixmap("extension", color="#0284C7" if is_light else "#38BDF8", size=16))
        self.ext_lbl = QLabel("自定义扩展插槽 (预留生态空间)")
        self.ext_lbl.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        ext_title_row.addWidget(self.ext_icon)
        ext_title_row.addWidget(self.ext_lbl)
        ext_title_row.addStretch()
        ext_layout.addLayout(ext_title_row)

        self.ext_desc = QLabel("预留模块化插件与企业系统连接器，后续可直接在此配置外接业务协同与私有模型")
        self.ext_desc.setStyleSheet(f"color: {'#64748B' if is_light else '#94A3B8'}; font-size: 11px;")
        ext_layout.addWidget(self.ext_desc)

        ext_grid = QGridLayout()
        ext_grid.setSpacing(8)
        ext_slots = [
            ("飞书 / 钉钉企业机器人 Webhook", "会议重要纪要与待办自动推送至群聊 (规划中)"),
            ("企业私有知识库外挂 (Confluence / Notion)", "自动索引企业沉淀知识，增强检索召回率 (规划中)"),
            ("本地离线大模型 (Ollama / vLLM 私有化)", "支持内网断网环境下的完全本地化隐私问答 (规划中)"),
        ]
        self.ext_boxes = []
        for i, (t, d) in enumerate(ext_slots):
            sbox = QFrame()
            self.ext_boxes.append(sbox)
            sb_l = QVBoxLayout(sbox)
            sb_l.setContentsMargins(10, 8, 10, 8)
            sb_l.setSpacing(2)
            st = QLabel(t)
            st.setStyleSheet(f"font-size: 11.5px; font-weight: 600; color: {'#334155' if is_light else '#CBD5E1'};")
            sd = QLabel(d)
            sd.setStyleSheet(f"font-size: 10.5px; color: {'#64748B' if is_light else '#94A3B8'};")
            sb_l.addWidget(st)
            sb_l.addWidget(sd)
            ext_grid.addWidget(sbox, i, 0)
        ext_layout.addLayout(ext_grid)
        v_layout.addWidget(self.card_ext)

        # ---------------- 底部保存操作栏 ----------------
        save_action_bar = QHBoxLayout()
        save_action_bar.setContentsMargins(4, 8, 4, 8)
        save_action_bar.setSpacing(12)
        save_action_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_save_settings = QPushButton("保存全部配置并立即生效")
        self.btn_save_settings.setFixedHeight(34)
        self.btn_save_settings.setIconSize(QSize(14, 14))
        self.btn_save_settings.setIcon(get_symbol_icon("save", color="#FFFFFF", size=14))
        self.btn_save_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_settings.clicked.connect(self._save_all_settings)
        save_action_bar.addWidget(self.btn_save_settings)

        self.settings_status_lbl = QLabel("")
        self.settings_status_lbl.setFixedHeight(34)
        self.settings_status_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        save_action_bar.addWidget(self.settings_status_lbl, 1)

        self.btn_goto_update = QPushButton("打开软件更新中心 →")
        self.btn_goto_update.setFixedHeight(34)
        self.btn_goto_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_goto_update.clicked.connect(lambda: self._switch_nav(4))
        save_action_bar.addWidget(self.btn_goto_update)

        v_layout.addLayout(save_action_bar)
        v_layout.addStretch()

        scroll.setWidget(container)
        stack.addWidget(scroll)

    def _toggle_llm_key_visibility(self):
        if self.input_llm_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_llm_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_llm_key.setIcon(get_symbol_icon("visibility_off", color="#64748B" if ThemeManager.get_instance().is_light() else "#94A3B8", size=14))
        else:
            self.input_llm_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_llm_key.setIcon(get_symbol_icon("visibility", color="#64748B" if ThemeManager.get_instance().is_light() else "#94A3B8", size=14))

    def _preview_tts(self):
        voice = self.combo_voice_meeting.currentData() or "zh-CN-YunxiNeural"
        text = "您好，这是 DeskEcho 的当前语音播报试听，知识库已准备就绪。"
        import threading
        import asyncio
        import edge_tts

        def _worker():
            try:
                temp_wav = Config.TEMP_DIR / "preview_tts.mp3"
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                communicate = edge_tts.Communicate(text, voice)
                loop.run_until_complete(communicate.save(str(temp_wav)))
                loop.close()
                QMetaObject.invokeMethod(self, lambda: self.play_tts_audio(str(temp_wav)), Qt.ConnectionType.QueuedConnection)
            except Exception as e:
                print(f"[PreviewTTS] 试听失败: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def _save_all_settings(self):
        updates = {}
        # LLM
        new_llm_key = self.input_llm_key.text().strip()
        if new_llm_key and not new_llm_key.startswith("••••"):
            updates["OPENAI_API_KEY"] = new_llm_key
        updates["OPENAI_BASE_URL"] = self.input_llm_url.text().strip()
        updates["LLM_MODEL"] = self.input_llm_model.text().strip()

        # TTS
        updates["ENABLE_TTS"] = "true" if self.chk_enable_tts.isChecked() else "false"
        updates["TTS_PROVIDER"] = "edge-tts" if "edge-tts" in self.combo_tts_provider.currentText() else "volcengine"
        updates["TTS_VOICE_MEETING"] = self.combo_voice_meeting.currentData() or "zh-CN-YunxiNeural"
        updates["TTS_VOICE_GENERAL"] = self.combo_voice_general.currentData() or "zh-CN-XiaoxiaoNeural"
        updates["TTS_VOICE_INSTRUCTION"] = self.combo_voice_instruction.currentData() or "zh-CN-YunjianNeural"
        updates["TTS_VOICE"] = updates["TTS_VOICE_MEETING"]

        # ASR
        updates["ASR_PROVIDER"] = "volcengine" if "volcengine" in self.combo_asr_provider.currentText() else "dashscope"
        updates["VOLC_APPID"] = self.input_volc_appid.text().strip()
        new_volc_token = self.input_volc_token.text().strip()
        if new_volc_token and not new_volc_token.startswith("••••"):
            updates["VOLC_ACCESS_TOKEN"] = new_volc_token
        updates["VOLC_RESOURCE_ID"] = self.input_volc_resource.text().strip()

        # Hotkey
        hotkey_val = self.combo_intercom_key.currentData() or "Alt_R"
        updates["INTERCOM_KEY"] = hotkey_val

        success = Config.save_settings(updates)
        if success:
            self.settings_status_lbl.setText("配置已成功保存并立即生效")
            self.settings_status_lbl.setStyleSheet("color: #10B981; font-size: 11.5px; font-weight: 600;")
            if hasattr(self, 'hotkey_tag'):
                self.hotkey_tag.setText(f"对讲热键: {Config.get_intercom_display_key()}")
            QTimer.singleShot(4000, lambda: self.settings_status_lbl.setText(""))
        else:
            self.settings_status_lbl.setText("保存配置失败，请检查文件写入权限")
            self.settings_status_lbl.setStyleSheet("color: #EF4444; font-size: 11.5px; font-weight: 600;")


    # ---------------- Page 4: 软件发版与版本更新 ----------------
    def _build_page_update(self, stack: QStackedWidget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(4, 4, 12, 36)
        v_layout.setSpacing(14)

        is_light = ThemeManager.get_instance().is_light()

        # 1. 软件更新控制台主卡片
        self.version_card = QFrame()
        self.version_card.setObjectName("card")
        if is_light:
            self.version_card.setStyleSheet("""
                QFrame#card {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                    padding: 16px;
                }
            """)
        else:
            self.version_card.setStyleSheet("""
                QFrame#card {
                    background-color: #11141D;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    padding: 16px;
                }
            """)
        v_card_layout = QVBoxLayout(self.version_card)
        v_card_layout.setContentsMargins(18, 16, 18, 16)
        v_card_layout.setSpacing(12)

        v_head_layout = QHBoxLayout()
        v_head_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.version_title = QLabel("发版与版本自动更新管理 (GitHub Release 官方发版通道)")
        self.version_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        v_head_layout.addWidget(self.version_title, 1)

        self.ver_badge = QLabel(f"v{APP_VERSION} (当前运行版本)")
        self.ver_badge.setFixedHeight(24)
        self.ver_badge.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        if is_light:
            self.ver_badge.setStyleSheet("color: #0284C7; font-size: 11px; background: rgba(2,132,199,0.10); border: 1px solid rgba(2,132,199,0.3); padding: 0px 8px; border-radius: 5px; font-weight: bold;")
        else:
            self.ver_badge.setStyleSheet("color: #26B0E4; font-size: 11px; background: rgba(38,176,228,0.15); border: 1px solid rgba(38,176,228,0.4); padding: 0px 8px; border-radius: 5px; font-weight: bold;")
        v_head_layout.addWidget(self.ver_badge)

        self.btn_check_update = QPushButton("检查新版本")
        self.btn_check_update.setFixedHeight(32)
        self.btn_check_update.setIconSize(QSize(14, 14))
        self.btn_check_update.setIcon(get_symbol_icon("search", color="#0284C7" if is_light else "#26B0E4", size=14))
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.btn_check_update.setStyleSheet("""
                QPushButton {
                    background: rgba(2, 132, 199, 0.08);
                    color: #0284C7;
                    border: 1px solid rgba(2, 132, 199, 0.35);
                    border-radius: 6px;
                    padding: 0px 16px;
                    font-size: 11.5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #0284C7;
                    color: #FFFFFF;
                }
            """)
        else:
            self.btn_check_update.setStyleSheet("""
                QPushButton {
                    background: rgba(38, 176, 228, 0.22);
                    color: #26B0E4;
                    border: 1px solid rgba(38, 176, 228, 0.5);
                    border-radius: 6px;
                    padding: 0px 16px;
                    font-size: 11.5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #26B0E4;
                    color: #FFFFFF;
                }
            """)
        self.btn_check_update.clicked.connect(self._manual_check_update)
        v_head_layout.addWidget(self.btn_check_update)

        self.btn_restart_app = QPushButton("立即重启客户端")
        self.btn_restart_app.setFixedHeight(32)
        self.btn_restart_app.setIconSize(QSize(14, 14))
        self.btn_restart_app.setIcon(get_symbol_icon("rocket_launch", color="#FFFFFF", size=14))
        self.btn_restart_app.setVisible(False)
        self.btn_restart_app.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restart_app.setStyleSheet("""
            QPushButton {
                background: #10B981;
                color: #FFFFFF;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 0px 16px;
                font-size: 11.5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #059669;
            }
        """)
        self.btn_restart_app.clicked.connect(self._restart_app)
        v_head_layout.addWidget(self.btn_restart_app)

        self.btn_cancel_restart = QPushButton("暂缓重启")
        self.btn_cancel_restart.setFixedHeight(32)
        self.btn_cancel_restart.setVisible(False)
        self.btn_cancel_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_light:
            self.btn_cancel_restart.setStyleSheet("""
                QPushButton {
                    background: #F1F5F9;
                    color: #64748B;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 0px 14px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #E2E8F0;
                    color: #0F172A;
                }
            """)
        else:
            self.btn_cancel_restart.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 0px 14px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                    color: #FFFFFF;
                }
            """)
        self.btn_cancel_restart.clicked.connect(self._cancel_restart_countdown)
        v_head_layout.addWidget(self.btn_cancel_restart)

        v_card_layout.addLayout(v_head_layout)

        self.update_info_lbl = QLabel(f"当前构建日期：{RELEASE_DATE} · 采用 GitHub Releases 官方云端发版通道，客户端已开启后台静默自检。")
        if is_light:
            self.update_info_lbl.setStyleSheet("color: #334155; font-size: 12px; line-height: 1.6; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px;")
        else:
            self.update_info_lbl.setStyleSheet("color: #CBD5E1; font-size: 12px; line-height: 1.6; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px 14px;")
        self.update_info_lbl.setWordWrap(True)
        v_card_layout.addWidget(self.update_info_lbl)

        v_layout.addWidget(self.version_card)

        # 2. 发版规格与自动化通道机制卡片
        self.spec_card = QFrame()
        self.spec_card.setObjectName("card")
        if is_light:
            self.spec_card.setStyleSheet("QFrame#card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; }")
        else:
            self.spec_card.setStyleSheet("QFrame#card { background-color: #11141D; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; }")
        s_layout = QVBoxLayout(self.spec_card)
        s_layout.setContentsMargins(18, 16, 18, 16)
        s_layout.setSpacing(10)

        self.spec_title = QLabel("发版规格与自动化通道机制")
        self.spec_title.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        s_layout.addWidget(self.spec_title)

        self.spec_desc = QLabel(
            "• 发版标准：DeskEcho 后续版本统一以单一 Windows 可执行程序 (DeskEcho.exe) 在 GitHub Releases 官方页面正规发版。\n"
            "• 客户端自愈：后台静默轮询 GitHub Releases，当检测到最新发版推送时，自动下载并在 3 秒内自动重启生效。\n"
            "• 数据安全隔离：自动更新全程保留本地密钥 (.env)、本地会议知识库 (omni_data/records.db) 与向量索引，无感平滑升级。"
        )
        self.spec_desc.setStyleSheet(f"color: {'#475569' if is_light else '#94A3B8'}; font-size: 11.5px; line-height: 1.7;")
        self.spec_desc.setWordWrap(True)
        s_layout.addWidget(self.spec_desc)
        v_layout.addWidget(self.spec_card)

        v_layout.addStretch()
        scroll.setWidget(container)
        stack.addWidget(scroll)

    def _manual_check_update(self):
        self.btn_check_update.setEnabled(False)
        self.update_info_lbl.setText("正在连接 GitHub Releases 官方接口检查最新版本...")

        self.update_worker = AutoUpdateWorker(current_version=APP_VERSION, auto_apply=True, parent=self)
        self.update_worker.update_detected.connect(self._on_update_detected)
        self.update_worker.update_progress.connect(lambda msg: self.update_info_lbl.setText(f"{msg}"))
        self.update_worker.update_finished.connect(self._on_update_finished)
        self.update_worker.update_failed.connect(self._on_update_failed)
        self.update_worker.start()

    def _on_update_detected(self, info: dict):
        new_v = info.get("version", "")
        self.ver_badge.setText(f"发现新版 v{new_v}")
        self.ver_badge.setStyleSheet("color: #F59E0B; font-size: 11px; background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.4); padding: 3px 8px; border-radius: 5px; font-weight: bold;")
        self.update_info_lbl.setText(f"发现新版本 DeskEcho v{new_v}！正在为您全自动下载并应用更新...")

    def _on_update_finished(self, new_v: str, info: dict):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("检查更新")
        self.ver_badge.setText(f"v{new_v} (已就绪)")
        self.ver_badge.setStyleSheet("color: #10B981; font-size: 11px; background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 5px; font-weight: bold;")
        self.btn_restart_app.setVisible(True)
        self.btn_cancel_restart.setVisible(True)
        
        changelog_str = "；".join(info.get("changelog", [])[:3])
        self.search_status_lbl.setText(f"已自动升级至 v{new_v}，即将重启")

        # 启动 3 秒自动重启倒计时
        self._countdown_seconds = 3
        self.update_info_lbl.setText(
            f"升级成功！DeskEcho 已自动更新至 v{new_v}。\n"
            f"更新内容：{changelog_str}\n"
            f"收到最新版本推送，客户端将在 {self._countdown_seconds} 秒后自动重启生效..."
        )
        self.btn_restart_app.setText(f"立即重启 ({self._countdown_seconds}s)")

        if hasattr(self, "_countdown_timer") and self._countdown_timer.isActive():
            self._countdown_timer.stop()
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)

        def _tick():
            self._countdown_seconds -= 1
            if self._countdown_seconds <= 0:
                self._countdown_timer.stop()
                self._restart_app()
            else:
                self.btn_restart_app.setText(f"立即重启 ({self._countdown_seconds}s)")
                self.update_info_lbl.setText(
                    f"升级成功！DeskEcho 已自动更新至 v{new_v}。\n"
                    f"更新内容：{changelog_str}\n"
                    f"收到最新版本推送，客户端将在 {self._countdown_seconds} 秒后自动重启生效..."
                )

        self._countdown_timer.timeout.connect(_tick)
        self._countdown_timer.start()

    def _cancel_restart_countdown(self):
        if hasattr(self, "_countdown_timer") and self._countdown_timer.isActive():
            self._countdown_timer.stop()
        self.btn_cancel_restart.setVisible(False)
        self.btn_restart_app.setText("立即重启客户端")
        self.update_info_lbl.setText("已取消自动重启。您可以随时点击【立即重启客户端】使新版本生效。")

    def _on_update_failed(self, err_msg: str):
        self.btn_check_update.setEnabled(True)
        self.update_info_lbl.setText(f"当前已是最新版本 (v{APP_VERSION})，或远端暂无更高发布版本。")
        self.search_status_lbl.setText("已是最新版本")
        QTimer.singleShot(3000, lambda: self.search_status_lbl.setText(""))

    def _restart_app(self):
        checker = UpdateChecker()
        checker.restart_app()

    # ---------------- 定时与刷新逻辑 ----------------
    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(8000)
        self.refresh_timer.timeout.connect(self.refresh_records)
        self.refresh_timer.start()

        self.debug_ipc_timer = QTimer(self)
        self.debug_ipc_timer.setInterval(1000)
        self.debug_ipc_timer.timeout.connect(self._check_debug_trigger)
        self.debug_ipc_timer.start()

    def _check_debug_trigger(self):
        try:
            trigger_file = Path("C:/DeskEcho/trigger_action.json")
            if not trigger_file.exists():
                return
            content = json.loads(trigger_file.read_text(encoding='utf-8'))
            action = content.get("action")
            out_img = content.get("output_path", "C:/DeskEcho/real_window.png")

            if action == "inspect_page0":
                self._switch_nav(0)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                pix = self.grab()
                pix.save(out_img)
                result = {"status": "success", "page": 0, "image_saved": out_img}
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action == "set_theme":
                target_t = content.get("theme", "light")
                ThemeManager.get_instance().set_theme(ThemeType.LIGHT if target_t == "light" else ThemeType.DARK)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                pix = self.grab()
                pix.save(out_img)
                result = {"status": "success", "theme": target_t, "image_saved": out_img}
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action.startswith("switch_page_"):
                page_idx = int(action.split("_")[-1])
                self._switch_nav(page_idx)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                pix = self.grab()
                pix.save(out_img)
                result = {"status": "success", "page": page_idx, "image_saved": out_img}
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action == "test_dialog":
                from ui.components.modern_dialog import ModernDialog
                from PyQt6.QtCore import QTimer
                dlg = ModernDialog(
                    parent=self,
                    title="确定彻底销毁所选记忆？",
                    message="操作后将从知识库中永久物理删除该记录，不可撤销恢复。",
                    detail="切片时间: 2026-10-29 14:30:00\n核心议题: 研发效能与跨域协同机制\n研判原因: 闲聊及无实质决议碎片",
                    dialog_type="danger",
                    confirm_text="彻底销毁",
                    cancel_text="放弃操作"
                )
                def _do_cap():
                    dlg_pix = dlg.grab()
                    dlg_pix.save(out_img)
                    dlg.accept()
                QTimer.singleShot(300, _do_cap)
                dlg.exec()
                result = {"status": "success", "image_saved": out_img}
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action == "clear_session":
                self._switch_nav(0)
                self.clear_answer_session()
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                pix = self.grab()
                pix.save(out_img)
                result = {"status": "success", "image_saved": out_img}
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action == "test_instruction":
                self._switch_nav(0)
                from core.instruction_handler import InstructionHandler
                h = InstructionHandler()
                query = content.get("query", "改进一下：把设置页面的文字间距再调宽一点")
                res = h.handle_instruction(query)
                self.display_answer(
                    markdown_text=res["answer"],
                    audio_path="",
                    is_followup=False,
                    focal_topic=res.get("focal_topic", "需求工单"),
                    response_mode="INSTRUCTION"
                )
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                pix = self.grab()
                pix.save(out_img)
                result = {
                    "status": "success",
                    "task_id": res.get("task_id"),
                    "focal_topic": res.get("focal_topic"),
                    "image_saved": out_img
                }
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action == "test_query":
                self._switch_nav(0)
                query = content.get("query", "")
                self.query_input.setText(query)
                self.query_submitted.emit(query)
                result = {
                    "status": "submitted",
                    "query": query
                }
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action == "capture_window":
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                pix = self.grab()
                pix.save(out_img)
                ans_text = self.answer_browser.toPlainText()
                result = {
                    "status": "success",
                    "answer_snippet": ans_text[:200],
                    "is_speaking": getattr(self, "is_speaking", False),
                    "image_saved": out_img
                }
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action == "test_non_intrusive_update":
                # 切换到切片库
                self._switch_nav(1)
                self._switch_mem_mode("normal")
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                # 模拟操作员正在阅读过往切片 (选中第 2 项，滚轮下移)
                if self.mem_list.count() > 2:
                    self.mem_list.setCurrentRow(2)
                    self._on_mem_item_selected(2)
                    self.mem_list.verticalScrollBar().setValue(120)
                QApplication.processEvents()
                # 模拟后台到达新切片 (插入假变更并触发 refresh_records)
                self.cached_records = list(self.cached_records)[:-1] if self.cached_records else []
                self.refresh_records()
                QApplication.processEvents()
                pix = self.grab()
                pix.save(out_img)
                result = {
                    "status": "success",
                    "pill_visible": self.new_slice_pill.isVisible(),
                    "pill_text": self.new_slice_pill.text(),
                    "current_row": self.mem_list.currentRow(),
                    "scroll_value": self.mem_list.verticalScrollBar().value(),
                    "image_saved": out_img
                }
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
                return

            if action == "inspect_trash":
                # 切换到会议记忆切片库 (Page 1)
                self._switch_nav(1)
                # 切换到或许没用分类
                self._switch_mem_mode("trash")
                # 确保界面布局渲染完成
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                if self.mem_list.count() > 0:
                    self.mem_list.setCurrentRow(0)
                    self._on_mem_item_selected(0)
                QApplication.processEvents()

                # 截取主窗口真实渲染像素
                pix = self.grab()
                pix.save(out_img)

                # 收集每一项详细渲染尺寸与文字信息
                items_info = []
                for i in range(min(10, self.mem_list.count())):
                    it = self.mem_list.item(i)
                    w = self.mem_list.itemWidget(it)
                    rec = it.data(Qt.ItemDataRole.UserRole) if it else {}
                    items_info.append({
                        "row": i,
                        "text": it.text() if it else "",
                        "time": rec.get("start_time"),
                        "reason": rec.get("trash_reason"),
                        "summary_snippet": rec.get("summary", "")[:90],
                    })

                result = {
                    "status": "success",
                    "mode": self.current_mem_mode,
                    "total_items": self.mem_list.count(),
                    "items": items_info,
                    "image_saved": out_img
                }
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                trigger_file.unlink()
        except Exception as e:
            try:
                Path("C:/DeskEcho/action_result.json").write_text(json.dumps({"status": "error", "error": str(e)}), encoding='utf-8')
                if trigger_file.exists():
                    trigger_file.unlink()
            except Exception:
                pass

    def refresh_records(self):
        try:
            records = self.store.query_recent(limit=200)

            # 比对数据库记录指纹 (ID、开始时间、纪要及有用标记)，判断数据库切片是否发生新增、删除或变更
            old_keys = [(r.get("id"), r.get("start_time"), r.get("summary"), r.get("is_useful")) for r in getattr(self, "cached_records", [])]
            new_keys = [(r.get("id"), r.get("start_time"), r.get("summary"), r.get("is_useful")) for r in records]
            data_changed = (old_keys != new_keys)

            normal_recs = []
            trash_recs = []
            for rec in records:
                summ = rec.get("summary", "")
                raw = rec.get("raw_text", "")
                is_user_useful = (rec.get("is_useful") == 1)
                if is_user_useful:
                    is_low = False
                    reason = "用户手动标记为有用资产"
                else:
                    is_low, reason = assess_slice_utility(summ, raw)
                rec_copy = dict(rec)
                rec_copy["is_low_utility"] = is_low
                rec_copy["trash_reason"] = reason
                if is_low:
                    trash_recs.append(rec_copy)
                else:
                    normal_recs.append(rec_copy)

            self.cached_records = records
            self.cached_normal_records = normal_recs
            self.cached_trash_records = trash_recs

            if hasattr(self, 'btn_mem_normal'):
                self.btn_mem_normal.setText(f"正式会议记忆 ({len(normal_recs)})")
            if hasattr(self, 'btn_mem_trash'):
                self.btn_mem_trash.setText(f"或许没用 ({len(trash_recs)})")
            if hasattr(self, 'sub_btn_memory'):
                self.sub_btn_memory.setText(f"会议记忆库 ({len(normal_recs)})")

            # 刷新首屏“今日已新增 X 段切片”徽章
            self._update_today_slice_badge()

            # 智能防打断机制：仅当数据切实变动时响应
            if data_changed:
                is_on_mem_page = (self.stack.currentIndex() == 1)
                is_scrolled_down = (self.mem_list.verticalScrollBar().value() > 20)
                is_inspecting_history = (self.mem_list.currentRow() > 0)
                is_searching = bool(hasattr(self, "mem_search_input") and self.mem_search_input.text().strip())

                # 判断操作员是否正在查看过往切片或搜索历史，若是则绝不打断
                user_is_busy_reading = is_on_mem_page and (is_scrolled_down or is_inspecting_history or is_searching)

                if user_is_busy_reading:
                    self._has_pending_update = True
                    if hasattr(self, "new_slice_pill"):
                        self.new_slice_pill.setText("收到新归档会议记忆 · 点击置顶查看")
                        self.new_slice_pill.setVisible(True)
                else:
                    self._has_pending_update = False
                    if hasattr(self, "new_slice_pill"):
                        self.new_slice_pill.setVisible(False)
                    self._render_mem_list(preserve_selection=True)
                    if hasattr(self, "refresh_roster"):
                        self.refresh_roster()

        except Exception as e:
            print(f"[MainWindow] 刷新记录失败: {e}")

    def _update_today_slice_badge(self):
        """计算今日录制切片数量并更新首屏胶囊徽章"""
        if not hasattr(self, 'today_slice_num'):
            return
        try:
            today_count = self.store.get_today_count()
        except Exception:
            today_count = 0
        self.today_slice_num.setText(str(today_count))

    def _update_today_slice_badge_style(self, is_light: bool):
        """为今日新增切片胶囊渲染高辨识度且克制的视觉包裹效果"""
        if not hasattr(self, 'today_slice_badge'):
            return

        if is_light:
            self.today_slice_badge.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.today_slice_icon.setPixmap(get_symbol_pixmap("auto_awesome", color="#0284C7", size=13))
            self.today_slice_lbl.setStyleSheet("color: #475569; font-size: 11px; font-weight: 500; border: none; background: transparent;")
            self.today_slice_num.setStyleSheet("""
                QLabel {
                    background-color: rgba(2, 132, 199, 0.12);
                    color: #0284C7;
                    border: 1px solid rgba(2, 132, 199, 0.28);
                    border-radius: 9px;
                    padding: 0px 7px;
                    font-size: 11px;
                    font-weight: 700;
                    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                }
            """)
            self.today_slice_suffix.setStyleSheet("color: #475569; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        else:
            self.today_slice_badge.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.today_slice_icon.setPixmap(get_symbol_pixmap("auto_awesome", color="#38BDF8", size=13))
            self.today_slice_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500; border: none; background: transparent;")
            self.today_slice_num.setStyleSheet("""
                QLabel {
                    background-color: rgba(56, 189, 248, 0.18);
                    color: #38BDF8;
                    border: 1px solid rgba(56, 189, 248, 0.35);
                    border-radius: 9px;
                    padding: 0px 7px;
                    font-size: 11px;
                    font-weight: 700;
                    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                }
            """)
            self.today_slice_suffix.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500; border: none; background: transparent;")

    def _render_mem_list(self, preserve_selection: bool = True):
        # 若搜索框当前有关键词，转入搜索渲染并保持选中
        if hasattr(self, "mem_search_input") and self.mem_search_input.text().strip():
            self._search_memory_slices(preserve_selection=preserve_selection)
            return

        target_records = self.cached_trash_records if self.current_mem_mode == "trash" else self.cached_normal_records

        # 兼容备用 dummy slice_list
        if hasattr(self, "slice_list"):
            self.slice_list.clear()

        # 记录当前已选切片 ID 及滚动条位置
        selected_id = None
        if preserve_selection and hasattr(self, "current_selected_record") and self.current_selected_record:
            selected_id = self.current_selected_record.get("id")

        list_scroll = self.mem_list.verticalScrollBar().value()
        detail_scroll = self.mem_detail_browser.verticalScrollBar().value()

        # 暂时阻塞列表信号，防止 clear 及循环 addItem 时误发 currentRowChanged 重置详情视口
        self.mem_list.blockSignals(True)
        self.mem_list.clear()

        if not target_records:
            self.mem_list.blockSignals(False)
            empty_msg = "暂无低价值次要记忆，会议记忆库非常健康！" if self.current_mem_mode == "trash" else "暂无沉淀正式切片数据"
            empty_item = QListWidgetItem(empty_msg)
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.mem_list.addItem(empty_item)
            self.mem_detail_browser.setHtml(f"<p style='color:#64748B; text-align:center; padding-top:120px;'>{empty_msg}</p>")
            if hasattr(self, "trash_detail_action_bar"):
                self.trash_detail_action_bar.setVisible(False)
            self.current_selected_record = None
            return

        target_row_to_select = -1
        for idx, rec in enumerate(target_records):
            time_str = rec.get("start_time", "")
            summary = rec.get("summary", "")
            first_line = summary.split("\n")[0] if summary else "常驻录音切片"
            first_line = re.sub(r'^[\s\d\.\-、*#]*(?:核心议题|议题|Topic|【核心议题】|主题)(?:[（\(].*?[）\)])?[：:\s]*', '', first_line).strip()
            if not first_line:
                first_line = "常规会议沟通讨论"

            clean_topic = first_line[:32] + "..." if len(first_line) > 32 else first_line
            if self.current_mem_mode == "trash":
                item = QListWidgetItem(f"{time_str}\n   {clean_topic}")
                reason = rec.get("trash_reason", "次要碎片")
                item.setToolTip(f"【次要记忆】: {time_str}\n【AI 研判理由】: {reason}\n{first_line}")
                item.setData(Qt.ItemDataRole.UserRole, rec)
                self.mem_list.addItem(item)
            else:
                item = QListWidgetItem(f"{time_str}\n   {clean_topic}")
                item.setToolTip(f"{time_str}\n{first_line}")
                item.setData(Qt.ItemDataRole.UserRole, rec)
                self.mem_list.addItem(item)

            if selected_id and rec.get("id") == selected_id:
                target_row_to_select = idx

        self.mem_list.blockSignals(False)

        if target_row_to_select >= 0:
            # 成功找回此前选中的切片：静默恢复选中并维持滚动位置，绝不重新调用 setHtml 导致详情重置滚动
            self.mem_list.blockSignals(True)
            self.mem_list.setCurrentRow(target_row_to_select)
            self.mem_list.blockSignals(False)
            self.mem_list.verticalScrollBar().setValue(list_scroll)
            self.mem_detail_browser.verticalScrollBar().setValue(detail_scroll)
        else:
            # 切换 Tab 或原切片被清理：选中第一项
            if self.mem_list.count() > 0:
                self.mem_list.setCurrentRow(0)
            else:
                self.current_selected_record = None

    def _on_slice_clicked(self, item: QListWidgetItem):
        rec = item.data(Qt.ItemDataRole.UserRole)
        if rec:
            self._render_record_to_detail(rec, self.answer_browser)

    def _on_mem_item_selected(self, row: int):
        if row < 0 or row >= self.mem_list.count():
            self.current_selected_record = None
            if hasattr(self, "trash_detail_action_bar"):
                self.trash_detail_action_bar.setVisible(False)
            return

        item = self.mem_list.item(row)
        rec = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not rec:
            self.current_selected_record = None
            if hasattr(self, "trash_detail_action_bar"):
                self.trash_detail_action_bar.setVisible(False)
            return

        # 若已经是当前选中的切片，避免重复 setHtml 导致详情窗口滚动条跳顶
        if self.current_selected_record and self.current_selected_record.get("id") == rec.get("id"):
            return

        self.current_selected_record = rec
        self._render_record_to_detail(rec, self.mem_detail_browser)

        if self.current_mem_mode == "trash":
            reason = rec.get("trash_reason", "无实质性决策且无落地待办推进")
            self.trash_reason_lbl.setText(f"AI 研判理由：{reason}")
            self.trash_detail_action_bar.setVisible(True)
        else:
            self.trash_detail_action_bar.setVisible(False)

    def _render_record_to_detail(self, rec: dict, browser: QTextBrowser):
        start_t = rec.get("start_time", "")
        end_t = rec.get("end_time", "")
        summary = rec.get("summary", "")
        summary = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]', '', summary)
        raw_text = rec.get("raw_text", "")
        raw_text = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]', '', raw_text)
        is_trash = rec.get("is_low_utility", False)
        reason = rec.get("trash_reason", "")
        is_light = ThemeManager.get_instance().is_light()

        heading_c = "#0F172A" if is_light else "#F8FAFC"
        box_bg = "#F8FAFC" if is_light else "#0A0C10"
        box_border = "#E2E8F0" if is_light else "rgba(255,255,255,0.06)"
        summary_c = "#0F172A" if is_light else "#CBD5E1"
        raw_c = "#475569" if is_light else "#94A3B8"
        time_text_c = "#0F172A" if is_light else "#FFFFFF"
        slice_bg = "rgba(2, 132, 199, 0.08)" if is_light else "rgba(19, 69, 157, 0.22)"
        slice_border = "#0284C7" if is_light else "#26B0E4"

        trash_badge_html = f"""
        <div style="background-color: {box_bg}; border: 1px solid {box_border}; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px;">
            <span style="color: {'#475569' if is_light else '#94A3B8'}; font-weight: 600; font-size: 11px;">次要记忆归档 · 诊断理由：</span>
            <span style="color: {'#64748B' if is_light else '#CBD5E1'}; font-size: 11.5px;">{reason}</span>
        </div>
        """ if is_trash else ""

        detail_html = f"""
        <div style="font-family: -apple-system, 'Segoe UI', sans-serif; line-height: 1.6;">
            {trash_badge_html}
            <div style="background-color: {box_bg}; border: 1px solid {box_border}; padding: 8px 12px; border-radius: 6px; margin-bottom: 14px;">
                <span style="color: {'#64748B' if is_light else '#94A3B8'}; font-size: 11px; font-weight: 600;">会议记忆区间：</span>
                <span style="color: {heading_c}; font-size: 12px; font-weight: 600;">{start_t} 至 {end_t}</span>
            </div>

            <div style="color: {heading_c}; font-size: 13.5px; font-weight: bold; margin-bottom: 6px;">结构化纪要提取</div>
            <div style="background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 8px; padding: 12px; color: {summary_c}; font-size: 12px; white-space: pre-wrap; margin-bottom: 14px; line-height: 1.6;">
{summary}
            </div>

            <div style="color: {heading_c}; font-size: 13.5px; font-weight: bold; margin-bottom: 6px;">原始语音对话转录</div>
            <div style="background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 8px; padding: 12px; color: {raw_c}; font-size: 12px; line-height: 1.5; white-space: pre-wrap;">
{raw_text}
            </div>
        </div>
        """
        browser.setHtml(detail_html)

    def _restore_slice_useful(self, rec: dict):
        """将次要记忆恢复为正式切片资产 (纠正 AI 误判)"""
        if not rec:
            return
        sid = rec.get("id", "")
        time_str = rec.get("start_time", "")
        if not sid:
            return

        ok = ModernDialog.confirm_action(
            self,
            title="恢复为正式切片",
            message="确定将此切片恢复为【正式会议资产】吗？",
            detail=f"切片标识: {sid}\n会议时间: {time_str}\n\n恢复后，该切片将移入【正式会议记忆】库，受到防误删保护，并可在后续对讲检索中作为核心证据参与计算。",
            confirm_text="恢复为正式资产"
        )
        if ok:
            success = self.store.set_slice_useful(sid, is_useful=True)
            if success:
                self.search_status_lbl.setText("✓ 已恢复为正式会议记忆资产")
                self.current_selected_record = None
                self.refresh_records()
            else:
                ModernDialog.show_warning(self, "操作失败", f"更新切片 {sid} 状态时出错。")

    def _delete_current_selected_slice(self):
        """选择性删除当前选中的次要记忆 (仅在'或许没用'生效)"""
        if self.current_mem_mode != "trash" or not self.current_selected_record:
            return
        rec = self.current_selected_record
        sid = rec.get("id", "")
        time_str = rec.get("start_time", "")
        reason = rec.get("trash_reason", "次要碎片")

        ok = ModernDialog.confirm_danger(
            self,
            title="确认彻底删除次要记忆",
            message="确定彻底删除此段次要记忆吗？",
            detail=f"切片标识: {sid}\n会议时间: {time_str}\n研判原因: {reason}\n\n该操作将同步从 SQLite 数据库及 ChromaDB 向量集合中彻底清除，不可恢复。",
            confirm_text="彻底删除"
        )
        if ok:
            success = self.store.delete_slice(sid)
            if success:
                self.search_status_lbl.setText("✓ 次要记忆已删除")
                self.current_selected_record = None
                self.refresh_records()
            else:
                ModernDialog.show_warning(self, "删除失败", f"删除记忆 {sid} 遇到错误，请检查日志。")

    def _clean_all_trash_slices(self):
        """一键清空所有次要记忆 (仅在'或许没用'生效)"""
        if self.current_mem_mode != "trash" or not self.cached_trash_records:
            ModernDialog.show_info(self, "暂无数据", "当前没有识别出的次要记忆。")
            return

        trash_ids = [r.get("id") for r in self.cached_trash_records if r.get("id")]
        count = len(trash_ids)
        ok = ModernDialog.confirm_danger(
            self,
            title="一键清空次要记忆",
            message=f"确定要一键清理当前识别出的全部 {count} 段次要记忆吗？",
            detail="这些切片经 AI 研判为闲聊、试音或无决议/无待办碎片。\n删除后将彻底释放空间并优化检索效率，操作不可逆！",
            confirm_text=f"一键清空 ({count})"
        )
        if ok:
            deleted_count = self.store.delete_slices(trash_ids)
            self.search_status_lbl.setText(f"✓ 已一键清理 {deleted_count} 段次要记忆")
            self.current_selected_record = None
            self.refresh_records()

    def _show_mem_list_context_menu(self, pos):
        """切片列表右键菜单 (仅在'或许没用'显示恢复与删除功能，正常切片无删除)"""
        if self.current_mem_mode != "trash":
            return
        item = self.mem_list.itemAt(pos)
        if not item:
            return
        rec = item.data(Qt.ItemDataRole.UserRole)
        if not rec:
            return

        is_light = ThemeManager.get_instance().is_light()
        menu = QMenu(self)
        if is_light:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    color: #0F172A;
                    font-size: 11px;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background-color: #F1F5F9;
                    color: #0284C7;
                    border-radius: 4px;
                }
            """)
        else:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #121724;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    color: #E2E8F0;
                    font-size: 11px;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background-color: #1E293B;
                    color: #FFFFFF;
                    border-radius: 4px;
                }
            """)
        restore_action = menu.addAction("判定有用并恢复 (移回正式资产)")
        restore_action.setIcon(get_symbol_icon("check_circle", color="#16A34A" if is_light else "#8AC657", size=13))
        del_action = menu.addAction("确认删除此段次要记忆")
        del_action.setIcon(get_symbol_icon("delete_forever", color="#DC2626" if is_light else "#EF4444", size=13))
        action = menu.exec(self.mem_list.mapToGlobal(pos))
        if action == restore_action:
            self._restore_slice_useful(rec)
        elif action == del_action:
            self._delete_current_selected_slice()

    def _search_memory_slices(self, preserve_selection: bool = False):
        kw = self.mem_search_input.text().strip()
        if not kw:
            self._render_mem_list(preserve_selection=preserve_selection)
            return

        target_records = self.cached_trash_records if self.current_mem_mode == "trash" else self.cached_normal_records
        filtered = [
            r for r in target_records
            if kw.lower() in (r.get("summary", "") + " " + r.get("raw_text", "")).lower()
        ]

        selected_id = None
        if preserve_selection and hasattr(self, "current_selected_record") and self.current_selected_record:
            selected_id = self.current_selected_record.get("id")

        list_scroll = self.mem_list.verticalScrollBar().value()
        detail_scroll = self.mem_detail_browser.verticalScrollBar().value()

        self.mem_list.blockSignals(True)
        self.mem_list.clear()

        target_row_to_select = -1
        for idx, rec in enumerate(filtered):
            time_str = rec.get("start_time", "")
            summary = rec.get("summary", "")
            first_line = summary.split("\n")[0] if summary else "匹配切片"

            clean_topic = first_line[:30] + "..." if len(first_line) > 30 else first_line
            if self.current_mem_mode == "trash":
                item = QListWidgetItem(f"{time_str}\n   {clean_topic}")
                reason = rec.get("trash_reason", "次要碎片")
                item.setToolTip(f"【次要记忆】: {time_str}\n【AI 研判理由】: {reason}\n{first_line}")
                item.setData(Qt.ItemDataRole.UserRole, rec)
                self.mem_list.addItem(item)
            else:
                item = QListWidgetItem(f"{time_str}\n   {clean_topic}")
                item.setData(Qt.ItemDataRole.UserRole, rec)
                self.mem_list.addItem(item)

            if selected_id and rec.get("id") == selected_id:
                target_row_to_select = idx

        self.mem_list.blockSignals(False)

        if filtered:
            if target_row_to_select >= 0:
                self.mem_list.blockSignals(True)
                self.mem_list.setCurrentRow(target_row_to_select)
                self.mem_list.blockSignals(False)
                self.mem_list.verticalScrollBar().setValue(list_scroll)
                self.mem_detail_browser.verticalScrollBar().setValue(detail_scroll)
            else:
                self.mem_list.setCurrentRow(0)
        else:
            self.mem_detail_browser.setHtml(f"<p style='color:#64748B; text-align:center; padding-top:100px;'>在当前分类下未检索到与 <b>“{kw}”</b> 相关的会议切片。</p>")
            if hasattr(self, "trash_detail_action_bar"):
                self.trash_detail_action_bar.setVisible(False)
            self.current_selected_record = None

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
            if hasattr(self, "ans_card") and not getattr(self.answer_browser, '_is_streaming', False):
                self.ans_card.stop_beam()
            if hasattr(self, "intercom_banner") and "播报" in self.intercom_banner.badge_lbl.text():
                self.intercom_banner.set_completed(
                    focal_topic=getattr(self, '_last_focal_topic', ''),
                    is_followup=getattr(self, '_last_is_followup', False),
                    response_mode=getattr(self, '_last_response_mode', 'MEETING')
                )
            self.tts_playback_finished.emit()

    def _on_output_finished(self):
        if hasattr(self, "ans_card") and not self.is_playing():
            self.ans_card.stop_beam()

    def is_playing(self) -> bool:
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def stop_speaking(self) -> bool:
        if hasattr(self, "ans_card"):
            self.ans_card.stop_beam()
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

    def toggle_history_drawer(self):
        """展开或收起左侧边栏的常驻会话历史菜单"""
        if hasattr(self, 'session_menu'):
            self.session_menu.toggle_expanded()

    def _on_history_session_selected(self, session_id: str):
        if self.stack.currentIndex() != 0:
            self._switch_nav(0)
        turns = self.store.get_session_turns(session_id)
        self.answer_browser.load_history_session(turns)
        
        title = "历史话题"
        updated_at = ""
        sessions = self.store.get_all_sessions(limit=100)
        for s in sessions:
            if s["id"] == session_id:
                title = s.get("title", "")
                updated_at = s.get("updated_at", "")
                break

        # 判断会话是否处于有效活跃交互 TTL 窗口内 (默认 600 秒)
        is_active = False
        if updated_at:
            try:
                import datetime
                clean_str = updated_at.replace("T", " ")
                if "." in clean_str:
                    dt = datetime.datetime.strptime(clean_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    dt = datetime.datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                diff_local = abs((datetime.datetime.now() - dt).total_seconds())
                diff_utc = abs((datetime.datetime.utcnow() - dt).total_seconds())
                is_active = (min(diff_local, diff_utc) <= 600.0)
            except Exception:
                is_active = False

        if is_active:
            self.session_switched.emit(session_id)
            self.intercom_banner.set_completed(focal_topic=title, is_followup=True)
            self.search_status_lbl.setText(f"✓ 已载入活跃话题「{title}」，可继续追问")
        else:
            self.new_session_requested.emit()
            self.intercom_banner.set_idle()
            self.search_status_lbl.setText(f"已载入历史会话回顾「{title}」")

        # 3.5 秒后自动消隐提示，绝不永久常驻
        QTimer.singleShot(3500, lambda: self.search_status_lbl.setText(""))

        # 3.5 秒后自动消隐提示，绝不永久常驻
        QTimer.singleShot(3500, lambda: self.search_status_lbl.setText(""))

    def _on_history_session_deleted(self, session_id: str):
        self.clear_answer_session()
        self.search_status_lbl.setText("✓ 历史会话已删除")
        QTimer.singleShot(3000, lambda: self.search_status_lbl.setText(""))

    def _set_ans_card_style(self, mode: str = "MEETING"):
        """根据当前回答来源动态切换解答卡边框：科技青(内部会议) vs 灵动紫(全网通识) vs 琥珀金(敏捷指令)"""
        if not hasattr(self, 'ans_card'):
            return
        is_light = ThemeManager.get_instance().is_light()
        self.ans_card.setStyleSheet(get_ans_card_style(mode, is_light))

    def _build_clean_status_bar(self):
        """构建轻量优雅的程序状态栏 (非系统原生灰框，无浮夸动效，极简高质感)"""
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        sb.setFixedHeight(26)

        is_light = ThemeManager.get_instance().is_light()

        # 左侧：引擎就绪状态
        self.status_engine_widget = QWidget()
        eng_layout = QHBoxLayout(self.status_engine_widget)
        eng_layout.setContentsMargins(8, 0, 8, 0)
        eng_layout.setSpacing(5)
        self.status_engine_icon = QLabel()
        self.status_engine_icon.setPixmap(get_symbol_pixmap("check_circle", color="#16A34A" if is_light else "#10B981", size=13))
        self.status_engine_lbl = QLabel("向量引擎与数据库已就绪")
        eng_layout.addWidget(self.status_engine_icon)
        eng_layout.addWidget(self.status_engine_lbl)
        sb.addWidget(self.status_engine_widget)

        # 右侧 1：热键提示
        self.status_hotkey_widget = QWidget()
        hot_layout = QHBoxLayout(self.status_hotkey_widget)
        hot_layout.setContentsMargins(6, 0, 6, 0)
        hot_layout.setSpacing(4)
        self.status_hotkey_icon = QLabel()
        self.status_hotkey_icon.setPixmap(get_symbol_pixmap("keyboard", color="#475569" if is_light else "#94A3B8", size=13))
        self.status_hotkey_lbl = QLabel(f"长按 [{Config.get_intercom_display_key()}] 随心对讲")
        hot_layout.addWidget(self.status_hotkey_icon)
        hot_layout.addWidget(self.status_hotkey_lbl)
        sb.addPermanentWidget(self.status_hotkey_widget)

        # 右侧 2：企业空间
        self.status_space_widget = QWidget()
        spc_layout = QHBoxLayout(self.status_space_widget)
        spc_layout.setContentsMargins(6, 0, 10, 0)
        spc_layout.setSpacing(4)
        self.status_space_icon = QLabel()
        self.status_space_icon.setPixmap(get_symbol_pixmap("apartment", color="#0284C7" if is_light else "#26B0E4", size=13))
        self.status_space_lbl = QLabel("美好智能 企业常驻空间")
        spc_layout.addWidget(self.status_space_icon)
        spc_layout.addWidget(self.status_space_lbl)
        sb.addPermanentWidget(self.status_space_widget)

    def _update_status_bar_theme(self, is_light: bool):
        sb = self.statusBar()
        if not sb:
            return
        if is_light:
            sb.setStyleSheet("""
                QStatusBar {
                    background-color: #F8FAFC;
                    border-top: 1px solid #E2E8F0;
                    color: #64748B;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
            if hasattr(self, 'status_engine_lbl'):
                self.status_engine_lbl.setStyleSheet("color: #0F766E; font-size: 11px; font-weight: 500;")
                self.status_engine_icon.setPixmap(get_symbol_pixmap("check_circle", color="#16A34A", size=13))
            if hasattr(self, 'status_hotkey_lbl'):
                self.status_hotkey_lbl.setStyleSheet("color: #475569; font-size: 11px;")
                self.status_hotkey_icon.setPixmap(get_symbol_pixmap("keyboard", color="#475569", size=13))
            if hasattr(self, 'status_space_lbl'):
                self.status_space_lbl.setStyleSheet("color: #0284C7; font-size: 11px; font-weight: 600;")
                self.status_space_icon.setPixmap(get_symbol_pixmap("apartment", color="#0284C7", size=13))
        else:
            sb.setStyleSheet("""
                QStatusBar {
                    background-color: #0A0C10;
                    border-top: 1px solid rgba(255, 255, 255, 0.05);
                    color: #64748B;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
            if hasattr(self, 'status_engine_lbl'):
                self.status_engine_lbl.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 500;")
                self.status_engine_icon.setPixmap(get_symbol_pixmap("check_circle", color="#10B981", size=13))
            if hasattr(self, 'status_hotkey_lbl'):
                self.status_hotkey_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
                self.status_hotkey_icon.setPixmap(get_symbol_pixmap("keyboard", color="#94A3B8", size=13))
            if hasattr(self, 'status_space_lbl'):
                self.status_space_lbl.setStyleSheet("color: #26B0E4; font-size: 11px; font-weight: 600;")
                self.status_space_icon.setPixmap(get_symbol_pixmap("apartment", color="#26B0E4", size=13))

    def _on_toggle_theme(self):
        ThemeManager.get_instance().toggle_theme()

    def _apply_current_theme(self):
        tm = ThemeManager.get_instance()
        is_light = tm.is_light()
        colors = tm.get_colors()

        # 1. 全局窗口 QSS
        self.setStyleSheet(tm.get_global_qss())

        # 2. 品牌卡与侧边栏 (通透无多余边框)
        if hasattr(self, 'brand_card'):
            self.brand_card.setStyleSheet("background: transparent; border: none; padding: 0;")
            if is_light:
                self.brand_title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #0F172A; letter-spacing: 0.5px;")
                self.brand_sub_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #0284C7; letter-spacing: 0.5px;")
                if hasattr(self, 'hotkey_tag'):
                    self.hotkey_tag.setStyleSheet("color: #64748B; font-size: 10.5px;")
            else:
                self.brand_title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;")
                self.brand_sub_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #26B0E4; letter-spacing: 0.5px;")
                if hasattr(self, 'hotkey_tag'):
                    self.hotkey_tag.setStyleSheet("color: #64748B; font-size: 10.5px;")

        # 3. 顶部 Top Bar
        if hasattr(self, 'breadcrumb_lbl'):
            self.breadcrumb_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {colors['text_muted']};")

        if hasattr(self, 'theme_btn'):
            self.theme_btn.setFixedSize(30, 30)
            self.theme_btn.setIconSize(QSize(16, 16))
            self.theme_btn.setStyleSheet(get_theme_btn_style(is_light))
            if is_light:
                self.theme_btn.setIcon(get_symbol_icon("dark_mode", color="#475569", size=16))
                self.theme_btn.setToolTip("切换为深色模式 (Dark Mode)")
            else:
                self.theme_btn.setIcon(get_symbol_icon("light_mode", color="#FBBF24", size=16))
                self.theme_btn.setToolTip("切换为浅色模式 (Light Mode)")

        if hasattr(self, 'top_version_btn'):
            self.top_version_btn.setFixedHeight(30)
            self.top_version_btn.setIconSize(QSize(13, 13))
            self.top_version_btn.setStyleSheet(get_top_version_style(is_light))
            self.top_version_btn.setIcon(get_symbol_icon("rocket_launch", color="#0284C7" if is_light else "#38BDF8", size=13))

        # 4. Page 0 控件
        if hasattr(self, 'cmd_card'):
            self.cmd_card.setStyleSheet(get_cmd_card_style(is_light))
        if hasattr(self, 'search_icon_lbl'):
            self.search_icon_lbl.setPixmap(get_symbol_pixmap("search", color="#0284C7" if is_light else "#26B0E4", size=18))
        if hasattr(self, 'query_input'):
            input_color = colors["text_primary"]
            self.query_input.setStyleSheet(f"QLineEdit {{ background: transparent; border: none; font-size: 13px; color: {input_color}; padding: 4px; }}")

        mode = getattr(self, '_last_response_mode', 'MEETING')
        if hasattr(self, 'ans_card'):
            self._set_ans_card_style(mode)
        if hasattr(self, 'ans_title_icon'):
            self.ans_title_icon.setPixmap(get_symbol_pixmap("chat", color="#0284C7" if is_light else "#26B0E4", size=16))
        if hasattr(self, 'ans_title'):
            self.ans_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {colors['text_primary']};")
        if hasattr(self, 'today_slice_badge'):
            self._update_today_slice_badge_style(is_light)
        if hasattr(self, 'copy_btn'):
            self.copy_btn.setIcon(get_symbol_icon("content_copy", color="#64748B" if is_light else "#94A3B8", size=13))
            self.copy_btn.setStyleSheet(f"background: transparent; border: none; color: {colors['text_muted']}; font-size: 11px;")
        if hasattr(self, 'answer_browser'):
            self.answer_browser.setStyleSheet(get_answer_browser_style(is_light))
            if hasattr(self.answer_browser, '_full_text') and self.answer_browser._full_text:
                self.answer_browser._render_combined(self.answer_browser._full_text, is_streaming=False, use_cached_latest=True)
            else:
                self.answer_browser.clear_history()

        if hasattr(self, 'intercom_banner'):
            if "对讲" in self.intercom_banner.badge_lbl.text():
                self.intercom_banner.set_idle()

        # 5. 简约程序状态栏
        self._update_status_bar_theme(is_light)

        # 6. 刷新其他动态组件
        if hasattr(self, 'record_switch'):
            self.record_switch.update()
        if hasattr(self, 'btn_ask'):
            self.btn_ask.update()
        if hasattr(self, 'btn_gear'):
            self._update_gear_button_style(active=(self.stack.currentIndex() in (1, 2, 3, 4)))
        if hasattr(self, 'session_menu'):
            self.session_menu.apply_theme()
            self.session_menu.refresh_sessions()
        self._update_settings_sub_tab_styles(self.stack.currentIndex())

        # 7. Page 1 会议记忆库动态样式
        if hasattr(self, 'mem_header_card'):
            if is_light:
                self.mem_header_card.setStyleSheet("""
                    QFrame#mem_header_card {
                        background-color: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 10px;
                    }
                """)
            else:
                self.mem_header_card.setStyleSheet("""
                    QFrame#mem_header_card {
                        background-color: #11141D;
                        border: 1px solid rgba(255, 255, 255, 0.07);
                        border-radius: 10px;
                    }
                """)
        if hasattr(self, 'mem_search_input'):
            if is_light:
                self.mem_search_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #F8FAFC;
                        border: 1px solid #CBD5E1;
                        border-radius: 8px;
                        padding: 7px 12px;
                        font-size: 12px;
                        color: #0F172A;
                    }
                    QLineEdit:focus {
                        border-color: #0284C7;
                    }
                """)
            else:
                self.mem_search_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #0A0C10;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 8px;
                        padding: 7px 12px;
                        font-size: 12px;
                        color: #FFFFFF;
                    }
                    QLineEdit:focus {
                        border-color: #26B0E4;
                    }
                """)
        if hasattr(self, 'mem_search_btn'):
            self.mem_search_btn.setIcon(get_symbol_icon("search", color="#0284C7" if is_light else "#26B0E4", size=13))
            if is_light:
                self.mem_search_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(2, 132, 199, 0.08);
                        color: #0284C7;
                        border: 1px solid rgba(2, 132, 199, 0.35);
                        border-radius: 8px;
                        padding: 7px 16px;
                        font-size: 12px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #0284C7;
                        color: #FFFFFF;
                    }
                """)
            else:
                self.mem_search_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(19, 69, 157, 0.35);
                        color: #26B0E4;
                        border: 1px solid rgba(38, 176, 228, 0.45);
                        border-radius: 8px;
                        padding: 7px 16px;
                        font-size: 12px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #26B0E4;
                        color: #FFFFFF;
                    }
                """)
        if hasattr(self, 'trash_banner'):
            if is_light:
                self.trash_banner.setStyleSheet("""
                    QFrame#trash_banner {
                        background: #F8FAFC;
                        border: 1px solid #E2E8F0;
                        border-radius: 8px;
                    }
                """)
            else:
                self.trash_banner.setStyleSheet("""
                    QFrame#trash_banner {
                        background: #11141D;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 8px;
                    }
                """)
        if hasattr(self, 'trash_tip_lbl'):
            self.trash_tip_lbl.setStyleSheet(f"color: {'#64748B' if is_light else '#94A3B8'}; font-size: 11px; font-weight: 500;")
        if hasattr(self, 'btn_clean_all_trash'):
            self.btn_clean_all_trash.setIcon(get_symbol_icon("delete_sweep", color="#64748B" if is_light else "#94A3B8", size=13))
            if is_light:
                self.btn_clean_all_trash.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #475569;
                        border: 1px solid #CBD5E1;
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background-color: #FEE2E2;
                        color: #DC2626;
                        border-color: #FCA5A5;
                    }
                """)
            else:
                self.btn_clean_all_trash.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.05);
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.12);
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background-color: rgba(239, 68, 68, 0.2);
                        color: #FCA5A5;
                        border-color: #EF4444;
                    }
                """)
        if hasattr(self, 'mem_list'):
            self.mem_list.setStyleSheet(get_mem_list_style(is_light))
        if hasattr(self, 'mem_detail_browser'):
            self.mem_detail_browser.setStyleSheet(get_mem_detail_style(is_light))
            if hasattr(self, 'current_selected_record') and self.current_selected_record:
                self._render_record_to_detail(self.current_selected_record, self.mem_detail_browser)
        if hasattr(self, 'trash_detail_action_bar'):
            if is_light:
                self.trash_detail_action_bar.setStyleSheet("""
                    QFrame#trash_detail_action_bar {
                        background-color: #F8FAFC;
                        border: 1px solid #E2E8F0;
                        border-radius: 8px;
                    }
                """)
                if hasattr(self, 'trash_reason_lbl'):
                    self.trash_reason_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500;")
            else:
                self.trash_detail_action_bar.setStyleSheet("""
                    QFrame#trash_detail_action_bar {
                        background-color: #11141D;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 8px;
                    }
                """)
                if hasattr(self, 'trash_reason_lbl'):
                    self.trash_reason_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
        if hasattr(self, 'btn_restore_curr_slice'):
            self.btn_restore_curr_slice.setIcon(get_symbol_icon("check_circle", color="#0284C7" if is_light else "#38BDF8", size=13))
            if is_light:
                self.btn_restore_curr_slice.setStyleSheet("""
                    QPushButton {
                        background: #FFFFFF;
                        color: #0284C7;
                        border: 1px solid #CBD5E1;
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background: rgba(2, 132, 199, 0.08);
                        border-color: #0284C7;
                    }
                """)
            else:
                self.btn_restore_curr_slice.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.05);
                        color: #38BDF8;
                        border: 1px solid rgba(255, 255, 255, 0.12);
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background: rgba(56, 189, 248, 0.15);
                        border-color: #38BDF8;
                    }
                """)
        if hasattr(self, 'btn_delete_curr_slice'):
            self.btn_delete_curr_slice.setIcon(get_symbol_icon("delete", color="#64748B" if is_light else "#94A3B8", size=13))
            if is_light:
                self.btn_delete_curr_slice.setStyleSheet("""
                    QPushButton {
                        background: #FFFFFF;
                        color: #64748B;
                        border: 1px solid #CBD5E1;
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background: #FEE2E2;
                        color: #DC2626;
                        border-color: #FCA5A5;
                    }
                """)
            else:
                self.btn_delete_curr_slice.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.05);
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.12);
                        border-radius: 6px;
                        padding: 5px 12px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background: rgba(239, 68, 68, 0.2);
                        color: #FCA5A5;
                        border-color: #EF4444;
                    }
                """)
        if hasattr(self, 'btn_mem_normal'):
            self._update_mem_tab_styles()

        # 8. Page 2: 企业通讯录动态样式
        if hasattr(self, 'roster_search_input'):
            if is_light:
                self.roster_search_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #FFFFFF;
                        border: 1px solid #CBD5E1;
                        border-radius: 8px;
                        color: #0F172A;
                        padding: 7px 14px;
                        font-size: 12px;
                    }
                    QLineEdit:focus {
                        border-color: #0284C7;
                    }
                """)
            else:
                self.roster_search_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #12151F;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 8px;
                        color: #FFFFFF;
                        padding: 7px 14px;
                        font-size: 12px;
                    }
                    QLineEdit:focus {
                        border-color: #26B0E4;
                        background-color: #161A28;
                    }
                """)
        if hasattr(self, 'refresh_roster_btn'):
            self.refresh_roster_btn.setIcon(get_symbol_icon("history", color="#0284C7" if is_light else "#CBD5E1", size=13))
            if is_light:
                self.refresh_roster_btn.setStyleSheet("""
                    QPushButton {
                        background: #FFFFFF;
                        color: #334155;
                        border: 1px solid #CBD5E1;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: #F1F5F9;
                        border-color: #0284C7;
                        color: #0284C7;
                    }
                """)
            else:
                self.refresh_roster_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.05);
                        color: #CBD5E1;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.1);
                        color: #FFFFFF;
                        border-color: #26B0E4;
                    }
                """)
        if hasattr(self, 'departed_toggle_btn'):
            self.departed_toggle_btn.setIcon(get_symbol_icon("apartment", color="#64748B", size=13))
            if is_light:
                self.departed_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F8FAFC;
                        color: #64748B;
                        border: 1px dashed #CBD5E1;
                        border-radius: 8px;
                        padding: 9px;
                        font-size: 11.5px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #F1F5F9;
                        color: #334155;
                        border-color: #94A3B8;
                    }
                """)
            else:
                self.departed_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0D1017;
                        color: #64748B;
                        border: 1px dashed rgba(255, 255, 255, 0.1);
                        border-radius: 8px;
                        padding: 9px;
                        font-size: 11.5px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #121622;
                        color: #94A3B8;
                        border-color: rgba(255, 255, 255, 0.2);
                    }
                """)
        if hasattr(self, 'employee_cards'):
            for card in self.employee_cards:
                card._apply_style(hover=False)

        # 9. Page 3: 引擎配置与系统设置动态样式
        card_style_light = """
            QFrame#settings_card {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#settings_card QLabel {
                color: #334155;
                font-size: 11.5px;
            }
            QFrame#settings_card QCheckBox {
                color: #0F172A;
                font-size: 11.5px;
            }
        """
        card_style_dark = """
            QFrame#settings_card {
                background-color: #11141D;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QFrame#settings_card QLabel {
                color: #CBD5E1;
                font-size: 11.5px;
            }
            QFrame#settings_card QCheckBox {
                color: #F1F5F9;
                font-size: 11.5px;
            }
        """
        for card_attr in ['card_tts', 'card_llm', 'card_asr', 'card_intercom', 'card_ext']:
            if hasattr(self, card_attr):
                getattr(self, card_attr).setStyleSheet(card_style_light if is_light else card_style_dark)

        if hasattr(self, 'settings_page_title'):
            self.settings_page_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        if hasattr(self, 'settings_page_desc'):
            self.settings_page_desc.setStyleSheet(f"font-size: 11.5px; color: {'#64748B' if is_light else '#94A3B8'};")

        # 头部标题与图标主题同步
        card_headers = [
            ('tts_icon', 'volume_up', 'tts_lbl'),
            ('llm_icon', 'psychology', 'llm_lbl'),
            ('asr_icon', 'graphic_eq', 'asr_lbl'),
            ('intercom_icon', 'keyboard', 'intercom_lbl'),
            ('ext_icon', 'extension', 'ext_lbl'),
        ]
        for icon_attr, sym, lbl_attr in card_headers:
            if hasattr(self, icon_attr):
                getattr(self, icon_attr).setPixmap(get_symbol_pixmap(sym, color="#0284C7" if is_light else "#38BDF8", size=16))
            if hasattr(self, lbl_attr):
                getattr(self, lbl_attr).setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")

        if hasattr(self, 'vad_hint_lbl'):
            self.vad_hint_lbl.setStyleSheet(f"color: {'#64748B' if is_light else '#94A3B8'}; font-size: 11.5px;")
        if hasattr(self, 'ext_desc'):
            self.ext_desc.setStyleSheet(f"color: {'#64748B' if is_light else '#94A3B8'}; font-size: 11px;")
        if hasattr(self, 'btn_toggle_llm_key'):
            self.btn_toggle_llm_key.setIcon(get_symbol_icon("visibility", color="#0284C7" if is_light else "#38BDF8", size=14))

        input_style_light = """
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #0284C7;
                background-color: #FFFFFF;
            }
        """
        input_style_dark = """
            QLineEdit {
                background-color: #0A0C10;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #26B0E4;
                background-color: #12151F;
            }
        """
        for inp_attr in ['input_llm_key', 'input_llm_url', 'input_llm_model',
                         'input_volc_appid', 'input_volc_token', 'input_volc_resource']:
            if hasattr(self, inp_attr):
                getattr(self, inp_attr).setStyleSheet(input_style_light if is_light else input_style_dark)

        combo_style = get_modern_combobox_style(is_light)
        for combo_attr in ['combo_tts_provider', 'combo_voice_meeting', 'combo_voice_general',
                          'combo_voice_instruction', 'combo_asr_provider', 'combo_intercom_key']:
            if hasattr(self, combo_attr):
                getattr(self, combo_attr).setStyleSheet(combo_style)

        if hasattr(self, 'btn_save_settings'):
            self.btn_save_settings.setFixedHeight(34)
            self.btn_save_settings.setIconSize(QSize(14, 14))
            self.btn_save_settings.setStyleSheet("""
                QPushButton {
                    background: #0284C7;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 0px 18px;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background: #0369A1;
                }
            """)
        if hasattr(self, 'btn_preview_tts'):
            self.btn_preview_tts.setFixedHeight(32)
            self.btn_preview_tts.setIconSize(QSize(14, 14))
            self.btn_preview_tts.setStyleSheet("""
                QPushButton {
                    background: #F1F5F9;
                    color: #0284C7;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 0px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(2, 132, 199, 0.1);
                    border-color: #0284C7;
                }
            """ if is_light else """
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #38BDF8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 0px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(56, 189, 248, 0.15);
                    border-color: #38BDF8;
                }
            """)
        if hasattr(self, 'ext_boxes'):
            for sbox in self.ext_boxes:
                sbox.setStyleSheet("""
                    QFrame {
                        background: #F8FAFC;
                        border: 1px dashed #CBD5E1;
                        border-radius: 6px;
                    }
                """ if is_light else """
                    QFrame {
                        background: #0A0C10;
                        border: 1px dashed rgba(255, 255, 255, 0.1);
                        border-radius: 6px;
                    }
                """)
        if hasattr(self, 'btn_goto_update'):
            if is_light:
                self.btn_goto_update.setStyleSheet("""
                    QPushButton {
                        background: rgba(2, 132, 199, 0.08);
                        color: #0284C7;
                        border: 1px solid rgba(2, 132, 199, 0.3);
                        border-radius: 5px;
                        padding: 6px 12px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: rgba(2, 132, 199, 0.18);
                    }
                """)
            else:
                self.btn_goto_update.setStyleSheet("""
                    QPushButton {
                        background: rgba(38, 176, 228, 0.12);
                        color: #38BDF8;
                        border: 1px solid rgba(38, 176, 228, 0.3);
                        border-radius: 5px;
                        padding: 6px 12px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: rgba(38, 176, 228, 0.25);
                        color: #FFFFFF;
                    }
                """)

        # 10. Page 4: 软件发版动态样式
        if hasattr(self, 'version_card'):
            if is_light:
                self.version_card.setStyleSheet("""
                    QFrame#card {
                        background-color: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 12px;
                        padding: 16px;
                    }
                """)
            else:
                self.version_card.setStyleSheet("""
                    QFrame#card {
                        background-color: #11141D;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 12px;
                        padding: 16px;
                    }
                """)
        if hasattr(self, 'version_title'):
            self.version_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        if hasattr(self, 'ver_badge'):
            self.ver_badge.setFixedHeight(24)
            self.ver_badge.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.ver_badge.setStyleSheet("color: #0284C7; font-size: 11px; background: rgba(2,132,199,0.10); border: 1px solid rgba(2,132,199,0.3); padding: 0px 8px; border-radius: 5px; font-weight: bold;" if is_light else "color: #26B0E4; font-size: 11px; background: rgba(38,176,228,0.15); border: 1px solid rgba(38,176,228,0.4); padding: 0px 8px; border-radius: 5px; font-weight: bold;")
        if hasattr(self, 'btn_check_update'):
            self.btn_check_update.setFixedHeight(32)
            self.btn_check_update.setIconSize(QSize(14, 14))
            self.btn_check_update.setIcon(get_symbol_icon("search", color="#0284C7" if is_light else "#26B0E4", size=14))
            if is_light:
                self.btn_check_update.setStyleSheet("""
                    QPushButton {
                        background: rgba(2, 132, 199, 0.08);
                        color: #0284C7;
                        border: 1px solid rgba(2, 132, 199, 0.35);
                        border-radius: 6px;
                        padding: 0px 16px;
                        font-size: 11.5px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #0284C7;
                        color: #FFFFFF;
                    }
                """)
            else:
                self.btn_check_update.setStyleSheet("""
                    QPushButton {
                        background: rgba(38, 176, 228, 0.22);
                        color: #26B0E4;
                        border: 1px solid rgba(38, 176, 228, 0.5);
                        border-radius: 6px;
                        padding: 0px 16px;
                        font-size: 11.5px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #26B0E4;
                        color: #FFFFFF;
                    }
                """)
        if hasattr(self, 'btn_cancel_restart'):
            self.btn_cancel_restart.setFixedHeight(32)
            if is_light:
                self.btn_cancel_restart.setStyleSheet("""
                    QPushButton {
                        background: #F1F5F9;
                        color: #475569;
                        border: 1px solid #CBD5E1;
                        border-radius: 6px;
                        padding: 0px 14px;
                        font-size: 11.5px;
                    }
                    QPushButton:hover {
                        background: #E2E8F0;
                        color: #0F172A;
                    }
                """)
            else:
                self.btn_cancel_restart.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        color: #CBD5E1;
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 6px;
                        padding: 0px 14px;
                    }
                """)
        if hasattr(self, 'spec_card'):
            self.spec_card.setStyleSheet("QFrame#card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; }" if is_light else "QFrame#card { background-color: #11141D; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; }")
        if hasattr(self, 'spec_title'):
            self.spec_title.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#0F172A' if is_light else '#FFFFFF'};")
        if hasattr(self, 'spec_desc'):
            self.spec_desc.setStyleSheet(f"color: {'#475569' if is_light else '#94A3B8'}; font-size: 11.5px; line-height: 1.7;")

    def clear_answer_session(self):
        """清空当前问答界面和会话上下文，开启新会话"""
        if hasattr(self, 'ans_card'):
            self.ans_card.stop_beam()
        if self.stack.currentIndex() != 0:
            self._switch_nav(0)
        self._set_ans_card_style("MEETING")
        self.search_status_lbl.setText("")
        if hasattr(self, 'query_input'):
            self.query_input.clear()
        self.answer_browser.clear_history()
        self.intercom_banner.set_idle()
        if hasattr(self, 'session_menu'):
            self.session_menu.set_active_session("")
            self.session_menu.collapse()
            self.session_menu.refresh_sessions()
        self.new_session_requested.emit()

    def display_answer(self, markdown_text: str, audio_path: str = "", is_followup: bool = False, focal_topic: str = "", response_mode: str = "MEETING"):
        if hasattr(self, 'ans_card'):
            self.ans_card.start_beam()
        self._last_focal_topic = focal_topic
        self._last_is_followup = is_followup
        self._last_response_mode = response_mode
        self.search_status_lbl.setText("")
        self._set_ans_card_style(response_mode)
        self.answer_browser.start_streaming(markdown_text, is_followup=is_followup)
        if hasattr(self, 'session_menu'):
            self.session_menu.refresh_sessions()
        if audio_path and os.path.exists(audio_path):
            self.intercom_banner.set_speaking()
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(audio_path)))
            self.player.play()
        else:
            self.intercom_banner.set_completed(focal_topic=focal_topic, is_followup=is_followup, response_mode=response_mode)

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
