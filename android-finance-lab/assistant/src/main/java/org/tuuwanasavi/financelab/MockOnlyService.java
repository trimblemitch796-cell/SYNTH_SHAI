package org.tuuwanasavi.financelab;
import android.accessibilityservice.AccessibilityService;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.Toast;
import java.util.List;

/** Explicit one-shot, fixed workflow. Never uses coordinates, gestures or arbitrary packages. */
public final class MockOnlyService extends AccessibilityService {
 private static final String PKG="org.tuuwanasavi.financelab.bank";
 private static final String REVIEW="DEMO-204 | AUD 126.00 | fee 0.00 | DEMO-ENERGY-001 | DEMO-EVERYDAY";
 private static MockOnlyService instance;
 private final Handler handler=new Handler(Looper.getMainLooper());
 private int phase=0;
 private long deadline;
 private boolean armed=false;
 private final Runnable tick=this::step;
 public static boolean connected(){return instance!=null;}
 public static void arm(boolean submit){if(instance==null)return;instance.handler.removeCallbacks(instance.tick);instance.phase=submit?3:0;instance.deadline=SystemClock.elapsedRealtime()+15000;instance.armed=true;instance.handler.postDelayed(instance.tick,600);}
 public static void stop(String reason){if(instance!=null){instance.armed=false;instance.handler.removeCallbacks(instance.tick);}}
 @Override protected void onServiceConnected(){instance=this;}
 @Override public void onInterrupt(){stop("Interrupted");}
 @Override public void onDestroy(){stop("Disconnected");instance=null;super.onDestroy();}
 @Override public void onAccessibilityEvent(AccessibilityEvent e){if(armed && PKG.contentEquals(e.getPackageName()==null?"":e.getPackageName())){handler.removeCallbacks(tick);handler.postDelayed(tick,250);}}
 private void end(String message){stop(message);Toast.makeText(this,message,Toast.LENGTH_LONG).show();}
 private AccessibilityNodeInfo node(AccessibilityNodeInfo root,String id){List<AccessibilityNodeInfo> nodes=root.findAccessibilityNodeInfosByViewId(PKG+":id/"+id);return nodes.size()==1?nodes.get(0):null;}
 private String value(AccessibilityNodeInfo n){return n==null||n.getText()==null?"":n.getText().toString();}
 private boolean set(AccessibilityNodeInfo n,String text){if(n==null||!n.isEditable()||!n.isEnabled())return false;Bundle args=new Bundle();args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,text);return n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,args);}
 private boolean click(AccessibilityNodeInfo n){return n!=null&&n.isEnabled()&&n.isClickable()&&n.performAction(AccessibilityNodeInfo.ACTION_CLICK);}
 private void step(){if(!armed)return;if(SystemClock.elapsedRealtime()>=deadline){end("144 HOLD: helper session expired.");return;}
 AccessibilityNodeInfo root=getRootInActiveWindow();
 if(root==null||!PKG.contentEquals(root.getPackageName()==null?"":root.getPackageName())){end("144 HOLD: expected mock bank is not the active app.");return;}
 if(!"SHAI MOCK BANK / V1".equals(value(node(root,"screen")))){end("144 HOLD: unknown mock screen.");return;}
 String status=value(node(root,"status"));boolean ok=false;
 if(phase==0){if(!status.startsWith("IDLE\n")){end("144 HOLD: reset the mock bank before preparing.");return;}ok=set(node(root,"recipient"),"DEMO-ENERGY-001");phase=1;}
 else if(phase==1){ok=set(node(root,"amount"),"126.00");phase=2;}
 else if(phase==2){if(!"DEMO-ENERGY-001".equals(value(node(root,"recipient")))||!"126.00".equals(value(node(root,"amount")))){end("144 HOLD: entered details do not match.");return;}armed=false;ok=click(node(root,"prepare"));end(ok?"Prepared. Review and approve yourself.":"144 HOLD: prepare action failed.");return;}
 else if(phase==3){if(!status.startsWith("APPROVED\n")||!REVIEW.equals(value(node(root,"review")))||!"DEMO-ENERGY-001".equals(value(node(root,"recipient")))||!"126.00".equals(value(node(root,"amount")))){end("144 HOLD: exact approved details are missing or changed.");return;}armed=false;ok=click(node(root,"submit"));end(ok?"Submitted to the mock bank. Read its final status.":"144 HOLD: mock submit failed.");return;}
 if(!ok){end("144 HOLD: screen action failed.");return;}handler.removeCallbacks(tick);handler.postDelayed(tick,300);
 }
}
