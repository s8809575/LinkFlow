package com.linkflow.app.nsd

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test

class NsdDiscoveryManagerTest {
    @Test
    fun discover_retries_and_returns_result() = runBlocking {
        var calls = 0
        val mgr = NsdDiscoveryManager(object : NsdDiscoveryManager.Discoverer {
            override suspend fun discoverOnce(): NsdDiscoveryManager.Result {
                calls++
                if (calls < 3) throw RuntimeException("fail")
                return NsdDiscoveryManager.Result("192.168.1.2", 8089, "p1")
            }
        })
        val res = mgr.discoverCompanionService(timeoutMs = 100, retries = 3, retryDelayMs = 1)
        assertEquals(3, calls)
        assertEquals("192.168.1.2", res.hostIpv4)
        assertEquals(8089, res.port)
        assertEquals("p1", res.pairingId)
    }
}

