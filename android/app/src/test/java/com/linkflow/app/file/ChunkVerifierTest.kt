package com.linkflow.app.file

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChunkVerifierTest {
    @Test
    fun crc32_matches_known_value() {
        val v = ChunkVerifier.crc32("abc".toByteArray())
        assertEquals(0x352441C2L, v)
    }

    @Test
    fun verifyChunk_accepts_matching_crc_and_rejects_mismatch() {
        val bytes = "linkflow".toByteArray()
        assertTrue(ChunkVerifier.verifyChunk(bytes, ChunkVerifier.crc32(bytes)))
        assertFalse(ChunkVerifier.verifyChunk(bytes, 0L))
    }
}
