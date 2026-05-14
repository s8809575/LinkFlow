package com.linkflow.app.nsd

import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.withContext
import java.net.Inet4Address
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class NsdDiscoveryManager(
    private val discoverer: Discoverer,
) {
    constructor(@Suppress("UNUSED_PARAMETER") context: Any, nsdManager: NsdManager) : this(AndroidDiscoverer(nsdManager))

    data class Result(
        val hostIpv4: String,
        val port: Int,
        val pairingId: String,
    )

    class NsdDiscoveryException(val code: String) : Exception(code)

    interface Discoverer {
        suspend fun discoverOnce(): Result
    }

    private class AndroidDiscoverer(private val nsdManager: NsdManager) : Discoverer {
        override suspend fun discoverOnce(): Result = withContext(Dispatchers.Main) {
            suspendCancellableCoroutine { cont ->
                var stopped = false
                var discoveryListener: NsdManager.DiscoveryListener? = null

                fun stopDiscovery() {
                    if (stopped) return
                    stopped = true
                    val l = discoveryListener ?: return
                    try {
                        nsdManager.stopServiceDiscovery(l)
                    } catch (_: Exception) {
                    }
                }

                val resolveListener = object : NsdManager.ResolveListener {
                    override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {}

                    override fun onServiceResolved(resolved: NsdServiceInfo) {
                        val host = resolved.host
                        val ipv4 = (host as? Inet4Address)?.hostAddress
                            ?: host?.hostAddress
                            ?: return
                        val pairingId = resolved.attributes["pairing_id"]?.toString(Charsets.UTF_8) ?: return
                        if (!pairingId.matches(Regex("^[A-Za-z0-9\\-]{1,64}$"))) return
                        stopDiscovery()
                        if (cont.isActive) cont.resume(Result(ipv4, 8089, pairingId))
                    }
                }

                val listener = object : NsdManager.DiscoveryListener {
                    override fun onDiscoveryStarted(serviceType: String) {}

                    override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                        stopDiscovery()
                        if (cont.isActive) cont.resumeWithException(NsdDiscoveryException("NSD_DISCOVERY_FAILED"))
                    }

                    override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {}

                    override fun onDiscoveryStopped(serviceType: String) {}

                    override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                        if (!serviceInfo.serviceType.contains("_companion._tcp")) return
                        nsdManager.resolveService(serviceInfo, resolveListener)
                    }

                    override fun onServiceLost(serviceInfo: NsdServiceInfo) {}
                }

                discoveryListener = listener
                cont.invokeOnCancellation { stopDiscovery() }
                nsdManager.discoverServices("_companion._tcp.", NsdManager.PROTOCOL_DNS_SD, listener)
            }
        }
    }

    suspend fun discoverCompanionService(
        timeoutMs: Long = 5_000,
        retries: Int = 3,
        retryDelayMs: Long = 1_000,
    ): Result {
        var lastError: Exception? = null
        repeat(retries) { attempt ->
            try {
                return withTimeout(timeoutMs) { discoverer.discoverOnce() }
            } catch (e: Exception) {
                lastError = e
                if (attempt != retries - 1) {
                    delay(retryDelayMs)
                }
            }
        }
        throw NsdDiscoveryException("NSD_DISCOVERY_FAILED").apply { initCause(lastError) }
    }
}

