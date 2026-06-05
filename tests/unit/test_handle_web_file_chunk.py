import base64
import os
import tempfile
import unittest

import main


class _BridgeStub:
    def __init__(self):
        self.messages = []

    def broadcast(self, data):
        self.messages.append(data)


class TestHandleWebFileChunk(unittest.IsolatedAsyncioTestCase):
    async def test_get_file_chunk(self):
        content = os.urandom(1024 + 7)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            file_path = f.name

        bridge = _BridgeStub()
        try:
            await main.handle_web_message(
                {
                    "type": "get_file_chunk",
                    "path": file_path,
                    "offset": 0,
                    "chunk_size": 2048,
                    "req_id": "r1",
                },
                bridge,
            )
            msg = bridge.messages[-1]
            self.assertEqual(msg["type"], "file_chunk")
            self.assertEqual(msg["req_id"], "r1")
            b = base64.b64decode(msg["data_b64"])
            self.assertEqual(b, content)
            self.assertTrue(msg["eof"])
        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass

