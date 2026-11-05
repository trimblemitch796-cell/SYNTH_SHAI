package org.tuuwanasavi.synthshai

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock

class NudgeService : Service() {
    companion object {
        private const val SESSION = 21
        private const val NUDGE = 22
        private const val STATUS_CHANNEL = "session"
        private const val NUDGE_CHANNEL = "encouragement"
        private const val STOP = "stop"
        internal val loop = NudgeLoop()

        fun prepare(context: Context): Boolean {
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(NotificationChannel(STATUS_CHANNEL, "Active session", NotificationManager.IMPORTANCE_LOW))
            manager.createNotificationChannel(NotificationChannel(NUDGE_CHANNEL, "Encouragement", NotificationManager.IMPORTANCE_DEFAULT))
            return manager.areNotificationsEnabled() &&
                manager.getNotificationChannel(NUDGE_CHANNEL).importance != NotificationManager.IMPORTANCE_NONE
        }

        fun start(context: Context) {
            if (loop.start(SystemClock.elapsedRealtime())) {
                context.startForegroundService(Intent(context, NudgeService::class.java))
            }
        }

        fun stop(context: Context) {
            loop.stop()
            context.getSystemService(NotificationManager::class.java).cancel(NUDGE)
            context.stopService(Intent(context, NudgeService::class.java))
        }
    }

    private val handler = Handler(Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            if (loop.lastNudge == null || !prepare(this@NudgeService)) {
                stop(this@NudgeService)
                return
            }
            if (loop.repeat(SystemClock.elapsedRealtime())) notifyNudge()
            handler.postDelayed(this, NudgeLoop.PERIOD)
        }
    }

    private fun builder(channel: String): Notification.Builder {
        val flags = PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP), flags)
        val hold = PendingIntent.getService(this, 1, Intent(this, NudgeService::class.java).setAction(STOP), flags)
        return Notification.Builder(this, channel)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(open)
            .addAction(Notification.Action.Builder(null, "144 HOLD", hold).build())
    }

    private fun notifyNudge() {
        val notification = builder(NUDGE_CHANNEL)
            .setContentTitle("Ready for one small step?")
            .setContentText("Give yourself three minutes to begin.")
            .setTimeoutAfter(NudgeLoop.WINDOW)
            .build()
        getSystemService(NotificationManager::class.java).notify(NUDGE, notification)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == STOP || loop.lastNudge == null || !prepare(this)) {
            stop(this)
            return START_NOT_STICKY
        }
        startForeground(SESSION, builder(STATUS_CHANNEL)
            .setContentTitle("SHAI encouragement is on")
            .setContentText("One reminder every five minutes while your phone is awake.")
            .setOngoing(true).build())
        notifyNudge()
        handler.removeCallbacks(tick)
        handler.postDelayed(tick, NudgeLoop.PERIOD)
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacks(tick)
        loop.stop()
        getSystemService(NotificationManager::class.java).cancel(NUDGE)
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
