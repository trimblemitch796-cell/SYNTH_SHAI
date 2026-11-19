package org.tuuwanasavi.synthshai
import org.junit.Assert.*
import org.junit.Test
class UshaiVoiceGateTest {
 @Test fun originalPythonParity(){val rows=javaClass.getResourceAsStream("/ushai-oracle.tsv")!!.bufferedReader().use{it.readLines()};assertEquals(64,rows.size);for(row in rows){val c=row.split('\t');val b=c[0].map{it=='1'};val d=UshaiVoiceGate.assess(VoiceEvidence(b[0],b[1],b[2],b[3],b[4],b[5]));assertEquals(c[1],d.outcome);assertEquals(c[2],d.reason);assertFalse(d.approvalGranted)}}
 @Test fun missingEvidenceHolds(){assertEquals("144 HOLD",UshaiVoiceGate.assess(null).outcome);for(i in 0..5){val b=mutableListOf<Boolean?>(true,true,true,false,false,true);b[i]=null;assertEquals("144 HOLD",UshaiVoiceGate.assess(VoiceEvidence(b[0],b[1],b[2],b[3],b[4],b[5])).outcome)}}
}
