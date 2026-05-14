package com.linkflow.app.file

import java.util.zip.CRC32

object ChunkVerifier {
    fun crc32(bytes: ByteArray): Long {
        val crc = CRC32()
        crc.update(bytes)
        return crc.value
    }
}

