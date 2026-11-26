package org.tuuwanasavi.synthshai

import org.junit.Assert.*
import org.junit.Test

class ReviewedTurnTest {
 @Test fun continuationRevokesOldReplyAndNeedsFreshApproval() {
  val t=ReviewedTurn();t.offer(1,"question");t.confirm(1,"question");t.generated(1,"first")
  assertFalse(t.continueReply(2))
  assertTrue(t.continueReply(1));assertNull(t.reply);assertNull(t.approve(1))
  assertFalse(t.continueReply(1))
  assertTrue(t.generated(1,"first plus next"));assertEquals("first plus next",t.approve(1))
  assertFalse(t.continueReply(1));assertNull(t.approve(1))
 }
 @Test fun stoppingContinuationRejectsLateOutput() {
  val t=ReviewedTurn();t.offer(1,"question");t.confirm(1,"question");t.generated(1,"first")
  t.continueReply(1);t.clear()
  assertFalse(t.generated(1,"late"));assertNull(t.approve(1));assertFalse(t.continueReply(1))
 }
 @Test fun requiresBothReviewsAndSpeaksExactOutputOnce() {
  val t=ReviewedTurn()
  assertNull(t.approve(1))
  assertFalse(t.generated(1,"premature"))
  assertTrue(t.offer(1,"misheard"))
  assertNull(t.approve(1))
  assertEquals("corrected question",t.confirm(1,"corrected question"))
  assertNull(t.confirm(1,"duplicate"))
  assertTrue(t.generated(1,"Exact Qwen output."))
  assertFalse(t.generated(1,"replacement"))
  assertEquals("Exact Qwen output.",t.approve(1))
  assertNull(t.approve(1))
  assertTrue(t.completed(1))
  assertFalse(t.completed(1))
 }
 @Test fun stopRevokesEveryStage() {
  for(stage in 0..3){
   val t=ReviewedTurn();t.offer(5,"question")
   if(stage>=1)t.confirm(5,"question")
   if(stage>=2)t.generated(5,"answer")
   if(stage>=3)t.approve(5)
   t.clear()
   assertNull(t.confirm(5,"question"));assertFalse(t.generated(5,"late answer"))
   assertNull(t.approve(5));assertFalse(t.completed(5))
  }
 }
 @Test fun staleCallbacksCannotReplaceNewTurn() {
  val t=ReviewedTurn();t.offer(1,"old");t.confirm(1,"old");t.clear()
  t.offer(2,"new");t.confirm(2,"new")
  assertFalse(t.generated(1,"late"));assertNull(t.approve(1))
  assertTrue(t.generated(2,"fresh"));assertEquals("fresh",t.approve(2))
  assertFalse(t.completed(1));assertTrue(t.completed(2))
 }
 @Test fun rejectsInvalidInputAndOutputWithoutSpeaking() {
  val t=ReviewedTurn()
  for(text in listOf(null,""," ","x".repeat(1001)))assertFalse(t.offer(1,text))
  t.offer(1,"question")
  assertNull(t.confirm(1," "));assertNull(t.confirm(1,"x".repeat(1001)))
  assertEquals("question",t.confirm(1," question "))
  assertFalse(t.generated(1," "));assertNull(t.approve(1))
  t.offer(2,"question");t.confirm(2,"question")
  assertFalse(t.generated(2,"x".repeat(3001)));assertNull(t.approve(2))
 }
 @Test fun nextTurnRequiresFreshConfirmation() {
  val t=ReviewedTurn();t.offer(1,"one");t.confirm(1,"one");t.generated(1,"answer");t.approve(1);t.completed(1)
  t.offer(2,"two")
  assertFalse(t.generated(2,"unapproved"));assertNull(t.approve(2))
  assertTrue(t.canConfirm(2));assertFalse(t.canSpeak(2))
 }
}
