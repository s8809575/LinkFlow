package com.linkflow.app.file

import java.util.zip.CRC32

object ChunkVerifier {
    fun crc32(bytes: ByteArray): Long {
        val crc = CRC32()
        crc.update(bytes)
        return crc.value
    }

    fun verifyChunk(bytes: ByteArray, expectedCrc32: Long): Boolean {
        return crc32(bytes) == (expectedCrc32 and 0xFFFFFFFFL)
    }
}
