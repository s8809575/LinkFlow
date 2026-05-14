package com.linkflow.app

import android.content.Context
import com.linkflow.app.crypto.SecureStorage
import com.linkflow.app.nsd.NsdServiceManager
import com.linkflow.app.util.PairingContextDTO
import com.linkflow.app.util.PairingSecretDTO

class ModuleA(context: Context) {
    private val nsd = NsdServiceManager(context)
    private val storage = SecureStorage(context)

    suspend fun getPairingContext(): PairingContextDTO {
        val serviceInfo = nsd.discover()
        val secret = storage.get() ?: throw IllegalStateException("No pairing secret found")
        return serviceInfo.copy(
            pairingId = secret.pairingId,
            keyB64 = secret.keyB64
        )
    }

    fun savePairingSecret(secret: PairingSecretDTO) {
        storage.save(secret)
    }
}
