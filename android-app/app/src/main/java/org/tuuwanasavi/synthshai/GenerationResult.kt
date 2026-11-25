package org.tuuwanasavi.synthshai

internal data class GenerationResult(
    val text: String, val reason: String, val loadMs: Long, val setupMs: Long,
    val promptMs: Long, val decodeMs: Long, val inputTokens: Int, val outputTokens: Int,
    val reused: Boolean
) {
    companion object {
        fun parse(bytes: ByteArray): GenerationResult {
            val raw = bytes.decodeToString()
            val boundary = raw.indexOf('\n')
            require(boundary in 1..256) { "Native result metadata unavailable." }
            val h = raw.substring(0, boundary).split('|')
            require(h.size == 9 && h[0] == "SHAI1" && h[1] in setOf("end", "limit", "stopped"))
            val times = h.subList(2, 6).map { it.toLong().also { n -> require(n >= 0) } }
            val input = h[6].toInt().also { require(it in 1..928) }
            val output = h[7].toInt().also { require(it in 0..96) }
            require(h[8] in setOf("0", "1"))
            return GenerationResult(raw.substring(boundary + 1), h[1], times[0], times[1], times[2], times[3], input, output, h[8] == "1")
        }
    }
}

internal data class ContinuedAnswer(val prompt: String, val label: String?, val text: String, val chunks: Int) {
    fun nextPrompt(): String {
        require(chunks in 1..2) { "Continuation limit reached; ask a shorter question." }
        return prompt + text.replace("<|", "< |")
    }
}
