import socket
import threading
from linkflow.core.protocol import LinkFlowProtocol
import json
import base64
import time
import os

class LinkFlowServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.is_running = False
        self.client_socket = None
        self._client_last_seen = {}
        self._client_lock = threading.Lock()
        self.heartbeat_timeout_sec = 15
        self.on_device_connected = None  # 设备连接回调
        self.on_device_disconnected = None  # 设备断开回调
        self._allowed_roots = None  # 内部存储
        self._allowed_roots_lock = threading.Lock()  # 锁保护
        self._reload_allowed_roots()  # 初始加载
    
    def _reload_allowed_roots(self):
        """重新从环境变量加载允许的根路径"""
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
        print(f"[文件服务] 已更新允许路径: {self._allowed_roots}")

    def add_allowed_root(self, path, perm="rw"):
        """添加一个允许的根路径"""
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
        print(f"[文件服务] 已添加允许路径: {path} (权限: {perm})")

    def remove_allowed_root(self, path):
        """删除一个允许的根路径"""
        with self._allowed_roots_lock:
            if self._allowed_roots is None:
                return
            self._allowed_roots = [e for e in self._allowed_roots if e.get("path") != path]
        self._update_env_var()
        print(f"[文件服务] 已删除允许路径: {path}")

    def _update_env_var(self):
        """更新环境变量"""
        with self._allowed_roots_lock:
            if self._allowed_roots:
                os.environ["LINKFLOW_ALLOWED_ROOTS"] = ";".join(
                    f'{e.get("path")}|{e.get("perm")}' for e in self._allowed_roots
                )
            else:
                os.environ["LINKFLOW_ALLOWED_ROOTS"] = ""

    @property
    def allowed_roots(self):
        """获取当前允许的根路径的副本"""
        with self._allowed_roots_lock:
            return self._allowed_roots.copy() if self._allowed_roots is not None else None

    def start(self):
        """启动 TCP 服务端"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.port = self.server_socket.getsockname()[1]
            self.server_socket.listen(5)
            self.is_running = True
            print(f"[*] LinkFlow 内核启动，监听端口: {self.port}...")
            
            # 开启独立线程等待连接，避免阻塞主界面
            threading.Thread(target=self._accept_loop, daemon=True).start()
            threading.Thread(target=self._heartbeat_monitor_loop, daemon=True).start()
        except Exception as e:
            print(f"[!] 启动失败: {e}")

    def _accept_loop(self):
        while self.is_running:
            try:
                client, addr = self.server_socket.accept()
                print(f"[+] 设备已连接: {addr}")
                self.client_socket = client
                with self._client_lock:
                    self._client_last_seen[client] = time.time()
                # 触发设备连接回调
                if self.on_device_connected:
                    try:
                        self.on_device_connected({"name": f"Device_{addr[0]}", "ip": addr[0], "port": addr[1]})
                    except Exception as e:
                        print(f"[!] 连接回调异常: {e}")
                # 为每个连接开启处理线程
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except OSError:
                break

    def _handle_client(self, client):
        """核心分发逻辑：根据协议类型分流处理"""
        try:
            while self.is_running:
                try:
                    header = client.recv(5)
                    if not header:
                        break

                    with self._client_lock:
                        self._client_last_seen[client] = time.time()

                    msg_type, length = LinkFlowProtocol.unpack_header(header)

                    payload = b""
                    while len(payload) < length:
                        packet = client.recv(length - len(payload))
                        if not packet:
                            break
                        payload += packet

                    self._dispatch_message(msg_type, payload, client)
                except ConnectionResetError:
                    break
        finally:
            with self._client_lock:
                self._client_last_seen.pop(client, None)
            try:
                client.close()
            except Exception:
                pass
            print("[-] 设备已断开连接")
            if self.client_socket is client:
                self.client_socket = None
                # 触发设备断开回调
                if self.on_device_disconnected:
                    try:
                        self.on_device_disconnected()
                    except Exception as e:
                        print(f"[!] 断开回调异常: {e}")

    def _dispatch_message(self, msg_type, payload, client):
        """根据协议类型，将数据交给对应的 Service 处理"""
        if msg_type == LinkFlowProtocol.TYPE_CLIPBOARD:
            text = payload.decode('utf-8')
            print(f"[剪贴板] 收到来自手机的内容: {text}")
            from core.clipboard_service import ClipboardService
            ClipboardService(on_update_callback=lambda _: None).set_clipboard_text(text)
            
        elif msg_type == LinkFlowProtocol.TYPE_CTRL_CMD:
            from core.monitor_service import MonitorService
            cmd = payload.decode('utf-8')
            print(f"[指令] 正在执行系统操作: {cmd}")
            success = MonitorService.execute_control_command(cmd)
            # 反馈执行结果给手机
            self.send_to_client(LinkFlowProtocol.TYPE_CTRL_CMD, {"status": "ok" if success else "fail"})

        elif msg_type == LinkFlowProtocol.TYPE_FILE_LIST:
            from core.file_service import FileService
            # 假设手机发送过来的是一个 JSON 字符串，包含路径 {"path": "C:/"}
            try:
                request_data = json.loads(payload.decode('utf-8'))
                target_path = request_data.get("path", "C:/")
                
                allowed_roots_copy = self.allowed_roots
                
                if allowed_roots_copy is not None and not FileService.is_path_allowed(target_path, allowed_roots_copy):
                    self._send_to_socket(client, LinkFlowProtocol.TYPE_FILE_LIST, {"error": "PATH_NOT_ALLOWED", "path": target_path})
                    return
                
                # 调用文件服务获取列表，传递 allowed_roots
                dir_info = FileService.get_directory_info(target_path, allowed_roots_copy)
                
                # 将结果发回手机端 (使用 0x11 类型)
                self.send_to_client(LinkFlowProtocol.TYPE_FILE_LIST, dir_info)
                print(f"[文件桥接] 已发送目录列表: {target_path}")
            except Exception as e:
                print(f"[!] 目录请求处理失败: {e}")

        elif msg_type == LinkFlowProtocol.TYPE_FILE_CHUNK_REQ:
            from core.file_service import FileService
            try:
                request_data = json.loads(payload.decode("utf-8"))
                file_path = request_data.get("path")
                offset = int(request_data.get("offset", 0))
                chunk_size = int(request_data.get("chunk_size", 1024 * 1024))

                if offset < 0:
                    self._send_to_socket(client, LinkFlowProtocol.TYPE_FILE_DATA, {"error": "BAD_OFFSET"})
                    return

                if chunk_size <= 0:
                    chunk_size = 1024 * 1024
                if chunk_size > 4 * 1024 * 1024:
                    chunk_size = 4 * 1024 * 1024
                
                allowed_roots_copy = self.allowed_roots

                if allowed_roots_copy is not None and not FileService.is_path_allowed(file_path, allowed_roots_copy):
                    self._send_to_socket(client, LinkFlowProtocol.TYPE_FILE_DATA, {"error": "PATH_NOT_ALLOWED", "path": file_path})
                    return

                chunk = FileService.read_file_chunk(file_path, offset, chunk_size=chunk_size, allowed_roots=allowed_roots_copy)
                if chunk is None:
                    self._send_to_socket(client, LinkFlowProtocol.TYPE_FILE_DATA, {"error": "READ_FAIL", "path": file_path, "offset": offset})
                    return

                eof = len(chunk) < chunk_size
                data_b64 = base64.b64encode(chunk).decode("ascii")
                self._send_to_socket(
                    client,
                    LinkFlowProtocol.TYPE_FILE_DATA,
                    {
                        "path": file_path,
                        "offset": offset,
                        "chunk_size": chunk_size,
                        "eof": eof,
                        "data_b64": data_b64,
                    },
                )
            except Exception as e:
                self._send_to_socket(client, LinkFlowProtocol.TYPE_FILE_DATA, {"error": "READ_FAIL", "detail": str(e)})

        elif msg_type == LinkFlowProtocol.TYPE_HEARTBEAT:
            self._send_to_socket(client, LinkFlowProtocol.TYPE_HEARTBEAT, b"")
        
        elif msg_type == LinkFlowProtocol.TYPE_REQ_PHONE_CLIPBOARD:
            # PC请求手机剪贴板，需要将请求转发给手机端
            # 这里我们需要等待手机端响应，然后返回给PC
            print("[剪贴板] 收到PC请求手机剪贴板")
            
        # ... 其他模块后续添加

    def send_to_client(self, msg_type, data):
        """主动向手机端推送数据"""
        if self.client_socket:
            try:
                packet = LinkFlowProtocol.pack(msg_type, data)
                self.client_socket.sendall(packet)
            except Exception as e:
                print(f"[!] 发送失败: {e}")

    def _send_to_socket(self, client, msg_type, data):
        try:
            client.sendall(LinkFlowProtocol.pack(msg_type, data))
        except Exception:
            pass

    def _heartbeat_monitor_loop(self):
        while self.is_running:
            now = time.time()
            stale = []
            with self._client_lock:
                for c, ts in list(self._client_last_seen.items()):
                    if now - ts > self.heartbeat_timeout_sec:
                        stale.append(c)

            for c in stale:
                try:
                    c.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    c.close()
                except Exception:
                    pass

            time.sleep(1)

    def stop(self):
        """关闭服务端并释放 socket（便于脚本与自动化环境退出）"""
        self.is_running = False
        client = self.client_socket
        try:
            if client:
                try:
                    client.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    client.close()
                except Exception:
                    pass
        finally:
            self.client_socket = None

        try:
            self.server_socket.close()
        except Exception:
            pass

        with self._client_lock:
            for c in list(self._client_last_seen.keys()):
                try:
                    c.close()
                except Exception:
                    pass
            self._client_last_seen.clear()

# 简易启动测试
if __name__ == "__main__":
    server = LinkFlowServer()
    server.start()
    input("按回车键停止服务...\n")
