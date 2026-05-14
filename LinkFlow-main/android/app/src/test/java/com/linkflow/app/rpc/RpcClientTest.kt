package com.linkflow.app.rpc

import com.linkflow.app.util.Notifier
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RpcClientTest {
    private class FakeNotifier : Notifier {
        var last: String? = null
        override fun toast(message: String) {
            last = message
        }
    }

    @Test
    fun invoke_returns_result_on_success() = runBlocking {
        val notifier = FakeNotifier()
        val transport = object : RpcTransport {
            override suspend fun invoke(method: String, params: JSONObject): JSONObject {
                return JSONObject().put("result", JSONObject().put("ok", true))
            }
        }
        val c = RpcClient(transport, notifier)
        val out = c.invoke("x", JSONObject())
        assertTrue(out.getJSONObject("result").getBoolean("ok"))
    }

    @Test
    fun invoke_retries_and_toasts_on_failure() = runBlocking {
        val notifier = FakeNotifier()
        var calls = 0
        val transport = object : RpcTransport {
            override suspend fun invoke(method: String, params: JSONObject): JSONObject {
                calls++
                throw RuntimeException("fail")
            }
        }
        val c = RpcClient(transport, notifier)
        try {
            c.invoke("x", JSONObject())
        } catch (_: Exception) {
        }
        assertEquals(3, calls)
        assertEquals("操作失败，已回滚", notifier.last)
    }
}

