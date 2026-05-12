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
import org.json.JSONObject
import java.io.InputStream
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.min

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

    private var pairingId: String? = null
    private var keyB64: String? = null
    private var host: String? = null
    private var port: Int = 8089

    private var framer: LengthPrefixedFramer = LengthPrefixedFramer()
    private var giveUpCallback: (() -> Unit)? = null

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

    suspend fun connectAndPair(host: String, port: Int, pairingId: String, keyB64: String) {
        this.host = host
        this.port = port
        this.pairingId = pairingId
        this.keyB64 = keyB64
        initLooperThread()
        withContext(Dispatchers.IO) { connectInternal() }
    }

    override suspend fun invoke(method: String, params: JSONObject): JSONObject {
        val id = requestId.getAndIncrement()
        val req = JSONObject()
            .put("jsonrpc", "2.0")
            .put("id", id)
            .put("method", method)
            .put("params", params)
        val d = CompletableDeferred<JSONObject>()
        inflight[id] = d
        sendRpc(req.toString().toByteArray(Charsets.UTF_8))
        return d.await()
    }

    private fun connectInternal() {
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
    }

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

    private fun startHeartbeat() {
        val h = handler ?: return
        var missed = 0
        fun tick() {
            val id = requestId.getAndIncrement()
            val req = JSONObject().put("jsonrpc", "2.0").put("id", id).put("method", "sys.heartbeat").put("params", JSONObject())
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
                    closeInternal()
                    scheduleReconnect()
                    return@postDelayed
                }
                tick()
            }, 30_000)
        }
        h.post { tick() }
    }

    private fun scheduleReconnect() {
        val h = handler ?: return
        var delayMs = 1000L
        fun attempt(remaining: Int) {
            if (remaining <= 0) {
                giveUpCallback?.invoke()
                return
            }
            h.postDelayed({
                try {
                    connectInternal()
                } catch (_: Exception) {
                    delayMs = min(delayMs * 2, 30_000)
                    attempt(remaining - 1)
                    return@postDelayed
                }
            }, delayMs)
        }
        attempt(5)
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

