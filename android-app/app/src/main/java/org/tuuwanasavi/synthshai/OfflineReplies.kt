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
        val storyTold: Boolean = false,
        val quizIndex: Int = -1,
        val quizMistakes: Int = 0,
        val strictMarks: Boolean = false
    )

    /** Four bounded written-word checks; these are examples, not a language model. */
    private data class Phrase(val english: String, val vietnamese: String, val hint: String)
    private val quizPhrases = listOf(
        Phrase("hello", "Xin chào", "first word is 'Xin'"),
        Phrase("thank you", "Cảm ơn", "first word is 'Cảm'"),
        Phrase("I don't understand", "Tôi không hiểu", "first word is 'Tôi'"),
        Phrase("Can you speak more slowly?", "Bạn có thể nói chậm hơn không?", "first word is 'Bạn'")
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
                "I'm SYNTH_SHAI Android V0.2.3, a scripted app on your phone. I do not independently think or connect to a live AI backend.",
                Topic.IDENTITY
            )
        }

        // The 144 HOLD check and explicit identity checks precede all tutoring.
        val quizResponse = handleQuiz(prompt, previous, input)
        if (quizResponse != null) return quizResponse

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
            Regex("""\b(?:story|stories)\b""").containsMatchIn(prompt) -> Topic.STORY
            else -> null
        }
        if (requestedTopic != null) {
            return when (requestedTopic) {
                Topic.VIETNAMESE -> Reply(
                    "Vietnamese topic selected. 'Xin chào' means hello. Say 'tell me more' for the next phrase, 'practice Vietnamese' for the easy quiz, or 'practice tones' to check written marks.",
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

    /**
     * Opt-in modes: beginner word matching or exact preset written-mark matching.
     * Neither mode can evaluate pronunciation or arbitrary Vietnamese grammar.
     */
    private fun handleQuiz(prompt: String, previous: Reply, rawInput: String): Reply? {
        // Strict written-mark checking is opt-in; keep the familiar accent-tolerant quiz.
        if (prompt == "practice tones" || prompt == "tone quiz" ||
            prompt == "practice vietnamese tones" || prompt == "check tone marks"
        ) return quizQuestion(0, strictMarks = true)
        if (prompt == "practice vietnamese" || prompt == "quiz me" ||
            prompt == "vietnamese quiz" || prompt == "test my vietnamese"
        ) return quizQuestion(0, strictMarks = false)

        val index = previous.quizIndex
        if (index !in quizPhrases.indices) return null

        if (prompt == "stop quiz" || prompt == "stop practice" || prompt == "stop lesson") {
            return Reply("Written Vietnamese quiz stopped. Say 'practice Vietnamese' to restart.", Topic.VIETNAMESE)
        }

        // Clear the quiz on explicit topic switches, never grade an unrelated topic request.
        if (prompt == "story" || prompt == "math" || prompt == "maths" ||
            prompt == "vietnamese" || prompt == "tell me a story" ||
            prompt == "tell a short story" || prompt.startsWith("switch to ")
        ) return null

        val phrase = quizPhrases[index]
        if (prompt == "hint") return previous.copy(
            message = "Hint for '" + phrase.english + "': " + phrase.hint + ". Type the Vietnamese phrase or 'skip'."
        )
        if (prompt == "repeat" || prompt == "repeat question") return previous.copy(
            message = quizQuestionText(index, previous.strictMarks)
        )
        if (prompt == "skip") return nextQuizQuestion(
            index,
            "Skipped. Standard Vietnamese: '" + phrase.vietnamese + "'.",
            previous.strictMarks
        )

        val answer = prompt.trimEnd { it == '?' || it == '!' || it == '.' || it == ' ' }
        val expected = normalize(phrase.vietnamese).trimEnd { it == '?' || it == '!' || it == '.' || it == ' ' }
        if (previous.strictMarks) {
            // Compare NFC-normalized *written* diacritics, without changing the
            // beginner quiz's accent-tolerant vocabulary matching.
            val writtenAnswer = Normalizer.normalize(rawInput.trim().lowercase(Locale.ROOT), Normalizer.Form.NFC)
                .replace(Regex("""\s+"""), " ")
                .trimEnd { it == '?' || it == '!' || it == '.' || it == ' ' }
            val writtenExpected = Normalizer.normalize(
                phrase.vietnamese.lowercase(Locale.ROOT), Normalizer.Form.NFC
            ).trimEnd { it == '?' || it == '!' || it == '.' || it == ' ' }

            if (writtenAnswer == writtenExpected) return nextQuizQuestion(
                index,
                "Written marks matched the preset spelling: '" + phrase.vietnamese +
                    "'. This does not assess pronunciation.",
                strictMarks = true
            )
            if (answer == expected) return previous.copy(
                message = "Written marks differ. Standard spelling: '" + phrase.vietnamese +
                    "'. Check the accents and vowel letters, then retry. Spoken tones were not assessed.",
                quizMistakes = previous.quizMistakes + 1
            )
        } else if (answer == expected) return nextQuizQuestion(
            index,
            "Written words matched. Standard spelling: '" + phrase.vietnamese +
                "'. Tone marks and pronunciation were not assessed.",
            strictMarks = false
        )

        val correction = if (previous.quizMistakes == 0) {
            "Not yet. For '" + phrase.english + "', " + phrase.hint +
                ". Try again, say 'hint', or 'skip'."
        } else {
            "Still not a match. The preset answer is '" + phrase.vietnamese +
                "'. Type it or 'skip'."
        }
        return previous.copy(message = correction, quizMistakes = previous.quizMistakes + 1)
    }

    private fun quizQuestion(index: Int, strictMarks: Boolean): Reply =
        Reply(
            quizQuestionText(index, strictMarks),
            Topic.VIETNAMESE,
            quizIndex = index,
            strictMarks = strictMarks
        )

    private fun quizQuestionText(index: Int, strictMarks: Boolean): String =
        (if (strictMarks) "Vietnamese written marks " else "Vietnamese written quiz ") +
            (index + 1) + "/" + quizPhrases.size +
            ": Type the Vietnamese for '" + quizPhrases[index].english +
            "'. " + (if (strictMarks) "Include the exact written accents. " else "") +
            "Say 'hint', 'skip', or 'stop quiz'."

    private fun nextQuizQuestion(index: Int, feedback: String, strictMarks: Boolean): Reply {
        val nextIndex = index + 1
        return if (nextIndex >= quizPhrases.size) Reply(
            feedback + " Quiz complete: four fixed text prompts. This is not a pronunciation test. " +
                "Say '" + (if (strictMarks) "practice tones" else "practice Vietnamese") + "' to restart.",
            Topic.VIETNAMESE
        ) else Reply(
            feedback + " " + quizQuestionText(nextIndex, strictMarks),
            Topic.VIETNAMESE,
            quizIndex = nextIndex,
            strictMarks = strictMarks
        )
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
