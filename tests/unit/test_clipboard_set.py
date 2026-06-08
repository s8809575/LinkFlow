import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python", "linkflow"))

from core.clipboard_service import ClipboardService


class _Win32ClipboardStub:
    CF_UNICODETEXT = 13

    def __init__(self):
        self.data = None

    def OpenClipboard(self):
        return None

    def CloseClipboard(self):
        return None

    def EmptyClipboard(self):
        return None

    def SetClipboardData(self, fmt, text):
        self.data = (fmt, text)
        return None


class TestClipboardSet(unittest.TestCase):
    def test_set_clipboard_text_writes(self):
        stub = _Win32ClipboardStub()
        sys.modules["win32clipboard"] = stub
        try:
            c = ClipboardService(on_update_callback=lambda _: None)
            ok = c.set_clipboard_text("hello")
            self.assertTrue(ok)
            self.assertEqual(stub.data, (stub.CF_UNICODETEXT, "hello"))
        finally:
            sys.modules.pop("win32clipboard", None)

    def test_set_clipboard_text_skips_same_content(self):
        stub = _Win32ClipboardStub()
        sys.modules["win32clipboard"] = stub
        try:
            c = ClipboardService(on_update_callback=lambda _: None)
            c.last_content = "same"
            ok = c.set_clipboard_text("same")
            self.assertTrue(ok)
            self.assertIsNone(stub.data)
        finally:
            sys.modules.pop("win32clipboard", None)

