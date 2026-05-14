package com.linkflow.app

import com.linkflow.app.pairing.ManualInputValidator
import com.linkflow.app.pairing.QrCodeParser
import org.junit.Assert.*
import org.junit.Test

class ModuleATest {
    // 1.二维码解析成功
    @Test
    fun parseQr_ok() {
        val d = QrCodeParser.parseQrPayload("p123;k456")
        assertEquals("p123", d.pairingId)
    }

    // 2.二维码格式错误
    @Test(expected = IllegalArgumentException::class)
    fun parseQr_fail() {
        QrCodeParser.parseQrPayload("bad")
    }

    // 3.手输入空
    @Test
    fun input_empty() {
        val r = ManualInputValidator.validateManualInput("", "k")
        assertFalse(r.ok)
    }

    // 4.手输入合法
    @Test
    fun input_ok() {
        val r = ManualInputValidator.validateManualInput("p", "k")
        assertTrue(r.ok)
    }

    // 5.DTO版本
    @Test
    fun dto_version() {
        val dto = com.linkflow.app.util.PairingContextDTO(
            hostIpv4 = "1.1.1.1",
            port=8089,
            pairingId="p",
            keyB64="k",
        )
        assertEquals("1.0.0", dto.schemaVersion)
    }
}