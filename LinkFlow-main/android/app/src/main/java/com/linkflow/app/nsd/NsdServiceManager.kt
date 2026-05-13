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

class NsdServiceManager(context: Context) {
    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val SERVICE_TYPE = "_companion._tcp."

    suspend fun discover(): PairingContextDTO {
        repeat(3) {
            try {
                return withTimeout(5000) {
                    startDiscover()
                }
            } catch (e: Exception) {
                if (it == 2) throw IOException("Discovery failed after 3 attempts")
            }
        }
        throw IOException("Discovery failed")
    }

    private suspend fun startDiscover(): PairingContextDTO =
        suspendCancellableCoroutine { cont ->
            val listener = object : NsdManager.DiscoveryListener {
                override fun onServiceFound(info: NsdServiceInfo) {
                    nsdManager.resolveService(info, object : NsdManager.ResolveListener {
                        override fun onServiceResolved(resolved: NsdServiceInfo) {
                            cont.resume(
                                PairingContextDTO(
                                    hostIpv4 = resolved.host.hostAddress ?: "0.0.0.0",
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
