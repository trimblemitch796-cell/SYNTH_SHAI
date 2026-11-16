package org.tuuwanasavi.synthshai

import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.os.Process

/** Stores only attempt time and process id, never conversation/model paths. */
internal fun previousGenerationExit(context: Context, prefs: SharedPreferences): String? {
    val started = prefs.getLong("generation_started", 0L)
    val pid = prefs.getInt("generation_pid", 0)
    if (started == 0L || pid == Process.myPid()) return null
    val reason = if (Build.VERSION.SDK_INT >= 30) runCatching {
        val manager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        manager.getHistoricalProcessExitReasons(null, pid, 5)
            .firstOrNull { it.timestamp >= started }?.reason
    }.getOrNull() else null
    prefs.edit().remove("generation_started").remove("generation_pid").apply()
    return generationExitMessage(reason)
}
internal fun generationExitMessage(reason: Int?): String = when (reason) {
    ApplicationExitInfo.REASON_LOW_MEMORY -> "Android reports the previous generation was stopped for low memory."
    ApplicationExitInfo.REASON_CRASH_NATIVE -> "Android reports a native-engine crash during the previous generation."
    ApplicationExitInfo.REASON_CRASH -> "Android reports an app crash during the previous generation."
    ApplicationExitInfo.REASON_ANR -> "Android reports the app stopped responding during the previous generation."
    ApplicationExitInfo.REASON_USER_REQUESTED, ApplicationExitInfo.REASON_USER_STOPPED -> "The previous generation was interrupted when the app was stopped."
    else -> "The previous generation was interrupted. Android did not provide a specific cause."
}
