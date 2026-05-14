package com.linkflow.app.pairing

import android.content.Context
import android.net.nsd.NsdManager
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.linkflow.app.R
import com.linkflow.app.nsd.NsdDiscoveryManager
import com.linkflow.app.prefs.SecurePrefs
import com.linkflow.app.rpc.RpcClient
import com.linkflow.app.tcp.TcpConnectionManager
import com.linkflow.app.util.Notifier
import kotlinx.coroutines.launch
import org.json.JSONObject

class PairingActivity : AppCompatActivity(), Notifier, QRScanFragment.Callback {
    private lateinit var ipView: TextView
    private lateinit var pairingIdEdit: EditText
    private lateinit var keyEdit: EditText
    private lateinit var discoverBtn: Button
    private lateinit var scanBtn: Button
    private lateinit var pairBtn: Button

    private val tcp = TcpConnectionManager()
    private lateinit var rpc: RpcClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_pairing)

        ipView = findViewById(R.id.pc_ip)
        pairingIdEdit = findViewById(R.id.pairing_id)
        keyEdit = findViewById(R.id.key_b64)
        discoverBtn = findViewById(R.id.btn_discover)
        scanBtn = findViewById(R.id.btn_scan)
        pairBtn = findViewById(R.id.btn_pair)

        rpc = RpcClient(tcp, this)

        val prefs = SecurePrefs.get(this)
        ipView.text = prefs.getString("pc_ip", "") ?: ""
        pairingIdEdit.setText(prefs.getString("pairing_id", "") ?: "")
        keyEdit.setText(prefs.getString("key_b64", "") ?: "")
        updatePairEnabled()

        tcp.setGiveUpCallback { runOnUiThread { toast("无法恢复连接") } }

        discoverBtn.setOnClickListener {
            lifecycleScope.launch { discoverPc() }
        }

        scanBtn.setOnClickListener {
            supportFragmentManager.beginTransaction()
                .replace(R.id.scan_container, QRScanFragment())
                .commitAllowingStateLoss()
        }

        pairBtn.setOnClickListener {
            lifecycleScope.launch { doPair() }
        }

        pairingIdEdit.addTextChangedListener(SimpleWatcher { updatePairEnabled() })
        keyEdit.addTextChangedListener(SimpleWatcher { updatePairEnabled() })
    }

    private fun updatePairEnabled() {
        pairBtn.isEnabled = pairingIdEdit.text.isNotBlank() && keyEdit.text.isNotBlank()
    }

    private suspend fun discoverPc() {
        val nsd = getSystemService(Context.NSD_SERVICE) as NsdManager
        val mgr = NsdDiscoveryManager(this, nsd)
        try {
            val res = mgr.discoverCompanionService()
            ipView.text = res.hostIpv4
            pairingIdEdit.setText(res.pairingId)
            SecurePrefs.get(this).edit()
                .putString("pc_ip", res.hostIpv4)
                .putString("pairing_id", res.pairingId)
                .apply()
        } catch (_: Exception) {
            toast("NSD_DISCOVERY_FAILED")
        }
    }

    private suspend fun doPair() {
        val ip = ipView.text.toString().trim()
        val pairingId = pairingIdEdit.text.toString().trim()
        val keyB64 = keyEdit.text.toString().trim()
        if (ip.isEmpty()) {
            toast("NSD_DISCOVERY_FAILED")
            return
        }
        if (!pairingId.matches(Regex("^[A-Za-z0-9\\-]{1,64}$"))) {
            toast("pairing_id 格式错误")
            return
        }
        try {
            val key = android.util.Base64.decode(keyB64, android.util.Base64.DEFAULT)
            if (key.size != 16) {
                toast("key_b64 格式错误")
                return
            }
        } catch (_: Exception) {
            toast("key_b64 格式错误")
            return
        }

        SecurePrefs.get(this).edit()
            .putString("pc_ip", ip)
            .putString("pairing_id", pairingId)
            .putString("key_b64", keyB64)
            .apply()

        var ok = false
        repeat(3) { attempt ->
            try {
                tcp.connectAndPair(ip, 8089, pairingId, keyB64)
                val res = rpc.invoke("system.stats", JSONObject())
                if (res.has("result")) {
                    ok = true
                }
                return@repeat
            } catch (_: Exception) {
                if (attempt == 2) ok = false
            }
        }
        if (!ok) {
            toast("配对失败")
        } else {
            toast("配对成功")
        }
    }

    override fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    override fun onQrParsed(pairingId: String, keyB64: String) {
        pairingIdEdit.setText(pairingId)
        keyEdit.setText(keyB64)
        updatePairEnabled()
        supportFragmentManager.beginTransaction().remove(supportFragmentManager.findFragmentById(R.id.scan_container)!!).commitAllowingStateLoss()
    }
}

