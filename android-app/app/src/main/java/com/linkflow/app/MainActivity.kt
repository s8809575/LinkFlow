package com.linkflow.app

import android.annotation.SuppressLint
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.DocumentsContract
import android.provider.MediaStore
import android.util.Base64
import android.view.View
import android.view.inputmethod.EditorInfo
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.Toast
import androidx.annotation.RequiresApi
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.edit
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    companion object {
        private const val PREFS_NAME = "linkflow_prefs"
        private const val KEY_SERVER_IP = "server_ip"
        private const val KEY_DOWNLOAD_HISTORY = "download_history"
        private const val SERVER_PORT = 8766
        private const val CONNECT_PATH = "/mobile"
        private const val REQUEST_STORAGE_PERMISSION = 100
        private const val FILE_CHOOSER_REQUEST = 200
    }

    private lateinit var webView: WebView
    private val handler = Handler(Looper.getMainLooper())
    private var filePathCallback: ValueCallback<Array<Uri>>? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        setupWebView()

        val savedIP = getSavedIP()
        if (!savedIP.isNullOrBlank()) {
            connectToServer(savedIP)
        } else {
            loadSettingsPage()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val settings: WebSettings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.allowFileAccess = true
        settings.allowContentAccess = true
        settings.setSupportZoom(true)
        settings.builtInZoomControls = true
        settings.displayZoomControls = false
        settings.loadWithOverviewMode = true
        settings.useWideViewPort = true
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        // 注入原生桥接
        webView.addJavascriptInterface(NativeBridge(), "LinkFlowNative")

        webView.webViewClient = object : WebViewClient() {

            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                super.onPageStarted(view, url, favicon)
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                // 每次页面加载完成后注入原生标志位，确保 JS 能可靠检测到桥接存在
                view?.evaluateJavascript(
                    "window.__lf_native__=true;if(window.LinkFlowNative)window.__lf_native__=true;",
                    null
                )
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true) {
                    loadSettingsPage()
                }
            }

            override fun onReceivedError(
                view: WebView?,
                errorCode: Int,
                description: String?,
                failingUrl: String?
            ) {
                super.onReceivedError(view, errorCode, description, failingUrl)
                if (failingUrl == view?.url || view?.url == null) {
                    loadSettingsPage()
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                super.onProgressChanged(view, newProgress)
            }

            // 接管网页权限请求，直接放行 clipboard-read / clipboard-write
            override fun onPermissionRequest(request: PermissionRequest?) {
                request?.grant(request.resources)
            }

            // 处理文件选择器（修复上传按钮无响应问题）
            override fun onShowFileChooser(
                webView: WebView?,
                callback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                filePathCallback?.onReceiveValue(null)
                filePathCallback = callback

                val intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.type = "*/*"
                try {
                    startActivityForResult(
                        Intent.createChooser(intent, "选择文件"),
                        FILE_CHOOSER_REQUEST
                    )
                } catch (e: Exception) {
                    filePathCallback = null
                    Toast.makeText(this@MainActivity, "无法打开文件选择器", Toast.LENGTH_SHORT).show()
                    return false
                }
                return true
            }
        }
    }

    /**
     * 原生桥接类 - 供 JavaScript 调用
     */
    inner class NativeBridge {

        // —— 文件保存 ——

        @JavascriptInterface
        fun saveFile(base64Data: String, fileName: String, mimeType: String) {
            handler.post {
                try {
                    val path = saveFileToDownloads(base64Data, fileName, mimeType)
                    // 通知 JS 下载结果（包含完整路径）
                    webView.post {
                        val escapedPath = path.replace("\\", "\\\\").replace("'", "\\'")
                        webView.evaluateJavascript(
                            "if(window.onFileSaved)window.onFileSaved('$escapedPath','$fileName')",
                            null
                        )
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@MainActivity, "保存失败: ${e.message}", Toast.LENGTH_LONG).show()
                    webView.post {
                        val escapedMsg = e.message?.replace("'", "\\'") ?: "未知错误"
                        webView.evaluateJavascript(
                            "if(window.onFileSaved)window.onFileSaved('','$escapedMsg')",
                            null
                        )
                    }
                }
            }
        }

        @JavascriptInterface
        fun saveImage(base64Data: String, fileName: String, mimeType: String) {
            handler.post {
                try {
                    // 复用已验证可靠的文件保存逻辑
                    val path = saveFileToDownloads(base64Data, fileName, mimeType)
                    val toastMsg = if (path.isNotBlank()) "已保存: $fileName" else "保存失败"
                    Toast.makeText(this@MainActivity, toastMsg, Toast.LENGTH_LONG).show()
                    addDownloadToHistory(fileName, path)
                    webView.post {
                        val escapedPath = path.replace("\\", "\\\\").replace("'", "\\'")
                        webView.evaluateJavascript(
                            "if(window.onImageSaved)window.onImageSaved(true,'$escapedPath','$fileName')",
                            null
                        )
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@MainActivity, "保存失败: ${e.message}", Toast.LENGTH_LONG).show()
                    webView.post {
                        val escapedMsg = e.message?.replace("'", "\\'") ?: "未知错误"
                        webView.evaluateJavascript(
                            "if(window.onImageSaved)window.onImageSaved(false,'','$escapedMsg')",
                            null
                        )
                    }
                }
            }
        }

        @JavascriptInterface
        fun showToast(message: String) {
            handler.post {
                Toast.makeText(this@MainActivity, message, Toast.LENGTH_SHORT).show()
            }
        }

        // —— 剪贴板 ——

        @JavascriptInterface
        fun getClip(): String {
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            if (cm.hasPrimaryClip()) {
                val clip = cm.primaryClip ?: return ""
                for (i in 0 until clip.itemCount) {
                    val item = clip.getItemAt(i)
                    val text = item.coerceToText(this@MainActivity).toString()
                    if (text.isNotBlank()) return text
                }
            }
            return ""
        }

        // —— 服务器连接 / 设置 ——

        @JavascriptInterface
        fun getSavedIP(): String {
            return getSavedIP() ?: ""
        }

        @JavascriptInterface
        fun saveAndConnect(ip: String) {
            handler.post {
                if (ip.isNotBlank()) {
                    saveIP(ip)
                    connectToServer(ip)
                }
            }
        }

        @JavascriptInterface
        fun openSettings() {
            handler.post { loadSettingsPage() }
        }

        // —— 下载管理 ——

        @JavascriptInterface
        fun openDownloadsFolder() {
            handler.post {
                try {
                    val intent = Intent(Intent.ACTION_VIEW).apply {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            setDataAndType(
                                MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                                DocumentsContract.Document.MIME_TYPE_DIR
                            )
                        } else {
                            val downloadsDir = Environment.getExternalStoragePublicDirectory(
                                Environment.DIRECTORY_DOWNLOADS
                            )
                            setDataAndType(Uri.parse(downloadsDir.absolutePath), "resource/folder")
                        }
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    startActivity(Intent.createChooser(intent, "选择文件管理器"))
                } catch (e: Exception) {
                    try {
                        // 降级：只打开 Downloads content URI
                        val fallbackIntent = Intent(Intent.ACTION_VIEW).apply {
                            setDataAndType(
                                MediaStore.Downloads.EXTERNAL_CONTENT_URI, "*/*"
                            )
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                        startActivity(fallbackIntent)
                    } catch (e2: Exception) {
                        Toast.makeText(this@MainActivity, "未找到文件管理器", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }

        @JavascriptInterface
        fun getDownloadHistory(): String {
            val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return prefs.getString(KEY_DOWNLOAD_HISTORY, "[]") ?: "[]"
        }

        @JavascriptInterface
        fun clearDownloadHistory() {
            getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit {
                putString(KEY_DOWNLOAD_HISTORY, "[]")
            }
        }
    }

    // ───────────── 文件保存核心逻辑 ─────────────

    /** 获取当前日期的下载子目录名: LFDownload_YYYYMMDD */
    private fun getDownloadSubfolder(): String {
        val dateStr = SimpleDateFormat("yyyyMMdd", Locale.getDefault()).format(Date())
        return "LFDownload_$dateStr"
    }

    /**
     * 保存文件到下载目录，返回保存路径
     */
    private fun saveFileToDownloads(base64Data: String, fileName: String, mimeType: String): String {
        return try {
            val data = Base64.decode(base64Data, Base64.DEFAULT)
            val path = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                saveUsingMediaStore(data, fileName, mimeType)
            } else {
                saveDirectToDownloads(data, fileName)
            }
            addDownloadToHistory(fileName, path)
            Toast.makeText(this, "已保存: $fileName", Toast.LENGTH_LONG).show()
            path
        } catch (e: Exception) {
            Toast.makeText(this, "保存失败: ${e.message}", Toast.LENGTH_LONG).show()
            ""
        }
    }

    @RequiresApi(Build.VERSION_CODES.Q)
    private fun saveUsingMediaStore(data: ByteArray, fileName: String, mimeType: String): String {
        val subfolder = getDownloadSubfolder()
        val relativePath = "${Environment.DIRECTORY_DOWNLOADS}/$subfolder"

        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, fileName)
            put(MediaStore.Downloads.MIME_TYPE, mimeType)
            put(MediaStore.Downloads.IS_PENDING, 1)
            put(MediaStore.Downloads.RELATIVE_PATH, relativePath)
        }

        val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: throw Exception("无法创建文件")

        contentResolver.openOutputStream(uri)?.use { stream ->
            stream.write(data)
        }

        values.clear()
        values.put(MediaStore.Downloads.IS_PENDING, 0)
        contentResolver.update(uri, values, null, null)

        return "${Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)}/$subfolder/$fileName"
    }

    private fun saveDirectToDownloads(data: ByteArray, fileName: String): String {
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.WRITE_EXTERNAL_STORAGE)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(android.Manifest.permission.WRITE_EXTERNAL_STORAGE),
                REQUEST_STORAGE_PERMISSION
            )
            throw Exception("请授予存储权限后重新下载")
        }

        val subfolder = getDownloadSubfolder()
        val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        val targetDir = File(downloadsDir, subfolder)
        if (!targetDir.exists()) targetDir.mkdirs()

        val file = File(targetDir, fileName)
        FileOutputStream(file).use { stream ->
            stream.write(data)
        }

        return file.absolutePath
    }

    /**
     * 保存图片到相册 (Pictures/LinkFlow/)，返回保存路径
     */
    private fun saveImageToGallery(base64Data: String, fileName: String, mimeType: String): String {
        val data = Base64.decode(base64Data, Base64.DEFAULT)

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                put(MediaStore.Images.Media.MIME_TYPE, mimeType)
                put(MediaStore.Images.Media.IS_PENDING, 1)
                put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/LinkFlow")
            }

            val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                ?: throw Exception("无法创建图片文件")

            contentResolver.openOutputStream(uri)?.use { stream ->
                stream.write(data)
            }

            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            contentResolver.update(uri, values, null, null)

            val picDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES)
            "${picDir.absolutePath}/LinkFlow/$fileName"
        } else {
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.WRITE_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(android.Manifest.permission.WRITE_EXTERNAL_STORAGE),
                    REQUEST_STORAGE_PERMISSION
                )
                throw Exception("请授予存储权限后重新保存")
            }

            val picDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES)
            val targetDir = File(picDir, "LinkFlow")
            if (!targetDir.exists()) targetDir.mkdirs()

            val file = File(targetDir, fileName)
            FileOutputStream(file).use { stream ->
                stream.write(data)
            }
            file.absolutePath
        }
    }

    // ───────────── 下载历史 ─────────────

    private fun addDownloadToHistory(fileName: String, path: String) {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val jsonStr = prefs.getString(KEY_DOWNLOAD_HISTORY, "[]") ?: "[]"
        val arr = try { JSONArray(jsonStr) } catch (e: Exception) { JSONArray() }

        val entry = JSONObject().apply {
            put("fileName", fileName)
            put("path", path)
            put("timestamp", System.currentTimeMillis())
        }
        arr.put(entry)

        // 限制最多保存 50 条
        while (arr.length() > 50) arr.remove(0)

        prefs.edit { putString(KEY_DOWNLOAD_HISTORY, arr.toString()) }
    }

    // ───────────── 权限回调 ─────────────

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_STORAGE_PERMISSION) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "权限已授予，请重新下载", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ───────────── 文件选择器回调 ─────────────

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == FILE_CHOOSER_REQUEST) {
            if (filePathCallback == null) return
            val results = if (resultCode == RESULT_OK && data?.data != null) {
                arrayOf(data.data!!)
            } else {
                null
            }
            filePathCallback?.onReceiveValue(results)
            filePathCallback = null
        }
    }

    // ───────────── IP 设置 / 连接 ─────────────

    private fun loadSettingsPage() {
        webView.visibility = View.VISIBLE
        webView.loadUrl("file:///android_asset/setup.html")
    }

    private fun showIPDialog() {
        val input = EditText(this).apply {
            hint = "输入电脑 IP 地址"
            setText(getSavedIP() ?: "")
            setSingleLine()
            setPadding(48, 32, 48, 32)
            imeOptions = EditorInfo.IME_ACTION_DONE
        }

        val dialog = AlertDialog.Builder(this)
            .setTitle("连接电脑")
            .setMessage("请输入电脑的 IP 地址")
            .setView(input)
            .setCancelable(true)
            .setPositiveButton("连接") { _, _ ->
                val ip = input.text.toString().trim()
                if (ip.isNotBlank()) {
                    saveIP(ip)
                    connectToServer(ip)
                }
            }
            .setNegativeButton("取消", null)
            .create()

        input.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                val ip = input.text.toString().trim()
                if (ip.isNotBlank()) {
                    saveIP(ip)
                    connectToServer(ip)
                    dialog.dismiss()
                }
                true
            } else {
                false
            }
        }

        dialog.show()
    }

    private fun connectToServer(ip: String) {
        val url = "http://$ip:$SERVER_PORT$CONNECT_PATH"

        Thread {
            val reachable = isServerReachable(ip, SERVER_PORT)
            handler.post {
                if (reachable) {
                    webView.visibility = View.VISIBLE
                    webView.loadUrl(url)
                } else {
                    // 连接失败，如果不是 setup 页面则回退到设置页
                    if (!webView.url.orEmpty().contains("setup.html")) {
                        loadSettingsPage()
                    }
                    // 通知 setup 页面连接结果
                    webView.evaluateJavascript(
                        "if(window.onConnectionResult)window.onConnectionResult(false,'服务器不可达')",
                        null
                    )
                }
            }
        }.start()
    }

    private fun isServerReachable(ip: String, port: Int): Boolean {
        return try {
            val url = URL("http://$ip:$port$CONNECT_PATH")
            val conn = url.openConnection() as HttpURLConnection
            conn.connectTimeout = 3000
            conn.readTimeout = 3000
            conn.requestMethod = "HEAD"
            conn.responseCode
            conn.disconnect()
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun getSavedIP(): String? {
        return getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_SERVER_IP, null)
    }

    private fun saveIP(ip: String) {
        getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit {
            putString(KEY_SERVER_IP, ip)
        }
    }

    // ───────────── 生命周期 ─────────────

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        if (::webView.isInitialized) {
            webView.destroy()
        }
        super.onDestroy()
    }
}
