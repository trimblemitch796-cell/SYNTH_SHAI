package org.tuuwanasavi.synthshai
import org.junit.Assert.*
import org.junit.Test
class VoiceLoopTest {
 class Ports:VoicePorts {val calls=mutableListOf<String>();override fun stopAll(){calls+="stop"};override fun listen(token:Long){calls+="listen"};override fun generate(token:Long,text:String){calls+="generate"};override fun speak(token:Long,text:String){calls+="speak"}}
 // Test-only protocol stimulus. This is NOT an installed safety policy or security proof.
 class SyntheticPolicy(val inputOK:Boolean=true,val outputOK:Boolean=true):VoicePolicy {override fun input(text:String)=inputOK;override fun output(text:String)=outputOK}
 fun ready(l:VoiceLoop):Long{val t=l.begin(true,true);l.checked(t,true);l.ready(t);return t}
 @Test fun doesNotInviteSpeechUntilReady(){val p=Ports();val l=VoiceLoop(p);val t=l.begin(true,true);l.checked(t,true);assertEquals(VoiceLoop.Phase.ARMING,l.phase);l.ready(t);assertEquals("Speak now",l.reason)}
 @Test fun noConsentOrBackgroundNeverListens(){for(v in listOf(false,true))for(c in listOf(false,true)){if(v&&c)continue;val p=Ports();val l=VoiceLoop(p);l.checked(l.begin(v,c),true);assertFalse(p.calls.contains("listen"))}}
 @Test fun unavailableSpeechHolds(){val l=VoiceLoop(Ports());val t=l.begin(true,true);l.checked(t,false);assertEquals(VoiceLoop.Phase.HOLD,l.phase)}
 @Test fun actualPolicyBlocksLiveModelDispatch(){val p=Ports();val l=VoiceLoop(p);val t=ready(l);l.transcript(t,"hello",1f);assertEquals(VoiceLoop.Phase.HOLD,l.phase);assertFalse(p.calls.contains("generate"));assertFalse(p.calls.contains("speak"))}
 @Test fun resultBeforeReadyFailsClosed(){val l=VoiceLoop(Ports());val t=l.begin(true,true);l.checked(t,true);l.transcript(t,"hello",1f);assertEquals(VoiceLoop.Phase.HOLD,l.phase)}
 @Test fun invalidConfidenceAndEmptyTextNeverGenerate(){for(c in listOf(null,Float.NaN,-1f,0.7f,1.1f)){val p=Ports();val l=VoiceLoop(p,SyntheticPolicy());val t=ready(l);l.transcript(t,"hello",c);assertFalse(p.calls.contains("generate"))};val p=Ports();val l=VoiceLoop(p,SyntheticPolicy());l.transcript(ready(l)," ",1f);assertFalse(p.calls.contains("generate"))}
 @Test fun syntheticProtocolTraversesLoopWithoutListeningDuringOutput(){val p=Ports();val l=VoiceLoop(p,SyntheticPolicy());val t=ready(l);l.transcript(t,"synthetic",1f);assertEquals(VoiceLoop.Phase.GENERATING,l.phase);l.generated(t,"synthetic output");assertEquals(VoiceLoop.Phase.SPEAKING,l.phase);assertEquals(listOf("stop","listen","generate","speak"),p.calls);l.spoken(t);assertEquals(VoiceLoop.Phase.ARMING,l.phase);assertEquals("listen",p.calls.last())}
 @Test fun outputHoldBlocksPlayback(){val p=Ports();val l=VoiceLoop(p,SyntheticPolicy(outputOK=false));val t=ready(l);l.transcript(t,"synthetic",1f);l.generated(t,"unchecked");assertFalse(p.calls.contains("speak"));assertEquals(VoiceLoop.Phase.HOLD,l.phase)}
 @Test fun stopDuringGenerationRejectsLateCompletion(){val p=Ports();val l=VoiceLoop(p,SyntheticPolicy());val t=ready(l);l.transcript(t,"synthetic",1f);l.stop();l.generated(t,"late");assertFalse(p.calls.contains("speak"))}
 @Test fun stopDuringPlaybackCannotRestartMic(){val p=Ports();val l=VoiceLoop(p,SyntheticPolicy());val t=ready(l);l.transcript(t,"synthetic",1f);l.generated(t,"synthetic");l.stop();val n=p.calls.size;l.spoken(t);assertEquals(n,p.calls.size)}
 @Test fun staleErrorCannotStopNewSession(){val l=VoiceLoop(Ports());val old=ready(l);ready(l);l.error(old,"late");assertEquals(VoiceLoop.Phase.LISTENING,l.phase)}
 @Test fun policyExceptionsFailClosed(){val p=Ports();val l=VoiceLoop(p,object:VoicePolicy{override fun input(text:String):Boolean=error("fail");override fun output(text:String)=true});l.transcript(ready(l),"hello",1f);assertFalse(p.calls.contains("generate"))}
}
