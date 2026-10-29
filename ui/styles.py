from typing import Dict, Any
from ui.theme_manager import ThemeManager, ThemeType

def get_theme_colors() -> Dict[str, str]:
    return ThemeManager.get_instance().get_colors()

def is_theme_light() -> bool:
    return ThemeManager.get_instance().is_light()

def get_cmd_card_style(is_light: bool) -> str:
    if is_light:
        return """
            QFrame#cmd_card {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
            QFrame#cmd_card:focus-within {
                border: 1.5px solid #0284C7;
            }
        """
    else:
        return """
            QFrame#cmd_card {
                background-color: #111520;
                border: 1px solid rgba(38, 176, 228, 0.40);
                border-radius: 10px;
            }
            QFrame#cmd_card:focus-within {
                border: 1.5px solid #26B0E4;
            }
        """

def get_ans_card_style(mode: str, is_light: bool) -> str:
    if is_light:
        if mode == "INSTRUCTION":
            return """
                QFrame#ans_card {
                    background-color: #FFFDF5;
                    border: 1.5px solid #D97706;
                    border-radius: 12px;
                }
            """
        elif mode == "GENERAL":
            return """
                QFrame#ans_card {
                    background-color: #FAF5FF;
                    border: 1.5px solid #9333EA;
                    border-radius: 12px;
                }
            """
        else:
            return """
                QFrame#ans_card {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """
    else:
        if mode == "INSTRUCTION":
            return """
                QFrame#ans_card {
                    background-color: #13100B;
                    border: 1.5px solid rgba(245, 158, 11, 0.7);
                    border-radius: 12px;
                }
            """
        elif mode == "GENERAL":
            return """
                QFrame#ans_card {
                    background-color: #0E1019;
                    border: 1.5px solid rgba(139, 92, 246, 0.65);
                    border-radius: 12px;
                }
            """
        else:
            return """
                QFrame#ans_card {
                    background-color: #0E1017;
                    border: 1px solid rgba(38, 176, 228, 0.28);
                    border-radius: 12px;
                }
            """

def get_answer_browser_style(is_light: bool) -> str:
    if is_light:
        return """
            QTextBrowser {
                background-color: #FFFFFF;
                border: none;
                padding: 12px;
                color: #0F172A;
                font-size: 13px;
                line-height: 1.6;
            }
        """
    else:
        return """
            QTextBrowser {
                background-color: #0A0C10;
                border: none;
                padding: 12px;
                color: #E2E8F0;
                font-size: 13px;
                line-height: 1.6;
            }
        """

def get_top_version_style(is_light: bool) -> str:
    if is_light:
        return """
            QPushButton {
                background-color: rgba(2, 132, 199, 0.08);
                color: #0284C7;
                border: 1px solid rgba(2, 132, 199, 0.25);
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """
    else:
        return """
            QPushButton {
                background-color: rgba(38, 176, 228, 0.12);
                color: #38BDF8;
                border: 1px solid rgba(38, 176, 228, 0.35);
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #26B0E4;
                color: #FFFFFF;
            }
        """

def get_theme_btn_style(is_light: bool) -> str:
    if is_light:
        return """
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #0284C7;
            }
        """
    else:
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: rgba(38, 176, 228, 0.2);
                border-color: #26B0E4;
            }
        """

def get_intercom_banner_style(state: str, is_light: bool) -> str:
    if state == "idle":
        if is_light:
            return """
                IntercomBanner {
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
            """
        else:
            return """
                IntercomBanner {
                    background: rgba(15, 23, 42, 0.45);
                    border: 1px solid rgba(255, 255, 255, 0.07);
                    border-radius: 8px;
                }
            """
    elif state == "listening":
        return """
            IntercomBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(239, 68, 68, 0.18), stop:1 rgba(38, 176, 228, 0.12));
                border: 1.5px solid rgba(239, 68, 68, 0.6);
                border-radius: 8px;
            }
        """
    elif state == "ack":
        return """
            IntercomBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(19, 69, 157, 0.25), stop:1 rgba(38, 176, 228, 0.15));
                border: 1.2px solid #26B0E4;
                border-radius: 8px;
            }
        """
    elif state == "speaking":
        if is_light:
            return """
                IntercomBanner {
                    background: rgba(22, 163, 74, 0.08);
                    border: 1.2px solid #16A34A;
                    border-radius: 8px;
                }
            """
        else:
            return """
                IntercomBanner {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(16, 185, 129, 0.18), stop:1 rgba(38, 176, 228, 0.15));
                    border: 1.2px solid #8AC657;
                    border-radius: 8px;
                }
            """
    return ""

def get_mem_list_style(is_light: bool) -> str:
    if is_light:
        return """
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 6px;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                background-color: #F8FAFC;
                border: 1px solid #F1F5F9;
                border-radius: 6px;
                padding: 8px 10px;
                margin-bottom: 6px;
                color: #0F172A;
            }
            QListWidget::item:hover {
                background-color: #F1F5F9;
                border-color: #CBD5E1;
            }
            QListWidget::item:selected {
                background-color: rgba(2, 132, 199, 0.08);
                border-left: 3px solid #0284C7;
                color: #0284C7;
            }
        """
    else:
        return """
            QListWidget {
                background-color: #11141D;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 10px;
                padding: 6px;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                background-color: #0A0C10;
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 6px;
                padding: 8px 10px;
                margin-bottom: 6px;
                color: #CBD5E1;
            }
            QListWidget::item:hover {
                background-color: #151D2C;
                border-color: rgba(38, 176, 228, 0.4);
            }
            QListWidget::item:selected {
                background-color: #12213A;
                border-left: 3px solid #26B0E4;
                color: #FFFFFF;
            }
        """

def get_mem_detail_style(is_light: bool) -> str:
    if is_light:
        return """
            QTextBrowser {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 16px;
                color: #0F172A;
                font-size: 13px;
                line-height: 1.6;
            }
        """
    else:
        return """
            QTextBrowser {
                background-color: #11141D;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 10px;
                padding: 16px;
                color: #E2E8F0;
                font-size: 13px;
                line-height: 1.6;
            }
        """
