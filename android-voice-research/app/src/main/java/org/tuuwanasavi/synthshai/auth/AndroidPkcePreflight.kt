package org.tuuwanasavi.synthshai.auth

import java.net.URI
import java.net.URLDecoder
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64

/**
 * Offline-only Android login preparation: PKCE S256, short-lived state/nonce,
 * and one-use redirect validation. This does NOT call an identity provider,
 * exchange an OAuth code, issue a SHAI session, store credentials, or enable
 * internet access. See ANDROID_LOGIN_PREFLIGHT.md before any integration.
 */
data class PkceStart(val codeChallenge: String, val state: String, val nonce: String)
data class PkceCompletion(val authorizationCode: String, val codeVerifier: String, val nonce: String)

class AndroidPkcePreflight(private val clockSeconds: () -> Long = {
    System.currentTimeMillis() / 1000L
}) {
    private data class Pending(
        val redirect: URI,
        val verifier: String,
        val state: String,
        val nonce: String,
        val created: Long
    )

    private val secureRandom = SecureRandom()
    private var pending: Pending? = null

    private fun randomBase64Url(): String {
        val entropy = ByteArray(32)
        secureRandom.nextBytes(entropy)
        return Base64.getUrlEncoder().withoutPadding().encodeToString(entropy)
    }

    /**
     * Create only a local transaction. Caller MUST later use an independently
     * reviewed system-browser + verified HTTPS App Link / PKCE provider flow.
     */
    @Synchronized
    fun begin(redirectUri: String): PkceStart? {
        val redirect = try { URI(redirectUri) } catch (_: Exception) { return null }
        if (!validHttpsRedirect(redirect)) return null
        val verifier = randomBase64Url()
        val state = randomBase64Url()
        val nonce = randomBase64Url()
        pending = Pending(redirect, verifier, state, nonce, clockSeconds())
        return PkceStart(pkceChallenge(verifier), state, nonce)
    }

    /**
     * Validates only the redirect shape, state, transaction age, and code
     * presence. It does NOT prove the code or user is authenticated.
     * Every callback attempt consumes the pending transaction, even if invalid.
     */
    @Synchronized
    fun consumeCallback(callbackUrl: String): PkceCompletion? {
        val attempt = pending ?: return null
        pending = null
        val age = clockSeconds() - attempt.created
        if (age !in 0L..300L || callbackUrl.length > 4096) return null
        val callback = try { URI(callbackUrl) } catch (_: Exception) { return null }
        if (!validHttpsRedirect(callback, allowQuery = true)) return null
        if (callback.scheme != attempt.redirect.scheme ||
            callback.rawAuthority != attempt.redirect.rawAuthority ||
            callback.rawPath != attempt.redirect.rawPath) return null
        val parameters = strictQuery(callback.rawQuery ?: return null) ?: return null
        if (parameters.keys != setOf("state", "code")) return null
        val state = parameters["state"] ?: return null
        val code = parameters["code"] ?: return null
        if (!MessageDigest.isEqual(
                state.toByteArray(StandardCharsets.UTF_8),
                attempt.state.toByteArray(StandardCharsets.UTF_8)
            )) return null
        if (code.isEmpty() || code.length > 2048 ||
            code.any { it.code < 33 || it.code > 126 }) return null
        return PkceCompletion(code, attempt.verifier, attempt.nonce)
    }

    @Synchronized
    fun cancel() { pending = null }

    private fun validHttpsRedirect(uri: URI, allowQuery: Boolean = false): Boolean =
        !uri.isOpaque && uri.scheme == "https" && !uri.host.isNullOrEmpty() &&
        uri.rawUserInfo == null && uri.rawFragment == null &&
        (allowQuery || uri.rawQuery == null) &&
        !uri.rawPath.isNullOrEmpty()

    private fun strictQuery(raw: String): Map<String, String>? {
        if (raw.isBlank() || raw.length > 4096) return null
        val parts = raw.split("&")
        if (parts.size != 2) return null
        val decoded = mutableMapOf<String, String>()
        for (part in parts) {
            val pair = part.split("=", limit = 2)
            if (pair.size != 2) return null
            val key: String
            val value: String
            try {
                key = URLDecoder.decode(pair[0], "UTF-8")
                value = URLDecoder.decode(pair[1], "UTF-8")
            } catch (_: IllegalArgumentException) {
                return null
            }
            if (key !in setOf("state", "code") || decoded.put(key, value) != null) return null
        }
        return decoded
    }

    companion object {
        /** RFC 7636 S256 PKCE transform, useful for offline specification tests. */
        fun pkceChallenge(verifier: String): String {
            val bytes = MessageDigest.getInstance("SHA-256").digest(
                verifier.toByteArray(StandardCharsets.US_ASCII)
            )
            return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
        }
    }
}
