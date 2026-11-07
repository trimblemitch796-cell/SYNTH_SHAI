package org.tuuwanasavi.synthshai.trial

import org.junit.Assert.assertEquals
import org.junit.Test

class TrialPreviewTest {
    @Test fun successfulSampleDisplaysReply() {
        assertEquals("hello", displayOutcome(200, "hello"))
    }

    @Test fun malformedSuccessGetsError() {
        assertEquals("Gateway response was empty.", displayOutcome(200, " "))
    }

    @Test fun blockedResponsesNeverDisplayReply() {
        for (status in listOf(401, 429, 503, 500)) {
            check(displayOutcome(status, "private content") != "private content")
        }
    }
}
