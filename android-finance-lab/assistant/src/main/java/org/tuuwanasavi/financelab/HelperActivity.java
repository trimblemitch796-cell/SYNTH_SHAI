package org.tuuwanasavi.financelab;
import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.provider.Settings;
import android.widget.*;

public final class HelperActivity extends Activity {
 private LinearLayout page;
 private void text(String value,int size){TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setPadding(0,16,0,16);page.addView(t);}
 private void button(String title,Runnable action){Button b=new Button(this);b.setText(title);b.setMinHeight(64);b.setOnClickListener(v->action.run());page.addView(b);}
 @Override public void onCreate(Bundle b){super.onCreate(b);ScrollView sc=new ScrollView(this);page=new LinearLayout(this);page.setOrientation(1);page.setPadding(28,24,28,36);sc.addView(page);setContentView(sc);
 text("SHAI Demo Helper",28);text("MOCK BANK ONLY / 144 HOLD",18);
 text("This helper can read and interact with the SHAI Mock Bank screens only. It follows one fixed fictional AUD 126.00 request. It cannot control Up, MetaMask or other apps. No screen contents are saved or transmitted. No Qwen connection.",18);
 text("Android accessibility access must be enabled by you. Enable only if you want this demo interaction. You can switch it off in Android settings at any time.",16);
 button("Open accessibility settings",()->startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
 button("Prepare fixed demo request",()->start(false));
 text("In the mock bank, review the details and approve yourself. Then open this helper again to verify and submit the approved fictional payment.",16);
 button("Verify and submit approved demo",()->start(true));
 button("Stop helper",()->{MockOnlyService.stop("Stopped by user.");Toast.makeText(this,"144 HOLD: helper stopped.",Toast.LENGTH_LONG).show();});
 text("No credentials needed. Two separate test apps; your existing SHAI chat app is unchanged. This prototype is not production security or a financial service.",14);
 }
 private void start(boolean submit){if(!MockOnlyService.connected()){Toast.makeText(this,"Enable SHAI mock-bank helper in accessibility settings first.",Toast.LENGTH_LONG).show();return;}
 MockOnlyService.arm(submit);try{startActivity(new Intent().setClassName("org.tuuwanasavi.financelab.bank","org.tuuwanasavi.financelab.BankActivity").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));}catch(Exception e){MockOnlyService.stop("Mock bank missing.");Toast.makeText(this,"Install SHAI Mock Bank first.",Toast.LENGTH_LONG).show();}}
}
