import sys
import os

os.environ['CRYPTOGRAPHY_OPENSSL_NO_LEGACY'] = '1'
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer --disable-gpu-compositing --disable-features=VizDisplayCompositor"
os.environ["QT_OPENGL"] = "software"
os.environ["QT_QUICK_BACKEND"] = "software"

import json

log_file_path = os.path.join(os.path.dirname(__file__), 'linkflow.log') if not getattr(sys, 'frozen', False) else \
                os.path.join(os.path.dirname(sys.executable), 'linkflow.log')

def log_to_file(message):
    try:
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    except:
        pass

print("[DEBUG] Python version:", sys.version)
log_to_file("[DEBUG] Python version: " + sys.version)
print("[DEBUG] sys.executable:", sys.executable)
log_to_file("[DEBUG] sys.executable: " + sys.executable)
print("[DEBUG] frozen:", getattr(sys, 'frozen', False))
log_to_file("[DEBUG] frozen: " + str(getattr(sys, 'frozen', False)))

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    print("[DEBUG] Running from frozen environment, _MEIPASS:", base_path)
    log_to_file("[DEBUG] Running from frozen environment, _MEIPASS: " + base_path)
    linkflow_path = os.path.join(base_path, 'linkflow')
    print("[DEBUG] Adding linkflow path:", linkflow_path)
    log_to_file("[DEBUG] Adding linkflow path: " + linkflow_path)
    sys.path.append(linkflow_path)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
    print("[DEBUG] Running from development environment, base_path:", base_path)
    log_to_file("[DEBUG] Running from development environment, base_path: " + base_path)

print("[DEBUG] sys.path after modifications:", sys.path[:5])

print("[DEBUG] Current sys.path:", sys.path[:3])
log_to_file("[DEBUG] Current sys.path: " + str(sys.path[:3]))

print("[DEBUG] Importing time...")
import time
print("[DEBUG] Importing threading...")
import threading
print("[DEBUG] Importing asyncio...")
import asyncio
print("[DEBUG] Importing base64...")
import base64
print("[DEBUG] Importing webbrowser...")
import webbrowser
print("[DEBUG] Importing subprocess...")
import subprocess
print("[DEBUG] Importing secrets...")
import secrets
print("[DEBUG] Importing uuid...")
import uuid
print("[DEBUG] Importing pickle...")
import pickle
print("[DEBUG] Importing datetime...")
import datetime
print("[DEBUG] Importing hashlib...")
import hashlib
print("[DEBUG] Importing zlib...")
import zlib

print("[DEBUG] All standard imports completed successfully!")

print("[DEBUG] Importing from linkflow.core.server...")
try:
    from linkflow.core.server import LinkFlowServer
    print("[DEBUG] Successfully imported LinkFlowServer")
except Exception as e:
    print("[ERROR] Failed to import LinkFlowServer:", e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[DEBUG] Importing from linkflow.core.protocol...")
try:
    from linkflow.core.protocol import LinkFlowProtocol
    print("[DEBUG] Successfully imported LinkFlowProtocol")
except Exception as e:
    print("[ERROR] Failed to import LinkFlowProtocol:", e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[DEBUG] All imports completed successfully!")

QT_AVAILABLE = False
try:
    from linkflow.gui import LinkFlowMainWindow, run_qt_app
    QT_AVAILABLE = True
    print("[DEBUG] PyQt5 WebEngine is available, will use embedded browser")
except ImportError as e:
    print("[DEBUG] PyQt5 WebEngine not available, will fall back to system browser:", e)

lf_server_ref = None
rpc_server_ref = None
uploader_ref = None
bridge_ref = None

def status_push_loop(server, bridge):
    print("[*] 状态推送线程已启动...")
    while True:
        try:
            from linkflow.core.monitor_service import MonitorService
            stats = MonitorService.get_system_stats()
            
            if server.client_socket:
                server.send_to_client(LinkFlowProtocol.TYPE_SYS_STATS, stats)
            
            bridge.broadcast({"type": "sys_stats", "val": stats})
            
        except Exception as e:
            print(f"[!] 推送循环异常: {e}")
        time.sleep(2)

async def handle_web_message(data, bridge):
    msg_type = data.get("type")
    req_id = data.get("req_id")
    
    def send_response(response_data):
        if req_id is not None:
            response_data["req_id"] = req_id
        bridge.broadcast(response_data)
    
    global uploader_ref

    try:
        if msg_type == "device_connected":
            print("[*] 手机网页已连接")
            bridge.broadcast({
                "type": "device_connected",
                "device": data.get("device", {})
            })
            return

        if msg_type == "device_disconnected":
            print("[*] 手机网页已断开")
            bridge.broadcast({
                "type": "device_disconnected"
            })
            return

        if msg_type == "heartbeat":
            send_response({"type": "heartbeat", "status": "ok"})
            return
    
        if msg_type == "get_network_info":
            import socket
            hostname = socket.gethostname()
            try:
                ip_list = socket.getaddrinfo(hostname, None, socket.AF_INET)
                ips = list(set([info[4][0] for info in ip_list]))
            except:
                ips = []
            
            hotspot_ip = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                hotspot_ip = s.getsockname()[0]
                s.close()
            except:
                pass
            
            send_response({
                "type": "network_info",
                "hostname": hostname,
                "ips": ips,
                "hotspot_ip": hotspot_ip or (ips[0] if ips else "127.0.0.1")
            })
            return

        if msg_type == "get_stats":
            from linkflow.core.monitor_service import MonitorService
            stats = MonitorService.get_system_stats()
            send_response({"type": "sys_stats", "val": stats})
            return

        if msg_type == "get_files":
            from linkflow.core.file_service import FileService
            path = data.get("path", "C:/")
            import ntpath
            path = ntpath.normpath(path)
            print(f"[*] 获取文件列表: {path}")
            
            allowed_roots = None
            if lf_server_ref and lf_server_ref.allowed_roots:
                allowed_roots = lf_server_ref.allowed_roots
            elif rpc_server_ref and rpc_server_ref.allowed_roots:
                allowed_roots = rpc_server_ref.allowed_roots
            else:
                roots = os.getenv("LINKFLOW_ALLOWED_ROOTS", "").strip()
                allowed_roots = [r.strip() for r in roots.split(";") if r.strip()] if roots else None
            
            print(f"[*] 当前授权路径列表: {allowed_roots}")
            
            result = FileService.get_directory_info(path, allowed_roots)
            
            if isinstance(result, dict) and "error" in result:
                print(f"[!] 获取文件列表失败: {result['error']}")
                send_response({"type": "file_list", "path": path, "list": [], "error": result.get("error")})
                return
            
            send_response({"type": "file_list", "path": path, "list": result or []})
            return

        if msg_type == "get_file_chunk":
            from linkflow.core.file_service import FileService
            file_path = data.get("path")
            offset = int(data.get("offset", 0))
            chunk_size = int(data.get("chunk_size", 1024 * 1024))

            allowed_roots = None
            if lf_server_ref and lf_server_ref.allowed_roots:
                allowed_roots = lf_server_ref.allowed_roots
            elif rpc_server_ref and rpc_server_ref.allowed_roots:
                allowed_roots = rpc_server_ref.allowed_roots
            else:
                roots = os.getenv("LINKFLOW_ALLOWED_ROOTS", "").strip()
                allowed_roots = [r.strip() for r in roots.split(";") if r.strip()] if roots else None
            if allowed_roots is not None and not FileService.is_path_allowed(file_path, allowed_roots):
                send_response({"type": "error", "code": "PATH_NOT_ALLOWED", "detail": {"path": file_path}})
                return

            if offset < 0:
                send_response({"type": "error", "code": "BAD_OFFSET", "detail": {"path": file_path, "offset": offset}})
                return

            if chunk_size <= 0:
                chunk_size = 1024 * 1024
            if chunk_size > 4 * 1024 * 1024:
                chunk_size = 4 * 1024 * 1024

            chunk = FileService.read_file_chunk(file_path, offset, chunk_size=chunk_size, allowed_roots=allowed_roots)
            if chunk is None:
                send_response({"type": "error", "code": "READ_FAIL", "detail": {"path": file_path}})
                return

            eof = len(chunk) < chunk_size
            payload = {
                "type": "file_chunk",
                "path": file_path,
                "offset": offset,
                "chunk_size": chunk_size,
                "eof": eof,
                "data_b64": base64.b64encode(chunk).decode("ascii"),
            }
            send_response(payload)
            return

        if msg_type == "init_upload":
            if uploader_ref is None:
                from linkflow.core.file_uploader import FileUploader
                uploader_ref = FileUploader()

            filename = data.get("filename")
            size = int(data.get("size", 0))
            crc32 = int(data.get("crc32", 0))
            target_path = data.get("target_path")

            allowed_roots = None
            if lf_server_ref and lf_server_ref.allowed_roots:
                allowed_roots = lf_server_ref.allowed_roots
            elif rpc_server_ref and rpc_server_ref.allowed_roots:
                allowed_roots = rpc_server_ref.allowed_roots
            else:
                roots = os.getenv("LINKFLOW_ALLOWED_ROOTS", "").strip()
                allowed_roots = [r.strip() for r in roots.split(";") if r.strip()] if roots else None

            if not target_path:
                send_response({"status": "error", "message": "TARGET_PATH_REQUIRED"})
                return

            from linkflow.core.file_service import FileService
            if allowed_roots is not None and not FileService.is_path_allowed(target_path, allowed_roots, require_write=True):
                send_response({"status": "error", "message": "PATH_NOT_ALLOWED"})
                return

            result = uploader_ref.init_upload(filename, size, crc32, target_path)
            send_response(result)
            return

        if msg_type == "write_upload_chunk":
            if uploader_ref is None:
                from linkflow.core.file_uploader import FileUploader
                uploader_ref = FileUploader()

            session_id = data.get("session_id")
            offset = int(data.get("offset", 0))
            data_b64 = data.get("data_b64")
            result = uploader_ref.write_chunk(session_id, offset, data_b64)
            send_response(result)
            return

        if msg_type == "commit_upload":
            if uploader_ref is None:
                from linkflow.core.file_uploader import FileUploader
                uploader_ref = FileUploader()

            session_id = data.get("session_id")
            result = uploader_ref.commit_upload(session_id)
            send_response(result)
            return

        if msg_type == "cancel_upload":
            if uploader_ref is None:
                from linkflow.core.file_uploader import FileUploader
                uploader_ref = FileUploader()

            session_id = data.get("session_id")
            result = uploader_ref.cancel_upload(session_id)
            send_response(result)
            return

        if msg_type == "get_clipboard":
            from linkflow.core.clipboard_service import ClipboardService
            try:
                loop = asyncio.get_running_loop()
                img_bytes, img_format = await loop.run_in_executor(None, ClipboardService.get_clipboard_image)

                if img_bytes:
                    print(f"[✓] 成功读取图片，大小: {len(img_bytes)} bytes")
                    response = {
                        "type": "clipboard_content",
                        "content_type": "image",
                        "format": img_format,
                        "data_base64": base64.b64encode(img_bytes).decode('ascii'),
                        "size": len(img_bytes),
                        "success": True
                    }
                    send_response(response)
                    bridge.broadcast({
                        "type": "clipboard_history_event",
                        "event_type": "pc_clipboard_fetched",
                        "content_type": "image",
                        "format": img_format,
                        "data_base64": base64.b64encode(img_bytes).decode('ascii'),
                        "size": len(img_bytes),
                        "timestamp": time.time()
                    })
                    return

                content = await loop.run_in_executor(None, ClipboardService.get_clipboard_text)

                if content:
                    print(f"[✓] 成功读取文本: {content[:50]}...")
                    response = {
                        "type": "clipboard_content",
                        "content_type": "text",
                        "content": content,
                        "success": True
                    }
                    send_response(response)
                    bridge.broadcast({
                        "type": "clipboard_history_event",
                        "event_type": "pc_clipboard_fetched",
                        "content_type": "text",
                        "content": content,
                        "timestamp": time.time()
                    })
                    return

                print(f"[*] 获取PC剪贴板文本: {(content or '(空)')[:50]}")
                response = {
                    "type": "clipboard_content",
                    "success": content is not None,
                    "content_type": "text",
                    "content": content or ""
                }
                send_response(response)

                bridge.broadcast({
                    "type": "clipboard_history_event",
                    "event_type": "pc_clipboard_fetched",
                    "content_type": "text",
                    "content": content or "",
                    "timestamp": time.time()
                })

            except Exception as e:
                print(f"[✗] 剪贴板读取失败: {e}")
                send_response({
                    "type": "error",
                    "code": "CLIPBOARD_READ_FAIL",
                    "detail": str(e)
                })
            return

        if msg_type == "set_clipboard":
            from linkflow.core.clipboard_service import ClipboardService
            content = data.get("content", "")
            ClipboardService.set_clipboard_text(content)
            send_response({"type": "clipboard_update", "content": content})
            return

        if msg_type == "send_clipboard_to_pc":
            from linkflow.core.clipboard_service import ClipboardService
            content = data.get("content", "")
            content_type = data.get("content_type", "text")
            data_b64 = data.get("data_base64")
            img_format = data.get("format")
            img_size = data.get("size", 0)

            print(f"[*] 收到手机剪贴板: type={content_type}, {content[:50] if content else '(空)'}")

            success = False
            if content_type == "image" and data_b64:
                try:
                    image_bytes = base64.b64decode(data_b64)
                    loop = asyncio.get_running_loop()
                    success = await loop.run_in_executor(None, ClipboardService.set_clipboard_image, image_bytes)
                    if success:
                        print(f"[*] 图片已写入PC剪贴板，大小: {img_size}")
                except Exception as e:
                    print(f"[!] 图片写入剪贴板失败: {e}")
                    success = False
            else:
                loop = asyncio.get_running_loop()
                success = await loop.run_in_executor(None, ClipboardService.set_clipboard_text, content)

            if success:
                print(f"[*] PC剪贴板处理成功")
                client_count = len(bridge.clients) if bridge.clients else 0
                print(f"[*] 准备广播给 {client_count} 个WebSocket客户端")

                if content_type == "image":
                    bridge.broadcast({
                        "type": "clipboard_update",
                        "content_type": "image",
                        "data_base64": data_b64,
                        "format": img_format,
                        "size": img_size,
                        "source": "phone"
                    })
                else:
                    bridge.broadcast({
                        "type": "clipboard_update",
                        "content": content,
                        "content_type": "text",
                        "source": "phone"
                    })
                send_response({"type": "clipboard_sent", "success": True, "content": content})
            else:
                print(f"[!] PC剪贴板设置失败")
                send_response({"type": "clipboard_sent", "success": False, "error": "设置剪贴板失败"})
            return

        if msg_type == "request_phone_clipboard":
            print("[*] PC请求手机剪贴板")
            
            has_clients = False
            if lf_server_ref and lf_server_ref.client_socket:
                has_clients = True
            if bridge.clients and len(bridge.clients) > 0:
                has_clients = True
            
            if not has_clients:
                send_response({"type": "phone_clipboard_result", "success": False, "error": "no_phone", "message": "手机设备未连接"})
                return
            
            try:
                bridge.broadcast({"type": "request_phone_clipboard"})
                send_response({"type": "phone_clipboard_result", "success": True, "message": "请求已发送到手机，请等待响应"})
            except Exception as e:
                print(f"[!] 发送请求失败: {e}")
                send_response({"type": "phone_clipboard_result", "success": False, "error": "send_fail", "message": str(e)})
            return

        if msg_type == "phone_clipboard_result":
            print(f"[*] 手机剪贴板权限响应: {data.get('success')}")
            bridge.broadcast(data)
            return

        if msg_type == "get_snapshot":
            from linkflow.core.monitor_service import MonitorService
            snapshot = MonitorService.get_screen_snapshot()
            send_response({"type": "snapshot", **snapshot})
            return

        if msg_type == "system_control":
            from linkflow.core.monitor_service import MonitorService
            cmd = data.get("command")
            print(f"[*] 收到控制命令: {cmd}")
            if cmd == "screen_off":
                send_response({"type": "control_result", "command": cmd, "status": "ok", "success": True})

                def delayed_screen_off():
                    import time as _time
                    _time.sleep(0.3)
                    ok = MonitorService.execute_control_command(cmd)
                    print(f"[*] 命令执行结果: {'成功' if ok else '失败'}")

                threading.Thread(target=delayed_screen_off, daemon=True).start()
                return

            ok = MonitorService.execute_control_command(cmd)
            print(f"[*] 命令执行结果: {'成功' if ok else '失败'}")
            send_response({"type": "control_result", "command": cmd, "status": "ok" if ok else "fail", "success": ok})
            return

        if msg_type == "get_allowed_paths":
            print("[*] 收到获取授权路径列表请求")
            
            allowed_roots = []
            if lf_server_ref and lf_server_ref.allowed_roots:
                allowed_roots = lf_server_ref.allowed_roots
            elif rpc_server_ref and rpc_server_ref.allowed_roots:
                allowed_roots = rpc_server_ref.allowed_roots
            else:
                roots = os.getenv("LINKFLOW_ALLOWED_ROOTS", "").strip()
                allowed_roots = [r.strip() for r in roots.split(";") if r.strip()] if roots else []
            
            print(f"[*] 返回授权路径列表: {allowed_roots}")
            send_response({"type": "allowed_paths", "paths": allowed_roots, "success": True})
            return

        if msg_type == "add_allowed_path":
            start_time = time.time()
            path = data.get("path")
            perm = data.get("perm", "rw")
            print(f"[*] 收到添加授权路径请求: {path}")
            if path:
                try:
                    if lf_server_ref:
                        lf_server_ref.add_allowed_root(path, perm=perm)
                        print(f"[*] 已添加到 LinkFlowServer")
                    if rpc_server_ref:
                        rpc_server_ref.add_allowed_root(path, perm=perm)
                        print(f"[*] 已添加到 RpcServer")
                    
                    elapsed = (time.time() - start_time) * 1000
                    print(f"[*] 添加授权路径成功，耗时: {elapsed:.2f}ms")
                    send_response({"type": "path_added", "path": path, "success": True, "elapsed_ms": elapsed})
                except Exception as e:
                    elapsed = (time.time() - start_time) * 1000
                    print(f"[!] 添加授权路径失败: {e}, 耗时: {elapsed:.2f}ms")
                    send_response({"type": "error", "code": "ADD_PATH_FAILED", "detail": {"path": path, "error": str(e)}})
            else:
                elapsed = (time.time() - start_time) * 1000
                print(f"[!] 无效路径: {path}, 耗时: {elapsed:.2f}ms")
                send_response({"type": "error", "code": "INVALID_PATH", "detail": {"path": path}})
            
            current_roots = []
            if lf_server_ref and lf_server_ref.allowed_roots:
                current_roots = lf_server_ref.allowed_roots
            elif rpc_server_ref and rpc_server_ref.allowed_roots:
                current_roots = rpc_server_ref.allowed_roots
            
            if bridge_ref:
                bridge_ref.broadcast({
                    "type": "allowed_paths_updated",
                    "paths": current_roots,
                    "timestamp": time.time()
                })
                print(f"[*] 已广播授权路径更新: {current_roots}")
            return

        if msg_type == "remove_allowed_path":
            start_time = time.time()
            path = data.get("path")
            print(f"[*] 收到删除授权路径请求: {path}")
            if path:
                try:
                    if lf_server_ref:
                        lf_server_ref.remove_allowed_root(path)
                        print(f"[*] 已从 LinkFlowServer 删除")
                    if rpc_server_ref:
                        rpc_server_ref.remove_allowed_root(path)
                        print(f"[*] 已从 RpcServer 删除")

                    elapsed = (time.time() - start_time) * 1000
                    send_response({"type": "path_removed", "path": path, "success": True, "elapsed_ms": elapsed})
                except Exception as e:
                    elapsed = (time.time() - start_time) * 1000
                    print(f"[!] 删除授权路径失败: {e}, 耗时: {elapsed:.2f}ms")
                    send_response({"type": "error", "code": "REMOVE_PATH_FAILED", "detail": {"path": path, "error": str(e)}})
            else:
                elapsed = (time.time() - start_time) * 1000
                send_response({"type": "error", "code": "INVALID_PATH", "detail": {"path": path, "elapsed_ms": elapsed}})

            current_roots = []
            if lf_server_ref and lf_server_ref.allowed_roots:
                current_roots = lf_server_ref.allowed_roots
            elif rpc_server_ref and rpc_server_ref.allowed_roots:
                current_roots = rpc_server_ref.allowed_roots

            if bridge_ref:
                bridge_ref.broadcast({
                    "type": "allowed_paths_updated",
                    "paths": current_roots,
                    "timestamp": time.time()
                })
            return
        
        send_response({"type": "error", "code": "UNKNOWN_TYPE", "detail": {"type": msg_type}})
        
    except Exception as e:
        print(f"[!] 处理消息时发生异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        try:
            response_data = {"type": "error", "code": "INTERNAL_ERROR", "detail": str(e)}
            if req_id is not None:
                response_data["req_id"] = req_id
            bridge.broadcast(response_data)
        except:
            print("[!] 发送错误响应失败")

def start_services():
    global lf_server_ref, rpc_server_ref, bridge_ref
    
    print("[DEBUG] 开始启动后台服务...")
    
    try:
        from linkflow.core.utils import WebBridge
        print("[DEBUG] 导入 WebBridge 成功")
    except Exception as e:
        print(f"[ERROR] 导入 WebBridge 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        from linkflow.core.clipboard_service import ClipboardService
        print("[DEBUG] 导入 ClipboardService 成功")
    except Exception as e:
        print(f"[ERROR] 导入 ClipboardService 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        from linkflow.core.rpc_server import LinkFlowRpcServer
        print("[DEBUG] 导入 LinkFlowRpcServer 成功")
    except Exception as e:
        print(f"[ERROR] 导入 LinkFlowRpcServer 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        from linkflow.core.mdns_service import MdnsService
        print("[DEBUG] 导入 MdnsService 成功")
    except Exception as e:
        print(f"[ERROR] 导入 MdnsService 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    lf_server = LinkFlowServer(host='0.0.0.0', port=5000)
    lf_server_ref = lf_server
    bridge = WebBridge(port=8766)
    bridge_ref = bridge
    pairing_id = os.getenv("LINKFLOW_PAIRING_ID")
    pairing_key_b64 = os.getenv("LINKFLOW_PAIRING_KEY_B64")
    pairing_key = base64.b64decode(pairing_key_b64) if pairing_key_b64 else secrets.token_bytes(16)
    rpc_server = LinkFlowRpcServer(host="0.0.0.0", port=8089, pairing_id=pairing_id, pairing_key=pairing_key)
    rpc_server_ref = rpc_server

    bridge.on_message_hook = lambda data: handle_web_message(data, bridge)

    def on_device_connected(device_info):
        print(f"[广播] 设备已连接: {device_info}")
        bridge.broadcast({"type": "device_connected", "device": device_info})
    
    def on_device_disconnected():
        print("[广播] 设备已断开")
        bridge.broadcast({"type": "device_disconnected"})
    
    lf_server.on_device_connected = on_device_connected
    lf_server.on_device_disconnected = on_device_disconnected

    lf_server.start()
    bridge.start_bridge()
    rpc_server.start()

    info = rpc_server.get_pairing_info()
    print("[*] RPC 服务已就绪")
    print(f"    端口: {info['port']}")
    print(f"    pairing_id: {info['pairing_id']}")
    if info["key_b64"]:
        print(f"    key_b64: {info['key_b64']}")

    from linkflow.core.monitor_service import MonitorService
    MonitorService.execute_control_command("keep_awake")
    print("[*] 防息屏模式已启用")

    mdns = MdnsService(service_name="LinkFlow", port=rpc_server.port, properties={"pairing_id": info["pairing_id"]})
    try:
        mdns.start()
        print("[*] mDNS 已广播: _companion._tcp.local.")
    except Exception as e:
        print(f"[!] mDNS 广播失败: {e}")

    last_pushed_clipboard = [""]
    def on_clipboard_change(text):
        if text == last_pushed_clipboard[0]:
            return
        last_pushed_clipboard[0] = text
        print(f"[推送] 发现新剪贴板内容，正在同步至手机...")
        lf_server.send_to_client(LinkFlowProtocol.TYPE_CLIPBOARD, text)
        bridge.broadcast({
            "type": "clipboard_update",
            "source": "pc",
            "content": text,
            "content_type": "text"
        })

    clip_service = ClipboardService(on_update_callback=on_clipboard_change)
    clip_service.start_watching()
    
    rpc_server.set_clipboard_service(clip_service)

    push_thread = threading.Thread(
        target=status_push_loop, 
        args=(lf_server, bridge), 
        daemon=True
    )
    push_thread.start()
    
    print("\n" + "="*30)
    print("   LinkFlow 服务已就绪")
    print("   端口: 5000")
    print("   状态: 等待手机端接入...")
    print("="*30 + "\n")
    
    return True

def open_system_browser():
    time.sleep(2)
    try:
        print("[*] 尝试打开系统浏览器...")
        log_to_file("[*] 尝试打开系统浏览器...")
        
        try:
            subprocess.run(['start', 'http://localhost:8766/desktop'], shell=True, check=True)
            print("[*] 使用 start 命令打开浏览器成功")
            log_to_file("[*] 使用 start 命令打开浏览器成功")
            return
        except Exception as e:
            print(f"[!] start 命令失败: {e}")
            log_to_file(f"[!] start 命令失败: {e}")
        
        try:
            subprocess.run(['cmd.exe', '/c', 'start', 'http://localhost:8766/desktop'], check=True)
            print("[*] 使用 cmd.exe 打开浏览器成功")
            log_to_file("[*] 使用 cmd.exe 打开浏览器成功")
            return
        except Exception as e:
            print(f"[!] cmd.exe 失败: {e}")
            log_to_file(f"[!] cmd.exe 失败: {e}")
        
        try:
            subprocess.run(['powershell.exe', '-Command', 'Start-Process "http://localhost:8766/desktop"'], check=True)
            print("[*] 使用 PowerShell 打开浏览器成功")
            log_to_file("[*] 使用 PowerShell 打开浏览器成功")
            return
        except Exception as e:
            print(f"[!] PowerShell 失败: {e}")
            log_to_file(f"[!] PowerShell 失败: {e}")
        
        try:
            if webbrowser.open('http://localhost:8766/desktop'):
                print("[*] 使用 webbrowser 模块打开浏览器成功")
                log_to_file("[*] 使用 webbrowser 模块打开浏览器成功")
                return
            else:
                print("[!] webbrowser.open 返回 False")
                log_to_file("[!] webbrowser.open 返回 False")
        except Exception as e:
            print(f"[!] webbrowser 模块失败: {e}")
            log_to_file(f"[!] webbrowser 模块失败: {e}")
            
        print("[!] 所有打开浏览器的方法都失败了，请手动访问 http://localhost:8766/desktop")
        log_to_file("[!] 所有打开浏览器的方法都失败了，请手动访问 http://localhost:8766/desktop")
                    
    except Exception as e:
        print(f"[!] 打开浏览器失败: {e}")
        log_to_file(f"[!] 打开浏览器失败: {e}")
        import traceback
        traceback.print_exc()
        log_to_file(f"[!] Traceback: {traceback.format_exc()}")

def main():
    print("[DEBUG] 开始启动 LinkFlow...")
    
    service_thread = threading.Thread(target=start_services, daemon=True)
    service_thread.start()
    
    print("[DEBUG] 等待服务启动...")
    for i in range(3):
        time.sleep(1)
        print(f"[DEBUG] 等待中... {i+1}/3")
    
    if QT_AVAILABLE:
        print("[*] 使用 Qt WebEngine 嵌入式浏览器")
        try:
            import sys
            from linkflow.gui import run_qt_app
            sys.exit(run_qt_app('http://localhost:8766/desktop'))
        except Exception as e:
            print(f"[!] Qt WebEngine 启动失败，回退到系统浏览器: {e}")
            import traceback
            traceback.print_exc()
            log_to_file(f"[!] Qt WebEngine 启动失败: {e}")
            log_to_file(f"[!] Traceback: {traceback.format_exc()}")
    else:
        print("[*] Qt WebEngine 不可用，使用系统浏览器")
    
    browser_thread = threading.Thread(target=open_system_browser, daemon=True)
    browser_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 正在关闭 LinkFlow...")

if __name__ == "__main__":
    main()