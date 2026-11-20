package org.tuuwanasavi.synthshai

/** Ephemeral presentation state; never treats an app status as generated text. */
class ReplyPanel {
 var input="No transcript received"; private set
 var message="No reply yet"; private set
 var response:String?=null; private set
 private var pending=false
 fun awaitingConfirmation(){pending=false;response=null;message="Review the transcript. Choose the fixed reply, or select a GGUF and confirm local generation."}
 fun fixedReply(text:String){pending=false;response=text;message="Fixed test reply — human-confirmed transcript; not a generated answer"}
 fun clear(){input="No transcript received";message="No reply yet";response=null;pending=false}
 fun waitingForInput(){response=null;message="Waiting for recognition. No message has been sent to Qwen.";pending=true}
 fun recognized(text:String?){input=text?.takeIf{it.isNotBlank()}?.take(1000)?:"No transcript received"}
 fun pending(){response=null;message="Pending — local model test running";pending=true}
 fun blocked(reason:String){response=null;pending=false;message=if(reason.contains("USHAI")) "$reason\nNext: input/output evidence and an approval interface must be reviewed. No generated speech is enabled." else "$reason\nNo reply generated. Check the recognition stage below."}
 fun stopped(reason:String){if(pending){blocked(reason)}}
 fun synthetic(text:String){pending=false;response=text.takeIf{it.isNotBlank()}?.take(3000);message=if(response==null)"No text returned by the fixed model test" else "Fixed model test reply — unreviewed; not spoken"}
 fun awaitingSpeechApproval(text:String){pending=false;response=text;message="Local reply — review before approving speech"}
 fun approved(text:String){pending=false;response=text;message="Permitted SHAI reply — this same text is passed to speech"}
 fun render()=message+(response?.let{"\n\n$it"}?:"")
 companion object {
  fun isFixedTest(text:String)=text.trim() in setOf("What is two plus two?", "What is two plus two? Answer with one number.")
 }
}
