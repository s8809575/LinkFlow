import base64
import json
import os
import socket
import time
import unittest


class TestRpcServerPairing(unittest.TestCase):
    def test_pair_bind_then_encrypted_request(self):
        from core.rpc_server import LinkFlowRpcServer
        from core.rpc_crypto import AesGcmCipher
        from core.rpc_framer import LengthPrefixedFramer

        key = os.urandom(16)
        pairing_id = "p1"
        server = LinkFlowRpcServer(host="127.0.0.1", port=0, pairing_id=pairing_id, pairing_key=key)
        server.start()
        try:
            time.sleep(0.1)
            info = server.get_pairing_info()
            self.assertEqual(info["pairing_id"], pairing_id)
            self.assertEqual(base64.b64decode(info["key_b64"]), key)
            s = socket.create_connection(("127.0.0.1", server.port), timeout=2)
            with s:
                plain = LengthPrefixedFramer()
                bind_req = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "pair.bind",
                    "params": {"pairing_id": pairing_id, "key_b64": base64.b64encode(key).decode("ascii")},
                }
                s.sendall(plain.pack(json.dumps(bind_req).encode("utf-8")))

                data = s.recv(4096)
                res_bytes, _ = plain.unpack_from_buffer(data)
                res = json.loads(res_bytes.decode("utf-8"))
                self.assertEqual(res["result"]["status"], "ok")

                cipher = AesGcmCipher(key)
                secure = LengthPrefixedFramer(cipher=cipher)
                stats_req = {"jsonrpc": "2.0", "id": 2, "method": "system.stats", "params": {}}
                s.sendall(secure.pack(json.dumps(stats_req).encode("utf-8")))

                data = s.recv(65535)
                res_bytes, _ = secure.unpack_from_buffer(data)
                res = json.loads(res_bytes.decode("utf-8"))
                self.assertEqual(res["id"], 2)
                self.assertIn("cpu_percent", res["result"])

                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as f:
                    f.write(b"abc")
                    f.flush()
                    p = f.name
                try:
                    stat_req = {"jsonrpc": "2.0", "id": 3, "method": "file.stat", "params": {"path": p}}
                    s.sendall(secure.pack(json.dumps(stat_req).encode("utf-8")))
                    data = s.recv(65535)
                    res_bytes, _ = secure.unpack_from_buffer(data)
                    res = json.loads(res_bytes.decode("utf-8"))
                    self.assertEqual(res["result"]["size"], 3)
                finally:
                    os.remove(p)
        finally:
            server.stop()

