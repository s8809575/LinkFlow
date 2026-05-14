import time
import threading

class ClipboardService:
    """
    模块二：实时剪贴板流转
    监听 PC 剪贴板变化并触发回调
    """
    def __init__(self, on_update_callback):
        self.on_update_callback = on_update_callback
        self.last_content = ""
        self._running = True

    def _get_clipboard_text(self):
        try:
            import win32clipboard
        except ImportError:
            return None

        try:
            win32clipboard.OpenClipboard()
            # CF_UNICODETEXT 对应全案中的文本自动同步功能
            try:
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return None

    def start_watching(self):
        """开启循环监听线程"""
        def watch_loop():
            while self._running:
                current_content = self._get_clipboard_text()
                # 检测内容是否变化且不为空
                if current_content and current_content != self.last_content:
                    self.last_content = current_content
                    # 触发回调，将内容发送至手机端
                    self.on_update_callback(current_content)
                time.sleep(1) # 每秒轮询一次，平衡性能与实时性

        threading.Thread(target=watch_loop, daemon=True).start()
        print("[*] 剪贴板监控服务已就绪")

    def set_clipboard_text(self, text):
        if text == self.last_content:
            return True

        try:
            import win32clipboard
        except ImportError:
            return False

        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
            finally:
                win32clipboard.CloseClipboard()
            self.last_content = text
            return True
        except Exception:
            return False

    def stop(self):
        self._running = False
