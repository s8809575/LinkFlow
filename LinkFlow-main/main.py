import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import threading
from core.server import LinkFlowServer
from core.protocol import LinkFlowProtocol
import asyncio
import base64
import os

def status_push_loop(server, bridge):
    print("[*] 状态推送线程已启动...")
    while True:
        try:
            from core.monitor_service import MonitorService
            stats = MonitorService.get_system_stats()
            
            # 1. 推送给手机 (TCP Socket)
            if server.client_socket:
                server.send_to_client(LinkFlowProtocol.TYPE_SYS_STATS, stats)
            
            # 2. 推送给电脑网页 (WebSocket) - 现在直接调用即可，内部已处理跨线程
            bridge.broadcast({"type": "sys_stats", "val": stats})
            
        except Exception as e:
            print(f"[!] 推送循环异常: {e}")
        time.sleep(2)

async def handle_web_message(data, bridge):
    """
    处理网页端通过 WebSocket 发来的消息。

    输入示例:
    - {"type":"get_files","path":"C:/"}
    - {"type":"control","cmd":"mute"}
    """
    msg_type = data.get("type")
    if msg_type == "get_files":
        from core.file_service import FileService
        path = data.get("path", "C:/")
        roots = os.getenv("LINKFLOW_ALLOWED_ROOTS", "").strip()
        allowed_roots = [r.strip() for r in roots.split(";") if r.strip()] if roots else None
        if allowed_roots is not None and not FileService.is_path_allowed(path, allowed_roots):
            bridge.broadcast({"type": "error", "code": "PATH_NOT_ALLOWED", "detail": {"path": path}})
            return
        files = FileService.get_directory_info(path)
        bridge.broadcast({"type": "file_list", "path": path, "list": files})
        return

    if msg_type == "control":
        from core.monitor_service import MonitorService
        cmd = data.get("cmd")
        ok = MonitorService.execute_control_command(cmd)
        bridge.broadcast({"type": "control_result", "cmd": cmd, "status": "ok" if ok else "fail"})
        return

    if msg_type == "get_file_chunk":
        from core.file_service import FileService
        file_path = data.get("path")
        offset = int(data.get("offset", 0))
        chunk_size = int(data.get("chunk_size", 1024 * 1024))
        req_id = data.get("req_id")

        roots = os.getenv("LINKFLOW_ALLOWED_ROOTS", "").strip()
        allowed_roots = [r.strip() for r in roots.split(";") if r.strip()] if roots else None
        if allowed_roots is not None and not FileService.is_path_allowed(file_path, allowed_roots):
            bridge.broadcast({"type": "error", "code": "PATH_NOT_ALLOWED", "detail": {"path": file_path, "offset": offset, "req_id": req_id}})
            return

        if offset < 0:
            bridge.broadcast({"type": "error", "code": "BAD_OFFSET", "detail": {"path": file_path, "offset": offset, "req_id": req_id}})
            return

        if chunk_size <= 0:
            chunk_size = 1024 * 1024
        if chunk_size > 4 * 1024 * 1024:
            chunk_size = 4 * 1024 * 1024

        chunk = FileService.read_file_chunk(file_path, offset, chunk_size=chunk_size)
        if chunk is None:
            bridge.broadcast({"type": "error", "code": "READ_FAIL", "detail": {"path": file_path, "offset": offset, "req_id": req_id}})
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
        if req_id is not None:
            payload["req_id"] = req_id
        bridge.broadcast(payload)
        return

    bridge.broadcast({"type": "error", "code": "UNKNOWN_TYPE", "detail": {"type": msg_type}})

def main():
    from core.utils import WebBridge
    from core.clipboard_service import ClipboardService
    from core.rpc_server import LinkFlowRpcServer
    import os
    import secrets
    from core.mdns_service import MdnsService

    # 1. 初始化服务器
    lf_server = LinkFlowServer(host='0.0.0.0', port=5000)
    bridge = WebBridge(port=8766)
    pairing_id = os.getenv("LINKFLOW_PAIRING_ID")
    pairing_key_b64 = os.getenv("LINKFLOW_PAIRING_KEY_B64")
    pairing_key = base64.b64decode(pairing_key_b64) if pairing_key_b64 else secrets.token_bytes(16)
    rpc_server = LinkFlowRpcServer(host="0.0.0.0", port=8089, pairing_id=pairing_id, pairing_key=pairing_key)

    bridge.on_message_hook = lambda data: handle_web_message(data, bridge)

    # 启动服务器监听
    lf_server.start()
    bridge.start_bridge()
    rpc_server.start()

    info = rpc_server.get_pairing_info()
    print("[*] RPC 服务已就绪")
    print(f"    端口: {info['port']}")
    print(f"    pairing_id: {info['pairing_id']}")
    if info["key_b64"]:
        print(f"    key_b64: {info['key_b64']}")

    mdns = MdnsService(service_name="LinkFlow", port=rpc_server.port, properties={"pairing_id": info["pairing_id"]})
    try:
        mdns.start()
        print("[*] mDNS 已广播: _companion._tcp.local.")
    except Exception as e:
        print(f"[!] mDNS 广播失败: {e}")

    # 定义剪贴板更新时的动作
    def on_clipboard_change(text):
        print(f"[推送] 发现新剪贴板内容，正在同步至手机...")
        lf_server.send_to_client(LinkFlowProtocol.TYPE_CLIPBOARD, text)

    # 启动剪贴板服务
    clip_service = ClipboardService(on_update_callback=on_clipboard_change)
    clip_service.start_watching()

    # 开启状态推送线程 (Daemon 模式随主程序退出)
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


    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 正在关闭 LinkFlow...")

if __name__ == "__main__":
    main()
