package org.tuuwanasavi.synthshai.auth

import org.junit.Assert.*
import org.junit.Test
import java.net.URLEncoder

/** Offline-only JVM checks. These tests never contact an OIDC issuer. */
class AndroidPkcePreflightTest {
    private val redirect = "https://login.example.invalid/android/callback"
    private var now = 1000L
    private val flow = AndroidPkcePreflight { now }

    private fun query(state: String, code: String = "fictional-auth-code"): String =
        redirect + "?state=" + URLEncoder.encode(state, "UTF-8") + "&code=" + code

    @Test fun knownRfc7636Challenge() {
        assertEquals("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            AndroidPkcePreflight.pkceChallenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"))
    }

    @Test fun generatesHighEntropyChallengeStateNonce() {
        val a = flow.begin(redirect)!!
        val b = flow.begin(redirect)!!
        for (value in listOf(a.state, a.nonce, a.codeChallenge, b.state, b.nonce)) {
            assertTrue(value.matches(Regex("[A-Za-z0-9_-]{43}")))
        }
        assertNotEquals(a.state, a.nonce)
        assertNotEquals(a.state, b.state)
        assertNotEquals(a.codeChallenge, b.codeChallenge)
    }

    @Test fun correctCallbackReturnsCodeAndVerifierForFutureExchangeOnly() {
        val start = flow.begin(redirect)!!
        val result = flow.consumeCallback(query(start.state))!!
        assertEquals("fictional-auth-code", result.authorizationCode)
        assertEquals(start.codeChallenge, AndroidPkcePreflight.pkceChallenge(result.codeVerifier))
        assertEquals(start.nonce, result.nonce)
    }

    @Test fun noPendingRequestCannotComplete() {
        assertNull(flow.consumeCallback(query("anything")))
    }

    @Test fun callbackCannotBeReplayed() {
        val start = flow.begin(redirect)!!
        assertNotNull(flow.consumeCallback(query(start.state)))
        assertNull(flow.consumeCallback(query(start.state)))
    }

    @Test fun badStateFailsAndBurnsTransaction() {
        val start = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(query("attacker")))
        assertNull(flow.consumeCallback(query(start.state)))
    }

    @Test fun wrongRedirectHostAndPathAreRejected() {
        val a = flow.begin(redirect)!!
        assertNull(flow.consumeCallback("https://login.example.invalid.attacker.test/android/callback?state=" + a.state + "&code=x"))
        val b = flow.begin(redirect)!!
        assertNull(flow.consumeCallback("https://login.example.invalid/android/callback/extra?state=" + b.state + "&code=x"))
    }

    @Test fun httpAndFragmentRedirectsAreRejected() {
        assertNull(flow.begin("http://login.example.invalid/android/callback"))
        assertNull(flow.begin(redirect + "#fragment"))
        val a = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(query(a.state) + "#evil"))
    }

    @Test fun duplicateStateAndCodeAreRejected() {
        val a = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(query(a.state) + "&state=" + a.state))
        val b = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(query(b.state) + "&code=attacker"))
    }

    @Test fun malformedPercentEncodingIsRejected() {
        val a = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(redirect + "?state=%GG&code=anything"))
        assertNull(flow.consumeCallback(query(a.state)))
    }

    @Test fun rejectsErrorAndUnexpectedOAuthParameters() {
        val a = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(redirect + "?state=" + a.state + "&error=access_denied"))
        val b = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(query(b.state) + "&id_token=something"))
    }

    @Test fun expiredAndFutureClockTransitionsAreRejected() {
        val a = flow.begin(redirect)!!
        now += 301
        assertNull(flow.consumeCallback(query(a.state)))
        val b = flow.begin(redirect)!!
        now -= 5
        assertNull(flow.consumeCallback(query(b.state)))
    }

    @Test fun explicitCancelDiscardsPendingLogin() {
        val a = flow.begin(redirect)!!
        flow.cancel()
        assertNull(flow.consumeCallback(query(a.state)))
    }

    @Test fun missingOrEmptyCodeIsRejected() {
        val a = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(redirect + "?state=" + a.state))
        val b = flow.begin(redirect)!!
        assertNull(flow.consumeCallback(query(b.state, "")))
    }

    @Test fun noSensitiveAndroidPermissionsAreNeededForThisHelper() {
        // Exercise only pure JVM state, not an HTTP/browser/token client.
        val a = flow.begin(redirect)!!
        assertNotNull(flow.consumeCallback(query(a.state)))
    }
}
