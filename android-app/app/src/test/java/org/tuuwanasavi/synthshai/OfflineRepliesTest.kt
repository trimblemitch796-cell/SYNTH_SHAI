package org.tuuwanasavi.synthshai

import org.junit.Assert.assertTrue
import org.junit.Assert.assertEquals
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
}
