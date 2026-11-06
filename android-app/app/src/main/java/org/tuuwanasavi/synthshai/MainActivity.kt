package org.tuuwanasavi.synthshai

import android.os.Bundle
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
    val messages = remember {
        mutableStateListOf(
            ChatLine(
                0,
                "Welcome to SYNTH_SHAI Android V0.2.3. This is an offline scripted demo, not a live AI service.",
                false
            )
        )
    }
    var draft by remember { mutableStateOf("") }
    var lastReply by remember { mutableStateOf(OfflineReplies.Reply("", OfflineReplies.Topic.NONE)) }
    val listState = rememberLazyListState()

    fun sendMessage() {
        val typed = draft.trim()
        if (typed.isEmpty()) return
        val response = OfflineReplies.reply(typed, lastReply)
        lastReply = response
        messages.add(ChatLine(nextId++, typed, true))
        messages.add(ChatLine(nextId++, response.message, false))
        // Bound session memory; never persist messages to disk or a service.
        while (messages.size > maxChatLines) messages.removeAt(0)
        draft = ""
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
                "OFFLINE DEMO  •  144 HOLD  •  No network or AI backend",
                style = MaterialTheme.typography.labelMedium,
                color = Color(0xFFB8D6FF)
            )
            Text(
                "Messages stay in this screen's memory only. This app has no live AI service.",
                style = MaterialTheme.typography.bodySmall,
                color = secondaryText
            )
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
                    enabled = draft.isNotBlank(),
                    onClick = { sendMessage() }
                ) { Text("Send") }
            }
        }
    }
}
