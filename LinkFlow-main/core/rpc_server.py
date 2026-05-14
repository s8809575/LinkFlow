import base64
import json
import socket
import threading
import time
import uuid

from core.monitor_service import MonitorService
from core.file_service import FileService
from core.rpc_crypto import AesGcmCipher, parse_key_b64
from core.rpc_framer import LengthPrefixedFramer


class LinkFlowRpcServer:
    def __init__(self, host="0.0.0.0", port=8089, pairing_id=None, pairing_key=None):
        self.host = host
        self.port = port
        self.pairing_id = pairing_id or str(uuid.uuid4())
        self.pairing_key = pairing_key or b""

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._running = False
        self._threads = []

    def get_pairing_info(self):
        return {
            "pairing_id": self.pairing_id,
            "key_b64": base64.b64encode(self.pairing_key).decode("ascii") if self.pairing_key else None,
            "port": self.port,
        }

    def start(self):
        self._server_socket.bind((self.host, self.port))
        self.port = self._server_socket.getsockname()[1]
        self._server_socket.listen(8)
        self._running = True
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()
        self._threads.append(t)

    def stop(self):
        self._running = False
        try:
            self._server_socket.close()
        except Exception:
            pass

    def _accept_loop(self):
        while self._running:
            try:
                client, _ = self._server_socket.accept()
            except OSError:
                break
            t = threading.Thread(target=self._client_loop, args=(client,), daemon=True)
            t.start()
            self._threads.append(t)

    def _client_loop(self, client):
        buf = b""
        secure = False
        framer = LengthPrefixedFramer()
        last_seen = time.time()
        try:
            while self._running:
                if time.time() - last_seen > 90:
                    break
                client.settimeout(1)
                try:
                    chunk = client.recv(65535)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                last_seen = time.time()
                while True:
                    msg_bytes, buf = framer.unpack_from_buffer(buf)
                    if msg_bytes is None:
                        break
                    res_bytes, secure_after, new_cipher = self._handle_message(msg_bytes, secure)
                    if res_bytes is not None:
                        client.sendall(framer.pack(res_bytes))
                    if secure_after and (not secure) and new_cipher:
                        secure = True
                        framer = LengthPrefixedFramer(cipher=new_cipher)
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _handle_message(self, msg_bytes, secure):
        try:
            req = json.loads(msg_bytes.decode("utf-8"))
        except Exception:
            return (
                json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}).encode(
                    "utf-8"
                ),
                False,
                None,
            )

        method = req.get("method")
        req_id = req.get("id")
        params = req.get("params") or {}

        if method == "pair.bind":
            pairing_id = params.get("pairing_id")
            key_b64 = params.get("key_b64")
            if pairing_id != self.pairing_id or not key_b64:
                return self._error(req_id, -32000, "PAIRING_DENIED"), False, None
            try:
                key = parse_key_b64(key_b64)
            except Exception:
                return self._error(req_id, -32602, "BAD_KEY"), False, None
            if self.pairing_key and self.pairing_key != key:
                return self._error(req_id, -32000, "PAIRING_DENIED"), False, None
            cipher = AesGcmCipher(key)
            return self._result(req_id, {"status": "ok"}), True, cipher

        if not secure:
            return self._error(req_id, -32001, "SECURE_CHANNEL_REQUIRED"), False, None

        if method == "system.stats":
            return self._result(req_id, MonitorService.get_system_stats()), False, None

        if method == "system.control":
            cmd = params.get("cmd")
            ok = MonitorService.execute_control_command(cmd)
            return self._result(req_id, {"status": "ok" if ok else "fail", "cmd": cmd}), False, None

        if method == "file.list":
            path = params.get("path", "C:/")
            return self._result(req_id, {"path": path, "list": FileService.get_directory_info(path)}), False, None

        if method == "file.stat":
            path = params.get("path")
            try:
                import os

                size = os.path.getsize(path)
                return self._result(req_id, {"path": path, "size": size}), False, None
            except Exception:
                return self._error(req_id, -32011, "STAT_FAIL"), False, None

        if method == "file.read_chunk":
            import zlib

            path = params.get("path")
            offset = int(params.get("offset", 0))
            size = int(params.get("size", 256 * 1024))
            chunk = FileService.read_file_chunk(path, offset, chunk_size=size)
            if chunk is None:
                return self._error(req_id, -32010, "READ_FAIL"), False, None
            crc = zlib.crc32(chunk) & 0xFFFFFFFF
            return (
                self._result(
                    req_id,
                    {
                        "path": path,
                        "offset": offset,
                        "size": len(chunk),
                        "eof": len(chunk) < size,
                        "crc32": crc,
                        "data_b64": base64.b64encode(chunk).decode("ascii"),
                    },
                ),
                False,
                None,
            )

        if method == "notify.push":
            title = params.get("title")
            body = params.get("body")
            return self._result(req_id, {"status": "ok", "title": title, "body": body}), False, None

        if method == "sys.heartbeat":
            return self._result(req_id, {"ts": int(time.time())}), False, None

        return self._error(req_id, -32601, "METHOD_NOT_FOUND"), False, None

    def _result(self, req_id, result):
        return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}).encode("utf-8")

    def _error(self, req_id, code, message):
        return json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}).encode("utf-8")

