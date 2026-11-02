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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

private data class ChatLine(val content: String, val fromHuman: Boolean)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                ShaiOfflineScreen()
            }
        }
    }
}

@Composable
private fun ShaiOfflineScreen() {
    val messages = remember {
        mutableStateListOf(
            ChatLine("Welcome to SYNTH_SHAI Android V0.1. This is an offline scripted demo, not a live AI service.", false)
        )
    }
    var draft by remember { mutableStateOf("") }

    Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFF0D1526)) {
        Column(
            modifier = Modifier.fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("SYNTH_SHAI", style = MaterialTheme.typography.headlineMedium)
            Text(
                "OFFLINE DEMO  •  144 HOLD  •  No network or AI backend",
                style = MaterialTheme.typography.labelMedium,
                color = Color(0xFFB8D6FF)
            )
            Text(
                "You are in control. Messages are kept in this screen only; they are not sent or saved.",
                style = MaterialTheme.typography.bodySmall
            )
            LazyColumn(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(messages) { line ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = if (line.fromHuman) Arrangement.End else Arrangement.Start
                    ) {
                        Card(
                            modifier = Modifier.fillMaxWidth(0.88f),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (line.fromHuman) Color(0xFF264D75) else Color(0xFF253044)
                            )
                        ) {
                            Text(line.content, modifier = Modifier.padding(12.dp))
                        }
                    }
                }
            }
            Row(modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(
                    value = draft,
                    onValueChange = { draft = it.take(1000) },
                    label = { Text("Message SHAI (offline)") },
                    modifier = Modifier.weight(1f),
                    maxLines = 3
                )
                Spacer(modifier = Modifier.width(8.dp))
                Button(
                    enabled = draft.isNotBlank(),
                    onClick = {
                        val typed = draft.trim()
                        if (typed.isNotEmpty()) {
                            messages.add(ChatLine(typed, true))
                            messages.add(ChatLine(OfflineReplies.respond(typed), false))
                            draft = ""
                        }
                    }
                ) { Text("Send") }
            }
        }
    }
}
