package com.lagaz.baixadordevideos

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Configurações e histórico do aplicativo (ficam só no aparelho). */
object Store {
    const val HISTORY_MAX = 500

    lateinit var prefs: SharedPreferences
        private set
    private lateinit var dir: File

    val cookieFile: File get() = File(dir, "cookies.txt")
    private val historyFile: File get() = File(dir, "historico.json")

    fun init(ctx: Context) {
        prefs = ctx.getSharedPreferences("config", Context.MODE_PRIVATE)
        dir = ctx.filesDir
    }

    // ---------- configurações ----------
    fun settings(): JSONObject = try {
        JSONObject(prefs.getString("settings", "{}") ?: "{}")
    } catch (e: Exception) {
        JSONObject()
    }

    fun saveSettings(json: String) {
        JSONObject(json) // valida
        prefs.edit().putString("settings", json).apply()
    }

    fun setting(key: String, default: Boolean): Boolean = settings().optBoolean(key, default)

    // ---------- histórico ----------
    @Synchronized
    fun history(): JSONArray = try {
        if (historyFile.exists()) JSONArray(historyFile.readText()) else JSONArray()
    } catch (e: Exception) {
        JSONArray()
    }

    @Synchronized
    private fun saveHistory(items: JSONArray) {
        val tmp = File(dir, "historico.tmp")
        tmp.writeText(items.toString())
        if (!tmp.renameTo(historyFile)) {
            historyFile.writeText(items.toString())
            tmp.delete()
        }
    }

    @Synchronized
    fun addHistory(entry: JSONObject) {
        val old = history()
        val list = JSONArray()
        list.put(entry)
        for (i in 0 until minOf(old.length(), HISTORY_MAX - 1)) list.put(old.get(i))
        saveHistory(list)
    }

    @Synchronized
    fun removeHistory(id: String) {
        val old = history()
        val list = JSONArray()
        for (i in 0 until old.length()) {
            val item = old.optJSONObject(i) ?: continue
            if (item.optString("id") != id) list.put(item)
        }
        saveHistory(list)
    }

    @Synchronized
    fun clearHistory() = saveHistory(JSONArray())

    // ---------- registro de erros (vai no relatório de erro) ----------
    @Synchronized
    fun addError(url: String, msg: String) {
        val old = errors()
        val list = JSONArray()
        list.put(JSONObject()
            .put("date", SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("pt", "BR")).format(Date()))
            .put("url", url)
            .put("msg", msg.take(800)))
        for (i in 0 until minOf(old.length(), 7)) list.put(old.get(i))
        prefs.edit().putString("errors", list.toString()).apply()
    }

    fun errors(): JSONArray = try {
        JSONArray(prefs.getString("errors", "[]") ?: "[]")
    } catch (e: Exception) {
        JSONArray()
    }
}
