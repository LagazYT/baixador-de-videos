package com.lagaz.baixadordevideos

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder

/** Mantém o download rodando com a tela desligada ou com o app em segundo plano. */
class DownloadService : Service() {

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Notifier.ensureChannels(this)
        val notification = Notifier.buildProgress(this, Engine.job)
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(Notifier.ID_PROGRESS, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
            } else {
                startForeground(Notifier.ID_PROGRESS, notification)
            }
        } catch (e: Exception) {
            // Sem permissão para serviço em primeiro plano: o download continua enquanto o app estiver aberto.
        }
        if (intent?.action == ACTION_CANCEL) {
            if (Engine.isStarted()) Engine.cancel()
        }
        val j = Engine.job
        if (j == null || !j.active) stopSelf()
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        try {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } catch (e: Exception) {
        }
        super.onDestroy()
    }

    companion object {
        const val ACTION_CANCEL = "com.lagaz.baixadordevideos.CANCEL"

        fun start(ctx: Context) {
            val i = Intent(ctx, DownloadService::class.java)
            try {
                if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
            } catch (e: Exception) {
                // o download segue mesmo sem o serviço
            }
        }

        fun stop(ctx: Context) {
            try {
                ctx.stopService(Intent(ctx, DownloadService::class.java))
            } catch (e: Exception) {
            }
        }
    }
}
