package org.tuuwanasavi.financelab;
import android.app.Activity;
import android.os.Bundle;
import android.os.SystemClock;
import android.graphics.Color;
import android.widget.*;
import org.tuuwanasavi.financelab.bank.R;

public final class BankActivity extends Activity {
 private PaymentGate gate;
 private LinearLayout page;
 private EditText recipient, amount;
 private TextView status, review, balance;
 private Button approve, submit;
 private boolean consent;
 private long approvedAt;
 private void text(String s,int size){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setPadding(0,14,0,14);page.addView(t);}
 private Button button(String title,Runnable fn){Button b=new Button(this);b.setText(title);b.setMinHeight(64);b.setOnClickListener(v->fn.run());page.addView(b);return b;}
 @Override public void onCreate(Bundle state){super.onCreate(state);gate=new PaymentGate(getPreferences(0).getBoolean("demoPaid",false));draw();}
 private void draw(){
  consent=false;ScrollView scroll=new ScrollView(this);page=new LinearLayout(this);page.setOrientation(1);page.setPadding(28,24,28,36);page.setBackgroundColor(Color.rgb(239,246,244));scroll.addView(page);setContentView(scroll);
  TextView marker=new TextView(this);marker.setId(R.id.screen);marker.setText("SHAI MOCK BANK / V1");marker.setTextSize(24);page.addView(marker);
  text("SIMULATION ONLY • No real money • No Up or MetaMask connection",16);
  balance=new TextView(this);balance.setTextSize(26);page.addView(balance);
  text("Fixed request: pay fictional Garden Energy invoice DEMO-204, AUD 126.00, from DEMO-EVERYDAY. Fee AUD 0.00.",18);
  text("Demo recipient",16);recipient=new EditText(this);recipient.setId(R.id.recipient);recipient.setSingleLine(true);recipient.setHint("DEMO-ENERGY-001");page.addView(recipient);
  text("Amount in AUD",16);amount=new EditText(this);amount.setId(R.id.amount);amount.setSingleLine(true);amount.setInputType(8194);amount.setHint("126.00");page.addView(amount);
  button("Prepare demo payment",()->{gate.prepare(recipient.getText().toString(),amount.getText().toString());consent=false;update();}).setId(R.id.prepare);
  review=new TextView(this);review.setId(R.id.review);review.setTextSize(18);review.setPadding(0,16,0,16);page.addView(review);
  CheckBox check=new CheckBox(this);check.setText("I reviewed the recipient, source, amount and fee.");check.setOnCheckedChangeListener((v,on)->{consent=on;update();});page.addView(check);
  approve=button("Approve exact demo details",()->{if(consent){approvedAt=SystemClock.elapsedRealtime();gate.approve(approvedAt);update();}});
  submit=button("Submit fictional payment",()->{if(gate.submit(SystemClock.elapsedRealtime(),recipient.getText().toString(),amount.getText().toString())){if(!getPreferences(0).edit().putBoolean("demoPaid",true).commit())gate.hold("Demo receipt could not be saved. Do not retry.");}update();});submit.setId(R.id.submit);
  button("Change recipient after approval",()->{recipient.setText("DEMO-CHANGED-999");gate.hold("Payment details changed after approval. Nothing was sent.");update();});
  button("Stop / revoke approval",()->{gate.revoke();update();});
  button("Match receipt to invoice",()->{gate.reconcile();update();});
  button("Open SHAI helper",()->{try{startActivity(new android.content.Intent().setClassName("org.tuuwanasavi.financelab.assistant","org.tuuwanasavi.financelab.HelperActivity"));}catch(Exception e){Toast.makeText(this,"Install SHAI Demo Helper first.",Toast.LENGTH_LONG).show();}});
  button("Reset fictional demo",()->{getPreferences(0).edit().clear().commit();gate=new PaymentGate(false);draw();});
  status=new TextView(this);status.setId(R.id.status);status.setTextSize(18);status.setPadding(0,20,0,20);status.setAccessibilityLiveRegion(1);page.addView(status);
  text("144 HOLD for real financial execution. Fixed scripted helper, not Qwen. Approval is not proof of identity. Restart discards pending approval; completed demo invoice remains recorded.",14);update();
 }
 private void update(){if(status==null)return;balance.setText(gate.isPaid()?"Fictional balance: AUD 2,324.00":"Fictional balance: AUD 2,450.00");review.setText(gate.state==PaymentGate.State.IDLE?"No payment prepared.":PaymentGate.REVIEW);status.setText(gate.state.name()+"\n"+gate.message);approve.setEnabled(gate.state==PaymentGate.State.PREPARED&&consent);submit.setEnabled(gate.state==PaymentGate.State.APPROVED);recipient.setEnabled(gate.state==PaymentGate.State.IDLE||gate.state==PaymentGate.State.HOLD);amount.setEnabled(recipient.isEnabled());}
 @Override protected void onDestroy(){if(gate!=null)gate.revoke();super.onDestroy();}
}
