package org.tuuwanasavi.synthshai

import android.os.Bundle
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
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
    private val generationStop = AtomicBoolean(false)
    override fun onStop() {
        generationStop.set(true)
        // Native release is nonblocking; an active call frees weights after its context.
        try { LocalEngine.releaseModel() } catch (_: LinkageError) { }
        super.onStop()
    }
    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        if (level >= android.content.ComponentCallbacks2.TRIM_MEMORY_RUNNING_LOW) {
            try { LocalEngine.releaseModel() } catch (_: LinkageError) { }
        }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    onSurface = readableText,
                    onSurfaceVariant = secondaryText
                )
            ) {
                ShaiOfflineScreen(generationStop)
            }
        }
    }
}

@Composable
private fun ShaiOfflineScreen(stop: AtomicBoolean) {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("local_model", 0) }
    val restored = remember { ChatHistoryCodec.decode(prefs.getString("chat_history", null)) }
    var nextId by remember { mutableStateOf(restored.size + 1) }
    val messages = remember { mutableStateListOf<ChatLine>().apply {
        restored.forEachIndexed { i, line -> add(ChatLine(i + 1, line.content, line.fromHuman)) }
    } }
    var model by remember { mutableStateOf(prefs.getString("uri", null)?.let(Uri::parse)) }
    var sourceMode by remember { mutableStateOf(false) }
    var sourceIndex by remember { mutableStateOf(0) }
    var sourcePage by remember { mutableStateOf(0) }
    var sourcePreview by remember { mutableStateOf(false) }
    fun readSource(): String {
        val name = SourceReader.files[sourceIndex]
        val bytes = context.assets.open("source_reader/$name").use { it.readBytes() }
        val hash = context.assets.open("source_reader/$name.sha256").bufferedReader().use { it.readText() }
        return SourceReader.verify(name, bytes, hash)
    }
    val ready = model != null
    var status by remember { mutableStateOf(previousGenerationExit(context, prefs) ?: if (ready) "Model ready" else "Select the Qwen2.5-0.5B-Instruct Q4_K_M file") }
    var busy by remember { mutableStateOf(false) }
    var lastTiming by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    DisposableEffect(Unit) { onDispose { stop.set(true) } }
    var draft by remember { mutableStateOf(prefs.getString("chat_draft", "").orEmpty().take(1000)) }
    val view = LocalView.current
    // Android honors this only while this view is visible. No wake-lock permission,
    // background execution or prevention of an explicit power-button lock.
    DisposableEffect(view, busy) {
        view.keepScreenOn = busy
        onDispose { view.keepScreenOn = false }
    }
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
            } catch (e: kotlinx.coroutines.CancellationException) {
                throw e
            } catch (e: OutOfMemoryError) {
                status = "The app ran out of memory. Close other apps and try a shorter message."
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
        if (uri != null) runWork("Preparing private model copy…") {
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
        if (typed.length > 16384) { status = "Message is too long. Shorten it before generating."; return }
        val selected = model ?: return
        val sourceLabel = if (sourceMode) "${SourceReader.files[sourceIndex]} section ${sourcePage + 1}" else null
        val prompt = if (sourceMode) {
            try {
                SourceReader.prompt(SourceReader.files[sourceIndex], sourcePage, readSource(), typed)
            } catch (e: Exception) {
                status = e.message ?: "Source unavailable; no answer generated."
                return
            }
        } else buildString {
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
        if (prompt.length > 32768) { status = "Conversation is too long. Clear chat or shorten the message."; return }
        runWork("Generating on this phone…") {
            prefs.edit().putLong("generation_started", System.currentTimeMillis())
                .putInt("generation_pid", android.os.Process.myPid()).commit()
            try {
            val started = android.os.SystemClock.elapsedRealtime()
            var verifiedAt = started
            val response = withContext(Dispatchers.Default) {
                withVerifiedModel(context, selected, stop) { modelPath ->
                    verifiedAt = android.os.SystemClock.elapsedRealtime()
                    LocalEngine.generate(modelPath, prompt.encodeToByteArray(), stop).decodeToString().trim()
                }
            }
            if (!stop.get()) {
                val ended = android.os.SystemClock.elapsedRealtime()
                lastTiming = "Last reply: ${(ended - started) / 1000}s · model check ${(verifiedAt - started) / 1000}s · inference ${(ended - verifiedAt) / 1000}s"
                check(response.isNotEmpty()) { "The model returned no text." }
                messages.add(ChatLine(nextId++, if (sourceLabel == null) typed else "[Source: $sourceLabel] $typed", true))
                messages.add(ChatLine(nextId++, if (sourceLabel == null) response else "[Generated explanation of $sourceLabel; check against source]\n$response", false))
                while (messages.size > maxChatLines) messages.removeAt(0)
                draft = ""
                val saved = ChatHistoryCodec.encode(messages.map { StoredChatLine(it.fromHuman, it.content) })
                withContext(Dispatchers.IO) {
                    prefs.edit().putString("chat_history", saved).remove("chat_draft").commit()
                }
            }
            } finally {
                prefs.edit().remove("generation_started").remove("generation_pid").apply()
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
                "ON-DEVICE AI  •  144 HOLD  •  Recent chat saved locally",
                style = MaterialTheme.typography.labelMedium,
                color = Color(0xFFB8D6FF)
            )
            Text(
                status,
                style = MaterialTheme.typography.bodySmall,
                color = secondaryText
            )
            if (lastTiming.isNotEmpty()) Text(lastTiming, style = MaterialTheme.typography.labelSmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (!busy) Button(onClick = { picker.launch(arrayOf("*/*")) }) { Text("Select GGUF") }
                if (busy) Button(onClick = { stop.set(true) }) { Text("Stop") }
                if (!busy && messages.isNotEmpty()) Button(onClick = { messages.clear(); draft = ""; prefs.edit().remove("chat_history").remove("chat_draft").commit(); status = "Chat cleared" }) { Text("Clear chat") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(enabled = !busy, onClick = { sourceMode = !sourceMode }) {
                    Text(if (sourceMode) "Read my code: ON" else "Read my code: OFF")
                }
                if (sourceMode) TextButton(enabled = !busy, onClick = {
                    try { readSource(); sourcePreview = true }
                    catch (e: Exception) { status = "Source unavailable; no answer generated." }
                }) { Text("Choose section") }
            }
            if (sourceMode) Text(
                "${SourceReader.files[sourceIndex]} · section ${sourcePage + 1} · read-only · question ≤300 characters. Previous chat is excluded.",
                style = MaterialTheme.typography.labelSmall
            )
            if (sourcePreview) {
                val source = runCatching { readSource() }.getOrDefault("")
                val pages = SourceReader.pages(source)
                AlertDialog(
                    onDismissRequest = { sourcePreview = false },
                    title = { Text("${SourceReader.files[sourceIndex]} ${sourcePage + 1}/${pages.size}") },
                    text = { Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                        Text(pages.getOrElse(sourcePage) { "Source unavailable" }, style = MaterialTheme.typography.bodySmall)
                        Row {
                            TextButton(onClick = { sourceIndex = (sourceIndex + 1) % SourceReader.files.size; sourcePage = 0 }) { Text("Next file") }
                            TextButton(enabled = sourcePage > 0, onClick = { sourcePage-- }) { Text("Back") }
                            TextButton(enabled = sourcePage + 1 < pages.size, onClick = { sourcePage++ }) { Text("Next") }
                        }
                    } },
                    confirmButton = { TextButton(onClick = { sourcePreview = false }) { Text("Use section") } }
                )
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
                    onValueChange = { draft = it.take(1000); prefs.edit().putString("chat_draft", draft).apply() },
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
