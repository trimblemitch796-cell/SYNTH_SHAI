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

    @Test fun stagingReadinessRequiresConfiguredClientAndHttpsOrigin() {
        val webId = "355882138973-d0c984tl8mfeq9rf0bea4lrk252pon2v.apps.googleusercontent.com"
        assertFalse(stagingReady("", webId))
        assertFalse(stagingReady("http://staging.example.test", webId))
        assertFalse(stagingReady("https://staging.example.test/login", webId))
        assertFalse(stagingReady("https://staging.example.test:8443", webId))
        assertFalse(stagingReady("https://staging.example.test", "unconfigured"))
        assertTrue(stagingReady("https://staging.example.test", webId))
    }

    @Test fun malformedChallengeIdDoesNotOpenGoogleChooser() {
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                runSignInCheck({ _, _, _, _ -> challenge().put("challenge_id", "bad") }) {
                    error("Chooser must remain closed")
                }
            }
        }
    }

    @Test fun malformedCompletionTokenDoesNotOpenGoogleChooser() {
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                runSignInCheck({ _, _, _, _ -> challenge().put("completion_token", "") }) {
                    error("Chooser must remain closed")
                }
            }
        }
    }

    @Test fun rejectedGoogleExchangeDoesNotIssueLogoutOrChat() {
        val paths = mutableListOf<String>()
        assertThrows(IllegalStateException::class.java) {
            runBlocking {
                runSignInCheck({ path, _, _, _ ->
                    paths.add(path)
                    if (path == "/auth/challenge") challenge()
                    else throw IllegalStateException("Synthetic server rejection")
                }) { "synthetic-id-token" }
            }
        }
        assertEquals(listOf("/auth/challenge", "/auth/google"), paths)
    }

    @Test fun invalidShaiSessionIsNeverSentAsBearer() {
        val paths = mutableListOf<String>()
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                runSignInCheck({ path, _, _, _ ->
                    paths.add(path)
                    when (path) {
                        "/auth/challenge" -> challenge()
                        "/auth/google" -> JSONObject().put("token_type", "Bearer")
                            .put("access_token", "invalid-token")
                        else -> error("Malformed session must not reach another endpoint")
                    }
                }) { "synthetic-google-token" }
            }
        }
        assertEquals(listOf("/auth/challenge", "/auth/google"), paths)
    }

    @Test fun failedServerLogoutMustNotBeReportedAsConfirmed() {
        val paths = mutableListOf<String>()
        assertThrows(LogoutUnconfirmed::class.java) {
            runBlocking {
                runSignInCheck({ path, _, _, bearer ->
                    paths.add(path)
                    when (path) {
                        "/auth/challenge" -> challenge()
                        "/auth/google" -> JSONObject().put("token_type", "Bearer")
                            .put("access_token", "a.b.c")
                        "/auth/logout" -> {
                            assertEquals("a.b.c", bearer)
                            throw IllegalStateException("Synthetic revocation failure")
                        }
                        else -> error("Unexpected endpoint")
                    }
                }) { "synthetic-google-token" }
            }
        }
        assertEquals(listOf("/auth/challenge", "/auth/google", "/auth/logout"), paths)
    }

}
