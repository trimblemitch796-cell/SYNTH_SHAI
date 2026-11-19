package org.tuuwanasavi.synthshai

/** Records app-observed timing, never infers when the human actually spoke. */
class RecognitionTiming {
 private var ready:Long?=null
 private var beginning:Long?=null
 private var finish:Long?=null
 private var terminal=false
 fun reset(){ready=null;beginning=null;finish=null;terminal=false}
 fun ready(at:Long){if(!terminal&&ready==null)ready=at}
 fun beginning(at:Long){if(!terminal&&beginning==null)beginning=at}
 fun requestFinish(at:Long):Boolean {
  if(terminal||ready==null||finish!=null)return false
  finish=at;return true
 }
 fun terminal(at:Long):String {
  terminal=true
  fun delta(a:Long?,b:Long?)=if(a==null||b==null||b<a)"unknown" else "${b-a} ms"
  return "READY to beginning callback: ${delta(ready,beginning)}; beginning callback to terminal: ${delta(beginning,at)}; manual finish requested: ${finish!=null}. Callback timing is not proof of speech timing."
 }
 fun cancel(){terminal=true}
}
