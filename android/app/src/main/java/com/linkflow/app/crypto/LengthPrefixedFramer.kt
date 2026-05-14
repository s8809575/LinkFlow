package com.linkflow.app.crypto

import java.nio.ByteBuffer
import java.nio.ByteOrder

class LengthPrefixedFramer(
    private val cipher: AesGcmCipher? = null,
) {
    fun pack(payload: ByteArray): ByteArray {
        val body = cipher?.encrypt(payload) ?: payload
        val len = ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putInt(body.size).array()
        return len + body
    }

    fun tryUnpack(buffer: ByteArray): Pair<ByteArray?, ByteArray> {
        if (buffer.size < 4) return Pair(null, buffer)
        val len = ByteBuffer.wrap(buffer, 0, 4).order(ByteOrder.BIG_ENDIAN).int
        if (len < 0) throw IllegalArgumentException("negative frame length")
        if (buffer.size < 4 + len) return Pair(null, buffer)
        val body = buffer.copyOfRange(4, 4 + len)
        val rest = buffer.copyOfRange(4 + len, buffer.size)
        val out = cipher?.decrypt(body) ?: body
        return Pair(out, rest)
    }
}

