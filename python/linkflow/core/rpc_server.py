import base64
import json
import os
import socket
import threading
import time
import uuid

from linkflow.core.monitor_service import MonitorService
from linkflow.core.file_service import FileService
from linkflow.core.file_uploader import FileUploader
from linkflow.core.audit_service import AuditService
from linkflow.core.rpc_crypto import AesGcmCipher, parse_key_b64
from linkflow.core.rpc_framer import LengthPrefixedFramer


class LinkFlowRpcServer:
    def __init__(self, host="0.0.0.0", port=8089, pairing_id=None, pairing_key=None, clipboard_service=None):
        self.host = host
        self.port = port
        self.pairing_id = pairing_id or str(uuid.uuid4())
        self.pairing_key = pairing_key or b""
        self._uploader = FileUploader()
        self._clipboard_service = clipboard_service
        self._audit_service = AuditService()
        self._allowed_roots = None
        self._allowed_roots_lock = threading.Lock()
        self._reload_allowed_roots()

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._running = False
        self._threads = []

    def _reload_allowed_roots(self):
        roots = os.getenv("LINKFLOW_ALLOWED_ROOTS", "").strip()
        with self._allowed_roots_lock:
            if roots:
                self._allowed_roots = []
                for r in roots.split(";"):
                    r = r.strip()
                    if not r:
                        continue
                    if "|" in r:
                        path, perm = r.rsplit("|", 1)
                        self._allowed_roots.append({"path": path, "perm": perm})
                    else:
                        self._allowed_roots.append({"path": r, "perm": "rw"})
            else:
                self._allowed_roots = []
        print(f"[RPC服务] 已更新允许路径: {self._allowed_roots}")

    def add_allowed_root(self, path, perm="rw"):
        entry = {"path": path, "perm": perm}
        with self._allowed_roots_lock:
            if self._allowed_roots is None:
                self._allowed_roots = [entry]
            else:
                existing = [i for i, e in enumerate(self._allowed_roots) if e.get("path") == path]
                if existing:
                    self._allowed_roots[existing[0]] = entry
                else:
                    self._allowed_roots.append(entry)
        self._update_env_var()
        print(f"[RPC服务] 已添加允许路径: {path} (权限: {perm})")

    def remove_allowed_root(self, path):
        with self._allowed_roots_lock:
            if self._allowed_roots is None:
                return
            self._allowed_roots = [e for e in self._allowed_roots if e.get("path") != path]
        self._update_env_var()
        print(f"[RPC服务] 已删除允许路径: {path}")

    def _update_env_var(self):
        with self._allowed_roots_lock:
            if self._allowed_roots:
                os.environ["LINKFLOW_ALLOWED_ROOTS"] = ";".join(
                    f'{e.get("path")}|{e.get("perm")}' for e in self._allowed_roots
                )
            else:
                os.environ["LINKFLOW_ALLOWED_ROOTS"] = ""

    @property
    def allowed_roots(self):
        with self._allowed_roots_lock:
            return self._allowed_roots.copy() if self._allowed_roots is not None else None

    def set_clipboard_service(self, service):
        self._clipboard_service = service

    def _audit(self, action, result, details=None):
        self._audit_service.record(
            device="rpc_client",
            action=action,
            result=result,
            details=details
        )

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
            allowed_roots = self._allowed_roots
            if allowed_roots and not FileService.is_path_allowed(path, allowed_roots):
                return self._error(req_id, -32009, "PATH_NOT_ALLOWED"), False, None
            dir_info = FileService.get_directory_info(path, allowed_roots)
            if isinstance(dir_info, dict) and "error" in dir_info:
                return self._error(req_id, -32009, dir_info["error"]), False, None
            return self._result(req_id, {"path": path, "list": dir_info}), False, None

        if method == "file.stat":
            path = params.get("path")
            allowed_roots = self._allowed_roots
            if allowed_roots and not FileService.is_path_allowed(path, allowed_roots):
                return self._error(req_id, -32009, "PATH_NOT_ALLOWED"), False, None
            try:
                size = os.path.getsize(path)
                return self._result(req_id, {"path": path, "size": size}), False, None
            except Exception:
                return self._error(req_id, -32011, "STAT_FAIL"), False, None

        if method == "file.read_chunk":
            import zlib

            path = params.get("path")
            allowed_roots = self._allowed_roots
            if allowed_roots and not FileService.is_path_allowed(path, allowed_roots):
                return self._error(req_id, -32009, "PATH_NOT_ALLOWED"), False, None
            offset = int(params.get("offset", 0))
            size = int(params.get("size", 256 * 1024))
            chunk = FileService.read_file_chunk(path, offset, chunk_size=size, allowed_roots=allowed_roots)
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

        if method == "file.upload_init":
            filename = params.get("filename")
            size = int(params.get("size", 0))
            crc32 = int(params.get("crc32", 0))
            result = self._uploader.init_upload(filename, size, crc32)
            return self._result(req_id, result), False, None

        if method == "file.upload_chunk":
            session_id = params.get("session_id")
            offset = int(params.get("offset", 0))
            data_b64 = params.get("data_b64", "")
            result = self._uploader.write_chunk(session_id, offset, data_b64)
            return self._result(req_id, result), False, None

        if method == "file.upload_commit":
            session_id = params.get("session_id")
            result = self._uploader.commit_upload(session_id)
            return self._result(req_id, result), False, None

        if method == "file.upload_cancel":
            session_id = params.get("session_id")
            result = self._uploader.cancel_upload(session_id)
            return self._result(req_id, result), False, None

        if method == "clipboard.get":
            if self._clipboard_service:
                text = self._clipboard_service.get_clipboard_text()
                return self._result(req_id, {"text": text or "", "ts": int(time.time())}), False, None
            else:
                return self._error(req_id, -32012, "CLIPBOARD_SERVICE_NOT_AVAILABLE"), False, None

        if method == "clipboard.set":
            if self._clipboard_service:
                text = params.get("text", "")
                success = self._clipboard_service.set_clipboard_text(text)
                return self._result(req_id, {"status": "ok" if success else "fail"}), False, None
            else:
                return self._error(req_id, -32012, "CLIPBOARD_SERVICE_NOT_AVAILABLE"), False, None

        if method == "screen.snapshot":
            result = MonitorService.get_screen_snapshot()
            if "error" in result:
                return self._error(req_id, -32013, result["error"]), False, None
            result["ts"] = int(time.time())
            return self._result(req_id, result), False, None

        if method == "audit.query":
            start_ts = params.get("start_ts")
            end_ts = params.get("end_ts")
            action_filter = params.get("action")
            records = self._audit_service.query(start_ts, end_ts, action_filter)
            return self._result(req_id, records), False, None

        if method == "audit.stats":
            stats = self._audit_service.get_stats()
            return self._result(req_id, stats), False, None

        return self._error(req_id, -32601, "METHOD_NOT_FOUND"), False, None

    def _result(self, req_id, result):
        return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}).encode("utf-8")

    def _error(self, req_id, code, message):
        return json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}).encode("utf-8")
