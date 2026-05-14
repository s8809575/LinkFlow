# module-A-spec（服务发现与安全配对）

## 1. 模块边界
- 职责：发现 `_companion._tcp` 服务、解析 `pairing_id`、建立配对上下文。
- 输入：Android 网络环境、二维码或手工输入的 `pairing_id;key_b64`。
- 输出：`PairingContextDTO`（冻结版本 `1.0.0`）。
- 禁止：直接发业务 RPC（`system.*`、`file.*`），禁止依赖文件传输逻辑。

## 2. 输入输出接口（冻结）

### 2.1 Kotlin 函数签名
```kotlin
suspend fun discoverCompanionService(
    timeoutMs: Long = 5000,
    retries: Int = 3,
    retryDelayMs: Long = 1000
): PairingContextDTO

fun parseQrPayload(payload: String): PairingSecretDTO
fun validateManualInput(pairingId: String, keyB64: String): ValidationResult
fun persistPairingSecret(pairingId: String, keyB64: String): Unit
```

### 2.2 DTO/消息格式
```json
{
  "PairingContextDTO": {
    "schema_version": "1.0.0",
    "host_ipv4": "192.168.137.1",
    "port": 8089,
    "pairing_id": "pair-abcd-1234",
    "key_b64": "Base64(16-byte-key)"
  }
}
```

## 3. 核心用例与验收（Given-When-Then）
- Given 手机与电脑在同一热点网段，When 调用发现接口，Then 在 5 秒内返回 IPv4+8089+pairing_id。
- Given mDNS 返回服务但缺少 `pairing_id`，When 连续重试 3 次，Then 抛 `NSD_DISCOVERY_FAILED` 并触发用户可见 Toast。
- Given 扫码内容为 `pairing_id;key_b64`，When 解析成功，Then 配对按钮可用且落库到 EncryptedSharedPreferences。
- Given 手动输入任一字段为空，When 页面渲染，Then 提交按钮为 disabled。

## 4. 显式排除（防镀金）
- 不实现业务 RPC 调用，不实现文件上传下载。
- 不实现历史配对设备管理页。
- 不实现跨平台（iOS）发现逻辑。

## 5. 测试要求
- 单元测试：行覆盖率 `>=80%`，分支覆盖率 `>=75%`。
- 必测分支：发现成功、发现超时、pairing_id 缺失、二维码格式错误、手输格式错误。

## 6. 外部依赖（版本锁定）
- `android.net.nsd.NsdManager`（Android 10+）
- `androidx.camera:*:1.3.4`
- `com.google.zxing:core:3.5.3`
- `androidx.security:security-crypto:1.1.0-alpha06`

## 7. 交付验收清单
- `NsdDiscoveryManager.kt`、`PairingActivity.kt`、`QRScanFragment.kt`、相关布局 XML。
- 覆盖率报告截图与测试命令输出。
