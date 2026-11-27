package org.tuuwanasavi.synthshai

/** Human confirmation authorizes only this fixed fixture, never model generation. */
class ConfirmedFixedReply {
    data class Candidate(val token: Long, val text: String)
    var candidate: Candidate? = null
        private set
    fun clear() { candidate = null }
    fun offer(token: Long, text: String?): Boolean {
        clear()
        if (text.isNullOrBlank() || text.length > 1000) return false
        candidate = Candidate(token, text)
        return true
    }
    fun consume(token: Long): String? {
        val pending = candidate ?: return null
        clear()
        return if (pending.token == token) FIXED_REPLY else null
    }
    companion object {
        const val FIXED_REPLY = "SYNTH SHAI speech output test. The garden is green."
    }
}
