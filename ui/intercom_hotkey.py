import time
from typing import Callable
from pynput import keyboard
from config import Config

class IntercomHotkeyListener:
    """
    基于 pynput 的全局热键对讲监听器
    默认采用笔记本免按 Fn 的极佳单键【右 Alt】(空格右侧大拇指直达)，同时深度兼顾传统 F8；
    按住开启收音，松开即刻检索；防误触（时长 < 0.5 秒忽略或打断）。
    """
    def __init__(self, on_press_cb: Callable[[], None], on_release_cb: Callable[[bool], None]):
        self.on_press_cb = on_press_cb
        self.on_release_cb = on_release_cb
        self.is_pressing = False
        self.press_start_time = 0.0
        self.target_key = self._parse_target_key(Config.INTERCOM_KEY)
        self.listener = None

    def _parse_target_key(self, key_str: str):
        key_str_lower = key_str.lower().strip()
        if key_str_lower in ("alt_r", "right_alt", "right alt", "右alt"):
            return keyboard.Key.alt_r
        if hasattr(keyboard.Key, key_str_lower):
            return getattr(keyboard.Key, key_str_lower)
        # 单字符情况
        return keyboard.KeyCode.from_char(key_str)

    def _is_intercom_key(self, key) -> bool:
        # 1. 优先匹配配置的热键
        if self.target_key is not None and key == self.target_key:
            return True
        # 2. 深度适配右 Alt (VK 165, alt_r, alt_gr)
        if key in (keyboard.Key.alt_r, getattr(keyboard.Key, 'alt_gr', None)):
            return True
        if hasattr(key, 'vk') and key.vk == 165:
            return True
        # 3. 始终兼容传统的 F8 键
        if key == keyboard.Key.f8:
            return True
        return False

    def _on_press(self, key):
        if self._is_intercom_key(key) and not self.is_pressing:
            self.is_pressing = True
            self.press_start_time = time.time()
            self.on_press_cb()

    def _on_release(self, key):
        if self._is_intercom_key(key) and self.is_pressing:
            self.is_pressing = False
            duration = time.time() - self.press_start_time
            is_valid = duration >= 0.5
            self.on_release_cb(is_valid)

    def start(self):
        if self.listener is None:
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.daemon = True
            self.listener.start()
            print(f"[Hotkey] 全局热键对讲监听已激活 (按住【右 Alt】对讲，松开检索)")

    def stop(self):
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
