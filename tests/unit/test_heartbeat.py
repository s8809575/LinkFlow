import os
import sys
import socket
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python", "linkflow"))

from core.protocol import LinkFlowProtocol
from core.server import LinkFlowServer


class TestHeartbeat(unittest.TestCase):
    def test_heartbeat_ack(self):
        server = LinkFlowServer(host="127.0.0.1", port=0)
        server.start()
        try:
            time.sleep(0.1)
            client = socket.create_connection(("127.0.0.1", server.port), timeout=2)
            with client:
                client.sendall(LinkFlowProtocol.pack(LinkFlowProtocol.TYPE_HEARTBEAT, b""))
                header = client.recv(5)
                msg_type, length = LinkFlowProtocol.unpack_header(header)
                self.assertEqual(msg_type, LinkFlowProtocol.TYPE_HEARTBEAT)
                self.assertEqual(length, 0)
        finally:
            server.stop()

