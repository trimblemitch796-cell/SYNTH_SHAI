package org.tuuwanasavi.synthshai.trial

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class TrialActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { TrialScreen() } }
    }
}

@Composable
private fun TrialScreen() {
    var message by remember { mutableStateOf("") }
    var sample by remember { mutableStateOf(Sample.CLOSED) }
    var result by remember { mutableStateOf("") }
    var expanded by remember { mutableStateOf(false) }
    Column(
        modifier = Modifier.fillMaxSize().systemBarsPadding().imePadding()
            .verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("SHAI Trial Preview", style = MaterialTheme.typography.headlineMedium)
        Text("144 HOLD · Seven-day trial inactive")
        Text("Rehearse a chat request on this phone. Messages stay on this screen. All responses below are samples.")
        OutlinedTextField(message, { if (it.length <= 2000) message = it },
            label = { Text("Test message") }, modifier = Modifier.fillMaxWidth())
        Box {
            OutlinedButton(onClick = { expanded = true }) { Text("Scenario: " + sample.label) }
            DropdownMenu(expanded, { expanded = false }) {
                Sample.values().forEach { choice ->
                    DropdownMenuItem(text = { Text(choice.label) }, onClick = {
                        sample = choice
                        result = ""
                        expanded = false
                    })
                }
            }
        }
        Button(onClick = {
            result = displayOutcome(sample.status, "Sample reply: " + message.trim())
        }, enabled = message.isNotBlank()) { Text("Run local preview") }
        if (result.isNotEmpty()) Text(result)
    }
}
