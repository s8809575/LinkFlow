package com.linkflow.app

import android.content.Context
import com.linkflow.app.crypto.SecureStorage
import com.linkflow.app.nsd.NsdDiscoveryManager
import com.linkflow.app.util.PairingContextDTO
import com.linkflow.app.util.PairingSecretDTO

class ModuleA(context: Context) {
    private val nsd = NsdDiscoveryManager(context)
    private val storage = SecureStorage(context)

    suspend fun getPairingContext(): PairingContextDTO {
        val result = nsd.discoverCompanionService()
        val secret = storage.get() ?: throw IllegalStateException("No secret")
        return PairingContextDTO(
            hostIpv4 = result.hostIpv4,
            port = result.port,
            pairingId = secret.pairingId,
            keyB64 = secret.keyB64
        )
    }

    fun savePairingSecret(secret: PairingSecretDTO) {
        storage.persistPairingSecret(secret.pairingId, secret.keyB64)
    }
}