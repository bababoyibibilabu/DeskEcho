import json
import os
from enum import Enum
from pathlib import Path
from typing import Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

class ThemeType(str, Enum):
    LIGHT = "light"
    DARK = "dark"

THEME_COLORS = {
    ThemeType.LIGHT: {
        "name": "light",
        "bg_window": "#F8FAFC",
        "bg_sidebar": "#F1F5F9",
        "bg_card": "#FFFFFF",
        "bg_sub_surface": "#F1F5F9",
        "bg_elevated": "#FFFFFF",
        "bg_hover": "rgba(15, 23, 42, 0.04)",
        "bg_selected": "rgba(2, 132, 199, 0.08)",
        "border_subtle": "#E2E8F0",
        "border_card": "#E2E8F0",
        "border_focus": "#0284C7",
        "text_primary": "#0F172A",
        "text_secondary": "#475569",
        "text_muted": "#94A3B8",
        "brand_primary": "#1D4ED8",          # 靛青 (Light)
        "brand_primary_hover": "#2563EB",
        "brand_accent": "#0284C7",           # 海青 (Light)
        "brand_accent_hover": "#0EA5E9",
        "brand_accent_bg": "rgba(2, 132, 199, 0.08)",
        "brand_success": "#16A34A",          # 鹦鹉绿 (Light)
        "brand_success_bg": "rgba(22, 163, 74, 0.10)",
        "brand_amber": "#D97706",            # 琥珀金 (Light)
        "brand_amber_bg": "rgba(217, 119, 6, 0.10)",
        "brand_danger": "#DC2626",
        "brand_danger_bg": "rgba(220, 38, 38, 0.10)",
        "scrollbar_bg": "transparent",
        "scrollbar_handle": "rgba(15, 23, 42, 0.15)",
        "scrollbar_handle_hover": "rgba(2, 132, 199, 0.6)",
        "code_bg": "#F1F5F9",
        "dialog_overlay": "rgba(15, 23, 42, 0.35)",
    },
    ThemeType.DARK: {
        "name": "dark",
        "bg_window": "#0A0C10",
        "bg_sidebar": "#07090D",
        "bg_card": "#11141D",
        "bg_sub_surface": "#181C28",
        "bg_elevated": "#141824",
        "bg_hover": "rgba(255, 255, 255, 0.05)",
        "bg_selected": "rgba(38, 176, 228, 0.12)",
        "border_subtle": "rgba(255, 255, 255, 0.07)",
        "border_card": "rgba(255, 255, 255, 0.07)",
        "border_focus": "#26B0E4",
        "text_primary": "#FFFFFF",
        "text_secondary": "#94A3B8",
        "text_muted": "#64748B",
        "brand_primary": "#13459D",          # 靛青 (Dark)
        "brand_primary_hover": "#1A56BC",
        "brand_accent": "#26B0E4",           # 海青 (Dark)
        "brand_accent_hover": "#4CC3ED",
        "brand_accent_bg": "rgba(38, 176, 228, 0.12)",
        "brand_success": "#8AC657",          # 鹦鹉绿 (Dark)
        "brand_success_bg": "rgba(138, 198, 87, 0.15)",
        "brand_amber": "#F59E0B",            # 琥珀金 (Dark)
        "brand_amber_bg": "rgba(245, 158, 11, 0.18)",
        "brand_danger": "#EF4444",
        "brand_danger_bg": "rgba(239, 68, 68, 0.18)",
        "scrollbar_bg": "transparent",
        "scrollbar_handle": "rgba(255, 255, 255, 0.16)",
        "scrollbar_handle_hover": "rgba(38, 176, 228, 0.8)",
        "code_bg": "#0D1117",
        "dialog_overlay": "rgba(0, 0, 0, 0.65)",
    }
}

class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.config_path = Path("D:/DeskEcho_Data/theme.json")
        if not self.config_path.parent.exists():
            self.config_path = Path("theme_preference.json")
            
        self.current_theme = self._load_preference()

    def _load_preference(self) -> ThemeType:
        try:
            if self.config_path.exists():
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                val = data.get("theme", "light")
                return ThemeType.LIGHT if val == "light" else ThemeType.DARK
        except Exception:
            pass
        return ThemeType.LIGHT  # 默认遵循用户偏好：优先默认 Light 主题

    def save_preference(self):
        try:
            self.config_path.write_text(
                json.dumps({"theme": self.current_theme.value}, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[ThemeManager] 保存主题设置失败: {e}")

    def toggle_theme(self) -> ThemeType:
        if self.current_theme == ThemeType.LIGHT:
            self.current_theme = ThemeType.DARK
        else:
            self.current_theme = ThemeType.LIGHT
            
        self.save_preference()
        self.theme_changed.emit(self.current_theme.value)
        return self.current_theme

    def set_theme(self, theme: ThemeType) -> ThemeType:
        self.current_theme = theme
        self.save_preference()
        self.theme_changed.emit(self.current_theme.value)
        return self.current_theme

    def get_colors(self) -> Dict[str, str]:
        return THEME_COLORS[self.current_theme]

    def is_light(self) -> bool:
        return self.current_theme == ThemeType.LIGHT

    def get_global_qss(self) -> str:
        c = self.get_colors()
        is_light = self.is_light()
        
        return f"""
            QMainWindow {{
                background-color: {c['bg_window']};
            }}
            QWidget {{
                color: {c['text_primary']};
                font-family: 'Segoe UI Variable Text', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
            }}
            QFrame#card {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border_card']};
                border-radius: 12px;
            }}
            QFrame#sidebar {{
                background-color: {c['bg_sidebar']};
                border-right: 1px solid {c['border_subtle']};
            }}
            QSplitter {{
                background: transparent;
                border: none;
            }}
            QSplitter::handle {{
                background-color: transparent;
            }}
            QSplitter::handle:horizontal {{
                width: 6px;
                background-color: transparent;
            }}
            QSplitter::handle:horizontal:hover {{
                background-color: {c['brand_accent']};
            }}
            QSplitter::handle:vertical {{
                height: 6px;
                background-color: transparent;
            }}
            QSplitter::handle:vertical:hover {{
                background-color: {c['brand_accent']};
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['scrollbar_handle']};
                border-radius: 3px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['scrollbar_handle_hover']};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {c['brand_primary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: transparent;
                height: 0px;
                width: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                border: none;
                background: transparent;
            }}
            QScrollBar:horizontal {{
                border: none;
                background: transparent;
                height: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {c['scrollbar_handle']};
                border-radius: 3px;
                min-width: 28px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {c['scrollbar_handle_hover']};
            }}
            QScrollBar::handle:horizontal:pressed {{
                background: {c['brand_primary']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: transparent;
                height: 0px;
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                border: none;
                background: transparent;
            }}
            QScrollBar::corner {{
                background: transparent;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QToolTip {{
                background-color: {c['bg_card']};
                color: {c['text_primary']};
                border: 1px solid {c['border_card']};
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11px;
            }}
            QLineEdit, QTextBrowser, QListWidget, QComboBox {{
                selection-background-color: {c['brand_accent']};
                selection-color: #FFFFFF;
            }}
        """
