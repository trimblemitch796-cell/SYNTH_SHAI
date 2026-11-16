package org.tuuwanasavi.synthshai

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.util.Base64

internal data class StoredChatLine(val fromHuman: Boolean, val content: String)

/** Bounded, app-private recent completed exchanges; no network or automatic replay. */
internal object ChatHistoryCodec {
    private const val maxLines = 40
    private const val maxChars = 24000
    private const val maxLineChars = 4096
    fun encode(lines: List<StoredChatLine>): String {
        require(lines.size % 2 == 0 && lines.withIndex().all { (i, line) -> line.fromHuman == (i % 2 == 0) })
        val saved = ArrayList<StoredChatLine>()
        var chars = 0
        for (i in lines.size - 2 downTo 0 step 2) {
            val pair = listOf(lines[i], lines[i + 1])
            val size = pair.sumOf { it.content.length }
            if (saved.size + 2 > maxLines || chars + size > maxChars || pair.any { it.content.length > maxLineChars }) break
            saved.addAll(0, pair); chars += size
        }
        val bytes = ByteArrayOutputStream()
        DataOutputStream(bytes).use { out ->
            out.writeInt(1); out.writeInt(saved.size)
            saved.forEach { out.writeBoolean(it.fromHuman); out.writeUTF(it.content) }
        }
        return Base64.getEncoder().encodeToString(bytes.toByteArray())
    }
    fun decode(encoded: String?): List<StoredChatLine> {
        if (encoded == null || encoded.length > 140000) return emptyList()
        return try {
            DataInputStream(ByteArrayInputStream(Base64.getDecoder().decode(encoded))).use { input ->
                if (input.readInt() != 1) return emptyList()
                val count = input.readInt()
                if (count !in 0..maxLines || count % 2 != 0) return emptyList()
                val result = ArrayList<StoredChatLine>()
                var chars = 0
                repeat(count) { index ->
                    val human = input.readBoolean()
                    val content = input.readUTF()
                    chars += content.length
                    if (human != (index % 2 == 0) || content.length > maxLineChars || chars > maxChars) return emptyList()
                    result.add(StoredChatLine(human, content))
                }
                if (input.read() != -1) return emptyList()
                result
            }
        } catch (_: Exception) { emptyList() }
    }
}
