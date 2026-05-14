package com.linkflow.app.rpc

import com.linkflow.app.util.Notifier
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject

class RpcClient(
    private val transport: RpcTransport,
    private val notifier: Notifier,
) {
    interface Rollback {
        suspend fun run()
    }

    suspend fun invoke(
        method: String,
        params: JSONObject,
        rollback: Rollback? = null,
    ): JSONObject {
        var last: Exception? = null
        repeat(3) {
            val out = withTimeoutOrNull(2_000) {
                try {
                    withContext(Dispatchers.IO) { transport.invoke(method, params) }
                } catch (e: Exception) {
                    last = e
                    null
                }
            }
            if (out != null) return out
            if (last == null) last = RpcException("TIMEOUT", "timeout")
        }
        if (rollback != null) {
            try {
                rollback.run()
            } catch (_: Exception) {
            }
        }
        notifier.toast("操作失败，已回滚")
        val err = last
        if (err is RpcException) throw err
        throw RpcException("RPC_FAIL", err?.message ?: "rpc fail")
    }
}

