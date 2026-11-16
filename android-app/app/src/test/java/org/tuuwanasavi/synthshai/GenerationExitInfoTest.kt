package org.tuuwanasavi.synthshai
import android.app.ApplicationExitInfo
import org.junit.Assert.*
import org.junit.Test
class GenerationExitInfoTest {
    @Test fun lowMemoryIsNotConfusedWithNativeCrash() {
        assertTrue(generationExitMessage(ApplicationExitInfo.REASON_LOW_MEMORY).contains("low memory"))
        assertTrue(generationExitMessage(ApplicationExitInfo.REASON_CRASH_NATIVE).contains("native-engine crash"))
        assertFalse(generationExitMessage(ApplicationExitInfo.REASON_CRASH_NATIVE).contains("low memory"))
    }
    @Test fun unknownDoesNotInventCause() {
        assertTrue(generationExitMessage(null).contains("did not provide a specific cause"))
        assertTrue(generationExitMessage(999).contains("did not provide a specific cause"))
    }
    @Test fun userStopDoesNotClaimEngineCrash() {
        assertTrue(generationExitMessage(ApplicationExitInfo.REASON_USER_REQUESTED).contains("app was stopped"))
    }
}
