# v0.5.1 startup follow-up

User reported a blank command window in v0.5. Root inspected the launcher and removed silent, unbounded Python/Tcl checks before application launch. A diagnostic entry point now reports live progress and saves the exact failing/hanging stage. Tool discovery no longer recursively searches installed packages before UI construction. The cause on Windows remains unconfirmed; startup.log is the next evidence if this update does not open the window.

Run START-WINDOWS.bat from a freshly extracted folder, after closing old blank windows. If still blocked, send `%LOCALAPPDATA%\BridgeLab\startup.log`. Validation: 116 tests passed, 2 skipped, compilation passed; no Windows/OPPO access.

# BridgeLab v0.5 release report

## What changed

| Request | Result |
|---|---|
| Direct PC file drop onto the mirror | Integrated upstream native drop with a configurable shared-storage destination, prepared/checked before the session. The target does not follow the Android app's current folder. |
| Manual destination setting | Overview → Download location → Change. Reopen the phone screen to apply it. Dashboard sends use the same folder. |
| Remove file browser as main workflow | Moved to optional More file options; regular PC→phone drops need no dashboard browsing. |
| Direct Android-file-manager→Explorer drag | Not implemented. Protocol and Android event/permission limitations documented; no OCR or unsafe filename guess. |
| Calls | Explicit user-confirmed phone-dialer handoff implemented. PC headset/microphone cellular audio not implemented. |
| App compatibility | Added Open on phone instead fallback using validated launcher resolution, plus better session titles. No promise that every app accepts virtual displays. |
| Beautiful, simpler UI | New navy/indigo sidebar, responsive cards, scrollable settings/help, plain statuses and control names. Technical tool browsing removed; diagnostics/logs retained. Actual Windows visual/scaling validation remains unperformed. |
| PC plug-and-play | Bundled tools selected internally. Existing runtime launches directly; if absent, guarded private Python downloader may set it up. First-time network/policy restrictions can still block setup, and no standalone EXE was built. |

## Work and checks

Six roles were assigned: calling, inbound mirror drop, reverse-drag feasibility, desktop design, packaging/testing, and Astra oversight. Followups hit the usage limit after initial deliverables/review. Root finished integration, link/canonical-path checks, installer temp cleanup, destination/session validation, plain-language statuses and final regression checks. No further agents were spawned after that interruption.

See TEST_REPORT.md for exact results. Tests cover preparation failure blocking launch, destination changes during startup, quoted path creation and linked-folder rejection using a real host shell, phone number safety, normal-app fallback validation, shutdown, and setup-source integrity. These are software checks, not Windows/OPPO acceptance.

## Important transfer behavior

Native mirror drops may replace an existing same-name file and dropped APKs install apps; this is explicitly shown in the interface. They use the backend transfer/logging path, not the dashboard's byte-count verification dialog. More file options retains safe staged phone→PC copies; it is not the requested continuous reverse-drag gesture.

## Next steps in priority order

1. Test v0.5 on the already-working ASUS TUF + OPPO setup: UI/scaling, mirror drops and destination changes, app-window fallback, dialer and close/reconnect. Use REAL_DEVICE_TEST.md and send exact failure messages/logs if any.
2. Produce and test a Windows frozen executable on a clean Windows machine. This is the gate to removing Python/script-policy dependence rather than advertising the source bootstrap as universal plug-and-play.
3. Prototype reverse drag with a cooperating Android source/file app or demonstrated OEM integration. First prove selected-file identity/URI grants and Windows virtual-file transfer without guessing or broad storage permissions. A generic companion cannot simply be assumed to solve arbitrary-app drag.
4. Prototype Windows Bluetooth phone transport/HFP in a correctly packaged native test app, then verify call uplink/downlink with the actual OPPO and PC audio devices. Do not request microphone/contact access until a concrete implementation requires it.
