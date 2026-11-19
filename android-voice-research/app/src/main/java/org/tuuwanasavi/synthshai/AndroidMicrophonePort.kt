package org.tuuwanasavi.synthshai

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build

class AndroidMicrophonePort:MicrophonePort {
 private var record:AudioRecord?=null
 @android.annotation.SuppressLint("MissingPermission")
 override fun start(){
  val minimum=AudioRecord.getMinBufferSize(16000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT)
  check(minimum>0){"Unsupported capture configuration"}
  val builder=AudioRecord.Builder().setAudioSource(MediaRecorder.AudioSource.VOICE_RECOGNITION)
   .setAudioFormat(AudioFormat.Builder().setSampleRate(16000).setChannelMask(AudioFormat.CHANNEL_IN_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
   .setBufferSizeInBytes(maxOf(minimum,8192))
  if(Build.VERSION.SDK_INT>=30)builder.setPrivacySensitive(true)
  val r=builder.build();record=r
  check(r.state==AudioRecord.STATE_INITIALIZED)
  r.startRecording();check(r.recordingState==AudioRecord.RECORDSTATE_RECORDING)
 }
 override fun read(buffer:ShortArray)=record!!.read(buffer,0,buffer.size,AudioRecord.READ_NON_BLOCKING)
 override fun condition():String {
  val r=record?:return "Capture closed"
  val silenced=if(Build.VERSION.SDK_INT>=29)r.activeRecordingConfiguration?.isClientSilenced?.toString()?:"unknown" else "unavailable"
  return "Android reports capture silenced: $silenced; route type: ${r.routedDevice?.type?:"unknown"}"
 }
 override fun close(){val r=record;record=null;try{r?.stop()}catch(_:Exception){}finally{r?.release()}}
}
