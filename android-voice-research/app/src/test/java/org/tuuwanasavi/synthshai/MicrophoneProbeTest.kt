package org.tuuwanasavi.synthshai
import org.junit.Assert.*
import org.junit.Test
class MicrophoneProbeTest {
 private class Port:MicrophonePort {
  var closes=0;var reads=0;var result=2;var samples=shortArrayOf(-32768,32767);var last:ShortArray?=null;var fail=false
  override fun start(){if(fail)throw SecurityException()}
  override fun read(buffer:ShortArray):Int{reads++;last=buffer;samples.copyInto(buffer);return result}
  override fun condition()="Android reports capture silenced: unknown"
  override fun close(){closes++}
 }
 @Test fun samplesAreErasedAfterEveryReadAndNeverCalledSpeech(){val p=Port();var text="";val probe=MicrophoneProbe(p,{0}){s,_->text=s};probe.start();probe.tick();assertTrue(p.last!!.all{it==0.toShort()});assertTrue(text.contains("peak: 32768"));assertTrue(text.contains("does not prove speech"));probe.stop()}
 @Test fun deadlineReleasesWithoutAdditionalReads(){val p=Port();var time=0L;var done=false;val probe=MicrophoneProbe(p,{time}){_,d->done=d};probe.start();probe.tick();time=5000;probe.tick();probe.tick();assertEquals(1,p.reads);assertEquals(1,p.closes);assertTrue(done)}
 @Test fun cancelIsIdempotentAndPreventsLateCapture(){val p=Port();val probe=MicrophoneProbe(p,{0}){_,_->};probe.start();probe.stop();probe.stop();probe.tick();assertEquals(0,p.reads);assertEquals(1,p.closes)}
 @Test fun startFailureStillReleases(){val p=Port();p.fail=true;var text="";val probe=MicrophoneProbe(p,{0}){s,_->text=s};probe.start();assertEquals(1,p.closes);assertTrue(text.contains("SecurityException"));probe.tick();assertEquals(0,p.reads)}
 @Test fun negativeReadDoesNotBecomeSilence(){val p=Port();p.result=-3;var text="";val probe=MicrophoneProbe(p,{0}){s,_->text=s};probe.start();probe.tick();assertTrue(text.contains("read error -3"));assertFalse(text.contains("all zero"));assertEquals(1,p.closes);assertTrue(p.last!!.all{it==0.toShort()})}
 @Test fun zeroSamplesDistinguishedFromAllZeroAudio(){val p=Port();p.result=0;var text="";val probe=MicrophoneProbe(p,{0}){s,_->text=s};probe.start();probe.tick();assertTrue(text.contains("No PCM samples"));probe.stop()}
 @Test fun allZeroAudioDoesNotAssertBrokenHardware(){val p=Port();p.samples=shortArrayOf(0,0);var text="";val probe=MicrophoneProbe(p,{0}){s,_->text=s};probe.start();probe.tick();assertTrue(text.contains("Samples were all zero; cause not established"));probe.stop()}
 @Test fun cancelledProbeCannotBeRestarted(){val p=Port();val probe=MicrophoneProbe(p,{0}){_,_->};probe.start();probe.stop();probe.start();probe.tick();assertEquals(0,p.reads);assertEquals(1,p.closes)}
}
