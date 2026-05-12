"""
模块D: RPC Server 新增方法集成测试
覆盖: clipboard.get, screen.snapshot, file.upload_*, audit.query 的权限与异常路径
"""
import base64
import json
import os
import socket
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rpc_server import LinkFlowRpcServer
from core.rpc_crypto import AesGcmCipher
from core.rpc_framer import LengthPrefixedFramer


class RPCTestHelper:
    def __init__(self, port):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.framer = LengthPrefixedFramer()

    def send_plain(self, req):
        self.s.sendall(self.framer.pack(json.dumps(req).encode("utf-8")))
        return self._recv()

    def send_secure(self, req, cipher):
        secure_framer = LengthPrefixedFramer(cipher=cipher)
        self.s.sendall(secure_framer.pack(json.dumps(req).encode("utf-8")))
        return self._recv(secure_framer)

    def _recv(self, framer=None):
        framer = framer or self.framer
        data = self.s.recv(65535)
        res_bytes, _ = framer.unpack_from_buffer(data)
        return json.loads(res_bytes.decode("utf-8"))

    def close(self):
        self.s.close()


class TestModuleDInsecureRequests(unittest.TestCase):
    """权限边界测试: 未建立安全通道时，高危方法应被拒绝"""

    @classmethod
    def setUpClass(cls):
        key = os.urandom(16)
        cls.pairing_id = "test-pair"
        cls.server = LinkFlowRpcServer(
            host="127.0.0.1", port=0,
            pairing_id=cls.pairing_id,
            pairing_key=key
        )
        cls.server.start()
        time.sleep(0.1)
        cls.port = cls.server.port
        cls.key = key

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_screen_snapshot_requires_secure(self):
        """UT-RS-E01: screen.snapshot 未配对返回 SECURE_CHANNEL_REQUIRED"""
        helper = RPCTestHelper(self.port)
        res = helper.send_plain({
            "jsonrpc": "2.0", "id": 10,
            "method": "screen.snapshot", "params": {}
        })
        self.assertEqual(res["error"]["code"], -32001)
        helper.close()

    def test_clipboard_get_requires_secure(self):
        """UT-RS-E03: clipboard.get 未配对返回 SECURE_CHANNEL_REQUIRED"""
        helper = RPCTestHelper(self.port)
        res = helper.send_plain({
            "jsonrpc": "2.0", "id": 11,
            "method": "clipboard.get", "params": {}
        })
        self.assertEqual(res["error"]["code"], -32001)
        helper.close()

    def test_upload_init_requires_secure(self):
        """UT-RS-E02: file.upload_init 未配对返回 SECURE_CHANNEL_REQUIRED"""
        helper = RPCTestHelper(self.port)
        res = helper.send_plain({
            "jsonrpc": "2.0", "id": 12,
            "method": "file.upload_init", "params": {"path": "C:/test.bin", "total_chunks": 1}
        })
        self.assertEqual(res["error"]["code"], -32001)
        helper.close()

    def test_audit_query_requires_secure(self):
        """UT-RS-E12: audit.query 未配对返回 SECURE_CHANNEL_REQUIRED"""
        helper = RPCTestHelper(self.port)
        res = helper.send_plain({
            "jsonrpc": "2.0", "id": 13,
            "method": "audit.query", "params": {"start_ts": 0, "end_ts": 0}
        })
        self.assertEqual(res["error"]["code"], -32001)
        helper.close()


class TestModuleDSecureRequests(unittest.TestCase):
    """已配对后的方法测试"""

    @classmethod
    def setUpClass(cls):
        key = os.urandom(16)
        cls.pairing_id = "test-pair-2"
        cls.server = LinkFlowRpcServer(
            host="127.0.0.1", port=0,
            pairing_id=cls.pairing_id,
            pairing_key=key
        )
        cls.server.start()
        time.sleep(0.1)
        cls.port = cls.server.port
        cls.key = key

        cls.helper = RPCTestHelper(cls.port)
        cls.cipher = AesGcmCipher(key)
        bind_res = cls.helper.send_plain({
            "jsonrpc": "2.0", "id": 1,
            "method": "pair.bind",
            "params": {"pairing_id": cls.pairing_id, "key_b64": base64.b64encode(key).decode()}
        })
        assert bind_res["result"]["status"] == "ok"

    @classmethod
    def tearDownClass(cls):
        cls.helper.close()
        cls.server.stop()

    def test_sys_heartbeat(self):
        """UT-RS-07: sys.heartbeat 返回时间戳"""
        res = self.helper.send_secure({
            "jsonrpc": "2.0", "id": 20,
            "method": "sys.heartbeat", "params": {}
        }, self.cipher)
        self.assertEqual(res["id"], 20)
        self.assertIn("ts", res["result"])

    def test_screen_snapshot(self):
        """UT-RS-02: screen.snapshot 返回结构"""
        res = self.helper.send_secure({
            "jsonrpc": "2.0", "id": 21,
            "method": "screen.snapshot", "params": {}
        }, self.cipher)
        self.assertEqual(res["id"], 21)
        if "error" in res:
            self.assertEqual(res["error"]["code"], -32012)
        else:
            self.assertIn("data_b64", res["result"])
            self.assertIn("timestamp", res["result"])

    def test_clipboard_get(self):
        """UT-RS-01: clipboard.get 返回 text 字段"""
        res = self.helper.send_secure({
            "jsonrpc": "2.0", "id": 22,
            "method": "clipboard.get", "params": {}
        }, self.cipher)
        self.assertEqual(res["id"], 22)
        self.assertIn("text", res["result"])

    def test_upload_init_and_cancel(self):
        """UT-RS-03 + cancel: 创建上传会话后取消"""
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "upload.bin")
            res = self.helper.send_secure({
                "jsonrpc": "2.0", "id": 23,
                "method": "file.upload_init",
                "params": {"path": dest, "total_chunks": 3}
            }, self.cipher)
            self.assertEqual(res["id"], 23)
            self.assertIn("upload_id", res["result"])
            uid = res["result"]["upload_id"]

            from core.upload_service import UploadService
            UploadService.cancel_session(uid)
            status = UploadService.get_session_status(uid)
            self.assertFalse(status["exists"])

    def test_upload_init_total_chunks_zero(self):
        """UT-RS-E05: total_chunks=0 返回 INVALID_TOTAL_CHUNKS"""
        with tempfile.TemporaryDirectory() as d:
            res = self.helper.send_secure({
                "jsonrpc": "2.0", "id": 24,
                "method": "file.upload_init",
                "params": {"path": os.path.join(d, "x.bin"), "total_chunks": 0}
            }, self.cipher)
            self.assertEqual(res["error"]["code"], -32018)
            self.assertIn("INVALID_TOTAL_CHUNKS", res["error"]["message"])

    def test_upload_init_path_not_allowed(self):
        """UT-RS-E04: 路径非法返回 PATH_NOT_ALLOWED"""
        with tempfile.TemporaryDirectory() as d:
            orig = os.environ.get("LINKFLOW_ALLOWED_ROOTS")
            os.environ["LINKFLOW_ALLOWED_ROOTS"] = d
            try:
                res = self.helper.send_secure({
                    "jsonrpc": "2.0", "id": 25,
                    "method": "file.upload_init",
                    "params": {"path": "/etc/evil", "total_chunks": 1}
                }, self.cipher)
                self.assertEqual(res["error"]["code"], -32018)
                self.assertIn("PATH_NOT_ALLOWED", res["error"]["message"])
            finally:
                if orig is None:
                    os.environ.pop("LINKFLOW_ALLOWED_ROOTS", None)
                else:
                    os.environ["LINKFLOW_ALLOWED_ROOTS"] = orig

    def test_upload_chunk_invalid_id(self):
        """UT-RS-E07: 不存在的 upload_id"""
        res = self.helper.send_secure({
            "jsonrpc": "2.0", "id": 26,
            "method": "file.upload_chunk",
            "params": {"upload_id": "no-such-id", "chunk_index": 0, "data_b64": base64.b64encode(b"x").decode()}
        }, self.cipher)
        self.assertEqual(res["error"]["code"], -32015)

    def test_upload_chunk_invalid_base64(self):
        """UT-RS-E12: 无效 base64 返回 INVALID_DATA"""
        with tempfile.TemporaryDirectory() as d:
            init_res = self.helper.send_secure({
                "jsonrpc": "2.0", "id": 270,
                "method": "file.upload_init",
                "params": {"path": os.path.join(d, "x.bin"), "total_chunks": 1}
            }, self.cipher)
            uid = init_res["result"]["upload_id"]

            res = self.helper.send_secure({
                "jsonrpc": "2.0", "id": 271,
                "method": "file.upload_chunk",
                "params": {"upload_id": uid, "chunk_index": 0, "data_b64": "not-valid-base64!!!"}
            }, self.cipher)
            self.assertEqual(res["error"]["code"], -32014)

            from core.upload_service import UploadService
            UploadService.cancel_session(uid)

    def test_upload_commit_session_not_found(self):
        """UT-RS-E07b: commit 不存在的 session"""
        res = self.helper.send_secure({
            "jsonrpc": "2.0", "id": 28,
            "method": "file.upload_commit",
            "params": {"upload_id": "no-such"}
        }, self.cipher)
        self.assertEqual(res["error"]["code"], -32016)
        self.assertIn("SESSION_NOT_FOUND", res["error"]["message"])

    def test_upload_full_flow(self):
        """UT-RS-03~05: 完整上传链路"""
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "out.bin")
            init_res = self.helper.send_secure({
                "jsonrpc": "2.0", "id": 300,
                "method": "file.upload_init",
                "params": {"path": dest, "total_chunks": 3}
            }, self.cipher)
            uid = init_res["result"]["upload_id"]

            for i in range(3):
                chunk_res = self.helper.send_secure({
                    "jsonrpc": "2.0", "id": 301 + i,
                    "method": "file.upload_chunk",
                    "params": {
                        "upload_id": uid,
                        "chunk_index": i,
                        "data_b64": base64.b64encode(f"chunk{i}".encode()).decode()
                    }
                }, self.cipher)
                self.assertEqual(chunk_res["id"], 301 + i)
                self.assertTrue(chunk_res["result"]["ok"])

            commit_res = self.helper.send_secure({
                "jsonrpc": "2.0", "id": 304,
                "method": "file.upload_commit",
                "params": {"upload_id": uid}
            }, self.cipher)
            self.assertEqual(commit_res["id"], 304)
            self.assertTrue(commit_res["result"]["ok"])
            self.assertTrue(os.path.exists(dest))
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"chunk0chunk1chunk2")

    def test_audit_query(self):
        """UT-RS-06: audit.query 返回日志列表"""
        from core.audit_service import AuditService
        AuditService.clear()
        AuditService.log("test-device", "test-action", "ok")

        res = self.helper.send_secure({
            "jsonrpc": "2.0", "id": 40,
            "method": "audit.query",
            "params": {"start_ts": 0, "end_ts": 0, "limit": 10}
        }, self.cipher)
        self.assertEqual(res["id"], 40)
        self.assertIn("logs", res["result"])
        self.assertIn("count", res["result"])
        self.assertGreaterEqual(res["result"]["count"], 1)


class TestMalformedRPC(unittest.TestCase):
    """畸形请求测试"""

    @classmethod
    def setUpClass(cls):
        key = os.urandom(16)
        cls.server = LinkFlowRpcServer(host="127.0.0.1", port=0, pairing_key=key)
        cls.server.start()
        time.sleep(0.1)
        cls.port = cls.server.port

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_malformed_json(self):
        """UT-RS-E10: 畸形 JSON 返回 Parse error"""
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        framer = LengthPrefixedFramer()
        s.sendall(framer.pack(b"not json at all"))
        data = s.recv(4096)
        res_bytes, _ = framer.unpack_from_buffer(data)
        res = json.loads(res_bytes.decode("utf-8"))
        self.assertEqual(res["error"]["code"], -32700)
        s.close()

    def test_unknown_method(self):
        """UT-RS-E11: 不存在的方法返回 METHOD_NOT_FOUND"""
        helper = RPCTestHelper(self.port)
        res = helper.send_plain({
            "jsonrpc": "2.0", "id": 99,
            "method": "nonexistent.method", "params": {}
        })
        self.assertEqual(res["error"]["code"], -32601)
        helper.close()


if __name__ == "__main__":
    unittest.main()
