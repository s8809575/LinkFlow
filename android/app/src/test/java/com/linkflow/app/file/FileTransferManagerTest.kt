package com.linkflow.app.file

import com.linkflow.app.rpc.RpcClient
import com.linkflow.app.rpc.RpcTransport
import com.linkflow.app.util.Notifier
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.Base64

class FileTransferManagerTest {
    private class SilentNotifier : Notifier {
        override fun toast(message: String) = Unit
    }

    @Test
    fun download_reads_fixed_chunks_and_writes_offsets() = runBlocking {
        val content = deterministicBytes(5 * 1024 * 1024 + 17)
        val calls = mutableListOf<Long>()
        val manager = FileTransferManager(
            rpc = RpcClient(
                object : RpcTransport {
                    override suspend fun invoke(method: String, params: JSONObject): JSONObject {
                        return when (method) {
                            "file.stat" -> JSONObject().put("result", JSONObject().put("size", content.size))
                            "file.read_chunk" -> {
                                val offset = params.getLong("offset")
                                val size = params.getInt("size")
                                calls += offset
                                assertEquals(FileTransferManager.CHUNK_SIZE_BYTES, size)
                                val end = minOf(offset + size, content.size.toLong()).toInt()
                                val bytes = content.copyOfRange(offset.toInt(), end)
                                JSONObject().put(
                                    "result",
                                    JSONObject()
                                        .put("path", params.getString("path"))
                                        .put("offset", offset)
                                        .put("size", bytes.size)
                                        .put("crc32", ChunkVerifier.crc32(bytes))
                                        .put("eof", end == content.size)
                                        .put("data_b64", Base64.getEncoder().encodeToString(bytes)),
                                )
                            }
                            else -> error("unexpected method $method")
                        }
                    }
                },
                SilentNotifier(),
            ),
        )
        val target = tempFile("download.bin")
        target.delete()

        val progress = manager.download(
            FileTransferRequestDTO("1.0.0", "/remote.bin", direction = "download"),
            target,
        ).toList()

        assertArrayEquals(content, target.readBytes())
        assertEquals(0, progress.first())
        assertEquals(100, progress.last())
        assertEquals(0L, calls.first())
        assertEquals(FileTransferManager.CHUNK_SIZE_BYTES.toLong(), calls[1])
        assertFalse(File(target.absolutePath + ".part").exists())
        assertFalse(File(target.absolutePath + ".offset").exists())
    }

    @Test
    fun download_resumes_from_saved_offset_without_refetching_confirmed_chunks() = runBlocking {
        val content = deterministicBytes(FileTransferManager.CHUNK_SIZE_BYTES * 3 + 13)
        val target = tempFile("resume.bin")
        target.delete()
        val part = File(target.absolutePath + ".part")
        val confirmed = FileTransferManager.CHUNK_SIZE_BYTES
        part.writeBytes(content.copyOfRange(0, confirmed))

        val manager = managerForDownload(content)
        manager.saveOffset(target.absolutePath, confirmed.toLong())

        val progress = manager.download(
            FileTransferRequestDTO("1.0.0", "/remote.bin", direction = "download"),
            target,
        ).toList()

        assertArrayEquals(content, target.readBytes())
        assertEquals(0, progress.first())
        assertTrue(progress.any { it > 0 })
        assertFalse(File(target.absolutePath + ".offset").exists())
    }

    @Test
    fun download_deletes_part_and_offset_after_crc_retry_exhaustion() = runBlocking {
        val content = deterministicBytes(FileTransferManager.CHUNK_SIZE_BYTES + 1)
        val target = tempFile("bad-crc.bin")
        target.delete()
        val manager = FileTransferManager(
            rpc = RpcClient(
                object : RpcTransport {
                    override suspend fun invoke(method: String, params: JSONObject): JSONObject {
                        return when (method) {
                            "file.stat" -> JSONObject().put("result", JSONObject().put("size", content.size))
                            "file.read_chunk" -> {
                                val bytes = content.copyOfRange(0, FileTransferManager.CHUNK_SIZE_BYTES)
                                JSONObject().put(
                                    "result",
                                    JSONObject()
                                        .put("path", params.getString("path"))
                                        .put("offset", params.getLong("offset"))
                                        .put("size", bytes.size)
                                        .put("crc32", 1L)
                                        .put("eof", false)
                                        .put("data_b64", Base64.getEncoder().encodeToString(bytes)),
                                )
                            }
                            else -> error("unexpected method $method")
                        }
                    }
                },
                SilentNotifier(),
            ),
        )
        manager.saveOffset(target.absolutePath, 0L)
        File(target.absolutePath + ".part").writeBytes(byteArrayOf(1, 2, 3))

        var failed = false
        try {
            manager.download(FileTransferRequestDTO("1.0.0", "/remote.bin", direction = "download"), target).toList()
        } catch (_: IllegalStateException) {
            failed = true
        }

        assertTrue(failed)
        assertFalse(File(target.absolutePath + ".part").exists())
        assertFalse(File(target.absolutePath + ".offset").exists())
    }

    @Test
    fun upload_sends_verified_chunks_and_resumes_from_offset() = runBlocking {
        val source = tempFile("upload.bin")
        val content = deterministicBytes(FileTransferManager.CHUNK_SIZE_BYTES * 2 + 9)
        source.writeBytes(content)
        val offsets = mutableListOf<Long>()
        val manager = FileTransferManager(
            rpc = RpcClient(
                object : RpcTransport {
                    override suspend fun invoke(method: String, params: JSONObject): JSONObject {
                        assertEquals("file.write_chunk", method)
                        val bytes = Base64.getDecoder().decode(params.getString("data_b64"))
                        assertTrue(ChunkVerifier.verifyChunk(bytes, params.getLong("crc32")))
                        offsets += params.getLong("offset")
                        return JSONObject().put("result", JSONObject().put("ok", true))
                    }
                },
                SilentNotifier(),
            ),
        )
        manager.saveOffset(source.absolutePath, FileTransferManager.CHUNK_SIZE_BYTES.toLong())

        val progress = manager.upload(
            FileTransferRequestDTO("1.0.0", "/remote.bin", direction = "upload"),
            source,
        ).toList()

        assertEquals(listOf(FileTransferManager.CHUNK_SIZE_BYTES.toLong(), (FileTransferManager.CHUNK_SIZE_BYTES * 2).toLong()), offsets)
        assertEquals(0, progress.first())
        assertEquals(100, progress.last())
        assertFalse(File(source.absolutePath + ".offset").exists())
    }

    private fun managerForDownload(content: ByteArray): FileTransferManager {
        return FileTransferManager(
            rpc = RpcClient(
                object : RpcTransport {
                    override suspend fun invoke(method: String, params: JSONObject): JSONObject {
                        return when (method) {
                            "file.stat" -> JSONObject().put("result", JSONObject().put("size", content.size))
                            "file.read_chunk" -> {
                                val offset = params.getLong("offset")
                                val size = params.getInt("size")
                                val end = minOf(offset + size, content.size.toLong()).toInt()
                                val bytes = content.copyOfRange(offset.toInt(), end)
                                JSONObject().put(
                                    "result",
                                    JSONObject()
                                        .put("path", params.getString("path"))
                                        .put("offset", offset)
                                        .put("size", bytes.size)
                                        .put("crc32", ChunkVerifier.crc32(bytes))
                                        .put("eof", end == content.size)
                                        .put("data_b64", Base64.getEncoder().encodeToString(bytes)),
                                )
                            }
                            else -> error("unexpected method $method")
                        }
                    }
                },
                SilentNotifier(),
            ),
        )
    }

    private fun deterministicBytes(size: Int): ByteArray {
        return ByteArray(size) { index -> ((index * 31 + 7) and 0xFF).toByte() }
    }

    private fun tempFile(name: String): File {
        return File.createTempFile(name, ".tmp").also { it.deleteOnExit() }
    }
}
