# 模块D 交付物 — 快速启动指南

## 环境准备

```bash
# Python 依赖（已在 requirements.txt 中锁定）
pip install psutil pywin32 websockets Pillow cryptography

# 或直接安装全部依赖
pip install -r requirements.txt
```

## 启动方式

```bash
cd LinkFlow-main
python main.py
```

启动后输出：
```
[*] RPC 服务已就绪
    端口: 8089
    pairing_id: <自动生成>
    key_b64: <自动生成>
[*] mDNS 已广播: _companion._tcp.local.
[*] 剪贴板监控服务已就绪
[*] 前端网桥已就绪: ws://localhost:8766
[*] LinkFlow 内核启动，监听端口: 5000...

   LinkFlow 服务已就绪
   端口: 5000
   状态: 等待手机端接入...
```

## 验证方法

### 1. RPC 端口连通性

```bash
# 检查 8089 端口是否监听
netstat -an | findstr 8089
```

### 2. JSON-RPC 接口验证（配对后）

配对成功后（见下方 Python 验证脚本），可调用：

```bash
# system.stats
python -c "
import socket, base64, json
from core.rpc_framer import LengthPrefixedFramer
from core.rpc_crypto import AesGcmCipher

key = b'your_16byte_key_here'
cipher = AesGcmCipher(key)
framer = LengthPrefixedFramer(cipher=cipher)

req = {'jsonrpc':'2.0','id':1,'method':'system.stats','params':{}}
s = socket.create_connection(('127.0.0.1', 8089))
s.sendall(framer.pack(json.dumps(req).encode()))
data = s.recv(65536)
print(json.loads(framer.unpack_from_buffer(data)[0].decode()))
s.close()
"
```

### 3. 新增接口快速验证

```bash
# clipboard.get（需先配对）
python -c "
import socket, base64, json
from core.rpc_framer import LengthPrefixedFramer
from core.rpc_crypto import AesGcmCipher

key = b'your_16byte_key_here'
cipher = AesGcmCipher(key)
framer = LengthPrefixedFramer(cipher=cipher)

req = {'jsonrpc':'2.0','id':2,'method':'clipboard.get','params':{}}
s = socket.create_connection(('127.0.0.1', 8089))
s.sendall(framer.pack(json.dumps(req).encode()))
data = s.recv(65536)
print(json.loads(framer.unpack_from_buffer(data)[0].decode()))
s.close()
"
```

### 4. 屏幕截图验证（需 Pillow）

```bash
python -c "
from core.monitor_service import MonitorService
result = MonitorService.get_screen_snapshot()
print('width:', result.get('width'))
print('height:', result.get('height'))
print('has data:', 'data_b64' in result)
"
```

## 冒烟测试

```bash
cd LinkFlow-main
python -m unittest discover -s tests -v
```

预计结果：大部分通过；`execute_control_command` 相关测试在 Windows 环境外可能挂起（Windows API 调用）。

## 已知限制

- `clipboard.get/set` 需要 pywin32，未安装时返回 `False`
- 上传路径受 `LINKFLOW_ALLOWED_ROOTS` 环境变量限制
- 所有高危操作（screen/clipboard/upload/audit）必须先完成 `pair.bind` 建立安全通道
