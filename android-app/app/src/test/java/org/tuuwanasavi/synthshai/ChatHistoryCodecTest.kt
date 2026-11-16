package org.tuuwanasavi.synthshai
import org.junit.Assert.*
import org.junit.Test
class ChatHistoryCodecTest {
    private fun pair(n: Int) = listOf(StoredChatLine(true, "question $n"), StoredChatLine(false, "answer $n"))
    @Test fun completedExchangesRestoreExactly() {
        val lines = pair(1) + pair(2) + listOf(StoredChatLine(true,"你好\n∆"),StoredChatLine(false,"Hello 🧬"))
        assertEquals(lines, ChatHistoryCodec.decode(ChatHistoryCodec.encode(lines)))
    }
    @Test fun retainsOnlyLatestTwentyCompleteExchanges() {
        val lines = (1..60).flatMap { pair(it) }
        assertEquals(lines.takeLast(40), ChatHistoryCodec.decode(ChatHistoryCodec.encode(lines)))
    }
    @Test fun boundedByTextBudgetWithoutSplittingPairs() {
        val lines = (1..30).flatMap { listOf(StoredChatLine(true,"x".repeat(1000)),StoredChatLine(false,"y".repeat(1000))) }
        val restored = ChatHistoryCodec.decode(ChatHistoryCodec.encode(lines))
        assertEquals(24, restored.size); assertEquals(24000, restored.sumOf { it.content.length })
    }
    @Test fun malformedOrOversizedStateIsIgnored() {
        for (text in listOf(null, "not base64!", "A".repeat(140001))) assertTrue(ChatHistoryCodec.decode(text).isEmpty())
        val valid = ChatHistoryCodec.encode(pair(1))
        assertTrue(ChatHistoryCodec.decode(valid.dropLast(4)).isEmpty())
    }
    @Test fun emptyStateRemainsEmpty() { assertTrue(ChatHistoryCodec.decode(ChatHistoryCodec.encode(emptyList())).isEmpty()) }
    @Test(expected = IllegalArgumentException::class) fun pendingPromptIsNotSavedAsCompletedExchange() { ChatHistoryCodec.encode(listOf(StoredChatLine(true,"pending"))) }
}
