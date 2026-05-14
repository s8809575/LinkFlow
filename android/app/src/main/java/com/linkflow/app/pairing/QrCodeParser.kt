package com.linkflow.app.pairing

import com.linkflow.app.util.PairingSecretDTO

object QrCodeParser {
    // ✅ spec签名
    fun parseQrPayload(payload: String): PairingSecretDTO {
        val split = payload.split(";")
        require(split.size == 2) { "QR format error" }
        return PairingSecretDTO(split[0].trim(), split[1].trim())
    }
}
