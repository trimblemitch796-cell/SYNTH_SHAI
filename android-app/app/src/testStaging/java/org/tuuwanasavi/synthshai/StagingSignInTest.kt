package org.tuuwanasavi.synthshai

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class StagingSignInTest {
    private val nonce = "n".repeat(43)
    private fun challenge() = JSONObject().put("nonce", nonce)
        .put("challenge_id", "i".repeat(43)).put("completion_token", "b".repeat(43))

    @Test fun validExchangeUsesSeparateSessionForLogout() = runBlocking {
        val paths = mutableListOf<String>()
        runSignInCheck({ path, body, _, bearer ->
            paths.add(path)
            when (path) {
                "/auth/challenge" -> challenge()
                "/auth/google" -> {
                    assertNull(bearer)
                    assertEquals("provider-fixture", body.getString("google_id_token"))
                    assertEquals("b".repeat(43), body.getString("completion_token"))
                    JSONObject().put("token_type", "Bearer").put("access_token", "a.b.c")
                }
                "/auth/logout" -> {
                    assertEquals("a.b.c", bearer)
                    JSONObject()
                }
                else -> error("Unexpected path")
            }
        }) {
            assertEquals(nonce, it)
            "provider-fixture"
        }
        assertEquals(listOf("/auth/challenge", "/auth/google", "/auth/logout"), paths)
    }

    @Test fun cancelledChooserCannotFinishExchange() {
        val paths = mutableListOf<String>()
        assertThrows(CancellationException::class.java) {
            runBlocking {
                runSignInCheck({ path, _, _, _ -> paths.add(path); challenge() }) {
                    throw CancellationException("fixture cancellation")
                }
            }
        }
        assertEquals(listOf("/auth/challenge"), paths)
    }

    @Test fun malformedChallengeCannotOpenChooser() {
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                runSignInCheck({ _, _, _, _ -> challenge().put("nonce", "bad") }) {
                    error("Unexpected chooser invocation")
                }
            }
        }
    }
}
