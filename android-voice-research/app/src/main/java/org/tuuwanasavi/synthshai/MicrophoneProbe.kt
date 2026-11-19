package org.tuuwanasavi.synthshai

import kotlin.math.abs
import kotlin.math.sqrt

interface MicrophonePort {
 fun start()
 fun read(buffer:ShortArray):Int
 fun condition():String
 fun close()
}
/** Short-lived diagnostic. No audio is retained, transcribed, replayed or written. */
class MicrophoneProbe(private val port:MicrophonePort,private val now:()->Long,private val update:(String,Boolean)->Unit) {
 private var running=false
 private var closed=false
 private var started=0L
 private val buffer=ShortArray(2048)
 private var count=0L
 private var nonzero=0L
 private var peak=0
 private var squares=0.0
 fun start(){
  if(running||closed)return
  try{port.start();running=true;started=now();update("Microphone check: speak normally for five seconds. Audio is discarded.",false)}
  catch(e:Exception){finish("Capture start failed: ${e.javaClass.simpleName}")}
 }
 fun tick(){
  if(!running)return
  try{
   if(now()-started>=5000){finish(summary());return}
   val n=port.read(buffer)
   if(n<0){finish("Capture read error $n. Cause not established.");return}
   require(n<=buffer.size)
   for(i in 0 until n){val v=buffer[i].toInt();count++;if(v!=0)nonzero++;peak=maxOf(peak,abs(v));squares+=v.toDouble()*v}
   update(summary()+"\nCapture active; audio discarded.",false)
  }catch(e:Exception){finish("Capture check failed: ${e.javaClass.simpleName}")}
  finally{buffer.fill(0)}
 }
 private fun summary():String {
  val rms=if(count==0L)0 else sqrt(squares/count).toInt()
  val meaning=when{count==0L->"No PCM samples read; not proof the microphone is faulty.";nonzero==0L->"Samples were all zero; cause not established.";else->"Nonzero audio samples received; this does not prove speech or recognizer input."}
  return "Samples: $count; nonzero: $nonzero; peak: $peak; RMS: $rms\n${port.condition()}\n$meaning"
 }
 private fun finish(message:String){
  running=false;buffer.fill(0)
  if(!closed){closed=true;runCatching{port.close()}}
  update(message+"\nMicrophone released. No transcript produced. 144 HOLD unchanged.",true)
 }
 fun stop(){if(!closed)finish("Microphone check cancelled")}
}
