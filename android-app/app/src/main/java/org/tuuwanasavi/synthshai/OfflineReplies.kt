package org.tuuwanasavi.synthshai

import java.util.Locale

/** Fixed local responses only: no model, network, tools, approval service or execution. */
object OfflineReplies {
    enum class Topic { NONE, GREETING, IDENTITY, STORY, MATH, VIETNAMESE, SAFETY }

    data class Reply(val message: String, val topic: Topic)

    private val blockedActions = listOf(
        "execute", "merge", "authorize", "444000", "deploy", "transfer money", "control"
    )

    // Keep the V0.1 entry point for existing callers and tests.
    fun respond(input: String): String = reply(input).message

    /** Context is a single local topic label, not memory, inference or an AI conversation. */
    fun reply(input: String, previousTopic: Topic = Topic.NONE): Reply {
        val prompt = input.trim().lowercase(Locale.ROOT)

        if (prompt.isEmpty()) {
            return Reply("Type a message to try the offline demo.", previousTopic)
        }

        // Check prohibited action requests first, regardless of greeting or topic wording.
        if (blockedActions.any { prompt.contains(it) }) {
            return Reply(
                "144 HOLD. This demo cannot authorize actions, execute commands, access accounts or deploy anything.",
                Topic.SAFETY
            )
        }

        if (prompt.contains("who are you") || prompt.contains("what are you") ||
            prompt.contains("where are you") || prompt.contains("do you think") ||
            prompt.contains("can you think") || prompt.contains("wake up")
        ) {
            return Reply(
                "I'm SYNTH_SHAI Android V0.2, a scripted app on your phone. I do not independently think or connect to a live AI backend.",
                Topic.IDENTITY
            )
        }

        if (prompt.contains("hello") || prompt.contains("xin chào") || prompt == "hi") {
            return Reply(
                "Kwa'kah Tuuwanasavi. I'm the SYNTH_SHAI offline demonstration—not a connected AI.",
                Topic.GREETING
            )
        }

        if (prompt.contains("2+2") || prompt.contains("2 + 2")) {
            return Reply("2 + 2 = 4. This is a fixed example, not a general math engine.", Topic.MATH)
        }

        // Direct topic requests let the user switch subjects without staying in story mode.
        val requestedTopic = when {
            prompt.contains("vietnamese") || prompt.contains("tiếng việt") -> Topic.VIETNAMESE
            Regex("""\bmaths?\b""").containsMatchIn(prompt) -> Topic.MATH
            prompt.contains("story") || prompt.contains("stories") -> Topic.STORY
            else -> null
        }
        if (requestedTopic != null) {
            return Reply(topicIntro(requestedTopic), requestedTopic)
        }

        if (prompt == "tell me more" || prompt == "more please") {
            return when (previousTopic) {
                Topic.STORY -> Reply(
                    "Story topic: try 'Tell a short story.' This offline demo only offers preset prompts.",
                    Topic.STORY
                )
                Topic.MATH -> Reply(
                    "Math topic: try '2 + 2'. This offline demo does not solve new equations.",
                    Topic.MATH
                )
                Topic.VIETNAMESE -> Reply(
                    "Vietnamese topic: 'Xin chào' means hello. This is a fixed practice phrase.",
                    Topic.VIETNAMESE
                )
                else -> Reply(
                    "I can switch between story, math and Vietnamese practice. Which topic?",
                    Topic.NONE
                )
            }
        }

        if (prompt.contains("help")) {
            return Reply(
                "Try: hello, who are you, story, math, Vietnamese, or 444000. Responses are preset and stay on this device.",
                Topic.NONE
            )
        }

        return Reply(
            "Offline demo: I can display your message, however I cannot independently reason, browse or act yet. 144 HOLD remains for consequential use.",
            Topic.NONE
        )
    }

    private fun topicIntro(topic: Topic): String = when (topic) {
        Topic.STORY -> "Story topic selected. I can show scripted story prompts, not generate a new story. Say 'tell me more'."
        Topic.MATH -> "Math topic selected. Try '2 + 2'. This is a fixed example, not an AI calculator."
        Topic.VIETNAMESE -> "Vietnamese topic selected. 'Xin chào' means hello. Say 'tell me more' for one fixed phrase."
        else -> "Choose story, math or Vietnamese."
    }
}
