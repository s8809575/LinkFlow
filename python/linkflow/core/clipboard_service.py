import time
import threading
import sys

class ClipboardService:
    """
    模块二：实时剪贴板流转
    监听 PC 剪贴板变化并触发回调
    """
    def __init__(self, on_update_callback):
        self.on_update_callback = on_update_callback
        self.last_content = ""
        self._running = True

    @staticmethod
    def get_clipboard_text():
        """获取当前剪贴板内容（静态方法）"""
        try:
            import win32clipboard
        except ImportError:
            return None

        try:
            win32clipboard.OpenClipboard()
            try:
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return None

    @staticmethod
    def get_clipboard_image():
        print("[DEBUG] get_clipboard_image 被调用", file=sys.stderr, flush=True)
        try:
            import win32clipboard
            from PIL import Image
            import io
        except ImportError:
            return None, None

        try:
            win32clipboard.OpenClipboard()
            try:
                formats = [
                    win32clipboard.CF_DIB,
                    win32clipboard.CF_BITMAP,
                    win32clipboard.RegisterClipboardFormat("PNG"),
                    win32clipboard.RegisterClipboardFormat("image/png"),
                ]

                for fmt in formats:
                    if win32clipboard.IsClipboardFormatAvailable(fmt):
                        try:
                            data = win32clipboard.GetClipboardData(fmt)
                            if data:
                                if isinstance(data, bytes):
                                    image = Image.open(io.BytesIO(data))
                                elif hasattr(data, 'Save'):
                                    import tempfile
                                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                                        data.Save(tmp.name)
                                        image = Image.open(tmp.name)
                                else:
                                    continue

                                img_bytes = io.BytesIO()
                                image.save(img_bytes, format='PNG')
                                return img_bytes.getvalue(), 'PNG'
                        except Exception as e:
                            print(f"[DEBUG] 尝试格式 {fmt} 失败: {e}", file=sys.stderr)
                            continue
                print("[!] 剪贴板中没有可用的图片格式")
                return None, None
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"[!] 获取剪贴板图片失败: {e}")
            return None, None

    @staticmethod
    def set_clipboard_image(image_bytes):
        try:
            print(f"[*] 设置剪贴板图片，大小: {len(image_bytes)} bytes")
            import win32clipboard
            from PIL import Image
            import io
        except ImportError:
            print("[!] 缺少必要的模块")
            return False

        try:
            retry_count = 3
            for i in range(retry_count):
                try:
                    img = Image.open(io.BytesIO(image_bytes))
                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        output = io.BytesIO()
                        img.save(output, format='BMP')
                        bmp_data = output.getvalue()
                        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data[14:])
                        print("[*] 剪贴板图片设置成功")
                        return True
                    finally:
                        win32clipboard.CloseClipboard()
                except Exception as e:
                    print(f"[!] 第 {i+1} 次重试失败: {e}")
                    time.sleep(0.1)
            return False
        except Exception as e:
            print(f"[!] 设置剪贴板图片失败: {e}")
            return False

    def start_watching(self):
        """开启循环监听线程"""
        def watch_loop():
            while self._running:
                current_content = ClipboardService.get_clipboard_text()
                # 检测内容是否变化且不为空
                if current_content and current_content != self.last_content:
                    self.last_content = current_content
                    # 触发回调，将内容发送至手机端
                    self.on_update_callback(current_content)
                time.sleep(1) # 每秒轮询一次，平衡性能与实时性

        threading.Thread(target=watch_loop, daemon=True).start()
        print("[*] 剪贴板监控服务已就绪")

    @staticmethod
    def set_clipboard_text(text):
        """设置剪贴板内容（静态方法）"""
        try:
            print(f"[*] 设置剪贴板内容，长度: {len(text)}")
            import win32clipboard
        except ImportError:
            print("[!] 缺少 win32clipboard 模块")
            return False

        try:
            # 重试机制
            retry_count = 3
            for i in range(retry_count):
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
                        print("[*] 剪贴板设置成功")
                        return True
                    finally:
                        win32clipboard.CloseClipboard()
                except Exception as e:
                    print(f"[!] 第 {i+1} 次重试失败: {e}")
                    import time
                    time.sleep(0.1)
            return False
        except Exception as e:
            print(f"[!] 设置剪贴板失败: {e}")
            return False

    def stop(self):
        self._running = False
