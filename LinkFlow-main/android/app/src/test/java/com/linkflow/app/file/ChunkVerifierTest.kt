package com.linkflow.app.file

import org.junit.Assert.assertEquals
import org.junit.Test

class ChunkVerifierTest {
    @Test
    fun crc32_matches_known_value() {
        val v = ChunkVerifier.crc32("abc".toByteArray())
        assertEquals(0x352441C2L, v)
    }
}

