package org.tuuwanasavi.synthshai.gatewaycheck;

import android.app.Activity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Proxy;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;

public final class GatewayCheck extends Activity {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private Button send;
    private TextView result;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int pad = Math.round(24 * getResources().getDisplayMetrics().density);
        layout.setPadding(pad, pad, pad, pad);
        TextView info = new TextView(this);
        info.setText("144 HOLD · Seven-day trial inactive\n\nConnect the test computer by USB with the loopback fixture running. This check sends one fixed test message.");
        layout.addView(info);
        send = new Button(this);
        send.setText("Run gateway check");
        send.setAllCaps(false);
        layout.addView(send);
        result = new TextView(this);
        layout.addView(result);
        setContentView(layout);
        send.setOnClickListener(view -> {
            send.setEnabled(false);
            result.setText("Checking local gateway…");
            worker.execute(() -> {
                String outcome = request();
                runOnUiThread(() -> {
                    if (isFinishing() || isDestroyed()) return;
                    result.setText(outcome);
                    send.setEnabled(true);
                });
            });
        });
    }

    private static String request() {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL("http://127.0.0.1:18765/chat").openConnection(Proxy.NO_PROXY);
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(3000);
            connection.setReadTimeout(3000);
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setRequestProperty("Authorization", "Bearer shai-loopback-fixture-only");
            byte[] body = new JSONObject().put("message", "Android gateway check").toString().getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream output = connection.getOutputStream()) { output.write(body); }
            int status = connection.getResponseCode();
            if (status == 401) return "HTTP 401 · Session rejected";
            if (status == 429) return "HTTP 429 · Request limit reached";
            if (status == 503) return "HTTP 503 · Gateway unavailable";
            if (status != 200) return "Unexpected gateway status: " + status;
            try (InputStream input = connection.getInputStream()) {
                ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                byte[] chunk = new byte[512];
                int n;
                while ((n = input.read(chunk)) != -1) {
                    if (bytes.size() + n > 4096) return "Invalid test response";
                    bytes.write(chunk, 0, n);
                }
                JSONObject reply = new JSONObject(bytes.toString("UTF-8"));
                if (reply.length() != 1 || !"fixture received: Android gateway check".equals(reply.opt("reply")))
                    return "Invalid test response";
            }
            return "HTTP 200 · Gateway confirmed the test message";
        } catch (IOException e) {
            return "Local gateway unreachable. Check the USB connection and fixture.";
        } catch (org.json.JSONException e) {
            return "Invalid test response";
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    @Override protected void onDestroy() {
        worker.shutdownNow();
        super.onDestroy();
    }
}
