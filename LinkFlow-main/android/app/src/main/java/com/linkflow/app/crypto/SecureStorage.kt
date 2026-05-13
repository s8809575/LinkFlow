package com.linkflow.app.crypto

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.linkflow.app.util.PairingSecretDTO
class SecureStorage(context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "pairing_secure_storage",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    fun save(secret: PairingSecretDTO) {
        prefs.edit()
            .putString("pairing_id", secret.pairingId)
            .putString("key_b64", secret.keyB64)
            .apply()
    }

    fun get(): PairingSecretDTO? {
        val id = prefs.getString("pairing_id", null) ?: return null
        val key = prefs.getString("key_b64", null) ?: return null
        return PairingSecretDTO(id, key)
    }
}
