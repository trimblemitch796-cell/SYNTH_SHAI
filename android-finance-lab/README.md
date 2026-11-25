# SHAI Android Finance Mock Lab v0.1

Created by Mitchell John Eric Trimble. **144 HOLD for all real financial execution.**

Two new, isolated Android packages. No changes to the existing local-chat app. No Internet permission, bank connection, wallet connection, credentials, Qwen inference or real money. The names SHAI/USHAI describe this demonstration workflow; they do not establish independent security or identity.

## What this adds

- SHAI Mock Bank: a fixed fictional AUD 126.00 electricity bill, review checkbox, human approval, two-minute expiry, revoke, changed-recipient hold, receipt reconciliation and duplicate prevention. The fictional paid flag survives process restart. Pending approvals do not.
- SHAI Demo Helper: an opt-in accessibility service confined to `org.tuuwanasavi.financelab.bank`. A fixed user-triggered sequence fills and prepares that bill. A separate explicit user command verifies the visible approved details and clicks mock submit once. It never clicks the approval button.
- No coordinate fallback, gestures, arbitrary commands or other target packages. It checks active package, version marker, unique resource IDs, recipient, amount, review text and approval status. The mock bank rechecks authority at submission.

## Install and try (device verification pending)

1. Install `SHAI-Mock-Bank-v01.apk` and `SHAI-Demo-Helper-v01.apk`. These are separate debug apps, not updates to local chat.
2. Open SHAI Demo Helper. Read the access explanation. If you choose, use its accessibility-settings button to enable **SHAI mock-bank helper only**. Android may restrict accessibility for sideloaded apps; do not weaken device protections just to run this prototype. Report any restriction for review.
3. Tap **Prepare fixed demo request**. Expected: mock bank opens, fictional recipient and amount are filled and prepared, then the helper stops.
4. In the mock bank, read the review details, select the checkbox, and tap **Approve exact demo details**.
5. Tap **Open SHAI helper**, then **Verify and submit approved demo** within two minutes. Expected: a single fictional confirmation and balance AUD 2,324.00.
6. To test HOLD: reset the fictional demo, repeat preparation and approval, then tap **Change recipient after approval** or **Stop / revoke approval** before requesting helper submission. Expected: HOLD, with no new mock payment.
7. Repeat submission after confirmation: it must not debit twice. Restart the mock bank: the paid invoice remains blocked until explicit demo reset.
8. Disable the helper in Android accessibility settings when finished.

The helper's armed interaction expires after 15 seconds and is cleared on interruption or service destruction. Leaving the expected screen causes HOLD when it next attempts a step. It does not persist screen data or send data anywhere. Android's accessibility permission is powerful even though this source restricts its target: inspect the code before enabling it.

## Verification

CI compiles both APKs and runs `tests/GateTest.java` against the actual Java payment gate. It also checks APK permissions. A successful compile is not evidence of successful cross-app interaction. Physical-device/emulator interaction remains unverified until separately recorded.

Local gate checks:

```sh
mkdir -p /tmp/finance-tests
javac -d /tmp/finance-tests bank/src/main/java/org/tuuwanasavi/financelab/PaymentGate.java tests/GateTest.java
java -cp /tmp/finance-tests GateTest
```

## Limitations and next evidence

This is a deterministic accessibility research helper, not an autonomous agent or an Up integration. User approval is not trusted identity. Package name checks are not signature attestation. The local mock gate is not independent USHAI enforcement; the UI's reviewed details are fixtures, not bank data. The demo reset deliberately clears fictional payment history. No durable production audit, database transaction, external payment idempotency or unknown-bank-outcome recovery is claimed. Real banking routes and distribution policy require separate review.

Next: verify the two-app flow and package/screen mismatch behaviour on an isolated emulator, then on the user's phone with consent. Live money remains HOLD.
