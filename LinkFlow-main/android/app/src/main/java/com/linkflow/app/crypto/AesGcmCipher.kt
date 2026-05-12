package com.linkflow.app.crypto

import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

class AesGcmCipher(key: ByteArray) {
    private val keySpec = SecretKeySpec(key, "AES")
    private val rng = SecureRandom()

    fun encrypt(plaintext: ByteArray, aad: ByteArray? = null): ByteArray {
        val nonce = ByteArray(12)
        rng.nextBytes(nonce)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, keySpec, GCMParameterSpec(128, nonce))
        if (aad != null) cipher.updateAAD(aad)
        val ct = cipher.doFinal(plaintext)
        return nonce + ct
    }

    fun decrypt(packet: ByteArray, aad: ByteArray? = null): ByteArray {
        require(packet.size >= 13)
        val nonce = packet.copyOfRange(0, 12)
        val ct = packet.copyOfRange(12, packet.size)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, keySpec, GCMParameterSpec(128, nonce))
        if (aad != null) cipher.updateAAD(aad)
        return cipher.doFinal(ct)
    }
}

