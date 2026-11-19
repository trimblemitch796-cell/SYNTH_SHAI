package org.tuuwanasavi.synthshai

import android.content.Context
import android.net.Uri
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

internal object LocalEngine {
    init { System.loadLibrary("shai_local") }
    external fun generate(modelPath: String, input: ByteArray, stop: AtomicBoolean): ByteArray
}

private val modelStorageLock = Any()
internal fun <T> withVerifiedModel(context: Context, uri: Uri, stop: AtomicBoolean, use: (String) -> T): T =
    synchronized(modelStorageLock) {
        val store = VerifiedModelStore(File(context.noBackupFilesDir, "verified-model"),
            491400032L, "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db")
        val model = store.prepare(stop) {
            context.contentResolver.openInputStream(uri) ?: error("The selected file is unavailable.")
        }
        check(!stop.get()) { "Stopped." }
        use(model.absolutePath)
    }
