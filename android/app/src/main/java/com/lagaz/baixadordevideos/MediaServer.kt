package com.lagaz.baixadordevideos

import android.content.Context
import android.net.Uri
import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.IOException
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.URLDecoder
import java.net.URLEncoder
import java.util.UUID
import java.util.concurrent.Executors

/**
 * Servidor local (só 127.0.0.1) que entrega os vídeos baixados ao player da aba Player.
 * Suporta "Range" (pedaços do arquivo), para poder avançar e voltar no vídeo.
 * Cada endereço leva um código secreto gerado a cada abertura do app.
 */
object MediaServer {
    private val token = UUID.randomUUID().toString().replace("-", "")
    private val pool = Executors.newCachedThreadPool()
    @Volatile private var server: ServerSocket? = null
    @Volatile var port = 0
        private set
    private lateinit var app: Context

    @Synchronized
    fun start(ctx: Context): Int {
        app = ctx.applicationContext
        server?.let { if (!it.isClosed) return port }
        val s = ServerSocket(0, 16, InetAddress.getByName("127.0.0.1"))
        server = s
        port = s.localPort
        Thread {
            while (!s.isClosed) {
                try {
                    val client = s.accept()
                    pool.execute { handle(client) }
                } catch (e: IOException) {
                    if (s.isClosed) break
                }
            }
        }.apply { isDaemon = true; name = "MediaServer" }.start()
        return port
    }

    fun urlFor(ctx: Context, uri: String, mime: String): String {
        start(ctx)
        val u = URLEncoder.encode(uri, "UTF-8")
        val t = URLEncoder.encode(mime, "UTF-8")
        return "http://127.0.0.1:$port/$token/media?u=$u&t=$t"
    }

    private class Source(val size: Long, val open: (Long) -> java.io.InputStream, val close: () -> Unit)

    private fun openSource(uri: String): Source {
        if (uri.startsWith("file:") || uri.startsWith("/")) {
            val f = File(if (uri.startsWith("file:")) Uri.parse(uri).path ?: "" else uri)
            if (!f.isFile) throw IOException("arquivo não encontrado")
            return Source(f.length(), { start -> FileInputStream(f).also { it.channel.position(start) } }, {})
        }
        val pfd = app.contentResolver.openFileDescriptor(Uri.parse(uri), "r")
            ?: throw IOException("arquivo não encontrado")
        val size = pfd.statSize
        return Source(size, { start ->
            FileInputStream(pfd.fileDescriptor).also { it.channel.position(start) }
        }, { try { pfd.close() } catch (e: Exception) { } })
    }

    private fun writeHead(out: OutputStream, status: String, headers: Map<String, String>) {
        val sb = StringBuilder("HTTP/1.1 $status\r\n")
        for ((k, v) in headers) sb.append(k).append(": ").append(v).append("\r\n")
        sb.append("\r\n")
        out.write(sb.toString().toByteArray(Charsets.ISO_8859_1))
    }

    private fun handle(socket: Socket) {
        socket.use { s ->
            try {
                s.soTimeout = 30_000
                val reader = BufferedReader(InputStreamReader(s.getInputStream(), Charsets.ISO_8859_1))
                val requestLine = reader.readLine() ?: return
                var range: String? = null
                while (true) {
                    val line = reader.readLine() ?: break
                    if (line.isEmpty()) break
                    val idx = line.indexOf(':')
                    if (idx > 0 && line.substring(0, idx).trim().equals("Range", ignoreCase = true)) {
                        range = line.substring(idx + 1).trim()
                    }
                }
                val parts = requestLine.split(" ")
                val method = parts.getOrNull(0) ?: "GET"
                val target = parts.getOrNull(1) ?: ""
                val out = s.getOutputStream()
                if (!target.startsWith("/$token/media?")) {
                    writeHead(out, "403 Forbidden", mapOf("Content-Length" to "0", "Connection" to "close"))
                    return
                }
                val query = target.substringAfter('?')
                val params = query.split('&').mapNotNull {
                    val kv = it.split('=', limit = 2)
                    if (kv.size == 2) kv[0] to URLDecoder.decode(kv[1], "UTF-8") else null
                }.toMap()
                val uri = params["u"] ?: ""
                val mime = params["t"]?.ifEmpty { null } ?: "application/octet-stream"
                val src = try {
                    openSource(uri)
                } catch (e: Exception) {
                    writeHead(out, "404 Not Found", mapOf("Content-Length" to "0", "Connection" to "close"))
                    return
                }
                try {
                    val size = src.size
                    var start = 0L
                    var end = size - 1
                    var partial = false
                    if (range != null && range.startsWith("bytes=") && size > 0) {
                        val spec = range.removePrefix("bytes=").split(',')[0].trim()
                        val a = spec.substringBefore('-')
                        val b = spec.substringAfter('-', "")
                        if (a.isEmpty() && b.isNotEmpty()) {
                            start = (size - b.toLong()).coerceAtLeast(0)
                        } else {
                            start = a.toLongOrNull() ?: 0L
                            if (b.isNotEmpty()) end = minOf(b.toLong(), size - 1)
                        }
                        if (start >= size) {
                            writeHead(out, "416 Range Not Satisfiable", mapOf(
                                "Content-Range" to "bytes */$size", "Content-Length" to "0", "Connection" to "close"))
                            return
                        }
                        partial = true
                    }
                    val length = (end - start + 1).coerceAtLeast(0)
                    val headers = linkedMapOf(
                        "Content-Type" to mime,
                        "Content-Length" to length.toString(),
                        "Accept-Ranges" to "bytes",
                        "Cache-Control" to "no-store",
                        "Connection" to "close",
                    )
                    if (partial) headers["Content-Range"] = "bytes $start-$end/$size"
                    writeHead(out, if (partial) "206 Partial Content" else "200 OK", headers)
                    if (method == "HEAD" || length == 0L) return
                    src.open(start).use { input ->
                        val buf = ByteArray(64 * 1024)
                        var remaining = length
                        while (remaining > 0) {
                            val n = input.read(buf, 0, minOf(buf.size.toLong(), remaining).toInt())
                            if (n < 0) break
                            out.write(buf, 0, n)
                            remaining -= n
                        }
                        out.flush()
                    }
                } finally {
                    src.close()
                }
            } catch (e: IOException) {
                // o player fechou a conexão (normal ao avançar/voltar)
            } catch (e: Exception) {
                // ignora pedidos inválidos
            }
        }
    }
}
