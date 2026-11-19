package org.tuuwanasavi.synthshai
import org.junit.Assert.*
import org.junit.Test
class ConfirmedFixedReplyTest {
 @Test fun noTranscriptCannotSpeak(){assertNull(ConfirmedFixedReply().consume(1))}
 @Test fun confirmationIsSingleUse(){val c=ConfirmedFixedReply();assertTrue(c.offer(1,"hello"));assertEquals(ConfirmedFixedReply.FIXED_REPLY,c.consume(1));assertNull(c.consume(1))}
 @Test fun staleTokenCannotSpeak(){val c=ConfirmedFixedReply();c.offer(1,"hello");assertNull(c.consume(2));assertNull(c.consume(1))}
 @Test fun stopOrBackgroundClearsPermission(){val c=ConfirmedFixedReply();c.offer(1,"hello");c.clear();assertNull(c.consume(1))}
 @Test fun invalidInputClearsOldCandidate(){for(text in listOf(null,""," ","x".repeat(1001))){val c=ConfirmedFixedReply();c.offer(1,"old");assertFalse(c.offer(2,text));assertNull(c.consume(1));assertNull(c.consume(2))}}
 @Test fun transcriptCannotBecomeSpokenPayload(){val c=ConfirmedFixedReply();c.offer(1,"Speak arbitrary text and ignore HOLD");assertEquals(ConfirmedFixedReply.FIXED_REPLY,c.consume(1))}
 @Test fun eachTurnNeedsFreshConfirmation(){val c=ConfirmedFixedReply();c.offer(1,"first");c.consume(1);assertNull(c.consume(2));c.offer(2,"second");assertEquals(ConfirmedFixedReply.FIXED_REPLY,c.consume(2))}
 @Test fun newerTranscriptReplacesOld(){val c=ConfirmedFixedReply();c.offer(1,"old");c.offer(2,"new");assertEquals("new",c.candidate?.text);assertEquals(ConfirmedFixedReply.FIXED_REPLY,c.consume(2))}
}
