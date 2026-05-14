import base64
import json
import os
import socket
import tempfile
import time
import unittest

from core.protocol import LinkFlowProtocol
from core.server import LinkFlowServer


class TestFileChunk(unittest.TestCase):
    def test_file_chunk_roundtrip(self):
        content = os.urandom(1024 * 1024 + 123)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            file_path = f.name

        server = LinkFlowServer(host="127.0.0.1", port=0)
        server.start()
        try:
            time.sleep(0.1)
            client = socket.create_connection(("127.0.0.1", server.port), timeout=2)
            with client:
                req1 = {
                    "path": file_path,
                    "offset": 0,
                    "chunk_size": 1024 * 1024,
                }
                client.sendall(LinkFlowProtocol.pack(LinkFlowProtocol.TYPE_FILE_CHUNK_REQ, req1))

                header = client.recv(5)
                msg_type, length = LinkFlowProtocol.unpack_header(header)
                payload = b""
                while len(payload) < length:
                    payload += client.recv(length - len(payload))

                self.assertEqual(msg_type, LinkFlowProtocol.TYPE_FILE_DATA)
                data = json.loads(payload.decode("utf-8"))
                self.assertFalse(data["eof"])
                b = base64.b64decode(data["data_b64"])
                self.assertEqual(b, content[: 1024 * 1024])

                req2 = {
                    "path": file_path,
                    "offset": 1024 * 1024,
                    "chunk_size": 1024 * 1024,
                }
                client.sendall(LinkFlowProtocol.pack(LinkFlowProtocol.TYPE_FILE_CHUNK_REQ, req2))

                header = client.recv(5)
                msg_type, length = LinkFlowProtocol.unpack_header(header)
                payload = b""
                while len(payload) < length:
                    payload += client.recv(length - len(payload))

                self.assertEqual(msg_type, LinkFlowProtocol.TYPE_FILE_DATA)
                data = json.loads(payload.decode("utf-8"))
                self.assertTrue(data["eof"])
                b = base64.b64decode(data["data_b64"])
                self.assertEqual(b, content[1024 * 1024 :])
        finally:
            server.stop()
            try:
                os.remove(file_path)
            except Exception:
                pass

