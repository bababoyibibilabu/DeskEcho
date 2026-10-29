import sys
from pathlib import Path
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtCore import Qt

def get_chevron_asset_path(filename: str) -> str:
    """获取下拉箭头 SVG 资源的绝对路径 (支持源码直跑与 PyInstaller 打包)"""
    candidates = [
        Path(sys.executable).parent / "assets" / filename,
        Path(__file__).parent.parent.parent / "assets" / filename,
        Path("assets") / filename,
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, Path(sys._MEIPASS) / "assets" / filename)
    for c in candidates:
        if c.exists():
            return str(c.resolve()).replace("\\", "/")
    return f"assets/{filename}"

class ModernComboBox(QComboBox):
    """
    DeskEcho 专属现代防误触下拉框：
    1. 拦截未展开状态下的鼠标滚轮滑动 (wheelEvent)，彻底杜绝浏览设置页面时意外误切配置项
    2. 去除 Windows 默认焦点的刺眼虚线框与反色选中态
    3. 集成精致轻量级 SVG 极简矢量下拉指示箭头 (替代系统沉重粗糙箭头)
    4. 保证在 Light (浅色) 与 Dark (深色) 两种主题下文字极致清晰高对比
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def wheelEvent(self, event):
        # 仅在下拉弹出视图已经显式打开时才允许滚轮滑动选择；未展开时直接 ignore 让事件向上传递滚动页面
        if self.view() and self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()

def get_modern_combobox_style(is_light: bool) -> str:
    arrow_file = "chevron_down_light.svg" if is_light else "chevron_down_dark.svg"
    arrow_url = get_chevron_asset_path(arrow_file)

    if is_light:
        return f"""
            QComboBox {{
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 0px 32px 0px 12px;
                font-size: 12px;
                font-weight: 500;
                selection-background-color: transparent;
                selection-color: #0F172A;
            }}
            QComboBox:hover {{
                border-color: #94A3B8;
                background-color: #F8FAFC;
            }}
            QComboBox:focus {{
                border-color: #0284C7;
                background-color: #FFFFFF;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 28px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: url("{arrow_url}");
                width: 14px;
                height: 14px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px;
                outline: none;
                selection-background-color: rgba(2, 132, 199, 0.12);
                selection-color: #0284C7;
            }}
            QComboBox QAbstractItemView::item {{
                height: 30px;
                padding: 4px 10px;
                color: #0F172A;
                border-radius: 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #F1F5F9;
                color: #0284C7;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: rgba(2, 132, 199, 0.12);
                color: #0284C7;
                font-weight: 600;
            }}
        """
    else:
        return f"""
            QComboBox {{
                background-color: #0A0C10;
                color: #F1F5F9;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 0px 32px 0px 12px;
                font-size: 12px;
                font-weight: 500;
                selection-background-color: transparent;
                selection-color: #F1F5F9;
            }}
            QComboBox:hover {{
                border-color: rgba(38, 176, 228, 0.4);
                background-color: #12151F;
            }}
            QComboBox:focus {{
                border-color: #26B0E4;
                background-color: #0E121B;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 28px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: url("{arrow_url}");
                width: 14px;
                height: 14px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #11141D;
                color: #F1F5F9;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 4px;
                outline: none;
                selection-background-color: rgba(38, 176, 228, 0.22);
                selection-color: #38BDF8;
            }}
            QComboBox QAbstractItemView::item {{
                height: 30px;
                padding: 4px 10px;
                color: #CBD5E1;
                border-radius: 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: rgba(255, 255, 255, 0.06);
                color: #FFFFFF;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: rgba(38, 176, 228, 0.22);
                color: #38BDF8;
                font-weight: 600;
            }}
        """
