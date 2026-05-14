# module-C-spec（文件分片传输与断点续传）

## 1. 模块边界
- 职责：按 256KB 固定分片传输、CRC32 校验、断点续传、进度流输出。
- 输入：`RpcSessionDTO`、`FileTransferRequestDTO`。
- 输出：`FileTransferResultDTO`、`Flow<Int>` 进度。
- 禁止：发现/配对逻辑、设备连接管理、系统控制命令。

## 2. 输入输出接口（冻结）

### 2.1 Kotlin 函数签名
```kotlin
fun download(req: FileTransferRequestDTO, target: File): Flow<Int>
fun upload(req: FileTransferRequestDTO, source: File): Flow<Int>
fun verifyChunk(bytes: ByteArray, expectedCrc32: Long): Boolean
fun loadOffset(path: String): Long
fun saveOffset(path: String, offset: Long): Unit
```

### 2.2 RPC 消息格式（冻结）
```json
{
  "read_chunk_req": {
    "jsonrpc":"2.0","id":9,"method":"file.read_chunk",
    "params":{"path":"C:/a.bin","offset":0,"size":262144}
  },
  "read_chunk_res": {
    "jsonrpc":"2.0","id":9,"result":{
      "path":"C:/a.bin","offset":0,"size":262144,"crc32":123456789,"eof":false,"data_b64":"..."
    }
  }
}
```

## 3. 核心用例与验收（Given-When-Then）
- Given 5MB 文件下载任务，When 网络稳定，Then 全部分片校验通过并输出 0→100 的进度。
- Given 中途杀进程，When 重启后继续任务，Then 从 `.offset` 记录点续传而非从 0 开始。
- Given 分片 CRC32 不匹配，When 重拉同分片最多 3 次仍失败，Then 删除 `.part` 与 `.offset` 并返回失败。
- Given 上传任务断网，When 重连恢复后继续上传，Then 已确认分片不重复上传。

## 4. 显式排除（防镀金）
- 不实现视频在线播放 UI。
- 不实现目录浏览 UI 组件。
- 不实现云端对象存储适配。

## 5. 测试要求
- 单元测试：行覆盖率 `>=80%`，分支覆盖率 `>=75%`。
- 集成样例文件：5MB/50MB/500MB 三档必须覆盖。

## 6. 外部依赖（版本锁定）
- `java.util.zip.CRC32`（JDK）
- Android 文件系统 API（API 29+）
- Kotlin Coroutines Flow `1.8.1`

## 7. 交付验收清单
- `FileTransferManager.kt`、`ChunkVerifier.kt`
- fixture 文件与 MD5 对账脚本输出。
