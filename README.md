# Module A: 服务发现与安全配对模块

## 1. 概述
本模块负责在局域网内定位 PC 端服务（Module D），并建立安全的初始配对关系。支持 mDNS 自动发现、二维码扫描及手动输入三种引导方式。

## 2. 核心功能
* **mDNS 服务发现**：基于 Android `NsdManager` 实现 `_companion._tcp.` 服务的自动检索。
* **多路径配对**：支持 `QrCodeParser`（扫码）与 `ManualInputValidator`（手动输入）双重校验。
* **安全存储**：利用 `EncryptedSharedPreferences` 对配对密钥进行 AES-256 加密落库。
* **连接验证**：在完成配对前通过 RPC 握手验证密钥有效性。

## 3. 输出定义
本模块产出 `PairingContextDTO` 供 **Module B** 调用，用于建立后续的长连接：
```json
{
  "host_ipv4": "string",
  "port": 8089,
  "pairing_id": "string",
  "key_b64": "string"
}
