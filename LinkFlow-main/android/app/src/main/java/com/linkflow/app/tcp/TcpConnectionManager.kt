package com.linkflow.app.tcp

import android.os.Handler
import android.os.HandlerThread
import android.os.Looper
import android.util.Base64
import com.linkflow.app.crypto.AesGcmCipher
import com.linkflow.app.crypto.LengthPrefixedFramer
import com.linkflow.app.rpc.RpcException
import com.linkflow.app.rpc.RpcTransport
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.InputStream
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.min
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeoutOrNull

// PairingContextDTO.kt
data class PairingContextDTO(
    val host: String,
    val port: Int,
    val pairingId: String,
    val keyB64: String
)

// RpcSessionDTO.kt
data class RpcSessionDTO(
    val connected: Boolean,
    val secureChannel: Boolean,
    val sessionId: String? = null
)

class TcpConnectionManager : RpcTransport {
    sealed class Event {
        data object ConnectionGiveUp : Event()
    }

    private val requestId = AtomicInteger(1)
    private val inflight = ConcurrentHashMap<Int, CompletableDeferred<JSONObject>>()

    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var socket: Socket? = null
    private var input: InputStream? = null
    private var output: OutputStream? = null
    private var readerThread: Thread? = null

    private var framer: LengthPrefixedFramer = LengthPrefixedFramer()
    private var giveUpCallback: (() -> Unit)? = null

    private var ctx: PairingContextDTO? = null
    private var isClosed = false
    private var isHeartbeatActive = false
    private var currentHeartbeatInterval: Long = 30000

    fun initLooperThread() {
        if (thread != null) return
        val t = HandlerThread("LinkFlow-Tcp")
        t.start()
        thread = t
        handler = Handler(t.looper)
    }

    fun setGiveUpCallback(cb: () -> Unit) {
        giveUpCallback = cb
    }

    suspend fun connectAndPair(ctx: PairingContextDTO): RpcSessionDTO {
        this.ctx = ctx
        isClosed = false
        initLooperThread()
        return withContext(Dispatchers.IO) { connectAndPairInternal() }
    }

     private suspend fun connectAndPairInternal(): RpcSessionDTO {
        establishConnection()
        val bindResult = performPairBind()
        if (bindResult.has("error")) {
            closeSession()
            val error = bindResult.getJSONObject("error")
            throw RpcException(
                code = error.optInt("code", -32001),
                message = error.optString("message", "PAIR_FAIL")
            )
        }
        stopReader()
        val key = Base64.decode(ctx!!.keyB64, Base64.DEFAULT)
        framer = LengthPrefixedFramer(cipher = AesGcmCipher(key))
        startReader(plain = false)
        startHeartbeat()
        return RpcSessionDTO(
            connected = true,
            secureChannel = true,
            sessionId = bindResult.optString("session_id")
        )
    }

    private fun establishConnection() {
        closeInternal()
        val s = Socket()
        s.tcpNoDelay = true
        s.connect(InetSocketAddress(ctx!!.host, ctx!!.port), 5000)
        socket = s
        input = s.getInputStream()
        output = s.getOutputStream()
        startReader(plain = true)
    }

    private suspend fun performPairBind(): JSONObject {
        val id = requestId.getAndIncrement()
        val request = JSONObject().apply {
            put("jsonrpc", "2.0")
            put("id", id)
            put("method", "pair.bind")
            put("params", JSONObject().apply {
                put("pairing_id", ctx!!.pairingId)
                put("key_b64", ctx!!.keyB64)
            })
        }

        val deferred = CompletableDeferred<JSONObject>()
        inflight[id] = deferred

        // 发送请求
        sendRpc(request.toString().toByteArray(Charsets.UTF_8))

        // 等待响应（5秒超时）
        val result = withTimeoutOrNull(5000) { deferred.await() }
            ?: throw RpcException(RpcException.TIMEOUT, "Pair bind timeout")

        return result
    }

    override suspend fun invoke(method: String, params: JSONObject): JSONObject {
        var lastException: Exception? = null

        for (attempt in 1..3) {
            try {
                val id = requestId.getAndIncrement()
                val request = JSONObject().apply {
                    put("jsonrpc", "2.0")
                    put("id", id)
                    put("method", method)
                    put("params", params)
                }

                val deferred = CompletableDeferred<JSONObject>()
                inflight[id] = deferred

                sendRpc(request.toString().toByteArray(Charsets.UTF_8))

                // 等待响应（5秒超时）
                val result = withTimeoutOrNull(5000) { deferred.await() }
                    ?: throw RpcException(RpcException.TIMEOUT, "Request timeout after attempt $attempt")

                // 检查是否为错误响应
                if (result.has("error")) {
                    val error = result.getJSONObject("error")
                    throw RpcException(
                        code = error.optInt("code", RpcException.SECURE_CHANNEL_REQUIRED),
                        message = error.optString("message", "RPC_ERROR")
                    )
                }

                return result

            } catch (e: Exception) {
                lastException = e
                if (attempt < 3) {
                    delay(1000L * attempt) // 线性退避重试
                }
            }
        }

        throw RpcException(RpcException.MAX_RETRIES, "Max retries reached", lastException)
    }

  /*  private fun connectInternal() {
        closeInternal()
        val s = Socket()
        s.tcpNoDelay = true
        s.connect(InetSocketAddress(host, port), 2000)
        socket = s
        input = s.getInputStream()
        output = s.getOutputStream()

        val bindId = requestId.getAndIncrement()
        val bindReq = JSONObject()
            .put("jsonrpc", "2.0")
            .put("id", bindId)
            .put("method", "pair.bind")
            .put("params", JSONObject().put("pairing_id", pairingId).put("key_b64", keyB64))
        val bindDeferred = CompletableDeferred<JSONObject>()
        inflight[bindId] = bindDeferred
        sendFrame(LengthPrefixedFramer().pack(bindReq.toString().toByteArray(Charsets.UTF_8)))

        startReader(plain = true)
        val bindRes = runBlockingAwait(bindDeferred, 2000)
        if (bindRes.optJSONObject("error") != null) {
            throw RpcException("PAIR_FAIL", "pair bind failed")
        }
        val key = Base64.decode(keyB64, Base64.DEFAULT)
        framer = LengthPrefixedFramer(cipher = AesGcmCipher(key))
        startReader(plain = false)
        startHeartbeat()
    }*/

    private fun runBlockingAwait(d: CompletableDeferred<JSONObject>, timeoutMs: Long): JSONObject {
        val start = System.currentTimeMillis()
        while (true) {
            if (d.isCompleted) return d.getCompleted()
            if (System.currentTimeMillis() - start > timeoutMs) throw RpcException("TIMEOUT", "timeout")
            Thread.sleep(10)
        }
    }

    private fun sendRpc(payload: ByteArray) {
        val out = output ?: throw RpcException("NO_CONNECTION", "no connection")
        out.write(framer.pack(payload))
        out.flush()
    }

    private fun sendFrame(frame: ByteArray) {
        val out = output ?: throw RpcException("NO_CONNECTION", "no connection")
        out.write(frame)
        out.flush()
    }

    private fun startReader(plain: Boolean) {
        readerThread?.interrupt()
        val inStream = input ?: return
        val usedFramer = if (plain) LengthPrefixedFramer() else framer
        readerThread = Thread {
            var buf = ByteArray(0)
            val tmp = ByteArray(65535)
            try {
                while (!Thread.currentThread().isInterrupted) {
                    val n = inStream.read(tmp)
                    if (n <= 0) break
                    buf += tmp.copyOfRange(0, n)
                    while (true) {
                        val (msg, rest) = usedFramer.tryUnpack(buf)
                        if (msg == null) break
                        buf = rest
                        val obj = JSONObject(msg.toString(Charsets.UTF_8))
                        val id = obj.optInt("id", -1)
                        if (id != -1) {
                            inflight.remove(id)?.complete(obj)
                        }
                    }
                }
            } catch (_: Exception) {
            } finally {
                closeInternal()
                scheduleReconnect()
            }
        }.apply { isDaemon = true; start() }
    }

    fun startHeartbeat(intervalMs: Long = 30000) {
        if (isHeartbeatActive || isClosed) return
        isHeartbeatActive = true
        currentHeartbeatInterval = intervalMs

        val h = handler ?: return
        var missed = 0

        fun tick() {
            if (isClosed || !isHeartbeatActive) return

            val id = requestId.getAndIncrement()
            val req = JSONObject().apply {
                put("jsonrpc", "2.0")
                put("id", id)
                put("method", "sys.heartbeat")
                put("params", JSONObject())
            }
            val d = CompletableDeferred<JSONObject>()
            inflight[id] = d

            try {
                sendRpc(req.toString().toByteArray(Charsets.UTF_8))
            } catch (_: Exception) {
                missed++
            }

            h.postDelayed({
                if (!d.isCompleted) missed++ else missed = 0
                if (missed >= 2) {
                    isHeartbeatActive = false
                    closeInternal()
                    scheduleReconnect()
                    return@postDelayed
                }
                tick()
            }, intervalMs)
        }

        h.post { tick() }
    }
    private fun scheduleReconnect() {
        if (isClosed) return

        var delayMs = 1000L
        var attempts = 0

        fun attempt() {
            if (isClosed) return

            if (attempts >= 5) {
                giveUpCallback?.invoke()
                closeSession()
                return
            }

            handler?.postDelayed({
                if (isClosed) return@postDelayed

                // 启动协程执行重连
                kotlinx.coroutines.GlobalScope.launch(Dispatchers.IO) {
                    try {
                        // 重新连接
                        establishConnection()

                        // 重新配对
                        val bindResult = performPairBind()

                        if (bindResult.has("error")) {
                            throw RpcException(-32002, "Re-pair failed")
                        }

                        // 切换回加密模式
                        withContext(Dispatchers.Main) {
                            stopReader()
                            val key = Base64.decode(ctx!!.keyB64, Base64.DEFAULT)
                            framer = LengthPrefixedFramer(cipher = AesGcmCipher(key))
                            startReader(plain = false)
                            startHeartbeat(currentHeartbeatInterval)
                        }

                    } catch (e: Exception) {
                        attempts++
                        delayMs = min(delayMs * 2, 30000)
                        attempt()
                    }
                }
            }, delayMs)
        }

        attempt()
    }

    private fun stopReader() {
        readerThread?.interrupt()
        readerThread?.join(500)
        readerThread = null
    }

    fun closeSession() {
        isClosed = true
        isHeartbeatActive = false
        stopReader()
        closeInternal()
        handler?.removeCallbacksAndMessages(null)
        thread?.quitSafely()
        thread = null
        handler = null
        ctx = null
    }
    private fun closeInternal() {
        try {
            socket?.close()
        } catch (_: Exception) {
        }
        socket = null
        input = null
        output = null
        inflight.forEach { (_, d) -> d.cancel() }
        inflight.clear()
    }
}

