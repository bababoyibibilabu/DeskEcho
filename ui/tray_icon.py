from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from version import APP_VERSION
from ui.components.icons import get_flower_logo_pixmap

class TrayManager(QObject):
    toggle_record_signal = pyqtSignal(bool)
    show_main_signal = pyqtSignal()
    open_update_signal = pyqtSignal()
    inject_demo_signal = pyqtSignal()
    quit_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = True
        self.tray_icon = QSystemTrayIcon(parent)
        self.icon_active = self._create_icon(is_active=True)
        self.icon_paused = self._create_icon(is_active=False)
        
        self.tray_icon.setIcon(self.icon_active)
        self.tray_icon.setToolTip("DeskEcho - 桌面会议记忆助理 (长按右Alt对讲)")

        self._build_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _create_icon(self, is_active: bool) -> QIcon:
        """动态绘制托盘图标 (美好智能 Flower Logo 变体)"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制 Flower Logo
        logo = get_flower_logo_pixmap(28)
        painter.drawPixmap(2, 2, logo)

        if not is_active:
            # 暂停时右下角加小暗灰角标
            painter.setBrush(QBrush(QColor(100, 116, 139)))
            painter.setPen(QPen(QColor(15, 23, 42), 1.5))
            painter.drawEllipse(18, 18, 12, 12)
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(21, 21, 2, 6)
            painter.drawRect(25, 21, 2, 6)
        
        painter.end()
        return QIcon(pixmap)

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0F121A;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px;
                color: #E2E8F0;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #1E2337;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 4px 6px;
            }
        """)
        
        from ui.components.icons import get_symbol_icon

        main_action = menu.addAction("打开控制台主界面")
        main_action.setIcon(get_symbol_icon("bolt", color="#26B0E4", size=14))
        main_action.triggered.connect(self.show_main_signal.emit)

        update_action = menu.addAction(f"软件发版与更新 (v{APP_VERSION})")
        update_action.setIcon(get_symbol_icon("rocket_launch", color="#38BDF8", size=14))
        update_action.triggered.connect(self.open_update_signal.emit)

        menu.addSeparator()

        self.toggle_action = menu.addAction("暂停会议录制")
        self.toggle_action.setIcon(get_symbol_icon("mic", color="#10B981", size=14))
        self.toggle_action.triggered.connect(self._toggle_recording)

        menu.addSeparator()

        demo_action = menu.addAction("写入示例会议记录 (演示用)")
        demo_action.setIcon(get_symbol_icon("article", color="#8AC657", size=14))
        demo_action.triggered.connect(self.inject_demo_signal.emit)

        menu.addSeparator()

        quit_action = menu.addAction("退出 DeskEcho")
        quit_action.setIcon(get_symbol_icon("delete_forever", color="#EF4444", size=14))
        quit_action.triggered.connect(self.quit_signal.emit)

        self.tray_icon.setContextMenu(menu)

    def set_record_state(self, should_record: bool):
        from ui.components.icons import get_symbol_icon
        self.is_recording = should_record
        if self.is_recording:
            self.toggle_action.setText("暂停会议录制")
            self.toggle_action.setIcon(get_symbol_icon("mic", color="#10B981", size=14))
            self.tray_icon.setIcon(self.icon_active)
        else:
            self.toggle_action.setText("恢复会议录制")
            self.toggle_action.setIcon(get_symbol_icon("mic", color="#F59E0B", size=14))
            self.tray_icon.setIcon(self.icon_paused)

    def _toggle_recording(self):
        self.set_record_state(not self.is_recording)
        self.toggle_record_signal.emit(self.is_recording)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 单击托盘图标唤出主界面
            self.show_main_signal.emit()
