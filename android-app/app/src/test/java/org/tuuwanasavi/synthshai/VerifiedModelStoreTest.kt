package org.tuuwanasavi.synthshai

import java.io.File
import java.io.IOException
import java.io.InputStream
import java.nio.file.Files
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean
import org.junit.Assert.*
import org.junit.Test

class VerifiedModelStoreTest {
    private val data = "GGUF synthetic test fixture".toByteArray()
    private val hash = MessageDigest.getInstance("SHA-256").digest(data).joinToString("") { "%02x".format(it) }
    private fun scenario(test: (File) -> Unit) {
        val dir = Files.createTempDirectory("private-model-test").toFile()
        try { test(dir) } finally { dir.deleteRecursively() }
    }
    private fun store(dir: File, space: Long = 1000000L) = VerifiedModelStore(dir, data.size.toLong(), hash, 32L) { space }
    private fun fails(action: () -> Unit) {
        try { action(); fail("Expected failure") } catch (_: IllegalStateException) {} catch (_: IllegalArgumentException) {}
    }
    @Test fun verifiedCopyIsReusedWithoutSourceAccess() = scenario { dir ->
        val source = File(dir, "original.gguf").apply { writeBytes(data) }
        val result = store(dir).prepare(AtomicBoolean(false)) { source.inputStream() }
        assertArrayEquals(data, result.readBytes()); assertArrayEquals(data, source.readBytes())
        assertEquals(result, store(dir).prepare(AtomicBoolean(false)) { error("Should reuse") })
        assertFalse(dir.listFiles()!!.any { it.name.endsWith(".part") })
    }
    @Test fun corruptExistingCopyIsReplacedOnlyAfterVerification() = scenario { dir ->
        File(dir, "qwen-verified.gguf").writeBytes(ByteArray(data.size))
        val result = store(dir).prepare(AtomicBoolean(false)) { data.inputStream() }
        assertArrayEquals(data, result.readBytes())
    }
    @Test fun badHashCannotPromote() = scenario { dir ->
        fails { store(dir).prepare(AtomicBoolean(false)) { ByteArray(data.size).inputStream() } }
        assertTrue(dir.listFiles()!!.isEmpty())
    }
    @Test fun shortAndLongFilesCannotPromote() = scenario { dir ->
        for (bytes in listOf(data.copyOf(data.size - 1), data + byteArrayOf(1))) {
            fails { store(dir).prepare(AtomicBoolean(false)) { bytes.inputStream() } }
            assertTrue(dir.listFiles()!!.isEmpty())
        }
    }
    @Test fun cancelledCopyCleansPartialFile() = scenario { dir ->
        val stop = AtomicBoolean(false)
        fails { store(dir).prepare(stop) {
            object : InputStream() {
                override fun read(): Int = -1
                override fun read(b: ByteArray, off: Int, len: Int): Int { stop.set(true); b[off] = 1; return 1 }
            }
        } }
        assertTrue(dir.listFiles()!!.isEmpty())
    }
    @Test fun interruptedCopyCleansPartialAndHidesPrivatePath() = scenario { dir ->
        try {
            store(dir).prepare(AtomicBoolean(false)) { throw IOException(dir.absolutePath) }
            fail("Expected failure")
        } catch (e: IllegalStateException) { assertFalse(e.message!!.contains(dir.absolutePath)) }
        assertTrue(dir.listFiles()!!.isEmpty())
    }
    @Test fun lowSpaceDoesNotOpenSource() = scenario { dir ->
        var opened = false
        fails { store(dir, 0).prepare(AtomicBoolean(false)) { opened = true; data.inputStream() } }
        assertFalse(opened)
        assertTrue(dir.listFiles()!!.isEmpty())
    }
    @Test fun stalePartRemovedButUnrelatedFilePreserved() = scenario { dir ->
        File(dir, "model-import-old.part").writeText("unfinished")
        val other = File(dir, "unrelated").apply { writeText("keep") }
        store(dir).prepare(AtomicBoolean(false)) { data.inputStream() }
        assertTrue(other.exists()); assertFalse(File(dir, "model-import-old.part").exists())
    }
}
