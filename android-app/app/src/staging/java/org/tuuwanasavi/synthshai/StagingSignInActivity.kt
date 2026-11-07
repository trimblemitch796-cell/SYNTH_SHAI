package org.tuuwanasavi.synthshai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URI
import javax.net.ssl.HttpsURLConnection

class StagingSignInActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val origin = getString(R.string.signin_origin)
            val client = getString(R.string.signin_client)
            val ready = stagingReady(origin, client)
            val scope = rememberCoroutineScope()
            var busy by remember { mutableStateOf(false) }
            var message by remember { mutableStateOf("") }
            Column(Modifier.padding(24.dp)) {
                Text("SHAI staging sign-in check")
                Button(enabled = ready && !busy, onClick = {
                    busy = true
                    message = "Opening sign-in…"
                    scope.launch {
                        try {
                            checkSignIn(origin, client)
                            message = "SHAI session issued and signed out."
                        } catch (e: CancellationException) {
                            throw e
                        } catch (e: GetCredentialCancellationException) {
                            message = "Sign-in cancelled."
                        } catch (e: LogoutUnconfirmed) {
                            message = "Session issued. Server sign-out could not be confirmed."
                        } catch (e: Exception) {
                            message = "Sign-in could not be verified."
                        } finally {
                            busy = false
                        }
                    }
                }) { Text("Sign in with Google") }
                Text(if (ready) message else "Staging server and Google client configuration required.")
            }
        }
    }

    private suspend fun checkSignIn(origin: String, client: String) {
        runSignInCheck({ path, body, expected, bearer -> post(origin, path, body, expected, bearer) }) { nonce ->
            val option = GetSignInWithGoogleOption.Builder(client).setNonce(nonce).build()
            val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
            val credential = CredentialManager.create(this@StagingSignInActivity).getCredential(this@StagingSignInActivity, request).credential
            require(credential is CustomCredential &&
                credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL)
            GoogleIdTokenCredential.createFrom(credential.data).idToken
        }
    }
}

internal suspend fun runSignInCheck(
    send: suspend (String, JSONObject, Int, String?) -> JSONObject,
    choose: suspend (String) -> String
) {
    val challenge = send("/auth/challenge",
        JSONObject().put("flow", "google-id-token-v1").put("platform", "android"), 201, null)
    val nonce = challenge.getString("nonce")
    val id = challenge.getString("challenge_id")
    val completion = challenge.getString("completion_token")
    require(listOf(nonce, id, completion).all { OPAQUE.matches(it) })
    val token = choose(nonce)
    val session = send("/auth/google", JSONObject().put("challenge_id", id)
        .put("completion_token", completion).put("google_id_token", token), 200, null)
    require(session.getString("token_type") == "Bearer")
    val bearer = session.getString("access_token")
    require(bearer.length <= 4096 && JWT.matches(bearer))
    try {
        send("/auth/logout", JSONObject(), 204, bearer)
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        throw LogoutUnconfirmed()
    }
}

internal class LogoutUnconfirmed : Exception()
private val OPAQUE = Regex("[A-Za-z0-9_-]{43}")
private val JWT = Regex("[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+")

internal fun stagingReady(origin: String, client: String): Boolean =
    client.matches(Regex("[0-9]+-[A-Za-z0-9_-]+\\.apps\\.googleusercontent\\.com")) &&
        validOrigin(origin)

private fun validOrigin(value: String): Boolean = runCatching {
    val uri = URI(value)
    uri.scheme == "https" && uri.host != null && uri.userInfo == null &&
        uri.query == null && uri.fragment == null && uri.rawPath.isEmpty() &&
        (uri.port == -1 || uri.port == 443)
}.getOrDefault(false)

private suspend fun post(origin: String, path: String, body: JSONObject, expected: Int,
                         bearer: String? = null): JSONObject = withContext(Dispatchers.IO) {
    val connection = URI(origin + path).toURL().openConnection() as HttpsURLConnection
    try {
        connection.instanceFollowRedirects = false
        connection.useCaches = false
        connection.connectTimeout = 5000
        connection.readTimeout = 8000
        connection.requestMethod = "POST"
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json")
        bearer?.let { connection.setRequestProperty("Authorization", "Bearer " + it) }
        connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        check(connection.responseCode == expected)
        if (expected == 204) return@withContext JSONObject()
        val bytes = connection.inputStream.use { input ->
            val buffer = java.io.ByteArrayOutputStream()
            val chunk = ByteArray(1024)
            while (true) {
                val count = input.read(chunk)
                if (count < 0) break
                require(buffer.size() + count <= 8192)
                buffer.write(chunk, 0, count)
            }
            buffer.toByteArray()
        }
        JSONObject(String(bytes, Charsets.UTF_8))
    } finally {
        connection.disconnect()
    }
}
