package com.linkflow.app.file

import android.content.Context
import com.linkflow.app.rpc.RpcClient
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

class FileTransferManager(
    private val context: Context,
    private val rpc: RpcClient,
) {
    fun download(path: String, outFile: File): Flow<Int> = flow {
        val chunkSize = 256 * 1024
        val stat = rpc.invoke("file.stat", JSONObject().put("path", path))
        val total = stat.getJSONObject("result").getLong("size")

        val part = File(outFile.absolutePath + ".part")
        val offsetFile = File(outFile.absolutePath + ".offset")
        var offset = offsetFile.takeIf { it.exists() }?.readText()?.trim()?.toLongOrNull() ?: 0L

        if (!part.exists()) part.createNewFile()
        FileOutputStream(part, true).use { fos ->
            while (true) {
                val params = JSONObject()
                    .put("path", path)
                    .put("offset", offset)
                    .put("size", chunkSize)

                var bytes: ByteArray? = null
                var eof = false
                var ok = false
                repeat(3) { attempt ->
                    val res = rpc.invoke(
                        "file.read_chunk",
                        params,
                        rollback = object : RpcClient.Rollback {
                            override suspend fun run() {
                                part.delete()
                                offsetFile.delete()
                            }
                        }
                    )
                    val result = res.getJSONObject("result")
                    val dataB64 = result.getString("data_b64")
                    val chunk = android.util.Base64.decode(dataB64, android.util.Base64.DEFAULT)
                    val expected = result.getLong("crc32")
                    val crc = ChunkVerifier.crc32(chunk)
                    if (crc == expected) {
                        bytes = chunk
                        eof = result.getBoolean("eof")
                        ok = true
                        return@repeat
                    }
                    if (attempt == 2) ok = false
                }
                if (!ok || bytes == null) {
                    part.delete()
                    offsetFile.delete()
                    throw IllegalStateException("CRC32 mismatch")
                }

                fos.write(bytes)
                fos.flush()
                offset += bytes.size
                offsetFile.writeText(offset.toString())

                val percent = if (total <= 0) 0 else ((offset.toDouble() / total.toDouble()) * 100).toInt().coerceIn(0, 100)
                emit(percent)

                if (eof) break
            }
        }

        if (outFile.exists()) outFile.delete()
        part.renameTo(outFile)
        offsetFile.delete()
        emit(100)
    }

    fun md5(file: File): String {
        val md = MessageDigest.getInstance("MD5")
        file.inputStream().use { ins ->
            val buf = ByteArray(1024 * 64)
            while (true) {
                val n = ins.read(buf)
                if (n <= 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }
}

