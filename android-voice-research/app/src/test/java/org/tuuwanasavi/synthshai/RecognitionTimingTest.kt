package org.tuuwanasavi.synthshai
import org.junit.Assert.*
import org.junit.Test
class RecognitionTimingTest {
 @Test fun reproducesReportedTimingWithoutClaimingSpeechDuration(){val t=RecognitionTiming();t.ready(395);t.beginning(5505);val s=t.terminal(5521);assertTrue(s.contains("5110 ms"));assertTrue(s.contains("16 ms"));assertTrue(s.contains("manual finish requested: false"));assertTrue(s.contains("not proof"))}
 @Test fun cannotFinishBeforeReady(){val t=RecognitionTiming();assertFalse(t.requestFinish(10))}
 @Test fun finishOnlyOnceAndNeverAfterTerminal(){val t=RecognitionTiming();t.ready(10);assertTrue(t.requestFinish(20));assertFalse(t.requestFinish(21));assertTrue(t.terminal(30).contains("requested: true"));assertFalse(t.requestFinish(40))}
 @Test fun noBeginningCallbackRemainsUnknown(){val t=RecognitionTiming();t.ready(5);assertTrue(t.terminal(20).contains("beginning callback: unknown"))}
 @Test fun cancelledSessionCannotFinish(){val t=RecognitionTiming();t.ready(10);t.cancel();assertFalse(t.requestFinish(20))}
 @Test fun resetDoesNotCarryOldFinishIntoNextSession(){val t=RecognitionTiming();t.ready(10);t.requestFinish(20);t.reset();t.ready(100);assertTrue(t.terminal(200).contains("requested: false"))}
 @Test fun duplicateReadyDoesNotRewriteTiming(){val t=RecognitionTiming();t.ready(10);t.ready(20);t.beginning(30);assertTrue(t.terminal(40).contains("20 ms"))}
}
