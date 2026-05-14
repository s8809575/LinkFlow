# 模块C README

模块C是 LinkFlow 的文件传输模块，负责在已建立安全 RPC 通道后完成文件分片下载、上传、CRC32 校验、断点续传和进度输出。

## 功能范围

已实现：

- 256KB 固定大小分片。
- `java.util.zip.CRC32` 分片校验。
- `.part` 临时文件下载。
- `.offset` 已确认偏移记录。
- 进程重启或网络重连后的断点续传。
- CRC 校验失败时最多重试 3 次，失败后清理 `.part/.offset`。
- `Flow<Int>` 输出 0 到 100 的传输进度。
- 5MB、50MB、500MB 集成样例 MD5 对账材料。

## 主要特性

- **分片传输**: 256KB 固定分片，支持流式并发。
-  **数据完整性**: 强制 CRC32 校验，分片级重试机制。
-  **断点续传**: 基于文件的偏移量持久化，无惧进程崩溃。
- **可观测性**: 响应式 `Flow<Int>` 进度推送。

## 快速上手

### 下载文件

```kotlin
val manager = FileTransferManager(context, rpcClient)
manager.download("C:/photos/large.zip", targetFile)
    .collect { progress ->
        println("当前下载进度: $progress%")
    }
```

### 上传文件

```
manager.upload(requestDto, sourceFile)
    .collect { progress ->
        updateUI(progress)
    }
```

## 核心依赖

- Kotlin Coroutines Flow 1.8.1
- Android API 29+
- java.util.zip.CRC32

## 关键文件

```text
android/app/src/main/java/com/linkflow/app/file/FileTransferManager.kt
android/app/src/main/java/com/linkflow/app/file/ChunkVerifier.kt
android/app/src/test/java/com/linkflow/app/file/FileTransferManagerTest.kt
android/app/src/test/java/com/linkflow/app/file/ChunkVerifierTest.kt
test-assets/fixtures/module_c_transfer_samples.json
test-assets/smoke/module_c_md5_check.py
```
