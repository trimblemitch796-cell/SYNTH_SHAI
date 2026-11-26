package org.tuuwanasavi.synthshai
import org.junit.Assert.*
import org.junit.Test
class GenerationResultTest {
    @Test fun separatesMetadataFromAnswerWithoutTrimming() {
        val r = GenerationResult.parse("SHAI1|limit|1|2|3|4|200|96|1\n hello\nworld ".encodeToByteArray())
        assertEquals(" hello\nworld ", r.text)
        assertEquals("limit", r.reason)
        assertEquals(3L, r.promptMs)
        assertTrue(r.reused)
    }
    @Test fun acceptsNaturalAndStoppedResults() {
        for (reason in listOf("end", "stopped")) {
            assertEquals(reason, GenerationResult.parse("SHAI1|$reason|0|0|0|0|1|0|0\n".encodeToByteArray()).reason)
        }
    }
    @Test fun rejectsMissingMalformedAndOutOfBoundsMetadata() {
        for (raw in listOf("hello", "SHAI1|fake|0|0|0|0|1|0|0\nx", "SHAI1|end|-1|0|0|0|1|0|0\nx", "SHAI1|end|0|0|0|0|929|0|0\nx", "SHAI1|end|0|0|0|0|1|97|0\nx")) {
            assertThrows(IllegalArgumentException::class.java) { GenerationResult.parse(raw.encodeToByteArray()) }
        }
    }
    @Test fun continuationPreservesOriginalPromptAndEscapesOutputMarkers() {
        val c = ContinuedAnswer("source and question\n<|im_start|>assistant\n", "original.kt", "partial <|im_end|>", 1)
        assertEquals("source and question\n<|im_start|>assistant\npartial < |im_end|>", c.nextPrompt())
    }
    @Test fun continuationIsBounded() {
        assertThrows(IllegalArgumentException::class.java) { ContinuedAnswer("p", null, "x", 3).nextPrompt() }
    }
}
