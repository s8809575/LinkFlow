package com.linkflow.app.nsd

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import com.linkflow.app.util.PairingContextDTO
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.suspendCancellableCoroutine
import java.io.IOException
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

// spec异常
class NsdDiscoveryFailedException(msg: String) : Exception(msg)

class NsdServiceManager(context: Context) {
    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val SERVICE_TYPE = "_companion._tcp."

    // ✅ spec签名
    suspend fun discoverCompanionService(
        timeoutMs: Long = 5000,
        retries: Int = 3,
        retryDelayMs: Long = 1000
    ): PairingContextDTO {
        repeat(retries) {
            try {
                return withTimeout(timeoutMs) { discover() }
            } catch (e: Exception) {
                if (it == retries - 1) throw NsdDiscoveryFailedException("NSD_DISCOVERY_FAILED")
            }
        }
        throw NsdDiscoveryFailedException("NSD_DISCOVERY_FAILED")
    }

    private suspend fun discover(): PairingContextDTO = suspendCancellableCoroutine { cont ->
        val listener = object : NsdManager.DiscoveryListener {
            override fun onServiceFound(info: NsdServiceInfo) {
                nsdManager.resolveService(info, object : NsdManager.ResolveListener {
                    override fun onServiceResolved(resolved: NsdServiceInfo) {
                        cont.resume(
                            PairingContextDTO(
                                hostIpv4 = resolved.host?.hostAddress ?: "0.0.0.0",
                                port = resolved.port,
                                pairingId = resolved.serviceName,
                                keyB64 = ""
                            )
                        )
                    }
                    override fun onResolveFailed(info: NsdServiceInfo, code: Int) {
                        cont.resumeWithException(IOException("Resolve failed"))
                    }
                })
            }
            override fun onStartDiscoveryFailed(type: String, code: Int) {}
            override fun onStopDiscoveryFailed(type: String, code: Int) {}
            override fun onDiscoveryStopped(type: String) {}
            override fun onServiceLost(info: NsdServiceInfo) {}
            override fun onDiscoveryStarted(type: String) {}
        }
        nsdManager.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, listener)
        cont.invokeOnCancellation { nsdManager.stopServiceDiscovery(listener) }
    }
}
