package org.tuuwanasavi.financelab;

/** Pure Java simulation gate. No bank connections or trusted identity claims. */
public final class PaymentGate {
    public static final String RECIPIENT = "DEMO-ENERGY-001";
    public static final long AMOUNT = 12600;
    public static final String REVIEW = "DEMO-204 | AUD 126.00 | fee 0.00 | DEMO-ENERGY-001 | DEMO-EVERYDAY";
    public enum State { IDLE, PREPARED, APPROVED, HOLD, CONFIRMED, RECONCILED }
    public State state = State.IDLE;
    public String message = "Fictional funds only. No accounts connected.";
    private String recipient;
    private long amount;
    private long expires;
    private boolean consumed;
    private boolean paid;
    public PaymentGate(boolean alreadyPaid) { paid=alreadyPaid; }
    public boolean isPaid() { return paid; }
    public long balance() { return paid ? 232400 : 245000; }
    public boolean prepare(String to, String value) {
        consumed=true;
        if(paid) return hold("Duplicate invoice blocked. Reset demo only to start a new fictional session.");
        if(!RECIPIENT.equals(to) || !"126.00".equals(value)) return hold("Request differs from the fixed fictional bill.");
        recipient=to;amount=AMOUNT;state=State.PREPARED;
        message="Review the exact details, then approve yourself.";return true;
    }
    public boolean approve(long now) {
        if(state!=State.PREPARED || paid) return hold("No valid prepared payment.");
        expires=now+120000;consumed=false;state=State.APPROVED;
        message="Exact details approved for two minutes, once only.";return true;
    }
    public boolean submit(long now, String observedRecipient, String observedAmount) {
        if(state!=State.APPROVED || consumed || paid) return hold("Missing, revoked or already-used approval.");
        if(now>=expires) return hold("Approval expired.");
        if(!RECIPIENT.equals(recipient) || amount!=AMOUNT || !recipient.equals(observedRecipient) || !"126.00".equals(observedAmount)) return hold("Payment details changed after approval.");
        consumed=true;paid=true;state=State.CONFIRMED;message="Mock payment confirmed. No real money moved.";return true;
    }
    public boolean revoke() {
        if(paid) { consumed=true;message="Future approval revoked. Submitted demo payment is not reversed.";return false; }
        return hold("You revoked approval. Nothing was sent.");
    }
    public boolean hold(String reason) { consumed=true;state=State.HOLD;message=reason;return false; }
    public void reconcile() { if(state==State.CONFIRMED){state=State.RECONCILED;message="Matched DEMO-RECEIPT-001 to DEMO-204.";} }
}
