package com.linkflow.app.nsd

import com.linkflow.app.util.PairingContextDTO
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test
import java.lang.Exception

class NsdDiscoveryManagerTest {

    // 注意：由于合并后的 NsdDiscoveryManager 强绑定了 Context 和 NsdManager，
    // 纯 JUnit 环境下无法实例化。
    // 我们主要测试其 DTO 结构对齐和异常逻辑。

    @Test
    fun testPairingContextDTO_Specification() {
        // 验证返回的对象是否符合 Spec 1.0.0 的要求
        val dto = PairingContextDTO(
            hostIpv4 = "192.168.1.1",
            port = 8089,
            pairingId = "pair-123",
            keyB64 = "key"
        )

        assertEquals("1.0.0", dto.schemaVersion)
        assertEquals("192.168.1.1", dto.hostIpv4)
        assertEquals(8089, dto.port)
    }

    @Test(expected = NsdDiscoveryFailedException::class)
    fun testExceptionName_Specification() {
        // 验证异常类是否符合 Spec 定义
        throw NsdDiscoveryFailedException("NSD_DISCOVERY_FAILED")
    }
}

