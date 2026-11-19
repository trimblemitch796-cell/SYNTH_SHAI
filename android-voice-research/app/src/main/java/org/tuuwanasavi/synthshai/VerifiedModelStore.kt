package org.tuuwanasavi.synthshai

import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.io.IOException
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean

/** Only verified bytes become a reusable model. Never changes the selected original. */
internal class VerifiedModelStore(
    private val directory: File,
    private val expectedSize: Long,
    private val expectedHash: String,
    private val reserveBytes: Long = 32L * 1024 * 1024,
    private val availableBytes: () -> Long = { directory.usableSpace }
) {
    @Synchronized
    fun prepare(stop: AtomicBoolean, source: () -> InputStream): File {
        try {
            check(!stop.get()) { "Stopped." }
            check(directory.isDirectory || directory.mkdirs()) { "Cannot prepare private model storage." }
            // Only our own interrupted imports, never downloaded originals or other files.
            directory.listFiles()?.filter { it.name.startsWith("model-import-") && it.name.endsWith(".part") }
                ?.forEach { check(it.delete()) { "Cannot clean an interrupted model import." } }
            val ready = File(directory, "qwen-verified.gguf")
            if (ready.isFile && ready.length() == expectedSize && verified(ready, stop)) return ready
            check(availableBytes() >= expectedSize + reserveBytes) {
                "Not enough free storage for a private model copy. Free at least 525 MB, then try again. The original download is unchanged."
            }
            val temporary = File.createTempFile("model-import-", ".part", directory)
            try {
                val digest = MessageDigest.getInstance("SHA-256")
                var copied = 0L
                source().use { input ->
                    FileOutputStream(temporary).use { output ->
                        val buffer = ByteArray(65536)
                        while (true) {
                            check(!stop.get()) { "Stopped." }
                            val count = input.read(buffer)
                            if (count < 0) break
                            if (count == 0) continue
                            copied += count
                            require(copied <= expectedSize) { "Model size does not match the required Qwen GGUF." }
                            digest.update(buffer, 0, count)
                            output.write(buffer, 0, count)
                        }
                        output.fd.sync()
                    }
                }
                require(copied == expectedSize && hex(digest.digest()) == expectedHash) {
                    "Model verification failed. Select the official Qwen Q4_K_M GGUF."
                }
                check(!stop.get()) { "Stopped." }
                Files.move(temporary.toPath(), ready.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
                return ready
            } finally {
                if (temporary.exists()) temporary.delete()
            }
        } catch (e: IOException) {
            throw IllegalStateException("Could not copy or read the model in private storage. Check free space and select the downloaded GGUF again.")
        } catch (e: SecurityException) {
            throw IllegalStateException("Model access was denied. Select the downloaded GGUF again.")
        }
    }

    private fun verified(file: File, stop: AtomicBoolean): Boolean {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(65536)
            while (true) {
                check(!stop.get()) { "Stopped." }
                val count = input.read(buffer)
                if (count < 0) break
                if (count > 0) digest.update(buffer, 0, count)
            }
        }
        return hex(digest.digest()) == expectedHash
    }
    private fun hex(bytes: ByteArray) = bytes.joinToString("") { "%02x".format(it) }
}
