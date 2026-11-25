import org.tuuwanasavi.financelab.PaymentGate;
public final class GateTest {
 static int n;static void yes(boolean x){n++;if(!x)throw new AssertionError("Check "+n);}
 static PaymentGate ready(){PaymentGate g=new PaymentGate(false);g.prepare("DEMO-ENERGY-001","126.00");g.approve(1000);return g;}
 public static void main(String[] args){
 PaymentGate g=ready();yes(g.submit(1001,"DEMO-ENERGY-001","126.00"));yes(g.balance()==232400);yes(!g.submit(1002,"DEMO-ENERGY-001","126.00"));yes(g.balance()==232400);
 g=ready();g.revoke();yes(!g.submit(1001,"DEMO-ENERGY-001","126.00"));yes(g.balance()==245000);
 g=ready();yes(!g.submit(121000,"DEMO-ENERGY-001","126.00"));
 g=ready();yes(!g.submit(1001,"DEMO-CHANGED","126.00"));
 g=ready();yes(!g.submit(1001,"DEMO-ENERGY-001","126.01"));
 g=new PaymentGate(false);yes(!g.submit(1,"DEMO-ENERGY-001","126.00"));yes(!g.approve(1));yes(!g.prepare("unknown","126.00"));yes(!g.prepare("DEMO-ENERGY-001","NaN"));
 g=new PaymentGate(true);yes(!g.prepare("DEMO-ENERGY-001","126.00"));
 g=ready();g.submit(1001,"DEMO-ENERGY-001","126.00");g.reconcile();yes(g.state==PaymentGate.State.RECONCILED);g.revoke();yes(g.balance()==232400);
 System.out.println(n+" gate assertions passed; simulation only.");
 }
}
