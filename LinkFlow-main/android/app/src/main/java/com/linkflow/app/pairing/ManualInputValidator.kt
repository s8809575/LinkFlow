package com.linkflow.app.pairing

data class ValidationResult(val ok: Boolean, val msg: String = "")

object ManualInputValidator {
    // ✅ spec签名
    fun validateManualInput(pairingId: String, keyB64: String): ValidationResult {
        if (pairingId.isBlank()) return ValidationResult(false, "pairing_id 不能为空")
        if (keyB64.isBlank()) return ValidationResult(false, "key_b64 不能为空")
        return ValidationResult(true)
    }
}
