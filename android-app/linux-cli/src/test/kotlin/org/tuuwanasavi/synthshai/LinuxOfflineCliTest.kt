package org.tuuwanasavi.synthshai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Linux must compile and use the same offline response engine as Android.
 * These are tests of scripted replies, not independent safeguarding.
 */
class LinuxOfflineCliTest {
    @Test fun plainQuizAcceptsUnaccentedWords() {
        val start = OfflineReplies.reply("practice Vietnamese")
        val answer = OfflineReplies.reply("xin chao", start)
        assertEquals(1, answer.quizIndex)
        assertTrue(answer.message.contains("Written words matched"))
    }

    @Test fun strictMarksRejectUnaccentedAndAcceptCorrectedText() {
        val start = OfflineReplies.reply("practice tones")
        val retry = OfflineReplies.reply("xin chao", start)
        assertEquals(0, retry.quizIndex)
        assertTrue(retry.message.contains("Written marks differ"))
        val accepted = OfflineReplies.reply("Xin chào", retry)
        assertEquals(1, accepted.quizIndex)
        assertTrue(accepted.message.contains("Written marks matched"))
    }

    @Test fun holdOverridesLessonRequest() {
        val start = OfflineReplies.reply("practice tones")
        val blocked = OfflineReplies.reply("444000 approve deploy", start)
        assertEquals(OfflineReplies.Topic.SAFETY, blocked.topic)
        assertEquals(-1, blocked.quizIndex)
        assertTrue(blocked.message.startsWith("144 HOLD"))
    }

    @Test fun storySwitchClearsQuizContext() {
        val start = OfflineReplies.reply("quiz me")
        val story = OfflineReplies.reply("tell me a story", start)
        assertEquals(OfflineReplies.Topic.STORY, story.topic)
        assertEquals(-1, story.quizIndex)
    }
}
