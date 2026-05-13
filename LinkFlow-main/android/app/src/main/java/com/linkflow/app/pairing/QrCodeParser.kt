package com.linkflow.app.pairing

import com.linkflow.app.util.PairingSecretDTO

object QrCodeParser {
    fun parse(payload: String): PairingSecretDTO {
        val split = payload.split(";")
        require(split.size == 2) { "Invalid QR format" }
        return PairingSecretDTO(
            pairingId = split[0].trim(),
            keyB64 = split[1].trim()
        )
    }
}
