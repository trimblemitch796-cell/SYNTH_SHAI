package org.tuuwanasavi.synthshai

import android.content.Context
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.system.Os
import android.system.OsConstants
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean

internal object LocalEngine {
    init { System.loadLibrary("shai_local") }
    external fun generate(fd: Int, input: ByteArray, stop: AtomicBoolean): ByteArray
}

internal fun <T> withVerifiedModel(context: Context, uri: Uri, stop: AtomicBoolean, use: (Int) -> T): T {
    val file = context.contentResolver.openFileDescriptor(uri, "r") ?: error("File is unavailable.")
    return file.use {
        require(file.statSize == 491400032L) { "Select the 491 MB Qwen Q4_K_M file in local storage." }
        val digest = MessageDigest.getInstance("SHA-256")
        // A duplicated descriptor shares the offset. Rewind before native model loading.
        ParcelFileDescriptor.AutoCloseInputStream(ParcelFileDescriptor.dup(file.fileDescriptor)).use { input ->
            val buffer = ByteArray(65536)
            while (true) {
                check(!stop.get()) { "Stopped." }
                val n = input.read(buffer)
                if (n < 0) break
                digest.update(buffer, 0, n)
            }
        }
        val hash = digest.digest().joinToString("") { "%02x".format(it) }
        require(hash == "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db") {
            "Model verification failed. Select the official Qwen Q4_K_M GGUF."
        }
        check(!stop.get()) { "Stopped." }
        Os.lseek(file.fileDescriptor, 0, OsConstants.SEEK_SET)
        use(file.fd)
    }
}
