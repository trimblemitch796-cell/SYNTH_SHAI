package org.tuuwanasavi.synthshai

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.*
import android.speech.*
import android.speech.tts.*
import android.widget.*
import java.util.Locale
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class MainActivity : Activity(), VoicePorts {
 private val review=ReviewedTurn()
 private lateinit var speakButton: Button
 private lateinit var transcriptEdit: EditText
 private lateinit var confirmButton: Button
 private val timing=RecognitionTiming()
 private val panel=ReplyPanel()
 private val loop=VoiceLoop(this)
 private val handler=Handler(Looper.getMainLooper())
 private val worker=Executors.newSingleThreadExecutor()
 private var cancellation=AtomicBoolean(false)
 private var working=false
 private var microphoneProbe:MicrophoneProbe?=null
 private val micTick=object:Runnable {override fun run(){microphoneProbe?.tick();if(microphoneProbe!=null)handler.postDelayed(this,40)}}
 private var visible=false
 private var recognizer: SpeechRecognizer?=null
 private var tts: TextToSpeech?=null
 private var model: Uri?=null
 private var language="en-AU"
 private var details="No session yet"
 private var callbacks=""
 private var rmsCount=0
 private var readyAt=0L
 private var startAt=0L
 private var stage="idle"
 private var independentToken=0L
 private lateinit var status: TextView
 private lateinit var evidence: TextView
 private lateinit var recognized: TextView
 private lateinit var reply: TextView
 private lateinit var typed: EditText
 private val deadline=Runnable { loop.error(loop.token,"Timed out during $stage");draw() }
 override fun onCreate(savedInstanceState: Bundle?) {
  super.onCreate(savedInstanceState)
  val c=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(24,24,24,24)}
  c.addView(TextView(this).apply{text="SYNTH SHAI";textSize=26f})
  c.addView(TextView(this).apply{text="Voice research 0.9 • human-reviewed Qwen\nConfirm your transcript to generate locally. Read the reply, then approve it for speech. Human review is not an automated safety check. Each turn starts with a tap; no chat history is retained. Speech services still need airplane-mode testing."})
  status=TextView(this).apply{textSize=20f};c.addView(status)
  c.addView(TextView(this).apply{text="Recognized input";textSize=18f})
  recognized=TextView(this).apply{setTextIsSelectable(true);isSaveEnabled=false};c.addView(recognized)
  transcriptEdit=EditText(this).apply{hint="Review or correct your transcript";isSaveEnabled=false;filters=arrayOf(android.text.InputFilter.LengthFilter(1000));inputType=android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS};c.addView(transcriptEdit)
  c.addView(TextView(this).apply{text="SHAI reply";textSize=22f})
  reply=TextView(this).apply{textSize=20f;setPadding(12,16,12,16);setBackgroundColor(0xffeeeeee.toInt());setTextIsSelectable(true);isSaveEnabled=false};c.addView(reply)
  c.addView(TextView(this).apply{text="Typed component test — only the fixed 2 + 2 prompt runs. Other messages remain under USHAI HOLD."})
  typed=EditText(this).apply{hint="Type: What is two plus two?";isSaveEnabled=false;inputType=android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS};c.addView(typed)
  fun button(name:String, action:()->Unit){c.addView(Button(this).apply{text=name;setOnClickListener{action()}})}
  button("Send typed test"){typedTest()}
  button("Check microphone signal — 5 seconds, no recording saved"){checkMicrophone()}
  button("Start microphone / recognition test"){startVoice()}
  button("Finish phrase — request transcript"){finishPhrase()}
  confirmButton=Button(this).apply{text="Confirm transcript — generate Qwen reply";isEnabled=false;setOnClickListener{confirmTranscript()}};c.addView(confirmButton)
  speakButton=Button(this).apply{text="Approve displayed reply — speak once";isEnabled=false;setOnClickListener{approveReply()}};c.addView(speakButton)
  button("Stop"){loop.stop("Stopped by human");draw()}
  button("Test fixed speech output (microphone off)"){fixedSpeech()}
  button("Select Qwen GGUF model"){
   if(!working){loop.stop();startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply{type="*/*";addCategory(Intent.CATEGORY_OPENABLE)},12)}
  }
  button("Run synthetic model test: 2 + 2"){probe()}
  button("End / clear"){loop.stop();panel.clear();transcriptEdit.text.clear();typed.text.clear();details="Cleared";callbacks="";draw()}
  evidence=TextView(this);c.addView(evidence)
  setContentView(ScrollView(this).apply{addView(c)});draw()
 }
 override fun onResume(){super.onResume();visible=true}
 override fun onPause(){visible=false;loop.stop("Left foreground");draw();super.onPause()}
 override fun onDestroy(){loop.stop();worker.shutdownNow();super.onDestroy()}
 override fun onActivityResult(request:Int,result:Int,data:Intent?){super.onActivityResult(request,result,data);if(request==12&&result==RESULT_OK){model=data?.data;details="Model selected; private copy verified before generation. Start recognition, then confirm the transcript.";draw()}}
 private fun draw(){
  if(!::status.isInitialized)return
  status.text="Human-reviewed research • ${review.phase}\nStage: $stage\nAutomated USHAI content safety is unverified"
  confirmButton.isEnabled=visible&&!working&&review.canConfirm(loop.token)
  speakButton.isEnabled=visible&&!working&&review.canSpeak(loop.token)
  transcriptEdit.isEnabled=visible&&!working&&review.canConfirm(loop.token)
  recognized.text=panel.input
  reply.text=panel.render()
  evidence.text=details+"\n"+callbacks+"\nRMS callback count: $rmsCount (absence does not prove silence)"
  window.decorView.keepScreenOn=loop.phase!=VoiceLoop.Phase.HOLD||working||stage=="Speech playback"||microphoneProbe!=null
 }
 private fun mark(name:String, timeoutMs:Long=30000){stage=name;handler.removeCallbacks(deadline);handler.postDelayed(deadline,timeoutMs);draw()}
 private fun event(name:String){callbacks=(callbacks+"\n${SystemClock.elapsedRealtime()-startAt}ms: $name").takeLast(1800);draw()}
 private fun active(t:Long)=visible&&t==loop.token
 override fun stopAll(){
  review.clear()
  val oldProbe=microphoneProbe;microphoneProbe=null;handler.removeCallbacks(micTick);oldProbe?.stop();if(oldProbe!=null)details="Microphone check cancelled; capture stopped. No transcript produced."
  timing.cancel()
  panel.stopped(loop.reason)
  independentToken++;cancellation.set(true);handler.removeCallbacks(deadline)
  runCatching{recognizer?.cancel()};runCatching{recognizer?.destroy()};recognizer=null
  runCatching{tts?.stop()};runCatching{tts?.shutdown()};tts=null;stage=loop.reason
 }
 private fun checkMicrophone(){
  if(working)return
  loop.stop();panel.clear()
  if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO),3);details="Grant microphone permission, then tap Check microphone again";draw();return}
  if(!visible)return
  val token=loop.token
  mark("Independent microphone check",10000)
  microphoneProbe=MicrophoneProbe(AndroidMicrophonePort(),{SystemClock.elapsedRealtime()}){message,done->
   if(active(token)){details=message;if(done){microphoneProbe=null;handler.removeCallbacks(micTick);handler.removeCallbacks(deadline);stage="Microphone check ended"};draw()}
  }
  microphoneProbe?.start()
  if(microphoneProbe!=null)handler.post(micTick)
 }
 private fun startVoice(){
  if(working){details="Wait for cancelled local-model work to release resources";draw();return}
  loop.stop();panel.clear();transcriptEdit.text.clear();callbacks="";rmsCount=0;readyAt=0;startAt=SystemClock.elapsedRealtime()
  if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO),3);details="Grant permission, then tap Start again";draw();return}
  if(Build.VERSION.SDK_INT<33||!SpeechRecognizer.isOnDeviceRecognitionAvailable(this)){details="On-device support query unavailable; no network fallback";draw();return}
  val t=loop.begin(visible,true);panel.waitingForInput();language=Locale.getDefault().toLanguageTag().takeIf{it.startsWith("en",true)}?:"en-AU"
  try{recognizer=SpeechRecognizer.createOnDeviceSpeechRecognizer(this);attachListener(t);query(t,false)}catch(e:Exception){loop.error(t,"Local speech setup: ${e.javaClass.simpleName}");draw()}
 }
 private fun intent()=Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply{
  putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
  putExtra(RecognizerIntent.EXTRA_LANGUAGE,language);putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,1)
  putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,false)
 }
 private fun english(tags:List<String>)=tags.mapNotNull{runCatching{Locale.Builder().setLanguageTag(it.replace('_','-')).build()}.getOrNull()}.filter{it.language=="en"}.map{it.toLanguageTag()}.distinct().sorted()
 @android.annotation.TargetApi(33)
 private fun query(t:Long,confirm:Boolean){
  if(!active(t))return
  mark("Checking installed recognition languages")
  recognizer!!.checkRecognitionSupport(intent(),mainExecutor,object:RecognitionSupportCallback{
   override fun onError(e:Int){if(active(t)){loop.error(t,"Support query error $e");draw()}}
   override fun onSupportResult(s:RecognitionSupport){
    if(!active(t))return
    details="Reported installed: ${s.installedOnDeviceLanguages.joinToString().take(700)}\nPending: ${s.pendingOnDeviceLanguages.joinToString().take(300)}"
    val choices=english(s.installedOnDeviceLanguages)
    if(confirm){if(language !in choices){loop.error(t,"Selected locale not confirmed installed");draw();return};loop.checked(t,true)}
    else{val selected=language.takeIf{it in choices}?:choices.firstOrNull();if(selected==null){loop.error(t,"No installed English locale reported");draw();return};language=selected;query(t,true)}
   }
  })
 }
 override fun listen(token:Long){
  if(!active(token))return
  // Initial recognition object is retained after support queries; later turns get a new one.
  try{
   if(recognizer==null){if(Build.VERSION.SDK_INT<31){loop.error(token,"On-device recognition unavailable");return};recognizer=SpeechRecognizer.createOnDeviceSpeechRecognizer(this)}
   attachListener(token)
   timing.reset();event("App requests startListening; locale=$language")
   mark("Preparing recogniser — wait for Speak now");recognizer!!.startListening(intent())
  }catch(e:Exception){loop.error(token,"Recognition startup: ${e.javaClass.simpleName}");draw()}
 }
 private fun finishPhrase(){
  if(!visible||loop.phase!=VoiceLoop.Phase.LISTENING||recognizer==null)return
  if(!timing.requestFinish(SystemClock.elapsedRealtime()))return
  event("Human requested stopListening; waiting for result, no restart")
  mark("Phrase finished — waiting for transcript")
  try{recognizer?.stopListening()}catch(e:Exception){loop.error(loop.token,"Finish request: ${e.javaClass.simpleName}");draw()}
 }
 private fun attachListener(token:Long){
   recognizer!!.setRecognitionListener(object:RecognitionListener{
    override fun onReadyForSpeech(b:Bundle?){if(active(token)){readyAt=SystemClock.elapsedRealtime();timing.ready(readyAt);loop.ready(token);val haptic=status.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);event("READY — Speak now; haptic accepted=$haptic");mark("SPEAK NOW: ask a short question, then tap Finish phrase")}}
    override fun onBeginningOfSpeech(){if(active(token)){timing.beginning(SystemClock.elapsedRealtime());event("Beginning of speech reported")}}
    override fun onRmsChanged(v:Float){if(active(token)){rmsCount++;if(rmsCount%10==1)draw()}}
    override fun onBufferReceived(b:ByteArray?){} // Discard, never persist.
    override fun onEndOfSpeech(){if(active(token)){event("End of speech reported");mark("Waiting for transcript")}}
    override fun onError(e:Int){if(active(token)){event("Recognition error $e; ready callback received=${readyAt!=0L}");details+="\n"+timing.terminal(SystemClock.elapsedRealtime());loop.error(token,if(e==7)"No recognition match (7); cause not established" else "Recognition error $e");draw()}}
    override fun onResults(b:Bundle?){if(!active(token))return;handler.removeCallbacks(deadline);event("Final results callback");details+="\n"+timing.terminal(SystemClock.elapsedRealtime());runCatching{recognizer?.destroy()};recognizer=null
     val text=b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull();val confidence=b?.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES)?.firstOrNull()
     details+="\nTranscript present=${!text.isNullOrBlank()}; confidence supplied=${confidence!=null} (text not saved)"
     panel.recognized(text)
     // Only accept a result from a recognizer that reached LISTENING.
     val wasListening=loop.phase==VoiceLoop.Phase.LISTENING
     loop.stop("Transcript received — waiting for human review")
     if(wasListening&&review.offer(loop.token,text)) {
      panel.reviewTranscript()
      transcriptEdit.setText(text)
      stage="Review transcript — microphone off"
      details+="\nConfidence is diagnostic only. Correct the transcript if needed, then confirm to send it to local Qwen."
     } else panel.blocked("No valid transcript after readiness; start another recognition test")
     draw()
    }
    override fun onPartialResults(b:Bundle?){}
    override fun onEvent(e:Int,b:Bundle?){}
   })
 }
 private fun prepareTts(t:Long,text:String,after:()->Unit){
  mark("Initialising local speech output")
  tts=TextToSpeech(this){result->runOnUiThread{
   if(!active(t))return@runOnUiThread
   try{
    val voices=tts?.voices.orEmpty().filter{it.locale.language=="en"&&!it.isNetworkConnectionRequired&&TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED !in it.features.orEmpty()}
    val voice=voices.sortedBy{it.name}.firstOrNull()
    if(result!=TextToSpeech.SUCCESS||voice==null||tts?.setVoice(voice)!=TextToSpeech.SUCCESS){loop.error(t,"Installed local English output unavailable");draw();return@runOnUiThread}
    details+="\nOutput voice reported local: ${voice.locale.toLanguageTag()}"
    tts!!.setOnUtteranceProgressListener(object:UtteranceProgressListener(){
     override fun onStart(id:String?){runOnUiThread{if(active(t))event("TTS playback started")}}
     override fun onDone(id:String?){runOnUiThread{if(active(t)){handler.removeCallbacks(deadline);event("TTS playback completed (audibility needs phone check)");after()}}}
     override fun onError(id:String?){runOnUiThread{if(active(t)){loop.error(t,"TTS playback error");draw()}}}
    })
    mark("Speech playback")
    if(tts!!.speak(text,TextToSpeech.QUEUE_FLUSH,null,t.toString())!=TextToSpeech.SUCCESS){loop.error(t,"TTS request failed");draw()}
   }catch(e:Exception){loop.error(t,"TTS setup: ${e.javaClass.simpleName}");draw()}
  }}
 }
 private fun confirmTranscript(){
  if(!visible||working||!review.canConfirm(loop.token))return
  if(model==null){details="Select a Qwen GGUF model first, then start recognition again.";draw();return}
  val text=review.confirm(loop.token,transcriptEdit.text.toString())?:run{details="Transcript must contain 1–1000 characters.";draw();return}
  panel.recognized(text)
  details="Human confirmed this transcript for local generation. Microphone off. Reply requires a separate review before speech."
  runModel(loop.token,text,false)
 }
 private fun approveReply(){
  if(!visible||working)return
  val t=loop.token
  val text=review.approve(t)?:return
  panel.reviewed(text)
  details="Human approved the displayed reply for one playback. Automated content safety remains unverified."
  prepareTts(t,text){
   if(review.completed(t)){loop.stop("Reply completed");stage="Reply completed — tap Start for the next turn";draw()}
  }
 }
 private fun fixedSpeech(){if(working)return;loop.stop();startAt=SystemClock.elapsedRealtime();callbacks="";details="Independent fixed text output test. Microphone off.";val t=loop.token;prepareTts(t,"SYNTH SHAI speech output test. The garden is green."){loop.stop("Fixed output completed");draw()}}
 override fun speak(token:Long,text:String){panel.approved(text);runCatching{recognizer?.destroy()};recognizer=null;prepareTts(token,text){runCatching{tts?.shutdown()};tts=null;loop.spoken(token);draw()}}
 override fun generate(token:Long,text:String){runModel(token,text,false)}
 private fun typedTest(){
  if(working)return
  val text=typed.text.toString()
  if(ReplyPanel.isFixedTest(text)){probe();return}
  loop.stop("144 HOLD: USHAI typed input content evidence is unverified")
  panel.blocked(loop.reason);details="Typed message was not sent to Qwen. Arbitrary typed conversation requires the same substantive review as voice.";draw()
 }
 private fun probe(){if(working)return;loop.stop();if(model==null){details="Select the same Qwen GGUF from Downloads first; existing app is untouched";draw();return};details="Synthetic model probe only. No recognised speech is used; output is not safety-verified.";runModel(loop.token,"What is two plus two? Answer with one number.",true)}
 private fun runModel(t:Long,text:String,synthetic:Boolean){
  if(!synthetic&&review.phase!=ReviewedTurn.Phase.GENERATING)return
  val uri=model?:run{loop.error(t,"No model selected");draw();return}
  if(!active(t)||working)return
  panel.pending();working=true;val stop=AtomicBoolean(false);cancellation=stop;mark("Preparing private model and generating",180000)
  worker.execute{
   val result=runCatching{withVerifiedModel(this,uri,stop){path->LocalEngine.generate(path,("<|im_start|>system\nYou are SYNTH SHAI. Answer briefly.<|im_end|>\n<|im_start|>user\n"+text.replace("<|","< |")+"<|im_end|>\n<|im_start|>assistant\n").encodeToByteArray(),stop).decodeToString()}}
   runOnUiThread{working=false;if(active(t)&&!stop.get()){handler.removeCallbacks(deadline);result.fold({response->if(synthetic){panel.synthetic(response);details="Fixed-prompt model test finished. This output is not content-reviewed and will not be spoken.";stage="Synthetic test complete; no speech playback"}else if(review.generated(t,response)){panel.unreviewed(response);details="Generation finished. Read the displayed reply, then approve it to speak once. Microphone off.";stage="Review Qwen reply — speech off"}else{loop.error(t,"Model returned an empty, oversized or stale reply")}},{error->loop.error(t,"Local model: ${error.javaClass.simpleName}: ${error.message?.take(300)}")})};draw()}
  }
 }
}
