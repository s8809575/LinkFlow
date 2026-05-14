# module-D-spec（PC 业务能力面：控制/监控/剪贴板/审计）

## 1. 模块边界
- 职责：提供 PC 侧 JSON-RPC 业务能力，实现模块化方法面并返回标准响应。
- 输入：来自 Module-B/Module-C 的 JSON-RPC 请求。
- 输出：标准 JSON-RPC `result/error`。
- 禁止：保存 Android 会话状态、禁止客户端 UI 逻辑。

## 2. 输入输出接口（冻结）

### 2.1 Python 方法面（RPC Method）
```text
pair.bind
system.stats
system.control
file.list
file.stat
file.read_chunk
file.upload_init
file.upload_chunk
file.upload_commit
clipboard.set
clipboard.get
screen.snapshot
sys.heartbeat
audit.query
```

### 2.2 响应格式
```json
{"jsonrpc":"2.0","id":7,"result":{"status":"ok"}}
{"jsonrpc":"2.0","id":7,"error":{"code":-32010,"message":"READ_FAIL"}}
```

## 3. 核心用例与验收（Given-When-Then）
- Given 已建立安全通道，When 调 `system.control` 传入 `mute/sleep/screen_off/reboot`，Then 返回 `status=ok|fail` 且动作真实执行。
- Given 调用 `clipboard.set`，When 文本有效，Then PC 剪贴板更新且防回环生效。
- Given 调用 `screen.snapshot`，When 请求成功，Then 返回可解码图片字节（base64）并附时间戳。
- Given 调用 `audit.query`，When 指定时间窗，Then 返回操作日志列表（含 ts/uuid/device/action/result）。

## 4. 显式排除（防镀金）
- 不实现 Web 管理后台完整 UI 重构。
- 不实现云端账户体系。
- 不实现跨平台系统指令（先 Windows 优先）。

## 5. 测试要求
- 单元测试：行覆盖率 `>=80%`，分支覆盖率 `>=75%`。
- 必测分支：权限拒绝、文件不存在、校验失败、非安全通道请求拒绝。

## 6. 外部依赖（版本锁定）
- Python `3.13.x`
- `psutil>=5.9`
- `pywin32>=306`
- `websockets>=11.0`
- Windows API（剪贴板、屏幕、电源管理）

## 7. 交付验收清单
- `core/rpc_server.py` 扩展（上传、剪贴板、截图、审计）。
- `core/monitor_service.py` 截图实现。
- `core/clipboard_service.py` 双向文本接口。
