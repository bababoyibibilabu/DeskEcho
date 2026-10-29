import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

from ui.main_window import MainWindow
from core.knowledge_engine import MeetingStore
from ui.theme_manager import ThemeManager

def main():
    app = QApplication.instance() or QApplication(sys.argv)

    # Initialize store and main window
    store = MeetingStore()
    win = MainWindow(store)
    win.show()
    app.processEvents()

    # 1. 验证品牌名称
    assert win.brand_title_lbl.text() == "DeskEcho", f"Expected DeskEcho, got {win.brand_title_lbl.text()}"
    assert win.brand_sub_lbl.text() == "美好智能", f"Expected 美好智能, got {win.brand_sub_lbl.text()}"
    print("[PASS] 左上角品牌 DeskEcho 与美好智能互换验证通过！")

    # 2. 验证倾听开关点击 (多次切换，彻底杜绝闪退)
    assert win.record_switch.is_active is True
    win.record_switch._toggle()  # 暂停
    app.processEvents()
    assert win.record_switch.is_active is False
    print("[PASS] 倾听开关暂停点击通过，无闪退！")

    # 截取暂停状态图
    img_paused = win.grab()
    img_paused.save("C:/Users/PC/.gemini/antigravity-cli/brain/5a084246-a6cf-4d4d-b400-28fb6aeaf7a5/verify_switch_paused.png")

    win.record_switch._toggle()  # 恢复
    app.processEvents()
    assert win.record_switch.is_active is True
    print("[PASS] 倾听开关恢复点击通过，无闪退！")

    # 3. 验证 Page 1 (或许没用切片库，无视觉污染)
    win._switch_nav(1)
    win._switch_mem_mode("trash")
    app.processEvents()
    assert win.trash_banner.isVisible() is True
    img_trash = win.grab()
    img_trash.save("C:/Users/PC/.gemini/antigravity-cli/brain/5a084246-a6cf-4d4d-b400-28fb6aeaf7a5/verify_trash_page_clean.png")
    print("[PASS] 或许有用界面素雅无视觉污染验证通过！")

    # 4. 验证 Page 3 (系统引擎与实用配置中心)
    win._switch_nav(3)
    app.processEvents()
    assert win.combo_voice_meeting is not None
    assert win.combo_voice_meeting.count() >= 4
    assert win.input_llm_key is not None
    assert win.btn_save_settings is not None
    img_settings = win.grab()
    img_settings.save("C:/Users/PC/.gemini/antigravity-cli/brain/5a084246-a6cf-4d4d-b400-28fb6aeaf7a5/verify_settings_center.png")
    print("[PASS] 系统引擎设置中心页面与各配置项验证通过！")

    win.close()
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
