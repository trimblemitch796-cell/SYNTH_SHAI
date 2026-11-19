package org.tuuwanasavi.synthshai

/** Protocol policy, not a natural-language harm detector. */
interface VoicePolicy { fun input(text: String): Boolean; fun output(text: String): Boolean }
object UshaiVoicePolicy : VoicePolicy {
    // Content evidence and uncertainty are not verified. Never manufacture approval.
    override fun input(text: String) = UshaiVoiceGate.assess(VoiceEvidence(true,true,false,null,null,false)).approvalGranted
    override fun output(text: String) = UshaiVoiceGate.assess(VoiceEvidence(true,true,false,null,null,false)).approvalGranted
}
interface VoicePorts { fun stopAll(); fun listen(token: Long); fun generate(token: Long, text: String); fun speak(token: Long, text: String) }
class VoiceLoop(private val ports: VoicePorts, private val policy: VoicePolicy = UshaiVoicePolicy) {
    enum class Phase { HOLD, CHECKING, ARMING, LISTENING, GENERATING, SPEAKING }
    var phase = Phase.HOLD; private set
    var token = 0L; private set
    var reason = "Inactive"; private set
    var continuous = false; private set
    fun stop(why: String = "Stopped by human") {
        token++; phase=Phase.HOLD; continuous=false; reason=why; ports.stopAll()
    }
    fun begin(foreground: Boolean, consent: Boolean): Long {
        stop()
        if(foreground && consent) { phase=Phase.CHECKING; continuous=true; reason="Checking local speech services" }
        else reason="Foreground consent required"
        return token
    }
    fun checked(t: Long, available: Boolean) {
        if(t!=token || phase!=Phase.CHECKING) return
        if(!available) { stop("Offline speech unavailable");return }
        phase=Phase.ARMING; reason="Preparing microphone — wait for Speak now"
        ports.listen(t)
    }
    fun ready(t: Long) {
        if(t==token && phase==Phase.ARMING) {phase=Phase.LISTENING;reason="Speak now"}
    }
    fun transcript(t: Long, text: String?, confidence: Float?) {
        if(t!=token) return
        if(phase==Phase.ARMING){stop("Recognizer returned before ready callback");return}
        if(phase!=Phase.LISTENING)return
        if(text.isNullOrBlank() || text.length>1000 || confidence==null || !confidence.isFinite() || confidence !in 0.8f..1f) {stop("Uncertain recognition");return}
        if(!runCatching { policy.input(text) }.getOrDefault(false)) {stop("144 HOLD: USHAI input content evidence is unverified");return}
        phase=Phase.GENERATING;reason="Generating locally";ports.generate(t,text)
    }
    fun generated(t: Long, text: String) {
        if(t!=token || phase!=Phase.GENERATING) return
        if(text.isBlank() || text.length>3000 || !runCatching { policy.output(text) }.getOrDefault(false)) {stop("144 HOLD: USHAI output review not satisfied");return}
        phase=Phase.SPEAKING;reason="Speaking — microphone off";ports.speak(t,text)
    }
    fun spoken(t: Long) {
        if(t!=token || phase!=Phase.SPEAKING || !continuous) return
        phase=Phase.ARMING;reason="Preparing next turn — wait for Speak now";ports.listen(t)
    }
    fun error(t: Long, why: String) { if(t==token) stop(why) }
}
