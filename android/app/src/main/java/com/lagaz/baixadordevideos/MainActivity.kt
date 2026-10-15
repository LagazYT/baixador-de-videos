package com.lagaz.baixadordevideos

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.DownloadManager
import android.content.ActivityNotFoundException
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.ActivityInfo
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.view.WindowInsetsController
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import org.json.JSONObject

class MainActivity : Activity() {

    companion object {
        @Volatile var visible = false
        private const val REQ_COOKIES = 7
        private const val REQ_STORAGE = 8
        private const val REQ_NOTIFY = 9
        private val URL_RE = Regex("https?://[^\\s\"'<>]+")
    }

    private lateinit var web: WebView
    private var fullView: View? = null
    private var fullCallback: WebChromeClient.CustomViewCallback? = null
    private var pageReady = false
    private var pendingShared: String? = null
    private var pendingDownload: String? = null
    private var pendingInstall = false

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Engine.start(this)

        web = WebView(this)
        web.setBackgroundColor(Color.parseColor("#0f1115"))
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.mediaPlaybackRequiresUserGesture = true
        web.settings.textZoom = 100
        web.isVerticalScrollBarEnabled = false
        web.addJavascriptInterface(Bridge(), "Native")
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowCustomView(view: View?, callback: CustomViewCallback?) {
                if (view == null) return
                if (fullView != null) {
                    callback?.onCustomViewHidden()
                    return
                }
                fullView = view
                fullCallback = callback
                (window.decorView as ViewGroup).addView(view, FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
                view.setBackgroundColor(Color.BLACK)
                web.visibility = View.GONE
                setFullscreenUi(true)
                requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
            }

            override fun onHideCustomView() {
                exitFullscreen()
            }
        }
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val u = request?.url?.toString() ?: return true
                if (u.startsWith("file:///android_asset/")) return false
                openExternal(u)
                return true
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                pageReady = true
            }
        }
        setContentView(web)

        Engine.listener = { type, data -> runOnUiThread { send(type, data) } }
        web.loadUrl("file:///android_asset/web/index.html")
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent != null) {
            setIntent(intent)
            handleIntent(intent)
        }
    }

    override fun onResume() {
        super.onResume()
        visible = true
        // voltou da tela de permissão "instalar apps desconhecidos": continua a instalação
        if (pendingInstall && Updater.canInstall(this)) {
            pendingInstall = false
            launchInstaller()
        }
    }

    private fun launchInstaller() {
        val intent = Updater.installIntent(this)
        if (intent == null) {
            send("appUpdateError", JSONObject().put("msg", "O arquivo da atualização não foi encontrado. Baixe de novo."))
            return
        }
        try {
            startActivity(intent)
        } catch (e: Exception) {
            send("appUpdateError", JSONObject().put("msg", "Não foi possível abrir o instalador do Android."))
        }
    }

    override fun onPause() {
        visible = false
        super.onPause()
    }

    override fun onDestroy() {
        Engine.listener = null
        web.destroy()
        super.onDestroy()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus && pageReady) send("focus", JSONObject())
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        send("systemDark", JSONObject().put("dark", isSystemDark()))
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (fullView != null) {
            exitFullscreen()
            return
        }
        if (!pageReady) {
            @Suppress("DEPRECATION")
            super.onBackPressed()
            return
        }
        web.evaluateJavascript("(window.App && App.onBack) ? App.onBack() : false") { r ->
            if (r != "true") moveTaskToBack(true)
        }
    }

    @Suppress("DEPRECATION")
    private fun setFullscreenUi(on: Boolean) {
        window.decorView.systemUiVisibility = if (on) {
            View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        } else {
            0
        }
    }

    private fun exitFullscreen() {
        val v = fullView ?: return
        (window.decorView as ViewGroup).removeView(v)
        fullView = null
        web.visibility = View.VISIBLE
        setFullscreenUi(false)
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        try {
            fullCallback?.onCustomViewHidden()
        } catch (e: Exception) {
        }
        fullCallback = null
        send("restoreBars", JSONObject())
    }

    private fun isSystemDark(): Boolean =
        (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES

    private fun send(type: String, data: JSONObject) {
        if (!this::web.isInitialized) return
        val payload = data.toString().replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        web.evaluateJavascript("window.App && App.onEvent(${JSONObject.quote(type)}, $payload)", null)
    }

    private fun handleIntent(intent: Intent?) {
        if (intent == null) return
        val text = when (intent.action) {
            Intent.ACTION_SEND -> intent.getStringExtra(Intent.EXTRA_TEXT) ?: ""
            Intent.ACTION_VIEW -> intent.dataString ?: ""
            else -> ""
        }
        val url = URL_RE.find(text)?.value?.trimEnd('.', ',', ')', ']') ?: return
        if (pageReady) send("shared", JSONObject().put("url", url)) else pendingShared = url
    }

    private fun openExternal(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (e: ActivityNotFoundException) {
            toast("Nenhum aplicativo para abrir este link.")
        }
    }

    private fun toast(msg: String) {
        runOnUiThread { Toast.makeText(this, msg, Toast.LENGTH_LONG).show() }
    }

    // ---------- permissões ----------
    private fun needsStoragePermission(): Boolean =
        Build.VERSION.SDK_INT < 29 &&
            checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED

    private fun askNotificationPermissionOnce() {
        if (Build.VERSION.SDK_INT < 33) return
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) return
        if (Store.prefs.getBoolean("askedNotify", false)) return
        Store.prefs.edit().putBoolean("askedNotify", true).apply()
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIFY)
    }

    private fun startDownload(json: String) {
        val err = Engine.download(JSONObject(json))
        if (err != null) send("error", JSONObject().put("msg", err).put("code", "busy"))
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_STORAGE) {
            val json = pendingDownload
            pendingDownload = null
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED && json != null) {
                startDownload(json)
            } else {
                send("error", JSONObject()
                    .put("msg", "Sem permissão para salvar na pasta Downloads. Permita o acesso aos arquivos e tente de novo.")
                    .put("code", "permission"))
            }
        }
    }

    // ---------- cookies.txt ----------
    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        @Suppress("DEPRECATION")
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_COOKIES || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        Engine.runInBackground {
            val result = JSONObject()
            try {
                val text = contentResolver.openInputStream(uri)?.use { it.readBytes() }
                    ?.toString(Charsets.UTF_8) ?: throw Exception("Não foi possível ler o arquivo.")
                if (text.length > 3_000_000) throw Exception("Arquivo grande demais para ser um cookies.txt.")
                val valid = text.lines().count { l ->
                    l.isNotBlank() && (!l.startsWith("#") || l.startsWith("#HttpOnly_")) && l.split("\t").size >= 7
                }
                if (valid == 0) throw Exception(
                    "Esse arquivo não parece um cookies.txt (formato Netscape). " +
                        "Exporte de novo com a extensão \"Get cookies.txt LOCALLY\"."
                )
                val content = if (text.trimStart().startsWith("#")) text else "# Netscape HTTP Cookie File\n$text"
                Store.cookieFile.writeText(content)
                result.put("ok", true).put("loaded", true).put("msg", "cookies.txt carregado ($valid cookies).")
            } catch (e: Exception) {
                result.put("ok", false).put("loaded", Store.cookieFile.exists())
                    .put("msg", e.message ?: "Erro ao ler o arquivo.")
            }
            runOnUiThread { send("cookies", result) }
        }
    }

    // ---------- ponte com a interface (JavaScript) ----------
    inner class Bridge {

        @JavascriptInterface
        fun getState(): String {
            val shared = pendingShared
            pendingShared = null
            val s = JSONObject()
                .put("settings", Store.settings())
                .put("systemDark", isSystemDark())
                .put("version", BuildConfig.VERSION_NAME)
                .put("ytdlp", if (Engine.setupState == "done") Engine.ytdlpVersion() else "")
                .put("setup", JSONObject().put("state", Engine.setupState).put("text", Engine.setupText))
                .put("cookies", Store.cookieFile.exists())
                .put("folder", "Download/" + MediaSaver.FOLDER)
            Engine.job?.let { s.put("job", it.toJson()) }
            if (shared != null) s.put("shared", shared)
            return s.toString()
        }

        @JavascriptInterface
        fun analyze(reqId: String, url: String) = Engine.analyze(reqId, url.trim())

        @JavascriptInterface
        fun search(reqId: String, query: String, source: String) = Engine.search(reqId, query.trim(), source)

        @JavascriptInterface
        fun download(json: String) {
            runOnUiThread {
                askNotificationPermissionOnce()
                if (needsStoragePermission()) {
                    pendingDownload = json
                    requestPermissions(arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE), REQ_STORAGE)
                } else {
                    startDownload(json)
                }
            }
        }

        @JavascriptInterface
        fun cancel() = Engine.cancel()

        @JavascriptInterface
        fun saveSettings(json: String) {
            try {
                Store.saveSettings(json)
            } catch (e: Exception) {
            }
        }

        @JavascriptInterface
        fun getHistory() {
            Engine.historyWithStatus { list ->
                runOnUiThread { send("history", JSONObject().put("items", list)) }
            }
        }

        @JavascriptInterface
        fun removeHistory(id: String) = Store.removeHistory(id)

        @JavascriptInterface
        fun clearHistory() = Store.clearHistory()

        @JavascriptInterface
        fun openFile(uri: String, mime: String) {
            runOnUiThread {
                try {
                    val i = Intent(Intent.ACTION_VIEW)
                        .setDataAndType(Uri.parse(uri), mime.ifEmpty { "*/*" })
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
                    startActivity(Intent.createChooser(i, "Abrir com"))
                } catch (e: Exception) {
                    toast("Não foi possível abrir o arquivo. Ele pode ter sido movido ou apagado.")
                }
            }
        }

        @JavascriptInterface
        fun shareFile(uri: String, mime: String) {
            runOnUiThread {
                try {
                    val i = Intent(Intent.ACTION_SEND)
                        .setType(mime.ifEmpty { "*/*" })
                        .putExtra(Intent.EXTRA_STREAM, Uri.parse(uri))
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    startActivity(Intent.createChooser(i, "Compartilhar vídeo"))
                } catch (e: Exception) {
                    toast("Não foi possível compartilhar o arquivo.")
                }
            }
        }

        @JavascriptInterface
        fun mediaUrl(uri: String, mime: String): String = try {
            MediaServer.urlFor(this@MainActivity, uri, mime)
        } catch (e: Exception) {
            ""
        }

        @JavascriptInterface
        fun keepScreenOn(on: Boolean) {
            runOnUiThread {
                if (on) window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                else window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            }
        }

        @JavascriptInterface
        fun checkAppUpdate(manual: Boolean) = Updater.check(manual)

        @JavascriptInterface
        fun downloadAppUpdate() = Updater.download(this@MainActivity)

        @JavascriptInterface
        fun installAppUpdate() {
            runOnUiThread {
                if (!Updater.canInstall(this@MainActivity)) {
                    pendingInstall = true
                    send("appInstallPermission", JSONObject())
                    try {
                        startActivity(Updater.permissionIntent(this@MainActivity))
                    } catch (e: Exception) {
                        pendingInstall = false
                        toast("Permita \"Instalar apps desconhecidos\" para o Baixador de Vídeos nas configurações do Android.")
                    }
                } else {
                    launchInstaller()
                }
            }
        }

        @JavascriptInterface
        fun openDownloads() {
            runOnUiThread {
                try {
                    startActivity(Intent(DownloadManager.ACTION_VIEW_DOWNLOADS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                } catch (e: Exception) {
                    toast("Abra o app Arquivos e procure a pasta Download/${MediaSaver.FOLDER}.")
                }
            }
        }

        @JavascriptInterface
        fun openUrl(url: String) {
            if (url.startsWith("http")) runOnUiThread { openExternal(url) }
        }

        @JavascriptInterface
        fun pickCookies() {
            runOnUiThread {
                val i = Intent(Intent.ACTION_OPEN_DOCUMENT)
                    .addCategory(Intent.CATEGORY_OPENABLE)
                    .setType("*/*")
                try {
                    @Suppress("DEPRECATION")
                    startActivityForResult(i, REQ_COOKIES)
                } catch (e: Exception) {
                    toast("Não foi possível abrir o seletor de arquivos.")
                }
            }
        }

        @JavascriptInterface
        fun clearCookies() {
            Store.cookieFile.delete()
        }

        @JavascriptInterface
        fun updateYtdlp() = Engine.updateNow()

        @JavascriptInterface
        fun readClipboard(): String = try {
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = cm.primaryClip
            if (clip != null && clip.itemCount > 0) clip.getItemAt(0).coerceToText(this@MainActivity).toString() else ""
        } catch (e: Exception) {
            ""
        }

        @Suppress("DEPRECATION")
        @JavascriptInterface
        fun setBars(color: String, lightIcons: Boolean) {
            runOnUiThread {
                try {
                    val c = Color.parseColor(color)
                    window.statusBarColor = c
                    window.navigationBarColor = c
                    window.decorView.setBackgroundColor(c)
                    web.setBackgroundColor(c)
                    if (Build.VERSION.SDK_INT >= 30) {
                        val mask = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or
                            WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS
                        window.insetsController?.setSystemBarsAppearance(if (lightIcons) mask else 0, mask)
                    } else {
                        var flags = window.decorView.systemUiVisibility
                        flags = if (lightIcons) flags or View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
                        else flags and View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR.inv()
                        if (Build.VERSION.SDK_INT >= 26) {
                            flags = if (lightIcons) flags or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
                            else flags and View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR.inv()
                        }
                        window.decorView.systemUiVisibility = flags
                    }
                } catch (e: Exception) {
                }
            }
        }

        @JavascriptInterface
        fun toast(msg: String) = this@MainActivity.toast(msg)
    }
}
