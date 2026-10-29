import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont
from ui.theme_manager import ThemeManager, ThemeType
from ui.components.icons import get_symbol_pixmap

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont
from ui.theme_manager import ThemeManager, ThemeType
from ui.components.icons import get_symbol_pixmap

class ModernDialog(QDialog):
    """
    符合美好智能品牌规范的高质感现代模态弹窗 (Light & Dark 自适应)
    高对比度、清晰排版、极简优雅，彻底告别粗糙、暗淡字迹不清
    """
    def __init__(
        self,
        parent: Optional[QWidget],
        title: str,
        message: str,
        detail: str = "",
        dialog_type: str = "danger",  # "danger", "warning", "info", "question"
        confirm_text: str = "确定",
        cancel_text: Optional[str] = "取消",
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setMaximumWidth(520)

        tm = ThemeManager.get_instance()
        is_light = tm.is_light()

        # 调色盘规范（确保任何显示屏上都绝对清晰）
        if is_light:
            bg_card = "#FFFFFF"
            border_col = "#CBD5E1"
            text_title = "#0F172A"
            text_body = "#1E293B"
            text_detail = "#334155"
            bg_detail = "#F8FAFC"
            border_detail = "#E2E8F0"
            btn_cancel_bg = "#F1F5F9"
            btn_cancel_border = "#CBD5E1"
            btn_cancel_text = "#334155"
            btn_cancel_hover = "#E2E8F0"
            btn_confirm_blue = "#0284C7"
            btn_confirm_danger = "#DC2626"
            btn_confirm_danger_hover = "#B91C1C"
            shadow_color = QColor(15, 23, 42, 60)
        else:
            bg_card = "#0F1422"
            border_col = "#334155"
            text_title = "#FFFFFF"
            text_body = "#F1F5F9"
            text_detail = "#CBD5E1"
            bg_detail = "#161E31"
            border_detail = "#26354D"
            btn_cancel_bg = "#1E293B"
            btn_cancel_border = "#475569"
            btn_cancel_text = "#E2E8F0"
            btn_cancel_hover = "#334155"
            btn_confirm_blue = "#26B0E4"
            btn_confirm_danger = "#EF4444"
            btn_confirm_danger_hover = "#DC2626"
            shadow_color = QColor(0, 0, 0, 160)

        # 主外部容器
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("dialogCard")
        
        # 阴影效果
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(28)
        shadow.setColor(shadow_color)
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        card.setStyleSheet(f"""
            QFrame#dialogCard {{
                background-color: {bg_card};
                border: 1.5px solid {border_col};
                border-radius: 12px;
                font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 20)
        card_layout.setSpacing(14)

        # 头部：图标 + 标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_name = "warning"
        icon_color = "#D97706" if is_light else "#F59E0B"
        if dialog_type == "danger":
            icon_name = "delete_forever"
            icon_color = btn_confirm_danger
        elif dialog_type == "info":
            icon_name = "info"
            icon_color = "#0284C7" if is_light else "#26B0E4"
        elif dialog_type == "question":
            icon_name = "check_circle"
            icon_color = "#16A34A" if is_light else "#8AC657"

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_symbol_pixmap(icon_name, color=icon_color, size=24))
        header_layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700;
            color: {text_title};
            border: none;
            background: transparent;
        """)
        header_layout.addWidget(title_lbl, 1)
        card_layout.addLayout(header_layout)

        # 主消息
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 500;
            line-height: 1.5;
            color: {text_body};
            border: none;
            background: transparent;
        """)
        card_layout.addWidget(msg_lbl)

        # 补充细节（若有）
        if detail:
            detail_box = QFrame()
            detail_box.setStyleSheet(f"""
                background-color: {bg_detail};
                border: 1px solid {border_detail};
                border-left: 3.5px solid {icon_color};
                border-radius: 6px;
                padding: 10px 12px;
            """)
            d_layout = QVBoxLayout(detail_box)
            d_layout.setContentsMargins(4, 2, 4, 2)
            detail_lbl = QLabel(detail)
            detail_lbl.setWordWrap(True)
            detail_lbl.setStyleSheet(f"""
                font-size: 12px;
                color: {text_detail};
                line-height: 1.5;
                font-weight: 450;
                border: none;
                background: transparent;
            """)
            d_layout.addWidget(detail_lbl)
            card_layout.addWidget(detail_box)

        card_layout.addSpacing(6)

        # 底部操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        if cancel_text:
            btn_cancel = QPushButton(cancel_text)
            btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cancel.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_cancel_bg};
                    color: {btn_cancel_text};
                    border: 1px solid {btn_cancel_border};
                    border-radius: 6px;
                    padding: 8px 18px;
                    font-size: 12.5px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {btn_cancel_hover};
                    color: {text_title};
                }}
            """)
            btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(btn_cancel)

        btn_confirm = QPushButton(confirm_text)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)

        if dialog_type == "danger":
            confirm_bg = btn_confirm_danger
            confirm_hover = btn_confirm_danger_hover
        else:
            confirm_bg = btn_confirm_blue
            confirm_hover = "#0369A1" if is_light else "#1FA0D1"

        btn_confirm.setStyleSheet(f"""
            QPushButton {{
                background-color: {confirm_bg};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 22px;
                font-size: 12.5px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {confirm_hover};
            }}
        """)
        btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(btn_confirm)

        card_layout.addLayout(btn_layout)
        root_layout.addWidget(card)

    @classmethod
    def confirm_danger(cls, parent: Optional[QWidget], title: str, message: str, detail: str = "", confirm_text: str = "确定删除", cancel_text: str = "取消") -> bool:
        dlg = cls(parent, title, message, detail=detail, dialog_type="danger", confirm_text=confirm_text, cancel_text=cancel_text)
        return dlg.exec() == QDialog.DialogCode.Accepted

    @classmethod
    def confirm_action(cls, parent: Optional[QWidget], title: str, message: str, detail: str = "", confirm_text: str = "确定", cancel_text: str = "取消") -> bool:
        dlg = cls(parent, title, message, detail=detail, dialog_type="question", confirm_text=confirm_text, cancel_text=cancel_text)
        return dlg.exec() == QDialog.DialogCode.Accepted

    @classmethod
    def show_info(cls, parent: Optional[QWidget], title: str, message: str, detail: str = "", button_text: str = "知道了"):
        dlg = cls(parent, title, message, detail=detail, dialog_type="info", confirm_text=button_text, cancel_text=None)
        dlg.exec()

    @classmethod
    def show_warning(cls, parent: Optional[QWidget], title: str, message: str, detail: str = "", button_text: str = "我知道了"):
        dlg = cls(parent, title, message, detail=detail, dialog_type="warning", confirm_text=button_text, cancel_text=None)
        dlg.exec()
