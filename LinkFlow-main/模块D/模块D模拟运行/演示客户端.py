"""
模块D 功能演示客户端
无需手机端/其他模块，直接测试模块D所有新增接口

使用前提：
1. 运行 main.py 启动 LinkFlow 服务
2. 确保 requirements.txt 依赖已安装
3. 本脚本在同一台机器上运行（RPC 连接 localhost:8089）
"""
import base64
import json
import socket
import secrets
import sys
import time

sys.path.insert(0, "../..")

from core.rpc_crypto import AesGcmCipher
from core.rpc_framer import LengthPrefixedFramer


class LinkFlowClient:
    def __init__(self, host="127.0.0.1", port=8089):
        self.host = host
        self.port = port
        self.socket = None
        self.framer = LengthPrefixedFramer()
        self.secure_framer = None
        self.pairing_id = None

    def connect(self):
        self.socket = socket.create_connection((self.host, self.port), timeout=5)
        print(f"[连接] 已连接到 {self.host}:{self.port}")

    def close(self):
        if self.socket:
            self.socket.close()
        print("[连接] 已断开")

    def _send(self, req, use_secure=False, timeout=10):
        """发送请求并接收响应"""
        framer = self.secure_framer if use_secure else self.framer
        self.socket.sendall(framer.pack(json.dumps(req).encode("utf-8")))
        self.socket.settimeout(timeout)
        buf = b""
        while True:
            try:
                chunk = self.socket.recv(65536)
                if not chunk:
                    break
                buf += chunk
                res_bytes, buf = framer.unpack_from_buffer(buf)
                if res_bytes is not None:
                    return json.loads(res_bytes.decode("utf-8"))
            except socket.timeout:
                break
        return {"error": {"code": -1, "message": "timeout"}}

    def pair_bind(self, pairing_id, key_b64):
        """配对，建立安全通道"""
        self.pairing_id = pairing_id
        key = base64.b64decode(key_b64)

        res = self._send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "pair.bind",
            "params": {"pairing_id": pairing_id, "key_b64": key_b64}
        })

        if "error" in res:
            print(f"[配对失败] {res['error']}")
            return False

        self.secure_framer = LengthPrefixedFramer(cipher=AesGcmCipher(key))
        print(f"[配对成功] pairing_id={pairing_id}")
        return True

    def call(self, method, params=None, req_id=10, timeout=10):
        """通过安全通道调用 RPC 方法"""
        req = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
        res = self._send(req, use_secure=True, timeout=timeout)
        return res

    # ──────────────────────────────────────────────
    # 模块D 新增方法
    # ──────────────────────────────────────────────

    def test_clipboard_get(self):
        """clipboard.get — 读取剪贴板"""
        print("\n[测试] clipboard.get")
        res = self.call("clipboard.get")
        if "error" in res:
            print(f"  错误: {res['error']}")
        else:
            print(f"  剪贴板内容: {repr(res['result']['text'])}")
        return res

    def test_screen_snapshot(self):
        """screen.snapshot — 截图"""
        print("\n[测试] screen.snapshot")
        res = self.call("screen.snapshot", timeout=30)
        if "error" in res:
            print(f"  错误: {res['error']}")
        else:
            r = res["result"]
            data_len = len(r.get("data_b64", ""))
            print(f"  截图: {r['width']}x{r['height']}, 数据大小={data_len} bytes, 时间戳={r['timestamp']}")
        return res

    def test_file_upload_init(self, path, total_chunks):
        """file.upload_init — 初始化上传"""
        print(f"\n[测试] file.upload_init (path={path}, total_chunks={total_chunks})")
        res = self.call("file.upload_init", {"path": path, "total_chunks": total_chunks})
        if "error" in res:
            print(f"  错误: {res['error']}")
        else:
            print(f"  upload_id: {res['result']['upload_id']}")
        return res

    def test_file_upload_chunk(self, upload_id, chunk_index, data):
        """file.upload_chunk — 上传分块"""
        print(f"  上传 chunk {chunk_index}, 大小={len(data)} bytes")
        res = self.call("file.upload_chunk", {
            "upload_id": upload_id,
            "chunk_index": chunk_index,
            "data_b64": base64.b64encode(data).decode()
        })
        if "error" in res:
            print(f"  错误: {res['error']}")
        else:
            print(f"  chunk {chunk_index} 成功")
        return res

    def test_file_upload_commit(self, upload_id):
        """file.upload_commit — 提交上传"""
        print(f"\n[测试] file.upload_commit")
        res = self.call("file.upload_commit", {"upload_id": upload_id})
        if "error" in res:
            print(f"  错误: {res['error']}")
        else:
            r = res["result"]
            print(f"  合并成功: path={r['path']}, size={r.get('size')}, crc32={r.get('crc32')}")
        return res

    def test_upload_full(self, dest_path, chunks):
        """完整上传流程"""
        print(f"\n[完整测试] 文件上传: {dest_path}")
        init_res = self.test_file_upload_init(dest_path, len(chunks))
        if "error" in init_res:
            return
        upload_id = init_res["result"]["upload_id"]

        for i, data in enumerate(chunks):
            self.test_file_upload_chunk(upload_id, i, data)

        self.test_file_upload_commit(upload_id)

    def test_audit_query(self, start_ts=0, end_ts=0, limit=10):
        """audit.query — 查询审计日志"""
        print(f"\n[测试] audit.query (start={start_ts}, end={end_ts}, limit={limit})")
        res = self.call("audit.query", {"start_ts": start_ts, "end_ts": end_ts, "limit": limit})
        if "error" in res:
            print(f"  错误: {res['error']}")
        else:
            logs = res["result"]["logs"]
            print(f"  共 {res['result']['count']} 条日志:")
            for log in logs:
                print(f"    [{log['ts']}] {log['device']} / {log['action']} / {log['result']}")
        return res


def main():
    # 连接 RPC 服务（端口从 main.py 启动日志中查看）
    port = 8089  # 如不一致请修改
    client = LinkFlowClient(port=port)
    client.connect()

    # 获取服务端提供的配对信息（启动时会打印）
    # 或者直接用环境变量/默认生成的值
    import os
    pairing_id = os.getenv("LINKFLOW_PAIRING_ID", None)
    key_b64 = os.getenv("LINKFLOW_PAIRING_KEY_B64", None)

    if not pairing_id or not key_b64:
        # 如果 main.py 用的是自动生成的，先从服务端拿到 pairing_id
        # 这里用简化方式：直接从 main.py 的输出复制过来
        print("\n[提示] 请确保 main.py 已启动，并从其输出中复制 pairing_id 和 key_b64")
        print("或者设置环境变量 LINKFLOW_PAIRING_ID 和 LINKFLOW_PAIRING_KEY_B64")
        print("\n如果没有配对信息，可以跳过配对测试以下基础功能：")
        print("  - system.stats（无需配对）")
        # 用随机配对信息尝试（会失败）
        pairing_id = "test-pair"
        key = secrets.token_bytes(16)
        key_b64 = base64.b64encode(key).decode()
        print(f"\n尝试配对 ID={pairing_id} ...")
        client.pair_bind(pairing_id, key_b64)
    else:
        client.pair_bind(pairing_id, key_b64)

    # ──────────────────────────────────────────
    # 以下为所有新增方法的演示
    # ──────────────────────────────────────────

    # 1. system.stats（原有，无需配对也可测，但这里已配对）
    print("\n" + "="*40)
    print("1. system.stats")
    print("="*40)
    res = client.call("system.stats")
    print(f"  CPU: {res['result']['cpu_percent']}%")
    print(f"  内存: {res['result']['memory_percent']}%")
    print(f"  系统: {res['result']['os_info']}")

    # 2. clipboard.get
    print("\n" + "="*40)
    print("2. clipboard.get")
    print("="*40)
    client.test_clipboard_get()

    # 3. screen.snapshot
    print("\n" + "="*40)
    print("3. screen.snapshot")
    print("="*40)
    client.test_screen_snapshot()

    # 4. audit.query
    print("\n" + "="*40)
    print("4. audit.query")
    print("="*40)
    client.test_audit_query()

    # 5. file.upload 完整流程
    print("\n" + "="*40)
    print("5. file.upload 完整上传流程")
    print("="*40)
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = os.path.join(tmpdir, "demo_upload.txt")
        chunks = [b"Hello ", b"Module-D ", b"Upload!"]
        client.test_upload_full(dest, chunks)

    # 6. system.control（注意：会真实执行！）
    print("\n" + "="*40)
    print("6. system.control")
    print("="*40)
    print("  (演示 mute 命令)")
    res = client.call("system.control", {"cmd": "mute"})
    if "error" in res:
        print(f"  错误: {res['error']}")
    else:
        print(f"  结果: {res['result']}")

    print("\n" + "="*40)
    print("演示完成")
    print("="*40)

    client.close()


if __name__ == "__main__":
    main()
