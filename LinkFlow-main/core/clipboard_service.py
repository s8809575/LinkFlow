import time
import threading

try:
    import win32clipboard
except ImportError:
    win32clipboard = None

class ClipboardService:
    """
    模块二：实时剪贴板流转
    监听 PC 剪贴板变化并触发回调
    """
    def __init__(self, on_update_callback):
        self.on_update_callback = on_update_callback
        self._lock = threading.Lock()
        self._last_content = None
        self._set_by_us_content = None
        self._running = True

    def _get_clipboard_text(self):
        if win32clipboard is None:
            return None
        try:
            win32clipboard.OpenClipboard()
            try:
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return None

    def get_clipboard_text(self):
        """
        读取当前剪贴板内容（主动读取，不触发监听回调）
        """
        text = self._get_clipboard_text()
        with self._lock:
            self._last_content = text
        return text

    def start_watching(self):
        """开启循环监听线程"""
        def watch_loop():
            while self._running:
                current = self._get_clipboard_text()
                with self._lock:
                    # M6: 防回环——如果内容等于我们刚写入的，跳过
                    if self._set_by_us_content is not None and current == self._set_by_us_content:
                        self._set_by_us_content = None
                        time.sleep(1)
                        continue
                    changed = current != self._last_content
                    if changed:
                        self._last_content = current

                if changed and current:
                    self.on_update_callback(current)
                time.sleep(1)

        threading.Thread(target=watch_loop, daemon=True).start()
        print("[*] 剪贴板监控服务已就绪")

    def set_clipboard_text(self, text):
        if text == self._last_content:
            return True

        if win32clipboard is None:
            return False

        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
            finally:
                win32clipboard.CloseClipboard()
            with self._lock:
                self._last_content = text
                self._set_by_us_content = text   # 标记，用于防回环
            return True
        except Exception:
            return False

    def stop(self):
        self._running = False
