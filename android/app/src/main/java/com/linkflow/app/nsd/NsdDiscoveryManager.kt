package com.linkflow.app.nsd

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import com.linkflow.app.util.PairingContextDTO
import kotlinx.coroutines.delay
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeout
import java.net.Inet4Address
import java.nio.charset.StandardCharsets
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

// ✅ Spec 要求的异常名
class NsdDiscoveryFailedException(msg: String) : Exception(msg)

class NsdDiscoveryManager(context: Context) {
    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val SERVICE_TYPE = "_companion._tcp."

    // ✅ Spec 要求必须存在的函数签名
    suspend fun discoverCompanionService(
        timeoutMs: Long = 5000,
        retries: Int = 3,
        retryDelayMs: Long = 1000
    ): PairingContextDTO {
        var lastError: Exception? = null
        repeat(retries) { attempt ->
            try {
                return withTimeout(timeoutMs) { performDiscovery() }
            } catch (e: Exception) {
                lastError = e
                if (attempt < retries - 1) delay(retryDelayMs)
            }
        }
        throw NsdDiscoveryFailedException("NSD_DISCOVERY_FAILED")
    }

    // ✅ 保留你原有的核心发现逻辑
    private suspend fun performDiscovery(): PairingContextDTO = suspendCancellableCoroutine { cont ->
        val listener = object : NsdManager.DiscoveryListener {
            override fun onServiceFound(info: NsdServiceInfo) {
                nsdManager.resolveService(info, object : NsdManager.ResolveListener {
                    override fun onServiceResolved(resolved: NsdServiceInfo) {
                        val host = resolved.host
                        val ipv4 = (host as? Inet4Address)?.hostAddress ?: "0.0.0.0"

                        // 修复之前的 Type inference 报错
                        val pIdBytes = resolved.attributes["pairing_id"]
                        val pId = pIdBytes?.let { String(it, StandardCharsets.UTF_8) }
                            ?: resolved.serviceName

                        if (cont.isActive) {
                            cont.resume(
                                PairingContextDTO(
                                    hostIpv4 = ipv4,
                                    port = resolved.port,
                                    pairingId = pId,
                                    keyB64 = "" // Spec 要求，初始为空
                                )
                            )
                        }
                    }
                    override fun onResolveFailed(info: NsdServiceInfo, code: Int) {}
                })
            }
            override fun onStartDiscoveryFailed(type: String, code: Int) {
                if (cont.isActive) cont.resumeWithException(Exception("Start Failed"))
            }
            override fun onDiscoveryStarted(type: String) {}
            override fun onDiscoveryStopped(type: String) {}
            override fun onServiceLost(info: NsdServiceInfo) {}
            override fun onStopDiscoveryFailed(type: String, code: Int) {}
        }

        nsdManager.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, listener)
        cont.invokeOnCancellation {
            try { nsdManager.stopServiceDiscovery(listener) } catch (_: Exception) {}
        }
    }
}

