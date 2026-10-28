import math
import random
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient

class AudioWaveVisualizer(QWidget):
    """
    Alma 风格的现代音频声波频谱指示器
    - 活跃状态：极具科技感的青绿/紫罗兰双色渐变跳动，模拟真实人声共振
    - 静止状态：平滑阻尼衰减至精致的基线呼吸状态
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(84, 26)
        self.is_active = True
        self.mode = "default" # "default" | "listening" | "speaking"
        self.bar_count = 7
        self.bars = [0.25] * self.bar_count
        self.target_bars = [0.25] * self.bar_count
        self.phase = 0.0

        self.timer = QTimer(self)
        self.timer.setInterval(30) # ~33 FPS 平滑动画
        self.timer.timeout.connect(self._update_animation)
        self.timer.start()

    def set_active(self, active: bool):
        self.is_active = active
        if not active:
            self.target_bars = [0.08] * self.bar_count

    def set_mode(self, mode: str):
        self.mode = mode
        self.update()

    def _update_animation(self):
        self.phase += 0.14
        num_bars = self.bar_count

        if self.is_active:
            for i in range(num_bars):
                # 复合正弦波叠加高频微噪，模拟人声频谱起伏
                w1 = math.sin(self.phase * 1.6 + i * 0.75) * 0.4
                w2 = math.cos(self.phase * 0.9 - i * 0.5) * 0.25
                noise = random.uniform(0.04, 0.22)
                val = 0.5 + w1 + w2 + noise
                self.target_bars[i] = min(1.0, max(0.12, val))
        else:
            for i in range(num_bars):
                # 静止时的微弱微光呼吸
                self.target_bars[i] = 0.08 + 0.04 * math.sin(self.phase * 0.8 + i)

        # 阻尼平滑插值 (Lerp)
        for i in range(num_bars):
            self.bars[i] += (self.target_bars[i] - self.bars[i]) * 0.32

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        bar_count = self.bar_count
        bar_width = 4
        spacing = 4
        total_width = bar_count * bar_width + (bar_count - 1) * spacing
        start_x = (width - total_width) / 2

        for i, val in enumerate(self.bars):
            bar_h = max(3.0, val * (height - 4))
            x = start_x + i * (bar_width + spacing)
            y = (height - bar_h) / 2

            # 美好智能 VI 品牌色彩体系
            if self.is_active:
                grad = QLinearGradient(x, y + bar_h, x, y)
                if self.mode == "listening":
                    # 语音收音：红色呼吸至海青
                    grad.setColorAt(0.0, QColor(239, 68, 68, int(180 + 70 * val)))
                    grad.setColorAt(1.0, QColor(38, 176, 228, int(200 + 55 * val)))
                elif self.mode == "speaking":
                    # 语音播报：翡翠绿至鹦鹉绿
                    grad.setColorAt(0.0, QColor(16, 185, 129, int(180 + 70 * val)))
                    grad.setColorAt(1.0, QColor(138, 198, 87, int(200 + 55 * val)))
                else:
                    # 默认：靛青 (#13459D) -> 海青 (#26B0E4) -> 鹦鹉绿 (#8AC657)
                    grad.setColorAt(0.0, QColor(19, 69, 157, int(170 + 75 * val)))
                    grad.setColorAt(0.5, QColor(38, 176, 228, int(185 + 65 * val)))
                    grad.setColorAt(1.0, QColor(138, 198, 87, int(200 + 55 * val)))
                painter.setBrush(QBrush(grad))
            else:
                painter.setBrush(QBrush(QColor(71, 85, 105, 90)))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(y), bar_width, int(bar_h), 2, 2)
