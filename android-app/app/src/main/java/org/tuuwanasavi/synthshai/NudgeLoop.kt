package org.tuuwanasavi.synthshai

internal class NudgeLoop {
    companion object {
        const val WINDOW = 180_000L
        const val PERIOD = 300_000L

        fun isStop(text: String): Boolean =
            text.trim().lowercase().replace("’", "'") in setOf(
                "144hold", "144 hold", "stop", "i've started", "ive started", "iv started", "i have started"
            )
    }

    var lastNudge: Long? = null
        private set

    fun start(now: Long): Boolean {
        if (lastNudge != null) return false
        lastNudge = now
        return true
    }

    fun repeat(now: Long): Boolean {
        val previous = lastNudge ?: return false
        if (now - previous < PERIOD) return false
        lastNudge = now
        return true
    }

    fun stop() { lastNudge = null }
}
