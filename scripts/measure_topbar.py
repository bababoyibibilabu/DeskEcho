import sys
import os
sys.path.insert(0, os.path.abspath("."))
from PyQt6.QtWidgets import QApplication
from core.knowledge_engine import MeetingStore
from ui.main_window import MainWindow

def measure_topbar():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication(sys.argv)
    store = MeetingStore()
    window = MainWindow(store)
    window.resize(1000, 700)
    window.show()
    
    # Switch to settings page (page 2)
    window._switch_nav(2)
    app.processEvents()

    widgets = [
        ("breadcrumb_lbl", window.breadcrumb_lbl),
        ("settings_tab_bar", window.settings_tab_bar),
        ("sub_btn_roster", window.sub_btn_roster),
        ("sub_btn_memory", window.sub_btn_memory),
        ("sub_btn_engine", window.sub_btn_engine),
        ("sub_btn_update", window.sub_btn_update),
        ("sub_btn_back", window.sub_btn_back),
        ("theme_btn", window.theme_btn),
        ("top_version_btn", window.top_version_btn),
    ]

    for name, w in widgets:
        g = w.geometry()
        pos = w.mapTo(window, g.topLeft())
        print(f"{name:20s}: local_rect=({g.x():3d}, {g.y():3d}, {g.width():3d}, {g.height():3d}), mapped_pos=({pos.x():3d}, {pos.y():3d})")

if __name__ == "__main__":
    measure_topbar()
