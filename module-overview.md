# LinkFlow 功能差距拆分总清单（可并行独立交付）

## 冻结约束（全局）
- 模块数量固定为 4：A/B/C/D，边界互斥，不允许跨模块直接调用。
- 模块交互仅通过冻结 DTO/IDL（版本：`IDL-v1.0.0`），不得新增隐式字段。
- 禁止全局可变状态、单例共享缓存、隐式事件总线。
- 允许的唯一跨模块依赖方式：`JSON-RPC` 消息 + 文件系统静态配置文件（只读）。
- 质量基线：单元测试行覆盖率 `>=80%`，分支覆盖率 `>=75%`。

## 模块分工总表

| 模块 | 功能域 | 负责人 | 预估人时 | 风险级别 | 交付物 |
|---|---|---|---:|---|---|
| Module-A | 服务发现与安全配对 | 同学A | 32h | 中 | `module-A-spec.md` + 发现/配对实现 + 单测 |
| Module-B | 连接会话与统一 RPC 客户端 | 同学B | 40h | 高 | `module-B-spec.md` + 长连接/重连/RPC实现 + 单测 |
| Module-C | 文件分片传输与断点续传 | 同学C | 48h | 高 | `module-C-spec.md` + 下载/上传/校验实现 + 单测 |
| Module-D | PC 业务能力面（控制/监控/剪贴板/审计） | 同学D | 44h | 中 | `module-D-spec.md` + Python RPC 扩展 + 单测 |

## 模块接口装配图（仅契约，不共享运行时状态）
- A 输出：`PairingContextDTO`
- B 输入：`PairingContextDTO`，输出：`RpcSessionDTO`
- C 输入：`RpcSessionDTO` + `FileTransferRequestDTO`，输出：`FileTransferResultDTO`
- D 输入：标准 JSON-RPC 请求，输出：标准 JSON-RPC 响应（由 B/C 调用）

## 冻结 DTO/IDL（`IDL-v1.0.0`）

```json
{
  "PairingContextDTO": {
    "schema_version": "1.0.0",
    "host_ipv4": "string",
    "port": 8089,
    "pairing_id": "string",
    "key_b64": "string"
  },
  "RpcSessionDTO": {
    "schema_version": "1.0.0",
    "session_id": "string",
    "connected": true,
    "secure_channel": true,
    "host_ipv4": "string",
    "port": 8089
  },
  "FileTransferRequestDTO": {
    "schema_version": "1.0.0",
    "path": "string",
    "offset": 0,
    "size": 262144,
    "direction": "download|upload"
  },
  "FileTransferResultDTO": {
    "schema_version": "1.0.0",
    "path": "string",
    "offset": 0,
    "size": 0,
    "crc32": 0,
    "eof": false,
    "ok": true,
    "error_code": "string|null"
  }
}
```

## 合并前冒烟准入
- 必跑脚本：`test-assets/smoke/run_smoke.py`
- 准入条件：
  - 所有 fixture JSON 可通过 schema 校验
  - 不存在跨模块非法 import（A↔B↔C↔D 直接引用）
  - 模块 mock 联调脚本返回 0 退出码
