package org.tuuwanasavi.synthshai

import java.util.Locale

/** Scripted responses only. No network, LLM, tool execution or approval backend. */
object OfflineReplies {
    fun respond(input: String): String {
        val prompt = input.trim().lowercase(Locale.ROOT)
        return when {
            prompt.isEmpty() -> "Type a message to try the offline demo."
            listOf("execute", "merge", "authorize", "444000", "deploy", "transfer money", "control").any {
                prompt.contains(it)
            } -> "144 HOLD. This demo cannot authorize actions, execute commands, access accounts or deploy anything."
            prompt.contains("hello") || prompt.contains("xin chào") || prompt == "hi" ->
                "Kwa'kah Tuuwanasavi. I'm the SYNTH_SHAI offline demonstration—not a connected AI."
            prompt.contains("who are you") || prompt.contains("what are you") ->
                "I'm SYNTH_SHAI Android V0.1, a scripted local chat demonstration. I have no AI model or live backend."
            prompt.contains("help") ->
                "Try: hello, who are you, or 444000. Responses are fixed and stay on this device."
            else ->
                "Offline demo: I can display your message, however I cannot independently reason, browse or act yet. 144 HOLD remains for consequential use."
        }
    }
}
