# module-B-spec（连接会话与统一 RPC 客户端）

## 1. 模块边界
- 职责：维护 TCP 长连接、心跳、重连、请求超时重试与异常标准化。
- 输入：`PairingContextDTO`、业务方法名与参数。
- 输出：`RpcSessionDTO`、标准 JSON-RPC 响应对象。
- 禁止：处理文件分片校验、禁止直接访问本地文件系统业务数据。

## 2. 输入输出接口（冻结）

### 2.1 Kotlin 函数签名
```kotlin
suspend fun connectAndPair(ctx: PairingContextDTO): RpcSessionDTO
suspend fun invoke(method: String, params: JSONObject): JSONObject
fun startHeartbeat(intervalMs: Long = 30000): Unit
fun closeSession(): Unit
```

### 2.2 JSON-RPC 协议
```json
{
  "request": {"jsonrpc":"2.0","id":1,"method":"sys.heartbeat","params":{}},
  "response_ok": {"jsonrpc":"2.0","id":1,"result":{"ts":1710000000}},
  "response_err": {"jsonrpc":"2.0","id":1,"error":{"code":-32001,"message":"SECURE_CHANNEL_REQUIRED"}}
}
```

## 3. 核心用例与验收（Given-When-Then）
- Given 已持有合法 `PairingContextDTO`，When 建连并执行 `pair.bind`，Then 返回 `RpcSessionDTO.connected=true` 且 `secure_channel=true`。
- Given 心跳连续两次无响应，When 触发重连逻辑，Then 采用指数退避（1s→2s→4s...最大30s）且最多5次。
- Given `invoke()` 超时，When 自动重试 3 次仍失败，Then 抛 `RpcException` 并返回统一错误码。
- Given 配对失败，When 收到错误响应，Then 立刻关闭会话并不上抛明文密钥。

## 4. 显式排除（防镀金）
- 不负责 UI 提示文案细节与页面组件渲染。
- 不实现具体文件传输逻辑（仅传递 RPC 调用）。
- 不实现审计落盘。

## 5. 测试要求
- 单元测试：行覆盖率 `>=80%`，分支覆盖率 `>=75%`。
- 必测分支：配对成功/失败、超时重试、断线重连5次放弃、心跳恢复。

## 6. 外部依赖（版本锁定）
- Kotlin Coroutines `1.8.1`
- Android `Socket`/`HandlerThread`（API 29+）
- AES-GCM：JCA `AES/GCM/NoPadding`

## 7. 交付验收清单
- `TcpConnectionManager.kt`、`RpcClient.kt`、`RpcException.kt`、`LengthPrefixedFramer.kt`、`AesGcmCipher.kt`
- 本地 fake transport 单测报告。
