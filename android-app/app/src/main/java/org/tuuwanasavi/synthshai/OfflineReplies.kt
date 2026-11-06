package org.tuuwanasavi.synthshai

import java.text.Normalizer
import java.util.Locale

/** Fixed local responses only: no model, network, tools, approval service or execution. */
object OfflineReplies {
    enum class Topic { NONE, GREETING, IDENTITY, STORY, MATH, VIETNAMESE, SAFETY }

    /** The extra fields describe only preset on-screen context; none is persisted. */
    data class Reply(
        val message: String,
        val topic: Topic,
        val lessonIndex: Int = 0,
        val storyTold: Boolean = false
    )

    private val blockedActions = listOf(
        "execute", "merge", "authorize", "444000", "deploy", "transfer money", "control"
    )

    private const val fallback =
        "Offline demo: I can display your message, however I cannot independently reason, browse or act yet. 144 HOLD remains for consequential use."

    private const val fixedStory =
        "Preset story: A little lantern lit the path home. Its light was small, however it helped everyone find their way."

    // Keep the V0.1/V0.2 entry points for existing callers and tests.
    fun respond(input: String): String = reply(input).message

    fun reply(input: String, previousTopic: Topic = Topic.NONE): Reply =
        reply(input, Reply("", previousTopic))

    /** Context consists only of the most recent preset reply, not a chat model. */
    fun reply(input: String, previous: Reply): Reply {
        val prompt = normalize(input)
        if (prompt.isEmpty()) {
            return previous.copy(message = "Type a message to try the offline demo.")
        }

        // Action requests take priority over all lessons, topics and follow-ups.
        if (blockedActions.any { prompt.contains(it) } || prompt.contains("144 hold")) {
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
                "I'm SYNTH_SHAI Android V0.2.1, a scripted app on your phone. I do not independently think or connect to a live AI backend.",
                Topic.IDENTITY
            )
        }

        // Both accented and unaccented Vietnamese input use the same fixed phrase.
        if (Regex("""\bxin\s+chao\b""").containsMatchIn(prompt)) {
            return Reply(
                "Vietnamese practice 1/4: 'Xin chào' means hello. Say 'tell me more' for the next preset phrase.",
                Topic.VIETNAMESE,
                lessonIndex = 1
            )
        }

        if (prompt.contains("hello") || prompt == "hi") {
            return Reply(
                "Kwa'kah Tuuwanasavi. I'm the SYNTH_SHAI offline demonstration—not a connected AI.",
                Topic.GREETING
            )
        }

        if (prompt.contains("tell a short story") || prompt.contains("tell me a story")) {
            return Reply(fixedStory, Topic.STORY, storyTold = true)
        }

        // Exact, scripted examples; this is not a general arithmetic evaluator.
        if (Regex("""(?<!\d)2\s*\+\s*2(?!\d)""").containsMatchIn(prompt)) {
            return Reply("2 + 2 = 4. This is a fixed example, not a general math engine.", Topic.MATH)
        }
        if (Regex("""(?<!\d)2\s*-\s*2(?!\d)""").containsMatchIn(prompt)) {
            return Reply("2 - 2 = 0. This is a fixed example, not a general math engine.", Topic.MATH)
        }

        val requestedTopic = when {
            prompt.contains("vietnamese") || prompt.contains("tieng viet") -> Topic.VIETNAMESE
            Regex("""\bmaths?\b""").containsMatchIn(prompt) -> Topic.MATH
            prompt.contains("story") || prompt.contains("stories") -> Topic.STORY
            else -> null
        }
        if (requestedTopic != null) {
            return when (requestedTopic) {
                Topic.VIETNAMESE -> Reply(
                    "Vietnamese topic selected. 'Xin chào' means hello. Say 'tell me more' for the next preset phrase.",
                    Topic.VIETNAMESE,
                    lessonIndex = 1
                )
                Topic.MATH -> Reply(
                    "Math topic selected. Try '2 + 2' or '2 - 2'. These are fixed examples, not an AI calculator.",
                    Topic.MATH
                )
                Topic.STORY -> Reply(
                    "Story topic selected. Say 'tell me a story' for the preset lantern story.",
                    Topic.STORY
                )
                else -> Reply("Choose story, math or Vietnamese.", Topic.NONE)
            }
        }

        // Ignore optional sentence-ending punctuation for the two fixed follow-ups.
        val followUp = prompt.trimEnd { it == '?' || it == '!' || it == '.' || it == ' ' }
        if (followUp == "tell me more" || followUp == "more please") {
            return when (previous.topic) {
                Topic.STORY -> if (previous.storyTold) {
                    Reply(
                        "Story detail: The lantern lit the path home. No other destination was specified in the preset story.",
                        Topic.STORY,
                        storyTold = true
                    )
                } else {
                    Reply("Story topic: try 'Tell a short story.' This offline demo only offers preset prompts.", Topic.STORY)
                }
                Topic.MATH -> Reply(
                    "Math topic: try '2 + 2' or '2 - 2'. I cannot solve new equations.",
                    Topic.MATH
                )
                Topic.VIETNAMESE -> nextVietnamese(previous.lessonIndex)
                else -> Reply(
                    "I can switch between story, math and Vietnamese practice. Which topic?",
                    Topic.NONE
                )
            }
        }

        if (previous.topic == Topic.STORY && previous.storyTold &&
            (prompt == "to where" || prompt == "to where?" ||
                prompt == "where did they go" || prompt == "where did they go?" ||
                prompt == "where did the lantern lead" || prompt == "where did the lantern lead?")
        ) {
            return Reply(
                "In the preset story, the lantern lit the path home. No other destination was stated.",
                Topic.STORY,
                storyTold = true
            )
        }

        if (prompt == "ready") {
            return Reply(
                "Ready. This is the scripted offline chat, not the separate encouragement app. Try 'story', 'math' or 'Vietnamese'.",
                Topic.NONE
            )
        }

        if (prompt.contains("help")) {
            return Reply(
                "Try: hello, who are you, story, math, Vietnamese, or 444000. Responses are preset and stay on this device.",
                Topic.NONE
            )
        }

        // An unrelated question clears topic context; do not invent follow-up meaning.
        return Reply(fallback, Topic.NONE)
    }

    private fun nextVietnamese(index: Int): Reply = when (index) {
        0 -> Reply("Vietnamese practice 1/4: 'Xin chào' means hello.", Topic.VIETNAMESE, lessonIndex = 1)
        1 -> Reply("Vietnamese practice 2/4: 'Cảm ơn' means thank you.", Topic.VIETNAMESE, lessonIndex = 2)
        2 -> Reply("Vietnamese practice 3/4: 'Tôi không hiểu' means I don't understand.", Topic.VIETNAMESE, lessonIndex = 3)
        3 -> Reply(
            "Vietnamese practice 4/4: 'Bạn có thể nói chậm hơn không?' means Can you speak more slowly?",
            Topic.VIETNAMESE,
            lessonIndex = 4
        )
        else -> Reply(
            "End of the four preset Vietnamese phrases. Say 'Vietnamese' to restart.",
            Topic.VIETNAMESE,
            lessonIndex = 4
        )
    }

    /** Accent-tolerant matching only; this does not translate arbitrary text. */
    private fun normalize(input: String): String =
        Normalizer.normalize(input.trim().lowercase(Locale.ROOT).replace('đ', 'd'), Normalizer.Form.NFD)
            .replace(Regex("""\p{Mn}+"""), "")
            .replace(Regex("""\s+"""), " ")
}
