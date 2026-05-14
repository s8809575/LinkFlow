import tempfile
import unittest
from unittest import mock

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

