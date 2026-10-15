package com.lagaz.baixadordevideos

import android.content.Context
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/** Atualizações do app: consulta as versões publicadas no GitHub, baixa e instala o APK. */
object Updater {
    private const val REPO = "LagazYT/baixador-de-videos"
    private const val API = "https://api.github.com/repos/$REPO/releases?per_page=30"
    private const val DOWNLOAD_PREFIX = "https://github.com/$REPO/releases/download/"
    const val PAGE = "https://github.com/$REPO/releases"

    @Volatile private var busy = false
    @Volatile var latest: JSONObject? = null
        private set
    @Volatile var readyApk: File? = null
        private set

    fun versionParts(v: String): List<Int> =
        Regex("\\d+").findAll(v).map { it.value.toIntOrNull() ?: 0 }.take(4).toList()

    fun isNewer(remote: String, local: String): Boolean {
        val a = versionParts(remote)
        val b = versionParts(local)
        for (i in 0 until maxOf(a.size, b.size)) {
            val x = a.getOrElse(i) { 0 }
            val y = b.getOrElse(i) { 0 }
            if (x != y) return x > y
        }
        return false
    }

    private fun abiSuffix(): String = when (Build.SUPPORTED_ABIS.firstOrNull() ?: "") {
        "armeabi-v7a" -> "-armv7.apk"
        "x86_64" -> "-x86_64.apk"
        else -> "-arm64.apk"
    }

    private fun httpGet(url: String): String {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 20_000
        c.readTimeout = 30_000
        c.setRequestProperty("User-Agent", "BaixadorDeVideos-Android/${BuildConfig.VERSION_NAME}")
        c.setRequestProperty("Accept", "application/vnd.github+json")
        try {
            if (c.responseCode !in 200..299) throw Exception("GitHub respondeu ${c.responseCode}")
            return c.inputStream.bufferedReader().use { it.readText() }
        } finally {
            c.disconnect()
        }
    }

    /** Procura a versão Android mais recente. Emite "appUpdate". */
    fun check(manual: Boolean) {
        if (busy) return
        busy = true
        Engine.runInBackground {
            try {
                val releases = JSONArray(httpGet(API))
                var found: JSONObject? = null
                for (i in 0 until releases.length()) {
                    val r = releases.optJSONObject(i) ?: continue
                    if (r.optBoolean("draft")) continue
                    if (r.optString("tag_name").startsWith("android-v")) {
                        found = r
                        break
                    }
                }
                if (found == null) throw Exception("Nenhuma versão Android publicada.")
                val version = found.optString("tag_name").removePrefix("android-v")
                val suffix = abiSuffix()
                var asset: JSONObject? = null
                val assets = found.optJSONArray("assets") ?: JSONArray()
                for (i in 0 until assets.length()) {
                    val a = assets.optJSONObject(i) ?: continue
                    if (a.optString("name").endsWith(suffix)) {
                        asset = a
                        break
                    }
                }
                var notes = found.optString("body", "")
                val idx = notes.indexOf("### Como instalar")
                if (idx > 0) notes = notes.substring(0, idx)
                val info = JSONObject()
                    .put("version", version)
                    .put("page", found.optString("html_url", PAGE))
                    .put("notes", notes.replace("## ", "").replace("### ", "").replace("**", "").trim().take(700))
                    .put("url", asset?.optString("browser_download_url", "") ?: "")
                    .put("size", asset?.optLong("size", 0L) ?: 0L)
                    .put("digest", asset?.optString("digest", "") ?: "")
                    .put("current", BuildConfig.VERSION_NAME)
                val newer = isNewer(version, BuildConfig.VERSION_NAME)
                latest = if (newer) info else null
                Engine.emit("appUpdate", JSONObject()
                    .put("state", if (newer) "available" else "latest")
                    .put("manual", manual)
                    .put("info", info))
            } catch (e: Throwable) {
                Engine.emit("appUpdate", JSONObject()
                    .put("state", "error").put("manual", manual)
                    .put("msg", e.message ?: "Sem conexão com a internet."))
            } finally {
                busy = false
            }
        }
    }

    private fun sha256(f: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        f.inputStream().use { input ->
            val buf = ByteArray(1 shl 16)
            while (true) {
                val n = input.read(buf)
                if (n < 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    @Suppress("DEPRECATION")
    private fun signatures(info: PackageInfo?): Set<String> {
        if (info == null) return emptySet()
        val sigs = if (Build.VERSION.SDK_INT >= 28) {
            info.signingInfo?.apkContentsSigners
        } else {
            info.signatures
        } ?: return emptySet()
        return sigs.map { it.toCharsString() }.toSet()
    }

    /** A atualização foi assinada com a mesma chave do app instalado? */
    @Suppress("DEPRECATION")
    private fun sameSigner(ctx: Context, apk: File): Boolean {
        return try {
            val pm = ctx.packageManager
            val flags = if (Build.VERSION.SDK_INT >= 28) PackageManager.GET_SIGNING_CERTIFICATES
            else PackageManager.GET_SIGNATURES
            val installed = signatures(pm.getPackageInfo(ctx.packageName, flags))
            val archive = signatures(pm.getPackageArchiveInfo(apk.absolutePath, flags))
            if (archive.isEmpty()) true else installed == archive
        } catch (e: Exception) {
            true
        }
    }

    /** Baixa o APK novo. Emite "appUpdateProgress" e depois "appUpdateReady" ou "appUpdateError". */
    fun download(ctx: Context) {
        val info = latest ?: return
        if (busy) return
        busy = true
        Engine.runInBackground {
            try {
                val url = info.optString("url")
                if (!url.startsWith(DOWNLOAD_PREFIX)) throw Exception("Esta versão não tem APK para o seu celular.")
                val dir = File(ctx.cacheDir, "updates")
                dir.deleteRecursively()
                dir.mkdirs()
                val dest = File(dir, "BaixadorDeVideos-${info.optString("version")}.apk")
                val c = URL(url).openConnection() as HttpURLConnection
                c.connectTimeout = 20_000
                c.readTimeout = 60_000
                c.instanceFollowRedirects = true
                c.setRequestProperty("User-Agent", "BaixadorDeVideos-Android/${BuildConfig.VERSION_NAME}")
                try {
                    if (c.responseCode !in 200..299) throw Exception("Download respondeu ${c.responseCode}")
                    val total = info.optLong("size", 0L).takeIf { it > 0 } ?: c.contentLengthLong
                    var done = 0L
                    var lastPct = -1
                    c.inputStream.use { input ->
                        dest.outputStream().use { out ->
                            val buf = ByteArray(1 shl 16)
                            while (true) {
                                val n = input.read(buf)
                                if (n < 0) break
                                out.write(buf, 0, n)
                                done += n
                                val pct = if (total > 0) (done * 100 / total).toInt() else -1
                                if (pct != lastPct) {
                                    lastPct = pct
                                    Engine.emit("appUpdateProgress", JSONObject().put("pct", pct))
                                }
                            }
                        }
                    }
                } finally {
                    c.disconnect()
                }
                val size = info.optLong("size", 0L)
                if (size > 0 && dest.length() != size) throw Exception("O download veio incompleto. Tente de novo.")
                val digest = info.optString("digest", "")
                if (digest.startsWith("sha256:") && sha256(dest) != digest.removePrefix("sha256:").lowercase()) {
                    dest.delete()
                    throw Exception("O arquivo baixado não confere com o publicado. Tente de novo.")
                }
                readyApk = dest
                Engine.emit("appUpdateReady", JSONObject()
                    .put("version", info.optString("version"))
                    .put("sameKey", sameSigner(ctx, dest)))
            } catch (e: Throwable) {
                Engine.emit("appUpdateError", JSONObject().put("msg", e.message ?: "Erro ao baixar."))
            } finally {
                busy = false
            }
        }
    }

    fun canInstall(ctx: Context): Boolean =
        Build.VERSION.SDK_INT < 26 || ctx.packageManager.canRequestPackageInstalls()

    fun permissionIntent(ctx: Context): Intent =
        Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + ctx.packageName))

    /** Abre o instalador do Android com o APK baixado. */
    fun installIntent(ctx: Context): Intent? {
        val apk = readyApk ?: return null
        if (!apk.exists()) return null
        val uri = FileProvider.getUriForFile(ctx, ctx.packageName + ".files", apk)
        return Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
    }
}
