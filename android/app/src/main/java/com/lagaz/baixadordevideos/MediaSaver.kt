package com.lagaz.baixadordevideos

import android.content.ContentValues
import android.content.Context
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.webkit.MimeTypeMap
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Copia o arquivo baixado para Downloads/BaixadorDeVideos (aparece na galeria e no gerenciador). */
object MediaSaver {
    const val FOLDER = "BaixadorDeVideos"

    class Saved(val uri: String, val name: String, val mime: String, val size: Long, val path: String)

    fun mimeOf(name: String): String {
        val ext = name.substringAfterLast('.', "").lowercase()
        val known = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext)
        if (known != null) return known
        return when (ext) {
            "mkv" -> "video/x-matroska"
            "webm" -> "video/webm"
            "mp4" -> "video/mp4"
            "m4a" -> "audio/mp4"
            "opus" -> "audio/ogg"
            "mp3" -> "audio/mpeg"
            else -> "application/octet-stream"
        }
    }

    fun save(ctx: Context, src: File): Saved {
        val name = src.name
        val mime = mimeOf(name)
        return if (Build.VERSION.SDK_INT >= 29) saveMediaStore(ctx, src, name, mime)
        else saveLegacy(ctx, src, mime)
    }

    private fun saveMediaStore(ctx: Context, src: File, name: String, mime: String): Saved {
        val resolver = ctx.contentResolver
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, name)
            put(MediaStore.MediaColumns.MIME_TYPE, mime)
            put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/" + FOLDER)
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }
        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: throw Exception("Não foi possível criar o arquivo na pasta Downloads.")
        try {
            val out = resolver.openOutputStream(uri)
                ?: throw Exception("Não foi possível gravar na pasta Downloads.")
            out.use { o -> src.inputStream().use { it.copyTo(o, 1 shl 16) } }
        } catch (e: Exception) {
            resolver.delete(uri, null, null)
            throw e
        }
        values.clear()
        values.put(MediaStore.MediaColumns.IS_PENDING, 0)
        resolver.update(uri, values, null, null)
        var finalName = name
        try {
            resolver.query(uri, arrayOf(MediaStore.MediaColumns.DISPLAY_NAME), null, null, null)?.use {
                if (it.moveToFirst()) finalName = it.getString(0) ?: name
            }
        } catch (e: Exception) {
            // mantém o nome original
        }
        return Saved(uri.toString(), finalName, mime, src.length(),
            "Download/$FOLDER/$finalName")
    }

    @Suppress("DEPRECATION")
    private fun saveLegacy(ctx: Context, src: File, mime: String): Saved {
        val dir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), FOLDER)
        if (!dir.exists() && !dir.mkdirs()) throw Exception("Sem permissão para salvar na pasta Downloads.")
        var dest = File(dir, src.name)
        var n = 1
        while (dest.exists()) {
            dest = File(dir, "${src.nameWithoutExtension} ($n).${src.extension}")
            n++
        }
        src.copyTo(dest)
        val latch = CountDownLatch(1)
        var found = ""
        MediaScannerConnection.scanFile(ctx, arrayOf(dest.absolutePath), arrayOf(mime)) { _, u ->
            if (u != null) found = u.toString()
            latch.countDown()
        }
        latch.await(10, TimeUnit.SECONDS)
        val uri = if (found.isNotEmpty()) found else Uri.fromFile(dest).toString()
        return Saved(uri, dest.name, mime, dest.length(), dest.absolutePath)
    }

    /** O arquivo ainda está no aparelho? */
    fun exists(ctx: Context, uri: String, path: String): Boolean {
        if (uri.startsWith("file:")) return File(Uri.parse(uri).path ?: path).exists()
        return try {
            ctx.contentResolver.query(Uri.parse(uri), arrayOf(MediaStore.MediaColumns._ID), null, null, null)
                ?.use { it.count > 0 } ?: false
        } catch (e: Exception) {
            false
        }
    }
}
