package com.linkflow.app.util

data class PairingContextDTO(
    val schemaVersion: String = "1.0.0",
    val hostIpv4: String,
    val port: Int,
    val pairingId: String,
    val keyB64: String
)
