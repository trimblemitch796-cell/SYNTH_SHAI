package org.tuuwanasavi.synthshai

/**
 * Offline, scripted Linux terminal companion to the Android demo.
 *
 * All replies come from the very same OfflineReplies.kt built into Android.
 * No model, network requests, accounts, audio, execution tools or automation.
 */
fun main() {
    println("SYNTH_SHAI Linux Offline CLI V0.2.3 | research demonstration | 144 HOLD")
    println("Type a message, or /exit to quit. Try: practice Vietnamese; practice tones.")
    var previous = OfflineReplies.Reply("", OfflineReplies.Topic.NONE)
    while (true) {
        val input = readLine() ?: break
        if (input.trim().equals("/exit", ignoreCase = true)) break
        if (input.isBlank()) continue
        val reply = OfflineReplies.reply(input, previous)
        previous = reply
        println("SHAI: " + reply.message)
    }
}
