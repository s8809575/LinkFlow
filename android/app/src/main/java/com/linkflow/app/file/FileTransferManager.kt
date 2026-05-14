package com.linkflow.app.file

import android.content.Context
import com.linkflow.app.rpc.RpcClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.RandomAccessFile
import java.security.MessageDigest
import java.util.Base64

data class RpcSessionDTO(
    val schemaVersion: String,
    val sessionId: String,
    val connected: Boolean,
    val secureChannel: Boolean,
    val hostIpv4: String,
    val port: Int,
)

data class FileTransferRequestDTO(
    val schemaVersion: String,
    val path: String,
    val offset: Long = 0L,
    val size: Int = FileTransferManager.CHUNK_SIZE_BYTES,
    val direction: String,
)

data class FileTransferResultDTO(
    val schemaVersion: String,
    val path: String,
    val offset: Long,
    val size: Long,
    val crc32: Long,
    val eof: Boolean,
    val ok: Boolean,
    val errorCode: String?,
)

class FileTransferManager(
    private val context: Context? = null,
    private val rpc: RpcClient,
) {
    fun download(req: FileTransferRequestDTO, target: File): Flow<Int> = flow {
        require(req.schemaVersion == IDL_VERSION) { "Unsupported IDL version: ${req.schemaVersion}" }
        require(req.direction == DIRECTION_DOWNLOAD) { "download requires direction=download" }

        val total = statRemoteSize(req.path)
        val part = partFile(target)
        val offsetFile = offsetFile(target.absolutePath)
        val savedOffset = loadOffset(target.absolutePath)
        var offset = if (savedOffset > 0L) savedOffset else req.offset.coerceAtLeast(0L)

        if (offset > total) {
            cleanup(part, offsetFile)
            offset = 0L
        }

        part.parentFile?.mkdirs()
        if (!part.exists()) part.createNewFile()
        if (part.length() < offset) offset = part.length()

        var lastProgress = -1
        suspend fun emitProgress(value: Int) {
            if (value != lastProgress) {
                emit(value)
                lastProgress = value
            }
        }

        emitProgress(0)
        if (offset > 0L) emitProgress(progress(offset, total))

        try {
            RandomAccessFile(part, "rw").use { out ->
                out.setLength(offset)
                out.seek(offset)
                while (offset < total) {
                    val result = readVerifiedChunk(req.path, offset, req.size)
                    out.write(result.bytes)
                    offset += result.bytes.size
                    saveOffset(target.absolutePath, offset)
                    emitProgress(progress(offset, total))
                    if (result.eof) break
                }
            }
        } catch (e: CrcMismatchException) {
            cleanup(part, offsetFile)
            throw e
        }

        if (target.exists() && !target.delete()) {
            cleanup(part, offsetFile)
            throw IllegalStateException("Cannot replace target file: ${target.absolutePath}")
        }
        if (!part.renameTo(target)) {
            cleanup(part, offsetFile)
            throw IllegalStateException("Cannot finalize download: ${target.absolutePath}")
        }
        offsetFile.delete()
        emitProgress(100)
    }

    fun upload(req: FileTransferRequestDTO, source: File): Flow<Int> = flow {
        require(req.schemaVersion == IDL_VERSION) { "Unsupported IDL version: ${req.schemaVersion}" }
        require(req.direction == DIRECTION_UPLOAD) { "upload requires direction=upload" }
        require(source.isFile) { "Upload source is not a file: ${source.absolutePath}" }

        val total = source.length()
        val savedOffset = loadOffset(source.absolutePath)
        var offset = if (savedOffset > 0L) savedOffset else req.offset.coerceAtLeast(0L)
        if (offset > total) {
            offsetFile(source.absolutePath).delete()
            offset = 0L
        }

        var lastProgress = -1
        suspend fun emitProgress(value: Int) {
            if (value != lastProgress) {
                emit(value)
                lastProgress = value
            }
        }

        emitProgress(0)
        if (offset > 0L) emitProgress(progress(offset, total))

        RandomAccessFile(source, "r").use { input ->
            input.seek(offset)
            val buffer = ByteArray(req.size.coerceAtMost(CHUNK_SIZE_BYTES))
            while (offset < total) {
                val expected = minOf(buffer.size.toLong(), total - offset).toInt()
                val read = input.read(buffer, 0, expected)
                if (read <= 0) break
                val bytes = buffer.copyOf(read)
                val crc32 = ChunkVerifier.crc32(bytes)
                val eof = offset + read >= total
                val params = JSONObject()
                    .put("path", req.path)
                    .put("offset", offset)
                    .put("size", read)
                    .put("crc32", crc32)
                    .put("eof", eof)
                    .put("data_b64", Base64.getEncoder().encodeToString(bytes))

                val response = rpc.invoke("file.write_chunk", params)
                val result = response.optJSONObject("result")
                if (result != null && !result.optBoolean("ok", true)) {
                    throw IllegalStateException(result.optString("error_code", "UPLOAD_FAIL"))
                }

                offset += read
                saveOffset(source.absolutePath, offset)
                emitProgress(progress(offset, total))
            }
        }

        offsetFile(source.absolutePath).delete()
        emitProgress(100)
    }

    fun download(path: String, outFile: File): Flow<Int> {
        return download(
            FileTransferRequestDTO(
                schemaVersion = IDL_VERSION,
                path = path,
                offset = 0L,
                size = CHUNK_SIZE_BYTES,
                direction = DIRECTION_DOWNLOAD,
            ),
            outFile,
        )
    }

    fun verifyChunk(bytes: ByteArray, expectedCrc32: Long): Boolean {
        return ChunkVerifier.verifyChunk(bytes, expectedCrc32)
    }

    fun loadOffset(path: String): Long {
        val file = offsetFile(path)
        return file.takeIf { it.isFile }?.readText()?.trim()?.toLongOrNull()?.coerceAtLeast(0L) ?: 0L
    }

    fun saveOffset(path: String, offset: Long): Unit {
        val file = offsetFile(path)
        file.parentFile?.mkdirs()
        file.writeText(offset.coerceAtLeast(0L).toString())
    }

    fun md5(file: File): String {
        val md = MessageDigest.getInstance("MD5")
        file.inputStream().use { input ->
            val buf = ByteArray(64 * 1024)
            while (true) {
                val read = input.read(buf)
                if (read <= 0) break
                md.update(buf, 0, read)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    private suspend fun statRemoteSize(path: String): Long = withContext(Dispatchers.IO) {
        val stat = rpc.invoke("file.stat", JSONObject().put("path", path))
        stat.getJSONObject("result").getLong("size")
    }

    private suspend fun readVerifiedChunk(path: String, offset: Long, requestedSize: Int): ChunkRead {
        val params = JSONObject()
            .put("path", path)
            .put("offset", offset)
            .put("size", requestedSize.coerceAtMost(CHUNK_SIZE_BYTES))

        repeat(MAX_CRC_RETRIES + 1) { attempt ->
            val response = rpc.invoke("file.read_chunk", params)
            val result = response.getJSONObject("result")
            val bytes = Base64.getDecoder().decode(result.getString("data_b64"))
            val expected = result.getLong("crc32")
            if (verifyChunk(bytes, expected)) {
                return ChunkRead(bytes = bytes, eof = result.getBoolean("eof"))
            }
            if (attempt == MAX_CRC_RETRIES) {
                throw CrcMismatchException("CRC32 mismatch after ${MAX_CRC_RETRIES + 1} attempts at offset $offset")
            }
        }
        throw CrcMismatchException("CRC32 mismatch at offset $offset")
    }

    private fun progress(offset: Long, total: Long): Int {
        return when {
            total <= 0L -> 100
            else -> ((offset.toDouble() / total.toDouble()) * 100.0).toInt().coerceIn(0, 100)
        }
    }

    private fun partFile(target: File): File = File(target.absolutePath + PART_SUFFIX)

    private fun offsetFile(path: String): File {
        return if (path.endsWith(OFFSET_SUFFIX)) File(path) else File(path + OFFSET_SUFFIX)
    }

    private fun cleanup(part: File, offset: File) {
        part.delete()
        offset.delete()
    }

    private data class ChunkRead(val bytes: ByteArray, val eof: Boolean)

    private class CrcMismatchException(message: String) : IllegalStateException(message)

    companion object {
        const val IDL_VERSION = "1.0.0"
        const val CHUNK_SIZE_BYTES = 256 * 1024
        private const val MAX_CRC_RETRIES = 3
        private const val PART_SUFFIX = ".part"
        private const val OFFSET_SUFFIX = ".offset"
        private const val DIRECTION_DOWNLOAD = "download"
        private const val DIRECTION_UPLOAD = "upload"
    }
}
