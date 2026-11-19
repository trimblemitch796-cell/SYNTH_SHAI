package org.tuuwanasavi.synthshai
/** Decision-only Catharsis port; no content classifier, provenance or authority issuer. */
data class VoiceEvidence(val intent:Boolean?,val consent:Boolean?,val verified:Boolean?,val contradiction:Boolean?,val harm:Boolean?,val resolved:Boolean?)
data class VoiceDecision(val outcome:String,val reason:String){val approvalGranted get()=false}
object UshaiVoiceGate {
 fun assess(e:VoiceEvidence?):VoiceDecision {
  fun hold(s:String)=VoiceDecision("144 HOLD",s)
  if(e==null)return hold("Evidence unavailable")
  if(listOf(e.intent,e.consent,e.verified,e.contradiction,e.harm,e.resolved).any{it==null})return hold("Unknown evidence")
  if(e.intent!=true)return hold("Undefined intent")
  if(e.consent!=true)return hold("Consent unverified")
  if(e.verified!=true)return hold("Evidence unverified")
  if(e.contradiction!=false)return hold("Contradiction detected")
  if(e.harm!=false)return hold("Potential harmful consequence")
  if(e.resolved!=true)return hold("Unresolved uncertainty")
  return VoiceDecision("REVIEW_REQUIRED","Evidence sufficient; a human must decide")
 }
}
