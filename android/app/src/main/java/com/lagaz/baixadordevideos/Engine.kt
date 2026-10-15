package com.lagaz.baixadordevideos

import android.content.Context
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
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

    class Job(
        val id: String,
        val url: String,
        val quality: String,
        val title: String,
        val uploader: String,
        val duration: String,
        val thumb: String,
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
                val formats = j.optJSONArray("formats") ?: JSONArray()
                for (i in 0 until formats.length()) {
                    val f = formats.optJSONObject(i) ?: continue
                    val h = f.optInt("height", 0)
                    if (h > 0 && f.optString("vcodec", "") != "none") heights.add(h)
                }
                val hs = JSONArray()
                heights.descendingSet().forEach { hs.put(it) }
                emit("analyzed", JSONObject()
                    .put("reqId", reqId)
                    .put("url", url)
                    .put("title", j.optString("title", "Sem título"))
                    .put("uploader", j.optString("uploader", "").ifEmpty { j.optString("channel", "") })
                    .put("duration", fmtDuration(j.optDouble("duration", 0.0)))
                    .put("thumbnail", bestThumb(j))
                    .put("heights", hs))
            } catch (e: Throwable) {
                val msg = cleanMsg(e.message ?: e.toString())
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
    private fun plans(quality: String): List<List<Pair<String, String?>>> {
        if (quality == "audio") {
            return listOf(
                listOf("-f" to "bestaudio/best", "-x" to null, "--audio-format" to "mp3",
                    "--audio-quality" to "192K"),
                // se a conversão para MP3 falhar, mantém o áudio original
                listOf("-f" to "bestaudio[ext=m4a]/bestaudio/best"),
            )
        }
        val h = quality.toIntOrNull()
        val hc = if (h != null) "[height<=$h]" else ""
        val main = if (h != null) "bv*$hc+ba/b$hc/bv*+ba/b/best" else "bv*+ba/b/best"
        return listOf(
            listOf("-f" to main, "--merge-output-format" to "mp4", "-S" to "res,ext:mp4:m4a"),
            listOf("-f" to main, "--merge-output-format" to "mkv"),
            listOf("-f" to "bv*[vcodec^=avc1]$hc+ba[acodec^=mp4a]/bv*[ext=mp4]$hc+ba[ext=m4a]/b[ext=mp4]$hc/b$hc",
                "--merge-output-format" to "mp4"),
            listOf("-f" to "b$hc/b"),
        )
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
        val j = Job(
            id = "dl" + System.currentTimeMillis(),
            url = url,
            quality = quality,
            title = data.optString("title", "").ifEmpty { url },
            uploader = data.optString("uploader", ""),
            duration = data.optString("duration", ""),
            thumb = data.optString("thumb", ""),
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
            if (text.startsWith("Processando") || text.startsWith("Convertendo")) {
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
            it.isFile && !it.name.endsWith(".part") && !it.name.endsWith(".ytdl") &&
                !it.name.endsWith(".temp") && !it.name.contains(".part-Frag")
        }
        ?.maxByOrNull { it.length() }

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
        val plans = plans(j.quality)
        var i = 0
        var retried = false
        var lastMsg = ""
        while (i < plans.size) {
            if (j.cancel) {
                cancelJob(j, dir)
                return
            }
            val r = request(j.url)
            r.addOption("-o", File(dir, "%(title).80B [%(id)s].%(ext)s").absolutePath)
            r.addOption("--windows-filenames")
            r.addOption("--no-mtime")
            for ((key, value) in plans[i]) {
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
                dir.deleteRecursively()
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
                Store.addHistory(entry)
                j.status = "done"
                j.text = if (i > 0) "Concluído (formato ajustado para compatibilidade)" else "Download concluído!"
                finishJob(j)
                emit("job", j.toJson())
                emit("done", JSONObject().put("entry", entry.put("exists", true)).put("fallback", i > 0))
                Notifier.done(app, j.title, saved)
                return
            } catch (e: Throwable) {
                if (j.cancel) {
                    cancelJob(j, dir)
                    return
                }
                lastMsg = cleanMsg(e.message ?: e.toString())
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
        j.status = "error"
        j.text = "Falha no download."
        finishJob(j)
        emit("job", j.toJson())
        emit("error", JSONObject().put("msg", msg).put("code", code))
        Notifier.failed(app, j.title)
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
