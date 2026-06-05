"""剪贴板服务单元测试"""
import os
import sys
import unittest
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python", "linkflow"))

from core.clipboard_service import ClipboardService


class TestClipboardService(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        self.callback_called = False
        self.callback_content = None
        
        def callback(content):
            self.callback_called = True
            self.callback_content = content
        
        self.service = ClipboardService(on_update_callback=callback)
    
    def tearDown(self):
        """清理测试环境"""
        self.service.stop()
    
    def test_get_clipboard_text(self):
        """测试获取剪贴板文本"""
        # 设置剪贴板内容
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, "Test clipboard text")
            win32clipboard.CloseClipboard()
            
            # 获取剪贴板内容
            result = self.service.get_clipboard_text()
            self.assertEqual(result, "Test clipboard text")
        except ImportError:
            self.skipTest("pywin32 not available")
    
    def test_set_clipboard_text(self):
        """测试设置剪贴板文本"""
        try:
            import win32clipboard
            
            # 设置剪贴板内容
            result = self.service.set_clipboard_text("Set test text")
            self.assertTrue(result)
            
            # 验证剪贴板内容
            win32clipboard.OpenClipboard()
            content = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            self.assertEqual(content, "Set test text")
        except ImportError:
            self.skipTest("pywin32 not available")
    
    def test_set_clipboard_duplicate(self):
        """测试设置相同内容不触发回调"""
        try:
            # 设置初始内容
            self.service.set_clipboard_text("Same text")
            initial_last = self.service.last_content
            
            # 再次设置相同内容
            result = self.service.set_clipboard_text("Same text")
            self.assertTrue(result)
            
            # 验证 last_content 未变化
            self.assertEqual(self.service.last_content, initial_last)
        except ImportError:
            self.skipTest("pywin32 not available")
    
    def test_callback_on_change(self):
        """测试剪贴板变化时触发回调"""
        try:
            import win32clipboard
            
            # 启动监听
            self.service.start_watching()
            
            # 等待监听线程启动
            time.sleep(0.5)
            
            # 设置新的剪贴板内容
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, "Callback test")
            win32clipboard.CloseClipboard()
            
            # 等待回调触发
            time.sleep(1.5)
            
            # 验证回调被调用
            self.assertTrue(self.callback_called)
            self.assertEqual(self.callback_content, "Callback test")
        except ImportError:
            self.skipTest("pywin32 not available")
        finally:
            self.service.stop()


if __name__ == "__main__":
    unittest.main()
