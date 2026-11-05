package org.tuuwanasavi.synthshai

import org.junit.Assert.*
import org.junit.Test

class NudgeLoopTest {
    @Test fun optInTimingStopAndRestart() {
        val loop = NudgeLoop()
        assertFalse(loop.repeat(0))
        assertTrue(loop.start(0))
        assertFalse(loop.start(10))
        assertEquals(180000L, NudgeLoop.WINDOW)
        assertFalse(loop.repeat(299999))
        assertTrue(loop.repeat(300000))
        assertFalse(loop.repeat(300001))
        loop.stop()
        assertFalse(loop.repeat(600000))
        assertTrue(loop.start(700000))
    }

    @Test fun handlesRealStopPhrases() {
        for (text in listOf("144hold", " 144 HOLD ", "IV started", "I’ve started", "stop")) {
            assertTrue(text, NudgeLoop.isStop(text))
        }
        assertFalse(NudgeLoop.isStop("again"))
    }
}
