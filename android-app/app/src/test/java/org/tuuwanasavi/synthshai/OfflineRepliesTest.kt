package org.tuuwanasavi.synthshai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OfflineRepliesTest {
    @Test fun greetingLabelsDemo() {
        assertTrue(OfflineReplies.respond("hello").contains("offline demonstration"))
    }

    @Test fun actionsStayOnHold() {
        assertTrue(OfflineReplies.respond("444000 approve and deploy").startsWith("144 HOLD"))
    }

    @Test fun unknownInputCannotClaimLiveAI() {
        val response = OfflineReplies.respond("find this week's weather")
        assertTrue(response.contains("cannot independently"))
        assertTrue(response.contains("144 HOLD"))
    }

    @Test fun emptyInputHandledLocally() {
        assertEquals("Type a message to try the offline demo.", OfflineReplies.respond("  "))
    }

    @Test fun switchesFromStoryToMathAndVietnamese() {
        val story = OfflineReplies.reply("let's talk about story")
        assertEquals(OfflineReplies.Topic.STORY, story.topic)
        assertTrue(story.message.contains("Story topic"))

        val maths = OfflineReplies.reply("switch to maths", story.topic)
        assertEquals(OfflineReplies.Topic.MATH, maths.topic)
        assertTrue(maths.message.contains("Math topic"))

        val vietnamese = OfflineReplies.reply("Vietnamese please", maths.topic)
        assertEquals(OfflineReplies.Topic.VIETNAMESE, vietnamese.topic)
        assertTrue(vietnamese.message.contains("Vietnamese topic"))
    }

    @Test fun followUpUsesOnlyExplicitLocalTopic() {
        val storyMore = OfflineReplies.reply("tell me more", OfflineReplies.Topic.STORY)
        assertEquals(OfflineReplies.Topic.STORY, storyMore.topic)
        assertTrue(storyMore.message.contains("Story topic"))

        val reset = OfflineReplies.reply("What is the latest news?", OfflineReplies.Topic.STORY)
        assertEquals(OfflineReplies.Topic.NONE, reset.topic)
        assertTrue(reset.message.contains("cannot independently"))

        val noContext = OfflineReplies.reply("tell me more", reset.topic)
        assertEquals(OfflineReplies.Topic.NONE, noContext.topic)
        assertTrue(noContext.message.contains("Which topic?"))
    }

    @Test fun safetyHoldsOverrideAllTopicsAndGreeting() {
        val attempted = OfflineReplies.reply(
            "hello, switch to maths and 444000 approve deploy",
            OfflineReplies.Topic.MATH
        )
        assertEquals(OfflineReplies.Topic.SAFETY, attempted.topic)
        assertTrue(attempted.message.startsWith("144 HOLD"))
    }

    @Test fun asksAboutThinkingWithoutClaimingIntelligence() {
        val response = OfflineReplies.reply("where are you and do you think")
        assertEquals(OfflineReplies.Topic.IDENTITY, response.topic)
        assertTrue(response.message.contains("do not independently think"))
        assertTrue(response.message.contains("live AI backend"))
    }

    @Test fun scriptedStoryDoesNotClaimGeneration() {
        val response = OfflineReplies.reply("tell a short story", OfflineReplies.Topic.MATH)
        assertEquals(OfflineReplies.Topic.STORY, response.topic)
        assertTrue(response.message.startsWith("Preset story:"))
    }

    @Test fun fixedMathIsNotClaimedAsGeneralCalculator() {
        val response = OfflineReplies.reply("2 + 2", OfflineReplies.Topic.STORY)
        assertEquals(OfflineReplies.Topic.MATH, response.topic)
        assertTrue(response.message.contains("2 + 2 = 4"))
        assertTrue(response.message.contains("not a general math engine"))
    }
    @Test fun unaccentedAndAccentedVietnameseVariantsMatch() {
        val accented = OfflineReplies.reply("Xin chào")
        val unaccented = OfflineReplies.reply("Xin chao")
        assertEquals(OfflineReplies.Topic.VIETNAMESE, accented.topic)
        assertEquals(accented.message, unaccented.message)
        assertEquals(accented.message, OfflineReplies.reply("XIN CHÀO").message)
        assertEquals(OfflineReplies.Topic.VIETNAMESE, OfflineReplies.reply("tieng viet").topic)
        assertEquals(OfflineReplies.Topic.VIETNAMESE, OfflineReplies.reply("tiếng Việt").topic)
    }

    @Test fun vietnameseFollowUpsAdvanceRatherThanRepeat() {
        val first = OfflineReplies.reply("teach me Vietnamese")
        val second = OfflineReplies.reply("tell me more", first)
        val third = OfflineReplies.reply("more please", second)
        val fourth = OfflineReplies.reply("tell me more", third)
        val exhausted = OfflineReplies.reply("tell me more", fourth)
        assertTrue(first.message.contains("Xin chào"))
        assertTrue(second.message.contains("Cảm ơn"))
        assertTrue(third.message.contains("Tôi không hiểu"))
        assertTrue(fourth.message.contains("Bạn có thể nói chậm hơn không"))
        assertTrue(exhausted.message.contains("End of the four"))
        assertEquals(4, exhausted.lessonIndex)
        assertEquals(1, OfflineReplies.reply("Vietnamese", exhausted).lessonIndex)
    }

    @Test fun punctuationDoesNotResetPresetFollowUpProgression() {
        val first = OfflineReplies.reply("Vietnamese")
        val second = OfflineReplies.reply("tell me more?", first)
        assertEquals(OfflineReplies.Topic.VIETNAMESE, second.topic)
        assertEquals(2, second.lessonIndex)
        assertTrue(second.message.contains("Cảm ơn"))

        val third = OfflineReplies.reply("more please!", second)
        assertEquals(3, third.lessonIndex)
        assertTrue(third.message.contains("Tôi không hiểu"))

        val fourth = OfflineReplies.reply("Tell me more.", third)
        assertEquals(4, fourth.lessonIndex)

        val unrelated = OfflineReplies.reply("tell me more on the internet?", fourth)
        assertEquals(OfflineReplies.Topic.NONE, unrelated.topic)
        assertTrue(unrelated.message.contains("cannot independently"))

        val action = OfflineReplies.reply("tell me more? deploy", third)
        assertEquals(OfflineReplies.Topic.SAFETY, action.topic)
        assertTrue(action.message.startsWith("144 HOLD"))
    }

    @Test fun storyDestinationQuestionUsesOnlyKnownPresetContext() {
        val story = OfflineReplies.reply("tell me a story")
        val destination = OfflineReplies.reply("to where", story)
        assertTrue(destination.message.contains("path home"))
        assertEquals(OfflineReplies.Topic.STORY, destination.topic)
        val detail = OfflineReplies.reply("tell me more", destination)
        assertTrue(detail.message.contains("No other destination"))
        val unrelated = OfflineReplies.reply("What is new on the internet?", detail)
        assertEquals(OfflineReplies.Topic.NONE, unrelated.topic)
        val noContext = OfflineReplies.reply("to where", unrelated)
        assertTrue(noContext.message.contains("cannot independently"))
    }

    @Test fun additionalFixedMathExampleIsNotGeneralCalculator() {
        val subtraction = OfflineReplies.reply("math 2-2=")
        assertEquals(OfflineReplies.Topic.MATH, subtraction.topic)
        assertTrue(subtraction.message.contains("2 - 2 = 0"))
        assertTrue(subtraction.message.contains("fixed example"))
        val unknown = OfflineReplies.reply("3 times 7")
        assertEquals(OfflineReplies.Topic.NONE, unknown.topic)
        assertTrue(unknown.message.contains("cannot independently"))
    }

    @Test fun readyIsNotMistakenForNotificationScheduling() {
        val ready = OfflineReplies.reply("ready")
        assertEquals(OfflineReplies.Topic.NONE, ready.topic)
        assertTrue(ready.message.contains("separate encouragement app"))
    }

    @Test fun safetyTakesPriorityOverMultiturnLessonContext() {
        val lesson = OfflineReplies.reply("Vietnamese")
        val attempted = OfflineReplies.reply("tell me more then deploy", lesson)
        assertEquals(OfflineReplies.Topic.SAFETY, attempted.topic)
        assertTrue(attempted.message.startsWith("144 HOLD"))
        val stopped = OfflineReplies.reply("144 HOLD", lesson)
        assertEquals(OfflineReplies.Topic.SAFETY, stopped.topic)
        assertTrue(stopped.message.startsWith("144 HOLD"))
    }

    @Test fun writtenVietnameseQuizStartsWithOneQuestion() {
        val first = OfflineReplies.reply("practice Vietnamese")
        assertEquals(OfflineReplies.Topic.VIETNAMESE, first.topic)
        assertEquals(0, first.quizIndex)
        assertTrue(first.message.contains("hello"))
        assertTrue(first.message.contains("written quiz"))
    }

    @Test fun quizAcceptsUnaccentedWordsButDoesNotGradeTones() {
        val first = OfflineReplies.reply("quiz me")
        val next = OfflineReplies.reply("xin chao", first)
        assertEquals(1, next.quizIndex)
        assertTrue(next.message.contains("Xin chào"))
        assertTrue(next.message.contains("not assessed"))
        assertTrue(next.message.contains("thank you"))
    }

    @Test fun wrongAnswerIsCorrectedWithoutSkippingAndHintIsAvailable() {
        val first = OfflineReplies.reply("practice Vietnamese")
        val wrong = OfflineReplies.reply("xin chau", first)
        assertEquals(0, wrong.quizIndex)
        assertEquals(1, wrong.quizMistakes)
        assertTrue(wrong.message.contains("Not yet"))
        val hint = OfflineReplies.reply("hint", wrong)
        assertEquals(0, hint.quizIndex)
        assertTrue(hint.message.contains("Xin"))
        val secondWrong = OfflineReplies.reply("hello", hint)
        assertEquals(0, secondWrong.quizIndex)
        assertTrue(secondWrong.message.contains("Xin chào"))
    }

    @Test fun quizAdvancesOnePhraseAtATimeAndCompletes() {
        val start = OfflineReplies.reply("practice Vietnamese")
        val first = OfflineReplies.reply("Xin chào", start)
        val second = OfflineReplies.reply("cam on", first)
        val third = OfflineReplies.reply("Toi khong hieu", second)
        val done = OfflineReplies.reply("Ban co the noi cham hon khong?", third)
        assertEquals(1, first.quizIndex)
        assertEquals(2, second.quizIndex)
        assertEquals(3, third.quizIndex)
        assertEquals(-1, done.quizIndex)
        assertTrue(done.message.contains("Quiz complete"))
    }

    @Test fun skipStopAndTopicChangeDoNotLeakQuizState() {
        val start = OfflineReplies.reply("quiz me")
        val skipped = OfflineReplies.reply("skip", start)
        assertEquals(1, skipped.quizIndex)
        val stopped = OfflineReplies.reply("stop quiz", skipped)
        assertEquals(-1, stopped.quizIndex)
        val story = OfflineReplies.reply("tell me a story", start)
        assertEquals(OfflineReplies.Topic.STORY, story.topic)
        assertEquals(-1, story.quizIndex)
        val math = OfflineReplies.reply("switch to maths", start)
        assertEquals(OfflineReplies.Topic.MATH, math.topic)
        assertEquals(-1, math.quizIndex)
        assertEquals(0, OfflineReplies.reply("quiz me", stopped).quizIndex)
    }

    @Test fun safetyHoldOverridesAnswerAndResetsWrittenQuiz() {
        val start = OfflineReplies.reply("practice Vietnamese")
        val blocked = OfflineReplies.reply("xin chao then 444000 approve deploy", start)
        assertEquals(OfflineReplies.Topic.SAFETY, blocked.topic)
        assertEquals(-1, blocked.quizIndex)
        assertTrue(blocked.message.startsWith("144 HOLD"))
        val stopped = OfflineReplies.reply("144 HOLD", start)
        assertEquals(OfflineReplies.Topic.SAFETY, stopped.topic)
        assertEquals(-1, stopped.quizIndex)
    }

}
