package com.lagaz.baixadordevideos

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Build
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Motor do aplicativo: análise de links, pesquisa e downloads usando o yt-dlp
 * (com Python, FFmpeg e QuickJS embutidos pela biblioteca youtubedl-android).
 */
object Engine {
    private const val DAY_MS = 24L * 60 * 60 * 1000
    private val ANSI = Regex("(?:\\u001B)?\\[[0-9;]*m")

    lateinit var app: Context
        private set

    /** Quem recebe os eventos (a tela). Pode ser nulo quando a tela está fechada. */
    @Volatile var listener: ((String, JSONObject) -> Unit)? = null

    private val bg = Executors.newCachedThreadPool()
    private val dlExec = Executors.newSingleThreadExecutor()
    private val ready = CountDownLatch(1)
    @Volatile private var initError: String? = null
    @Volatile var setupState = "running"
        private set
    @Volatile var setupText = "Preparando o motor de download..."
        private set
    @Volatile private var updating = false

    @Volatile var job: Job? = null
        private set

    /** Trecho do vídeo (em segundos). */
    class Section(val start: Double, val end: Double, val exact: Boolean) {
        fun toJson(): JSONObject = JSONObject().put("start", start).put("end", end).put("exact", exact)
    }

    class Job(
        val id: String,
        val url: String,
        val quality: String,
        val title: String,
        val uploader: String,
        val duration: String,
        val thumb: String,
        val mode: String = "off",       // H.264: off | h264 | recode | pref
        val height: Int = 0,
        val subCode: String = "",
        val subAuto: Boolean = false,
        val subLabel: String = "",
        val section: Section? = null,
    ) {
        @Volatile var status = "starting"
        @Volatile var pct = 0f
        @Volatile var text = "Iniciando..."
        @Volatile var cancel = false
        @Volatile var lastEmit = 0L
        @Volatile var lastNotify = 0L

        val active: Boolean get() = status == "starting" || status == "downloading" ||
            status == "processing" || status == "saving"

        fun toJson(): JSONObject = JSONObject()
            .put("id", id).put("url", url).put("quality", quality).put("title", title)
            .put("status", status).put("pct", pct.toDouble()).put("text", text)
            .put("active", active)
    }

    fun isStarted(): Boolean = this::app.isInitialized

    fun start(ctx: Context) {
        if (isStarted()) return
        app = ctx.applicationContext
        Store.init(app)
        Notifier.ensureChannels(app)
        bg.execute { setup() }
    }

    fun emit(type: String, data: JSONObject = JSONObject()) {
        try {
            listener?.invoke(type, data)
        } catch (e: Exception) {
            // tela fechada
        }
    }

    // ---------- preparação ----------
    private fun setSetup(state: String, text: String) {
        setupState = state
        setupText = text
        emit("setup", JSONObject().put("state", state).put("text", text))
    }

    private fun setup() {
        try {
            setSetup("running", "Preparando o motor de download (só demora na primeira vez)...")
            YoutubeDL.getInstance().init(app)
            FFmpeg.getInstance().init(app)
        } catch (e: Throwable) {
            initError = e.message ?: e.toString()
            setSetup("error", "Não foi possível preparar o motor de download: $initError")
            ready.countDown()
            return
        }
        val last = Store.prefs.getLong("lastUpdate", 0L)
        if (Store.setting("autoUpdate", true) && System.currentTimeMillis() - last > DAY_MS) {
            setSetup("running", "Atualizando o yt-dlp para a versão mais recente...")
            doUpdate()
        }
        setSetup("done", "")
        ready.countDown()
    }

    private fun waitReady() {
        if (!ready.await(240, TimeUnit.SECONDS)) throw Exception("O motor de download ainda está sendo preparado. Tente de novo em instantes.")
        initError?.let { throw Exception("O motor de download não pôde ser preparado: $it") }
    }

    fun ytdlpVersion(): String = try {
        YoutubeDL.getInstance().version(app) ?: ""
    } catch (e: Throwable) {
        ""
    }

    private fun doUpdate(): String {
        return try {
            val status = YoutubeDL.getInstance().updateYoutubeDL(app)
            Store.prefs.edit().putLong("lastUpdate", System.currentTimeMillis()).apply()
            if (status?.name == "ALREADY_UP_TO_DATE") "O yt-dlp já está na versão mais recente."
            else "yt-dlp atualizado!"
        } catch (e: Throwable) {
            "Não foi possível atualizar agora: " + shortMsg(e.message ?: e.toString())
        }
    }

    fun updateNow() {
        if (updating) return
        updating = true
        emit("update", JSONObject().put("state", "running").put("text", "Atualizando o yt-dlp..."))
        bg.execute {
            try {
                waitReady()
                val msg = doUpdate()
                emit("update", JSONObject().put("state", "done").put("text", msg).put("version", ytdlpVersion()))
            } catch (e: Exception) {
                emit("update", JSONObject().put("state", "error").put("text", e.message ?: "Erro"))
            } finally {
                updating = false
            }
        }
    }

    // ---------- utilidades ----------
    fun cleanMsg(raw: String?): String {
        val text = ANSI.replace(raw ?: "", "").trim()
        val lines = text.lines().map { it.trim() }.filter { it.isNotEmpty() }
        val errors = lines.filter { it.startsWith("ERROR") }
        val pick = if (errors.isNotEmpty()) errors.takeLast(3) else lines.takeLast(3)
        return pick.joinToString("\n").take(700).ifEmpty { "Erro desconhecido." }
    }

    private fun shortMsg(raw: String) = cleanMsg(raw).take(200)

    fun needsLogin(msg: String): Boolean {
        val m = msg.lowercase()
        return listOf("confirm your age", "sign in to confirm", "age-restricted", "age restricted",
            "cookies-from-browser", "login required", "--cookies").any { m.contains(it) }
    }

    private fun isPostprocess(msg: String): Boolean {
        val m = msg.lowercase()
        return listOf("postprocessing", "conversion failed", "ffmpeg", "ffprobe").any { m.contains(it) }
    }

    private fun isFormatError(msg: String): Boolean {
        val m = msg.lowercase()
        return m.contains("requested format is not available") || m.contains("format is not available")
    }

    fun fmtDuration(seconds: Double): String {
        if (seconds <= 0 || seconds.isNaN() || seconds.isInfinite()) return ""
        val s = seconds.toLong()
        val h = s / 3600
        val m = (s % 3600) / 60
        val sec = s % 60
        return if (h > 0) String.format(Locale.US, "%d:%02d:%02d", h, m, sec)
        else String.format(Locale.US, "%d:%02d", m, sec)
    }

    private fun fmtViews(n: Long): String = when {
        n <= 0 -> ""
        n >= 1_000_000 -> String.format(Locale("pt", "BR"), "%.1f mi de visualizações", n / 1_000_000.0)
        n >= 1_000 -> "${n / 1000} mil visualizações"
        else -> "$n visualizações"
    }

    fun fmtBytes(n: Long): String {
        if (n <= 0) return "--"
        var v = n.toDouble()
        for (u in listOf("B", "KB", "MB", "GB")) {
            if (v < 1024) return String.format(Locale.US, "%.1f %s", v, u)
            v /= 1024
        }
        return String.format(Locale.US, "%.1f TB", v)
    }

    private fun request(url: String, playlist: Boolean = false): YoutubeDLRequest {
        val r = YoutubeDLRequest(url)
        if (!playlist) r.addOption("--no-playlist")
        r.addOption("--no-color")
        r.addOption("--cache-dir", File(app.cacheDir, "ytdlp-cache").absolutePath)
        val cookies = Store.cookieFile
        if (cookies.exists()) r.addOption("--cookies", cookies.absolutePath)
        return r
    }

    private fun parseJson(out: String): JSONObject {
        val start = out.indexOf('{')
        val end = out.lastIndexOf('}')
        if (start < 0 || end <= start) throw Exception("Resposta inesperada do yt-dlp.")
        return JSONObject(out.substring(start, end + 1))
    }

    private fun bestThumb(j: JSONObject): String {
        val t = j.optString("thumbnail", "")
        if (t.startsWith("http")) return t
        val arr = j.optJSONArray("thumbnails") ?: return ""
        var best = ""
        var bestW = -1
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            val u = o.optString("url", "")
            val w = o.optInt("width", 0)
            if (u.startsWith("http") && (w >= bestW)) {
                best = u
                bestW = w
            }
        }
        return best
    }

    // ---------- opções do download (H.264, legendas, trecho) ----------
    const val NOTE_FALLBACK = "formato ajustado para compatibilidade"
    const val NOTE_NO_RECODE = "sem converter para H.264: a conversão falhou"
    const val NOTE_NO_SUBS = "sem legenda: não foi possível baixá-la"
    private const val H264 = "[vcodec~='^(avc|h264)']"
    private const val RECODE_PPA = "VideoConvertor:-c:v libx264 -preset veryfast -crf 20 " +
        "-pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart"
    private val SUB_EXT = setOf("srt", "vtt", "ass")
    private val SKIP_EXT = SUB_EXT + setOf("jpg", "jpeg", "webp", "png", "part", "ytdl", "temp", "json")

    private val LANG_NAMES = mapOf(
        "pt" to "Português", "pt-BR" to "Português (Brasil)", "pt-PT" to "Português (Portugal)",
        "en" to "Inglês", "en-US" to "Inglês (EUA)", "en-GB" to "Inglês (Reino Unido)",
        "es" to "Espanhol", "es-419" to "Espanhol (América Latina)", "es-ES" to "Espanhol (Espanha)",
        "fr" to "Francês", "de" to "Alemão", "it" to "Italiano", "ja" to "Japonês", "ko" to "Coreano",
        "zh" to "Chinês", "zh-Hans" to "Chinês (simplificado)", "zh-Hant" to "Chinês (tradicional)",
        "ru" to "Russo", "ar" to "Árabe", "hi" to "Hindi", "tr" to "Turco", "pl" to "Polonês",
        "nl" to "Holandês", "id" to "Indonésio", "vi" to "Vietnamita", "th" to "Tailandês",
    )

    private fun langName(code: String): String =
        LANG_NAMES[code] ?: LANG_NAMES[code.substringBefore('-')] ?: code

    /** Legendas do vídeo. Automáticas: só o idioma original, português e inglês. */
    private fun subtitleOptions(j: JSONObject): JSONArray {
        val out = mutableListOf<Triple<String, String, Boolean>>()
        val seen = mutableSetOf<String>()
        fun nameOf(arr: JSONArray?, code: String): String {
            val n = langName(code)
            if (n != code) return n
            if (arr != null) for (i in 0 until arr.length()) {
                val nm = arr.optJSONObject(i)?.optString("name", "") ?: ""
                if (nm.isNotEmpty()) return nm
            }
            return code
        }
        j.optJSONObject("subtitles")?.let { manual ->
            val keys = manual.keys().asSequence().toList()
                .sortedWith(compareBy<String>({ !it.startsWith("pt") }, { it }))
            for (code in keys) {
                if (code == "live_chat" || code == "rechat") continue
                val arr = manual.optJSONArray(code) ?: continue
                if (arr.length() == 0) continue
                out.add(Triple(nameOf(arr, code), code, false))
                seen.add(code.substringBefore('-'))
            }
        }
        j.optJSONObject("automatic_captions")?.let { auto ->
            val keys = auto.keys().asSequence().toList()
            val picks = keys.filter { it.endsWith("-orig") }.take(1) +
                listOf("pt-BR", "pt", "en").filter { auto.has(it) }
            for (code in picks) {
                val plain = code.removeSuffix("-orig")
                val base = plain.substringBefore('-')
                val arr = auto.optJSONArray(code) ?: continue
                if (base in seen || arr.length() == 0) continue
                seen.add(base)
                out.add(Triple(nameOf(arr, plain).replace(" (Original)", "") + " (automática)", code, true))
            }
        }
        val labels = mutableSetOf<String>()
        val res = JSONArray()
        for ((label0, code, auto) in out) {
            val label = if (label0 in labels) "$label0 [$code]" else label0
            labels.add(label)
            res.put(JSONObject().put("label", label).put("code", code).put("auto", auto))
        }
        return res
    }

    /** Endereços das thumbnails, da melhor para a pior (a maior às vezes não existe). */
    private fun thumbCandidates(j: JSONObject): JSONArray {
        val list = mutableListOf<Triple<Int, Long, String>>()
        val arr = j.optJSONArray("thumbnails")
        if (arr != null) for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            val u = o.optString("url", "")
            if (!u.startsWith("http")) continue
            list.add(Triple(o.optInt("preference", 0), o.optLong("width", 0) * o.optLong("height", 0), u))
        }
        val sorted = list.sortedWith(compareByDescending<Triple<Int, Long, String>> { it.first }
            .thenByDescending { it.second }).map { it.third }.distinct().toMutableList()
        val main = j.optString("thumbnail", "")
        if (main.startsWith("http") && main !in sorted) sorted.add(0, main)
        val res = JSONArray()
        sorted.take(4).forEach { res.put(it) }
        return res
    }

    private fun num(v: Double): String =
        if (v == Math.floor(v)) v.toLong().toString() else String.format(Locale.US, "%.2f", v)

    private fun clockText(v: Double): String {
        val s = v.toLong()
        val h = s / 3600
        val m = (s % 3600) / 60
        val sec = s % 60
        val base = if (h > 0) String.format(Locale.US, "%d:%02d:%02d", h, m, sec)
        else String.format(Locale.US, "%d:%02d", m, sec)
        val frac = v - s
        return if (frac >= 0.05) base + "." + (Math.round(frac * 10) % 10) else base
    }

    private fun sectionTag(s: Section): String {
        fun one(v: Double): String {
            val t = v.toLong()
            val h = t / 3600
            val m = (t % 3600) / 60
            val sec = t % 60
            return (if (h > 0) "${h}h" else "") + String.format(Locale.US, "%dm%02ds", m, sec)
        }
        return "trecho ${one(s.start)}-${one(s.end)}"
    }

    private fun isSubtitleError(msg: String): Boolean {
        val m = msg.lowercase()
        return m.contains("subtitle") && (m.contains("unable to download") || m.contains("http error") || m.contains("429"))
    }

    private fun safeName(t: String): String =
        t.replace(Regex("[\\\\/:*?\"<>|\\r\\n\\t]"), "_").trim(' ', '.').take(100).ifEmpty { "thumbnail" }

    // ---------- análise ----------
    fun analyze(reqId: String, url: String) {
        bg.execute {
            try {
                waitReady()
                val r = request(url)
                r.addOption("-J")
                val resp = YoutubeDL.getInstance().execute(r, null, false, null)
                val j = parseJson(resp.out)
                if (j.optString("_type") == "playlist") {
                    throw Exception("Este link é de uma playlist. Abra um vídeo da playlist e copie o link dele.")
                }
                val heights = sortedSetOf<Int>()
                val h264 = sortedSetOf<Int>()
                var codecKnown = false
                val formats = j.optJSONArray("formats") ?: JSONArray()
                for (i in 0 until formats.length()) {
                    val f = formats.optJSONObject(i) ?: continue
                    val h = f.optInt("height", 0)
                    val vc = if (f.isNull("vcodec")) "" else f.optString("vcodec", "")
                    if (vc.isNotEmpty() && vc != "none") {
                        codecKnown = true
                        if (h > 0 && (vc.startsWith("avc") || vc.startsWith("h264"))) h264.add(h)
                    }
                    if (h > 0 && vc != "none") heights.add(h)
                }
                val hs = JSONArray()
                heights.descendingSet().forEach { hs.put(it) }
                val h264s = JSONArray()
                h264.descendingSet().forEach { h264s.put(it) }
                emit("analyzed", JSONObject()
                    .put("reqId", reqId)
                    .put("url", url)
                    .put("title", j.optString("title", "Sem título"))
                    .put("uploader", j.optString("uploader", "").ifEmpty { j.optString("channel", "") })
                    .put("duration", fmtDuration(j.optDouble("duration", 0.0)))
                    .put("thumbnail", bestThumb(j))
                    .put("thumbs", thumbCandidates(j))
                    .put("id", j.optString("id", ""))
                    .put("durationSec", j.optDouble("duration", 0.0).let { if (it.isNaN()) 0.0 else it })
                    .put("heights", hs)
                    .put("h264", h264s)
                    .put("codecKnown", codecKnown)
                    .put("subs", subtitleOptions(j)))
            } catch (e: Throwable) {
                val msg = cleanMsg(e.message ?: e.toString())
                if (!reqId.startsWith("p")) Store.addError(url, msg)
                val code = when {
                    needsLogin(msg) -> "login"
                    isFormatError(msg) -> "format"
                    else -> "generic"
                }
                emit("analyzeError", JSONObject().put("reqId", reqId).put("msg", msg).put("code", code))
            }
        }
    }

    // ---------- pesquisa ----------
    fun search(reqId: String, query: String, source: String) {
        bg.execute {
            try {
                waitReady()
                val prefix = when (source) {
                    "youtube_recent" -> "ytsearchdate"
                    "soundcloud" -> "scsearch"
                    else -> "ytsearch"
                }
                val r = request("$prefix" + "15:" + query, playlist = true)
                r.addOption("--flat-playlist")
                r.addOption("-J")
                val resp = YoutubeDL.getInstance().execute(r, null, false, null)
                val j = parseJson(resp.out)
                val entries = j.optJSONArray("entries") ?: JSONArray()
                val results = JSONArray()
                for (i in 0 until entries.length()) {
                    val e = entries.optJSONObject(i) ?: continue
                    val id = e.optString("id", "")
                    var url = e.optString("webpage_url", "")
                    if (!url.startsWith("http")) url = e.optString("url", "")
                    if (!url.startsWith("http")) {
                        if (prefix.startsWith("yt") && id.isNotEmpty()) url = "https://www.youtube.com/watch?v=$id"
                        else continue
                    }
                    var thumb = bestThumb(e)
                    if (thumb.isEmpty() && prefix.startsWith("yt") && id.isNotEmpty()) {
                        thumb = "https://i.ytimg.com/vi/$id/mqdefault.jpg"
                    }
                    val meta = listOf(
                        e.optString("channel", "").ifEmpty { e.optString("uploader", "") },
                        fmtDuration(e.optDouble("duration", 0.0)),
                        fmtViews(e.optLong("view_count", 0L)),
                    ).filter { it.isNotEmpty() }.joinToString("  •  ")
                    results.put(JSONObject()
                        .put("url", url)
                        .put("title", e.optString("title", "Sem título"))
                        .put("uploader", e.optString("channel", "").ifEmpty { e.optString("uploader", "") })
                        .put("duration", fmtDuration(e.optDouble("duration", 0.0)))
                        .put("meta", meta)
                        .put("thumb", thumb))
                }
                emit("searchResults", JSONObject().put("reqId", reqId).put("results", results))
            } catch (e: Throwable) {
                emit("searchError", JSONObject().put("reqId", reqId)
                    .put("msg", "Não foi possível pesquisar agora.\n" + shortMsg(e.message ?: e.toString())))
            }
        }
    }

    // ---------- downloads ----------
    private class Plan(val args: List<Pair<String, String?>>, val note: String?)

    /** Receitas de download: a pedida e, se a conversão falhar, alternativas mais seguras. */
    private fun plans(quality: String, mode: String, height: Int): List<Plan> {
        if (quality == "audio") {
            return listOf(
                Plan(listOf("-f" to "bestaudio/best", "-x" to null, "--audio-format" to "mp3",
                    "--audio-quality" to "192K"), null),
                // se a conversão para MP3 falhar, mantém o áudio original
                Plan(listOf("-f" to "bestaudio[ext=m4a]/bestaudio/best"), NOTE_FALLBACK),
            )
        }
        val h = quality.toIntOrNull()
        val hc = if (h != null) "[height<=$h]" else ""
        val main = if (h != null) "bv*$hc+ba/b$hc/bv*+ba/b/best" else "bv*+ba/b/best"
        val std = listOf(
            listOf("-f" to main, "--merge-output-format" to "mp4", "-S" to "res,ext:mp4:m4a"),
            listOf("-f" to main, "--merge-output-format" to "mkv"),
            listOf("-f" to "bv*[vcodec^=avc1]$hc+ba[acodec^=mp4a]/bv*[ext=mp4]$hc+ba[ext=m4a]/b[ext=mp4]$hc/b$hc",
                "--merge-output-format" to "mp4"),
            listOf("-f" to "b$hc/b"),
        )
        val hh = if (height > 0) "[height<=$height]" else hc
        val first: List<Pair<String, String?>>? = when (mode) {
            "h264" -> listOf("-f" to "bv*$H264$hh+ba[acodec^=mp4a]/bv*$H264$hh+ba/b$H264$hh/$main",
                "--merge-output-format" to "mp4", "-S" to "res,ext:mp4:m4a")
            "pref" -> listOf("-f" to main, "--merge-output-format" to "mp4",
                "-S" to "vcodec:h264,res,acodec:aac,ext:mp4:m4a")
            // junta em MKV (aceita qualquer codec) e converte para MP4 H.264
            "recode" -> listOf("-f" to main, "--merge-output-format" to "mkv",
                "--recode-video" to "mp4", "--postprocessor-args" to RECODE_PPA)
            else -> null
        }
        if (first == null) return std.mapIndexed { i, a -> Plan(a, if (i == 0) null else NOTE_FALLBACK) }
        val out = mutableListOf(Plan(first, null))
        std.forEachIndexed { i, a -> out.add(Plan(a, if (mode == "recode" && i == 0) NOTE_NO_RECODE else NOTE_FALLBACK)) }
        return out
    }

    /** Opções de legenda e trecho, somadas a qualquer receita. */
    private fun extraArgs(j: Job, withSubs: Boolean): List<Pair<String, String?>> {
        val a = mutableListOf<Pair<String, String?>>()
        if (withSubs && j.subCode.isNotEmpty() && j.section == null) {
            // --write-subs também nas automáticas: mantém o .srt depois de embutir
            a.add("--write-subs" to null)
            if (j.subAuto) a.add("--write-auto-subs" to null)
            a.add("--sub-langs" to j.subCode)
            a.add("--sub-format" to "srt/vtt/best")
            a.add("--convert-subs" to "srt")
            if (j.quality != "audio") a.add("--embed-subs" to null)
        }
        j.section?.let { s ->
            a.add("--download-sections" to "*${num(s.start)}-${num(s.end)}")
            // o MP3 é convertido de qualquer jeito: corta no ponto exato
            if (s.exact || j.quality == "audio") a.add("--force-keyframes-at-cuts" to null)
        }
        return a
    }

    /** Começa um download. Retorna uma mensagem de erro ou null se começou. */
    fun download(data: JSONObject): String? {
        val current = job
        if (current != null && current.active) {
            return "Já existe um download em andamento. Espere terminar para iniciar outro."
        }
        val url = data.optString("url", "")
        if (!url.startsWith("http")) return "Link inválido."
        val q = data.optString("quality", "best")
        val quality = if (q == "best" || q == "audio" || q.toIntOrNull() != null) q else "best"
        val m = data.optString("compat", "off")
        val mode = if (quality != "audio" && m in listOf("h264", "recode", "pref")) m else "off"
        val section = data.optJSONObject("section")?.let { o ->
            val st = o.optDouble("start", 0.0)
            val en = o.optDouble("end", 0.0)
            if (st.isNaN() || en.isNaN() || st < 0 || en - st < 0.5) return "Trecho inválido."
            Section(st, en, o.optBoolean("exact", false))
        }
        val j = Job(
            id = "dl" + System.currentTimeMillis(),
            url = url,
            quality = quality,
            title = data.optString("title", "").ifEmpty { url },
            uploader = data.optString("uploader", ""),
            duration = data.optString("duration", ""),
            thumb = data.optString("thumb", ""),
            mode = mode,
            height = data.optInt("height", 0),
            subCode = data.optString("subLang", ""),
            subAuto = data.optBoolean("subAuto", false),
            subLabel = data.optString("subLabel", ""),
            section = section,
        )
        job = j
        emit("job", j.toJson())
        DownloadService.start(app)
        dlExec.execute { runJob(j) }
        return null
    }

    fun cancel() {
        val j = job ?: return
        if (!j.active) return
        j.cancel = true
        j.text = "Cancelando..."
        emit("job", j.toJson())
        try {
            YoutubeDL.getInstance().destroyProcessById(j.id)
        } catch (e: Throwable) {
            // já terminou
        }
    }

    private fun progressText(line: String, pct: Float): String? {
        val l = line.trim()
        if (l.startsWith("[Merger]") || l.startsWith("[VideoRemuxer]") || l.startsWith("[FixupM3u8]")) {
            return "Processando arquivo (juntando áudio e vídeo)..."
        }
        if (l.startsWith("[ExtractAudio]")) return "Convertendo para MP3..."
        if (l.startsWith("[VideoConvertor]")) return "Convertendo para MP4 H.264... pode levar alguns minutos."
        if (l.startsWith("[EmbedSubtitle]")) return "Colocando a legenda no vídeo..."
        if (l.startsWith("[download]") && l.contains("%")) {
            return l.removePrefix("[download]").trim()
                .replace(" of ", " de ").replace(" at ", " a ")
                .replace("ETA", "faltam").replace("~", "")
                .replace(Regex("\\s+"), " ")
        }
        if (pct >= 0) return null
        return null
    }

    private fun onProgress(j: Job, pct: Float, line: String) {
        if (j.cancel) return
        val text = progressText(line, pct)
        if (text != null) {
            if (text.startsWith("Processando") || text.startsWith("Convertendo") || text.startsWith("Colocando")) {
                j.status = "processing"
                j.pct = 100f
            } else {
                j.status = "downloading"
                if (pct >= 0) j.pct = pct
            }
            j.text = text
        } else if (pct >= 0) {
            j.status = "downloading"
            j.pct = pct
        }
        val now = System.currentTimeMillis()
        if (now - j.lastEmit > 300) {
            j.lastEmit = now
            emit("job", j.toJson())
        }
        if (now - j.lastNotify > 1000) {
            j.lastNotify = now
            Notifier.progress(app, j)
        }
    }

    private fun pickOutput(dir: File): File? = dir.listFiles()
        ?.filter {
            it.isFile && it.extension.lowercase() !in SKIP_EXT && !it.name.contains(".part-Frag")
        }
        ?.maxByOrNull { it.length() }

    private fun subtitleFiles(dir: File): List<File> =
        dir.listFiles()?.filter { it.isFile && it.extension.lowercase() in SUB_EXT } ?: emptyList()

    private fun finishJob(j: Job) {
        DownloadService.stop(app)
        Notifier.clearProgress(app)
    }

    private fun runJob(j: Job) {
        try {
            waitReady()
        } catch (e: Exception) {
            failJob(j, e.message ?: "Erro", "generic")
            return
        }
        val dir = File(app.cacheDir, "dl/${j.id}")
        dir.deleteRecursively()
        dir.mkdirs()
        val plans = plans(j.quality, j.mode, j.height)
        var withSubs = true
        var subNote: String? = null
        var i = 0
        var retried = j.mode == "recode"  // não repete uma conversão demorada
        var lastMsg = ""
        val attempts = mutableListOf<String>()
        val tag = j.section?.let { " (" + sectionTag(it) + ")" } ?: ""
        if (j.section != null) {
            // o FFmpeg baixa o trecho sem informar o progresso: a barra fica em movimento
            j.status = "processing"
            j.text = "Baixando o trecho de ${clockText(j.section.start)} a ${clockText(j.section.end)}..."
            emit("job", j.toJson())
        }
        while (i < plans.size) {
            if (j.cancel) {
                cancelJob(j, dir)
                return
            }
            val plan = plans[i]
            val r = request(j.url)
            r.addOption("-o", File(dir, "%(title).80B [%(id)s]$tag.%(ext)s").absolutePath)
            r.addOption("--windows-filenames")
            r.addOption("--no-mtime")
            for ((key, value) in plan.args + extraArgs(j, withSubs)) {
                if (value == null) r.addOption(key) else r.addOption(key, value)
            }
            try {
                YoutubeDL.getInstance().execute(r, j.id, false) { pct, _, line ->
                    onProgress(j, pct, line)
                }
                if (j.cancel) {
                    cancelJob(j, dir)
                    return
                }
                val file = pickOutput(dir) ?: throw Exception("O arquivo baixado não foi encontrado.")
                j.status = "saving"
                j.pct = 100f
                j.text = "Salvando na pasta Downloads..."
                emit("job", j.toJson())
                val saved = MediaSaver.save(app, file)
                for (sub in subtitleFiles(dir)) {
                    try {
                        MediaSaver.save(app, sub)  // .srt ao lado do vídeo
                    } catch (e: Exception) {
                        // a legenda já está embutida no vídeo
                    }
                }
                dir.deleteRecursively()
                val notes = listOfNotNull(plan.note, subNote).joinToString("; ")
                val entry = JSONObject()
                    .put("id", System.currentTimeMillis().toString())
                    .put("url", j.url)
                    .put("title", j.title)
                    .put("uploader", j.uploader)
                    .put("duration", j.duration)
                    .put("quality", j.quality)
                    .put("uri", saved.uri)
                    .put("path", saved.path)
                    .put("name", saved.name)
                    .put("mime", saved.mime)
                    .put("size", saved.size)
                    .put("date", SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("pt", "BR")).format(Date()))
                    .put("thumb", j.thumb)
                    .put("compat", j.mode != "off" && plan.note == null)
                    .put("subs", if (withSubs && j.section == null) j.subLabel else "")
                j.section?.let { entry.put("section", it.toJson()) }
                Store.addHistory(entry)
                j.status = "done"
                j.text = if (notes.isNotEmpty()) "Concluído, $notes." else "Download concluído!"
                finishJob(j)
                emit("job", j.toJson())
                emit("done", JSONObject().put("entry", entry.put("exists", true))
                    .put("note", notes).put("fallback", notes.isNotEmpty()))
                Notifier.done(app, j.title, saved)
                return
            } catch (e: Throwable) {
                if (j.cancel) {
                    cancelJob(j, dir)
                    return
                }
                lastMsg = cleanMsg(e.message ?: e.toString())
                attempts.add(lastMsg)
                if (withSubs && j.subCode.isNotEmpty() && j.section == null && isSubtitleError(lastMsg)) {
                    // a legenda falhou (o YouTube às vezes limita): baixa sem ela
                    withSubs = false
                    subNote = NOTE_NO_SUBS
                    j.text = "Não foi possível baixar a legenda. Baixando sem ela..."
                    emit("job", j.toJson())
                    continue
                }
                if (isPostprocess(lastMsg)) {
                    if (i == 0 && !retried) {
                        // falha momentânea na junção: tenta de novo reaproveitando o que já baixou
                        retried = true
                        j.text = "A junção dos arquivos falhou. Tentando de novo..."
                        emit("job", j.toJson())
                        Thread.sleep(2500)
                        continue
                    }
                    if (i + 1 < plans.size) {
                        i++
                        j.text = "A conversão falhou. Tentando outro formato..."
                        emit("job", j.toJson())
                        continue
                    }
                }
                break
            }
        }
        dir.deleteRecursively()
        // as receitas de reserva costumam terminar em "formato indisponível": mostra a causa real
        lastMsg = attempts.firstOrNull { !isFormatError(it) } ?: lastMsg
        val code = when {
            needsLogin(lastMsg) -> "login"
            isFormatError(lastMsg) -> "format"
            else -> "generic"
        }
        failJob(j, lastMsg, code)
    }

    private fun cancelJob(j: Job, dir: File) {
        dir.deleteRecursively()
        j.status = "cancelled"
        j.text = "Download cancelado."
        finishJob(j)
        emit("job", j.toJson())
        emit("cancelled", JSONObject())
    }

    private fun failJob(j: Job, msg: String, code: String) {
        Store.addError(j.url, msg)
        j.status = "error"
        j.text = "Falha no download."
        finishJob(j)
        emit("job", j.toJson())
        emit("error", JSONObject().put("msg", msg).put("code", code))
        Notifier.failed(app, j.title)
    }

    // ---------- thumbnail ----------
    fun saveThumb(urls: JSONArray, title: String, vid: String) {
        bg.execute {
            var last = "Este vídeo não tem thumbnail."
            for (k in 0 until urls.length()) {
                val url = urls.optString(k, "")
                if (!url.startsWith("http")) continue
                try {
                    val conn = (URL(url).openConnection() as HttpURLConnection).apply {
                        connectTimeout = 15000
                        readTimeout = 20000
                        setRequestProperty("User-Agent", "Mozilla/5.0")
                    }
                    val bytes = try {
                        if (conn.responseCode !in 200..299) throw Exception("HTTP ${conn.responseCode}")
                        conn.inputStream.use { it.readBytes() }
                    } finally {
                        conn.disconnect()
                    }
                    val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        ?: throw Exception("Formato de imagem não suportado.")
                    val dir = File(app.cacheDir, "thumb-out").apply { deleteRecursively(); mkdirs() }
                    val base = safeName(title) + (if (vid.isNotEmpty()) " [${safeName(vid)}]" else "") + " - thumbnail"
                    val f = File(dir, "$base.jpg")
                    f.outputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, 95, it) }
                    val saved = MediaSaver.save(app, f)
                    dir.deleteRecursively()
                    emit("thumbSaved", JSONObject().put("name", saved.name).put("w", bmp.width)
                        .put("h", bmp.height).put("uri", saved.uri))
                    return@execute
                } catch (e: Throwable) {
                    last = e.message ?: e.toString()
                }
            }
            Store.addError(urls.optString(0, ""), "Thumbnail: $last")
            emit("thumbError", JSONObject().put("msg", "Não foi possível salvar a thumbnail.\n$last"))
        }
    }

    // ---------- relatório de erro ----------
    fun report(lastError: String): String {
        val sb = StringBuilder()
        sb.append("Baixador de Vídeos ${BuildConfig.VERSION_NAME} (Android)\n")
        sb.append("Android: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})\n")
        sb.append("Aparelho: ${Build.MANUFACTURER} ${Build.MODEL} • ${Build.SUPPORTED_ABIS.firstOrNull() ?: "?"}\n")
        sb.append("yt-dlp: ${if (setupState == "done") ytdlpVersion() else setupState}\n")
        sb.append("cookies.txt: ${if (Store.cookieFile.exists()) "carregado" else "nenhum"}\n")
        sb.append("Data: ${SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("pt", "BR")).format(Date())}\n")
        if (lastError.isNotBlank()) sb.append("\nÚltimo erro:\n${lastError.trim().take(1500)}\n")
        val errs = Store.errors()
        if (errs.length() > 0) {
            sb.append("\nRegistro de erros (mais recentes):\n")
            for (i in 0 until errs.length()) {
                val e = errs.optJSONObject(i) ?: continue
                sb.append("[${e.optString("date")}] ${e.optString("url")}\n${e.optString("msg")}\n----\n")
            }
        }
        return sb.toString()
    }

    // ---------- histórico ----------
    fun historyWithStatus(onReady: (JSONArray) -> Unit) {
        bg.execute {
            val list = Store.history()
            for (i in 0 until list.length()) {
                val e = list.optJSONObject(i) ?: continue
                e.put("exists", MediaSaver.exists(app, e.optString("uri", ""), e.optString("path", "")))
            }
            onReady(list)
        }
    }

    fun runInBackground(task: () -> Unit) {
        bg.execute { task() }
    }
}
