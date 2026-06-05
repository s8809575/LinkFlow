import os
import sys
import socket
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python", "linkflow"))

from core.server import LinkFlowServer
from core.protocol import LinkFlowProtocol


class TestLinkFlowServer(unittest.TestCase):
    def test_start_updates_ephemeral_port(self):
        server = LinkFlowServer(host="127.0.0.1", port=0)
        server.start()
        try:
            self.assertNotEqual(server.port, 0)
            self.assertGreater(server.port, 0)
        finally:
            if hasattr(server, "stop"):
                server.stop()

    def test_file_list_request_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = LinkFlowServer(host="127.0.0.1", port=0)
            server.start()
            try:
                time.sleep(0.1)
                client = socket.create_connection(("127.0.0.1", server.port), timeout=2)
                with client:
                    req = LinkFlowProtocol.pack(
                        LinkFlowProtocol.TYPE_FILE_LIST, {"path": tmpdir}
                    )
                    client.sendall(req)

                    header = client.recv(5)
                    msg_type, length = LinkFlowProtocol.unpack_header(header)
                    payload = b""
                    while len(payload) < length:
                        payload += client.recv(length - len(payload))

                    self.assertEqual(msg_type, LinkFlowProtocol.TYPE_FILE_LIST)
                    data = payload.decode("utf-8")
                    self.assertIn("[", data)
            finally:
                if hasattr(server, "stop"):
                    server.stop()

