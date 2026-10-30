# BridgeLab: 30-day personal-to-startup experiment

## The product hypothesis

A Windows + Android power user will repeatedly use a single low-friction companion to complete cross-device tasks faster than launching separate tools, and some will pay for reliably integrated workflows that existing utilities don't handle well.

**Counter-hypothesis:** scrcpy + KDE Connect + Quick Share are already sufficient, and a launcher adds no meaningful value.

## Phase 1: Seven-day personal baseline

1. For two days, use your existing setup (Phone Link / KDE Connect / scrcpy / manual transfers) without BridgeLab. Log your five most frequent cross-device tasks.
2. For the following five days, use BridgeLab for matching tasks. Keep a separate stopwatch for **time to visible first frame**; `actions.csv` reports only local command execution time, not visual latency.
3. For each task, write down time to completion, whether it worked on the first attempt, extra prompts, failure reason and whether you would repeat the workflow tomorrow.
4. Record the phone model, Android version, laptop specs, USB cable and Wi-Fi conditions. Do not share device serials.
5. Note features users *ask for* that cannot be achieved safely with standard permissions.

Suggested comparison tasks:
- Open phone and reply to a message.
- Copy an Android text snippet into a Windows document.
- Send a PDF from Windows to Android.
- Open a Windows article on Android.
- Return a camera photo from Android to Windows (baseline tools only for v0.1).

Do not automatically count an operation as "faster" just because the scrcpy process launched quickly. Measure the complete user action.

## Phase 2: Weeks 2–3, user discovery

Interview 10–15 people who use Windows + Android at least weekly. Avoid framing the question as "Would you like an Apple-like ecosystem?" That leading question will generate meaningless agreement.

Ask instead:
1. What was the **last** task where you moved something between phone and laptop?
2. How did you complete it? Show the actual steps.
3. What was the most annoying part, and how often does it occur?
4. Which tools have you already tried, and why did you stop using them?
5. Would you install an app requiring USB debugging? What would prevent you?
6. If the task took 30 seconds less, would that matter enough to change behavior?
7. What would justify a paid app when scrcpy, KDE Connect and Quick Share are free?

Offer five people a hands-on beta. Observe behavior rather than treating hypothetical payment interest as demand.

## Phase 3: Week 4, decision gates

These thresholds are **proposed go/no-go criteria**, not industry benchmarks or prior research:

| Gate | Pass criterion |
| --- | --- |
| Functional reliability | ≥95% success on top 3 workflows across test sessions |
| End-to-end speed | ≥25% median task time improvement over current workflow, or clear quality gain |
| Repeat usage | ≥3 of 5 testers choose the prototype on at least 4 of 7 days |
| Compatibility | Core features tested on ≥3 Android brands (if available) |
| Onboarding | A new tester can get working within 5 minutes with setup instructions |
| Differentiation | ≥3 testers independently describe the **same** missing capability |
| Paid demand | At least 2 people explicitly commit to a paid beta or demonstrate equivalent purchase intent |

If speed/reliability gates fail, fix the prototype. If repeat usage and differentiation fail, do **not** build a complex cross-platform ecosystem. Pivot to the one frequently painful workflow that survives interviews.

## Event instrumentation

BridgeLab writes `actions.csv` locally. It records: `time_utc, action, result, elapsed_ms, bytes`.

Cautions:
- `mirror_start` / `virtual_display` = local **process launch**, not usable-stream time.
- `open_url` = ADB command completion, not visual app-launch completion.
- `file_push` = elapsed transfer command time, not the full human task.
- Logs don't automatically capture task outcomes, UI satisfaction or phone-to-Windows operations. Use `task_benchmark_template.csv` for those.

## Where to go if it wins

Build the next feature users actually request:

- If latency matters: capture true first-frame/input latency and optimize decoding, resolution and reconnection.
- If clipboard is the pain: design an opt-in Android agent within platform clipboard constraints; do not promise universal background access.
- If app continuity matters: start with share intents, URLs and compatible app integrations, not unrestricted app-state extraction.
- If USB setup is the pain: investigate Android's official wireless debugging pairing and safer non-ADB integration modes.
- If distribution becomes important: implement a signed Windows installer, permission explanation, update mechanism and real device matrix.

Avoid introducing accounts/cloud infrastructure until a real use case justifies it.
