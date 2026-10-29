import math
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QPainterPath, QConicalGradient
)
from ui.theme_manager import ThemeManager

class BorderBeamContainer(QFrame):
    """
    基于 Jakub Antalik 动效哲学的 Border Beam (边框流光漫游容器)
    - 待命状态：呈现极简沉静的微弱边框；
    - 流式输出中 (start_beam)：激活沿边框平滑流转的光束；
    - 输出完毕 (stop_beam)：平滑静止，绝不喧宾夺主。
    """
    def __init__(self, parent=None, border_radius=10):
        super().__init__(parent)
        self.border_radius = border_radius
        self._is_beaming = False
        self._angle = 0.0
        
        self._timer = QTimer(self)
        self._timer.setInterval(25)  # ~40 FPS, 丝滑且超轻量
        self._timer.timeout.connect(self._on_tick)

    def start_beam(self):
        if not self._is_beaming:
            self._is_beaming = True
            self._angle = 0.0
            self._timer.start()
            self.update()

    def stop_beam(self):
        if self._is_beaming:
            self._is_beaming = False
            self._timer.stop()
            self.update()

    def _on_tick(self):
        self._angle = (self._angle + 3.0) % 360.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        
        tm = ThemeManager.get_instance()
        colors = tm.get_colors()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, self.border_radius, self.border_radius)

        if not self._is_beaming:
            # 静态常规边框
            pen = QPen(QColor(colors["border_card"]), 1)
            painter.strokePath(path, pen)
        else:
            # 动态 Border Beam
            center_x = rect.center().x()
            center_y = rect.center().y()
            
            # 使用圆锥渐变形成 60 度弧长的发光掠影
            gradient = QConicalGradient(center_x, center_y, -self._angle)
            
            c_accent = QColor(colors["brand_accent"])
            c_accent.setAlpha(255)
            c_primary = QColor(colors["brand_primary"])
            c_primary.setAlpha(180)
            c_transparent = QColor(colors["brand_accent"])
            c_transparent.setAlpha(0)

            # 扫掠光束比例区间
            gradient.setColorAt(0.0, c_transparent)
            gradient.setColorAt(0.08, c_accent)
            gradient.setColorAt(0.16, c_primary)
            gradient.setColorAt(0.24, c_transparent)
            gradient.setColorAt(1.0, c_transparent)

            # 先画底座微光
            pen_base = QPen(QColor(colors["border_card"]), 1)
            painter.strokePath(path, pen_base)

            # 再画流动光束 (2px 粗细，高光明显)
            pen_beam = QPen(gradient, 2)
            painter.strokePath(path, pen_beam)

        painter.end()
