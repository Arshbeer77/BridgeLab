# BridgeLab v0.5 bounded oversight review

Scope: two focused source/documentation reviews of new bootstrap setup, mirror drops, dialer handoff, UI truth, and existing child-process lifecycle. This review does not establish Windows, OPPO, or native drag compatibility.

## Release boundaries

- Dropping a PC file onto the mirrored phone uses a fixed destination chosen before the mirror starts. It does not discover the folder currently open in the phone's file manager.
- Upstream scrcpy's dropped lowercase `.apk` behavior installs a package rather than copying it as an ordinary file. Ordinary same-name pushes may replace files. Explain these behaviors before presenting mirror drop as available.
- Exact dragging from an arbitrary Android app in the mirror into Windows Explorer is not implemented. A staged file-browser copy, feasibility document, or future source design must not be represented as fulfilling that requested interaction.
- The phone dialer handoff uses `ACTION_DIAL`; the user still presses Call. It is not full cellular calling with the PC headset/microphone and requests no speculative call/microphone permissions.
- App windows run on the selected real phone and share its accounts/data. Capability checks and Linux tests do not prove ColorOS compatibility.
- New UI simplicity must preserve explicit selected-device targeting, operation status, safe close behavior, and access to useful diagnostics when an action fails.
- Automatic setup may reuse Python or download the pinned official installer for a private per-user runtime. It must verify both hash and PSF Authenticode before execution, honor machine policy, and avoid administrator/PATH changes.

## First review

The dialer implementation uses a strict ASCII phone-number allowlist, selected-device capture and recheck, a bounded request without retry, and no number logging. Bootstrap code checks the pinned HTTPS download, SHA-256, signer, per-user install options, and resulting Python/Tk. The batch launcher no longer overrides execution policy.

Corrections requested:

1. Use a unique temporary installer directory and unconditional cleanup. A fixed temporary filename lets simultaneous launches overwrite or delete each other's download; scattered cleanup also misses exceptional failures.
2. Canonicalize the remote mirror-drop destination and recheck shared-storage boundaries. A lexical `/sdcard/...` check alone can follow an existing link outside the intended location.
3. Preserve explicit UI language for fixed folder, APK install behavior, replacement behavior, unavailable exact outgoing drag, and unavailable full headset calling.

## Validation and recommendation

Final focused review pending integration. No broad test suite has been repeated by this reviewer for v0.5. The integrator's test report and archive verification are the release evidence; Windows/phone acceptance remains a separate gate. Recommend only a clearly limited software-tested beta candidate once the raised corrections and final integration review are complete.

## Integrator disposition after agent interruption

Astra's first review above is retained as authored. Follow-up agents hit usage limits; no final independent Astra approval is claimed. The root integrator addressed unique installer temp/finally cleanup and descendant-link/canonical destination checks, with regression tests. It completed destination integration, fallback app launch UI and source-package launch paths. The normal interface no longer exposes tool browsing; technical reports remain under Help. Final test/archive results belong to TEST_REPORT.md. GUI/Windows/OPPO behavior remains unvalidated.
