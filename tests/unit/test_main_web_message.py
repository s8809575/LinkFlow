import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python"))
import main


class _BridgeStub:
    def __init__(self):
        self.messages = []

    def broadcast(self, data):
        self.messages.append(data)


class TestMainWebMessage(unittest.IsolatedAsyncioTestCase):
    async def test_handle_web_message_get_files(self):
        bridge = _BridgeStub()
        with tempfile.TemporaryDirectory() as tmpdir:
            await main.handle_web_message({"type": "get_files", "path": tmpdir}, bridge)
        self.assertTrue(any(m.get("type") == "file_list" for m in bridge.messages))

    async def test_handle_web_message_control(self):
        bridge = _BridgeStub()
        with mock.patch("core.monitor_service.MonitorService.execute_control_command") as m:
            m.return_value = True
            await main.handle_web_message({"type": "control", "cmd": "mute"}, bridge)
        self.assertTrue(any(m.get("type") == "control_result" for m in bridge.messages))

    async def test_handle_web_message_init_upload_passes_target_path(self):
        bridge = _BridgeStub()
        uploader = mock.Mock()
        uploader.init_upload.return_value = {"status": "ok", "session_id": "sid-1"}

        with mock.patch.object(main, "uploader_ref", uploader):
            await main.handle_web_message(
                {
                    "type": "init_upload",
                    "filename": "resume.pdf",
                    "size": 12,
                    "crc32": 123,
                    "target_path": "E:/Homework",
                },
                bridge,
            )

        uploader.init_upload.assert_called_once_with("resume.pdf", 12, 123, "E:/Homework")
        self.assertTrue(any(m.get("status") == "ok" for m in bridge.messages))

