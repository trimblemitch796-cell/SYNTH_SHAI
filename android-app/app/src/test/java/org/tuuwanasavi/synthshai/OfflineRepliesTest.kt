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

    @Test fun fixedMathIsNotClaimedAsGeneralCalculator() {
        val response = OfflineReplies.reply("2 + 2", OfflineReplies.Topic.STORY)
        assertEquals(OfflineReplies.Topic.MATH, response.topic)
        assertTrue(response.message.contains("2 + 2 = 4"))
        assertTrue(response.message.contains("not a general math engine"))
    }
}
