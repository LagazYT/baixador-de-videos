package com.lagaz.baixadordevideos

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build

/** Notificações: progresso do download (com botão Cancelar) e aviso de concluído. */
object Notifier {
    const val CH_PROGRESS = "downloads"
    const val CH_DONE = "concluidos"
    const val ID_PROGRESS = 1001
    private const val ID_DONE = 1002

    fun ensureChannels(ctx: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val nm = ctx.getSystemService(NotificationManager::class.java) ?: return
        nm.createNotificationChannel(
            NotificationChannel(CH_PROGRESS, "Downloads em andamento", NotificationManager.IMPORTANCE_LOW)
        )
        nm.createNotificationChannel(
            NotificationChannel(CH_DONE, "Downloads concluídos", NotificationManager.IMPORTANCE_DEFAULT)
        )
    }

    @Suppress("DEPRECATION")
    private fun builder(ctx: Context, channel: String): Notification.Builder =
        if (Build.VERSION.SDK_INT >= 26) Notification.Builder(ctx, channel) else Notification.Builder(ctx)

    private fun openAppIntent(ctx: Context): PendingIntent {
        val i = Intent(ctx, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        return PendingIntent.getActivity(ctx, 0, i,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    fun buildProgress(ctx: Context, j: Engine.Job?): Notification {
        val cancel = PendingIntent.getService(ctx, 1,
            Intent(ctx, DownloadService::class.java).setAction(DownloadService.ACTION_CANCEL),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val b = builder(ctx, CH_PROGRESS)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(j?.title ?: "Baixador de Vídeos")
            .setContentText(j?.text ?: "Preparando...")
            .setOnlyAlertOnce(true)
            .setOngoing(true)
            .setContentIntent(openAppIntent(ctx))
        if (j != null) {
            val indeterminate = j.status != "downloading" || j.pct <= 0f
            b.setProgress(100, j.pct.toInt().coerceIn(0, 100), indeterminate)
            @Suppress("DEPRECATION")
            b.addAction(android.R.drawable.ic_menu_close_clear_cancel, "Cancelar", cancel)
        }
        return b.build()
    }

    private fun manager(ctx: Context): NotificationManager? =
        ctx.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager

    fun progress(ctx: Context, j: Engine.Job) {
        try {
            manager(ctx)?.notify(ID_PROGRESS, buildProgress(ctx, j))
        } catch (e: Exception) {
            // sem permissão de notificação
        }
    }

    fun clearProgress(ctx: Context) {
        try {
            manager(ctx)?.cancel(ID_PROGRESS)
        } catch (e: Exception) {
        }
    }

    private fun shouldNotify(): Boolean =
        !MainActivity.visible && Store.setting("notify", true)

    fun done(ctx: Context, title: String, saved: MediaSaver.Saved) {
        if (!shouldNotify()) return
        try {
            val view = Intent(Intent.ACTION_VIEW)
                .setDataAndType(Uri.parse(saved.uri), saved.mime)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
            val pi = PendingIntent.getActivity(ctx, 2, view,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val n = builder(ctx, CH_DONE)
                .setSmallIcon(android.R.drawable.stat_sys_download_done)
                .setContentTitle("Download concluído")
                .setContentText(title)
                .setAutoCancel(true)
                .setContentIntent(pi)
                .build()
            manager(ctx)?.notify(ID_DONE, n)
        } catch (e: Exception) {
        }
    }

    fun failed(ctx: Context, title: String) {
        if (!shouldNotify()) return
        try {
            val n = builder(ctx, CH_DONE)
                .setSmallIcon(android.R.drawable.stat_notify_error)
                .setContentTitle("Falha no download")
                .setContentText(title)
                .setAutoCancel(true)
                .setContentIntent(openAppIntent(ctx))
                .build()
            manager(ctx)?.notify(ID_DONE, n)
        } catch (e: Exception) {
        }
    }
}
