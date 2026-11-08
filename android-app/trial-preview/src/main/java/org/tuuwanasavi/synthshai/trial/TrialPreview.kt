package org.tuuwanasavi.synthshai.trial

/** Synthetic gateway outcomes. This preview has no issuer, endpoint or network permission. */
enum class Sample(val label: String, val status: Int) {
    REPLY("Sample reply", 200),
    SESSION("Expired session", 401),
    LIMIT("Request limit", 429),
    CLOSED("Trial closed", 503)
}

fun displayOutcome(status: Int, reply: String?): String = when (status) {
    200 -> reply?.takeIf { it.isNotBlank() } ?: "Gateway response was empty."
    401 -> "Sign-in required. This session cannot send messages."
    429 -> "Request limit reached. Try again later."
    503 -> "Trial unavailable. Check the trial window and service status."
    else -> "Chat unavailable."
}
