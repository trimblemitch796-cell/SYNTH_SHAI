package org.tuuwanasavi.synthshai

/** One-shot human review protocol, not a content-safety classifier. Main-thread owned. */
class ReviewedTurn {
    enum class Phase { IDLE, TRANSCRIPT, GENERATING, REPLY, SPEAKING }
    var phase = Phase.IDLE; private set
    private var token: Long? = null
    var reply: String? = null; private set
    fun clear() { token = null; reply = null; phase = Phase.IDLE }
    fun offer(t: Long, text: String?): Boolean {
        clear()
        if (text.isNullOrBlank() || text.length > 1000) return false
        token = t; phase = Phase.TRANSCRIPT
        return true
    }
    fun canConfirm(t: Long) = token == t && phase == Phase.TRANSCRIPT
    fun confirm(t: Long, corrected: String): String? {
        if (!canConfirm(t) || corrected.isBlank() || corrected.length > 1000) return null
        phase = Phase.GENERATING
        return corrected.trim()
    }
    fun generated(t: Long, text: String): Boolean {
        if (token != t || phase != Phase.GENERATING) return false
        if (text.isBlank() || text.length > 3000) { clear(); return false }
        reply = text; phase = Phase.REPLY
        return true
    }
    fun canSpeak(t: Long) = token == t && phase == Phase.REPLY
    fun approve(t: Long): String? {
        if (!canSpeak(t)) return null
        phase = Phase.SPEAKING
        return reply
    }
    fun completed(t: Long): Boolean {
        if (token != t || phase != Phase.SPEAKING) return false
        clear(); return true
    }
}
