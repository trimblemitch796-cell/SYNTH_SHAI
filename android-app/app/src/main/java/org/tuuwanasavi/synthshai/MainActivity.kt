package org.tuuwanasavi.synthshai

import android.os.Bundle
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.platform.LocalContext
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp

private val background = Color(0xFF0D1526)
private val readableText = Color(0xFFF3F7FF)
private val secondaryText = Color(0xFFCEDCF0)
private const val maxChatLines = 120

private data class ChatLine(val id: Int, val content: String, val fromHuman: Boolean)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    onSurface = readableText,
                    onSurfaceVariant = secondaryText
                )
            ) {
                ShaiOfflineScreen()
            }
        }
    }
}

@Composable
private fun ShaiOfflineScreen() {
    var nextId by remember { mutableStateOf(1) }
    val messages = remember { mutableStateListOf<ChatLine>() }
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("local_model", 0) }
    var model by remember { mutableStateOf(prefs.getString("uri", null)?.let(Uri::parse)) }
    val ready = model != null
    var status by remember { mutableStateOf(if (ready) "Model ready" else "Select the Qwen2.5-0.5B-Instruct Q4_K_M file") }
    var busy by remember { mutableStateOf(false) }
    val stop = remember { AtomicBoolean(false) }
    val scope = rememberCoroutineScope()
    DisposableEffect(Unit) { onDispose { stop.set(true) } }
    var draft by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    fun runWork(label: String, work: suspend () -> Unit) {
        if (busy) return
        busy = true
        stop.set(false)
        status = label
        scope.launch {
            try {
                work()
                status = if (stop.get()) "Stopped" else "Model ready"
            } catch (e: Exception) {
                status = e.localizedMessage ?: "Local operation failed"
            } catch (e: LinkageError) {
                status = "The native runtime could not load on this device."
            } finally {
                busy = false
            }
        }
    }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) runWork("Verifying model…") {
            withContext(Dispatchers.IO) {
                withVerifiedModel(context, uri, stop) { }
                context.contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            val previous = model
            prefs.edit().putString("uri", uri.toString()).apply()
            model = uri
            if (previous != null && previous != uri) runCatching {
                context.contentResolver.releasePersistableUriPermission(previous, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
        }
    }

    fun sendMessage() {
        val typed = draft.trim()
        if (typed.isEmpty() || busy || !ready) return
        val selected = model ?: return
        val prompt = buildString {
            append("<|im_start|>system\nYou are SHAI, a helpful offline text companion.<|im_end|>\n")
            fun turn(role: String, text: String) {
                append("<|im_start|>").append(role).append('\n')
                append(text.replace("<|", "< |")).append("<|im_end|>\n")
            }
            // Keep only complete recent exchanges. Native code enforces the token limit.
            messages.takeLast(4).forEach { turn(if (it.fromHuman) "user" else "assistant", it.content) }
            turn("user", typed)
            append("<|im_start|>assistant\n")
        }
        runWork("Generating on this phone…") {
            val response = withContext(Dispatchers.Default) {
                withVerifiedModel(context, selected, stop) { fd ->
                    LocalEngine.generate(fd, prompt.encodeToByteArray(), stop).decodeToString().trim()
                }
            }
            if (!stop.get()) {
                check(response.isNotEmpty()) { "The model returned no text." }
                messages.add(ChatLine(nextId++, typed, true))
                messages.add(ChatLine(nextId++, response, false))
                while (messages.size > maxChatLines) messages.removeAt(0)
                draft = ""
            }
        }
    }

    LaunchedEffect(messages.size, messages.lastOrNull()?.id) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.lastIndex)
    }

    Surface(modifier = Modifier.fillMaxSize(), color = background, contentColor = readableText) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .imePadding()
                .navigationBarsPadding()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                "SYNTH_SHAI",
                style = MaterialTheme.typography.headlineMedium,
                color = readableText
            )
            Text(
                "ON-DEVICE AI  •  144 HOLD",
                style = MaterialTheme.typography.labelMedium,
                color = Color(0xFFB8D6FF)
            )
            Text(
                status,
                style = MaterialTheme.typography.bodySmall,
                color = secondaryText
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (!busy) Button(onClick = { picker.launch(arrayOf("*/*")) }) { Text("Select GGUF") }
                if (busy) Button(onClick = { stop.set(true) }) { Text("Stop") }
                if (!busy && messages.isNotEmpty()) Button(onClick = { messages.clear(); draft = ""; status = "Chat cleared" }) { Text("Clear chat") }
            }
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(messages, key = { it.id }) { line ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = if (line.fromHuman) Arrangement.End else Arrangement.Start
                    ) {
                        Card(
                            modifier = Modifier.fillMaxWidth(0.88f),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (line.fromHuman) Color(0xFF264D75) else Color(0xFF253044),
                                contentColor = readableText
                            )
                        ) {
                            Text(
                                line.content,
                                modifier = Modifier.padding(12.dp),
                                color = readableText
                            )
                        }
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.Bottom
            ) {
                OutlinedTextField(
                    value = draft,
                    enabled = ready && !busy,
                    onValueChange = { draft = it.take(1000) },
                    label = { Text("Message SHAI (offline)") },
                    modifier = Modifier.weight(1f),
                    maxLines = 3,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                    keyboardActions = KeyboardActions(onSend = { sendMessage() }),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = readableText,
                        unfocusedTextColor = readableText,
                        focusedLabelColor = secondaryText,
                        unfocusedLabelColor = secondaryText,
                        focusedBorderColor = Color(0xFFB9A2FF),
                        unfocusedBorderColor = secondaryText
                    )
                )
                Spacer(modifier = Modifier.width(8.dp))
                Button(
                    enabled = ready && !busy && draft.isNotBlank(),
                    onClick = { sendMessage() }
                ) { Text("Send") }
            }
        }
    }
}
