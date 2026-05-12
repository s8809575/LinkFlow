"""
模块D: ClipboardService 单元测试
覆盖: get_clipboard_text, set_clipboard_text, 防回环
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestClipboardServiceGet(unittest.TestCase):
    @patch("core.clipboard_service.win32clipboard")
    def test_get_returns_text(self, mock_wb):
        """UT-CB-01: get_clipboard_text 返回字符串"""
        mock_wb.CF_UNICODETEXT = 13
        mock_wb.OpenClipboard.return_value = None
        mock_wb.GetClipboardData.return_value = "hello"
        mock_wb.CloseClipboard.return_value = None

        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: None)
        result = svc.get_clipboard_text()
        self.assertEqual(result, "hello")

    @patch("core.clipboard_service.win32clipboard")
    def test_get_returns_none_when_empty(self, mock_wb):
        """UT-CB-E01: 剪贴板为空时返回 None"""
        mock_wb.OpenClipboard.side_effect = Exception("empty")
        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: None)
        result = svc.get_clipboard_text()
        self.assertIsNone(result)

    @patch("core.clipboard_service.win32clipboard")
    def test_get_updates_last_content(self, mock_wb):
        """M5: get 后 _last_content 同步"""
        mock_wb.CF_UNICODETEXT = 13
        mock_wb.OpenClipboard.return_value = None
        mock_wb.GetClipboardData.return_value = "synced"
        mock_wb.CloseClipboard.return_value = None

        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: None)
        svc.get_clipboard_text()
        self.assertEqual(svc._last_content, "synced")

    @patch("core.clipboard_service.win32clipboard")
    def test_get_no_callback_trigger(self, mock_wb):
        """get_clipboard_text 不触发回调"""
        callback_calls = []
        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: callback_calls.append(x))
        svc.get_clipboard_text()
        self.assertEqual(callback_calls, [])


class TestClipboardServiceSet(unittest.TestCase):
    @patch("core.clipboard_service.win32clipboard")
    def test_set_returns_true_on_success(self, mock_wb):
        """UT-CB-02: set_clipboard_text 成功返回 True"""
        mock_wb.OpenClipboard.return_value = None
        mock_wb.CloseClipboard.return_value = None

        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: None)
        ok = svc.set_clipboard_text("world")
        self.assertTrue(ok)

    @patch("core.clipboard_service.win32clipboard")
    def test_set_updates_last_content(self, mock_wb):
        """set 后 _last_content 和 _set_by_us_content 同步"""
        mock_wb.OpenClipboard.return_value = None
        mock_wb.CloseClipboard.return_value = None

        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: None)
        svc.set_clipboard_text("marked")
        self.assertEqual(svc._last_content, "marked")
        self.assertEqual(svc._set_by_us_content, "marked")

    @patch("core.clipboard_service.win32clipboard")
    def test_set_same_as_last_returns_true_without_write(self, mock_wb):
        """重复设置相同内容不重复写入"""
        mock_wb.OpenClipboard.return_value = None
        mock_wb.CloseClipboard.return_value = None

        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: None)
        svc.set_clipboard_text("same")
        svc.set_clipboard_text("same")
        # OpenClipboard 只应被调用一次（第二次因 last_content 相同跳过）
        self.assertEqual(mock_wb.OpenClipboard.call_count, 1)

    @patch("core.clipboard_service.win32clipboard")
    def test_set_raises_when_win32_unavailable(self, mock_wb):
        """UT-CB-E02: pywin32 不可用时返回 False"""
        mock_wb.OpenClipboard.side_effect = ImportError
        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: None)
        ok = svc.set_clipboard_text("text")
        self.assertFalse(ok)


class TestClipboardServiceWatchLoop(unittest.TestCase):
    @patch("core.clipboard_service.win32clipboard")
    def test_watch_loop_no_callback_on_set_by_us(self, mock_wb):
        """UT-CB-E04: 自己 set 的内容不触发回调（防回环）"""
        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: x)

        # 模拟刚写入的内容
        svc._last_content = "myself"
        svc._set_by_us_content = "myself"
        current = "myself"

        callback_calls = []
        with svc._lock:
            if svc._set_by_us_content is not None and current == svc._set_by_us_content:
                svc._set_by_us_content = None
            else:
                callback_calls.append(current)

        self.assertEqual(callback_calls, [])
        self.assertIsNone(svc._set_by_us_content)

    @patch("core.clipboard_service.win32clipboard")
    def test_init_last_content_is_none(self, mock_wb):
        """L4: 初始化时 _last_content 为 None，等待 watch_loop 同步"""
        from core.clipboard_service import ClipboardService
        svc = ClipboardService(on_update_callback=lambda x: None)
        self.assertIsNone(svc._last_content)


if __name__ == "__main__":
    unittest.main()
