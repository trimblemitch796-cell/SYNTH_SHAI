# 0.3.6 warm-model research build

The user reported slow answers in 0.3.5. Inspection found that every generate call loaded and freed the model weights. This version retains at most one loaded model between foreground requests. It creates a fresh conversation context for every request, preserving the existing explicit prompt/history behavior. The SHA-256 model check still runs on every request; verification is not bypassed for speed.

Leaving the activity sets its generation stop flag and requests weight release. Memory-pressure callbacks also request release. Native release never waits for an active generation lock: the active request destroys its context before releasing weights on exit. Cancellation remains cooperative; model loading and one native decode operation are not instantly interruptible. Returning after release requires a cold load. Retention trades higher memory use between messages for avoiding repeated model loads; no phone speedup is claimed yet.

The UI records total reply time, model-check time, and inference time (including any cold model load, prompt processing and decoding). First-response latency and decoding speed are not directly improved. No persistent model training or source editing is added. 144 HOLD remains a display label, not an output safety filter.

Validation: local C++ cache checks cover reuse, replacing a key without simultaneous model allocations, explicit release, repeated release, and retry after load failure. Address/undefined sanitizers passed with leak detection disabled locally because LeakSanitizer cannot run under this host's tracing environment. The CI native test step runs full sanitizers. Android build and actual phone performance remain pending until CI/device evidence is recorded.

Phone comparison: record the same short question twice while staying in the app, then leave and return and repeat it. Compare the displayed phase timings, not just subjective responsiveness. Check Stop, backgrounding during generation and reopening. A slower second response can still occur from prompt length, thermal throttling or OS memory pressure.

Version 12 / 0.3.6-warm-model installs separately as SHAI 0.3.6 Speed Test (package suffix .localchat.warmmodel036). Existing source-reader installation and chats remain separate. Select the GGUF again. Compare identical questions in both apps; each keeps its own private model copy.
