# BridgeLab v0.5.1 test report

Run date: 2026-10-30. Linux x86_64, CPython 3.12.14, isolated virtual environment, no third-party Python packages for the suite.

## Final results

`python -m unittest discover -v`: **118 discovered; 116 passed; 2 intentionally skipped; 0 failures.** The skips are the inherited checks for an optional bundled Python installer, absent from this source ZIP. `python -m compileall -q .` passed.

Coverage retains v0.4 command validation, session consent/Stop/reconnect contexts, background shutdown, app lifecycle and safe file handling. New checks cover mirror-drop target aliases/private-path restrictions, preparation errors, target changes while launch is pending, strict dialer-number validation and intent results, validated normal-phone app launch/failure/timeout, real Tcl plain-status variables, and bootstrap source/hash/signature/order/per-user/temp-cleanup constraints.

A real host-shell protocol check verifies quoted folder creation with spaces, apostrophes and shell punctuation, and confirms a symlinked descendant fails without creating files outside the destination. Existing host-shell listing tests remain. These are host-shell checks, not Android-device tests. Setup tests inspect the script source; PowerShell itself was not executed.

## Environment and unperformed checks

- GUI launch attempted: failed at Tk initialization with no DISPLAY. No rendered screenshot, actual Windows scaling, native Explorer drop, screen-reader pass or visual-layout signoff is claimed.
- No Windows VM/Wine/PowerShell or connected phone. No frozen BridgeLab.exe was built. The Windows workflow is an unexecuted recipe.
- Native mirror dropping uses the official bundled backend; destination command/arguments are tested, not an actual Windows-to-OPPO transfer here. APK install and same-name replacement semantics are explicitly disclosed in the UI.
- User reports v0.4 screen control and app windows working; that evidence does not certify v0.5.
- Exact reverse drag and full PC-headset cellular-call audio are not implemented. Their research/design reports are not passing implementations.
- First-run runtime download/signature/install and machine-policy behavior need a clean Windows-user test. Existing runtime direct-launch wiring is source-tested, not Windows-executed.

## Release integrity and review

All 16 bundled scrcpy runtime files are compared byte-for-byte against the pinned official release, whose ZIP SHA-256 is b12a2c4ee8be317422451fc7dcf8ee20a71b5ea7ef9ad73ddd825a25316227a5. Final ZIP CRC/per-file hashes and a separately saved/downloaded copy are checked during packaging before delivery; this establishes archive integrity, not device compatibility.

Six roles were assigned; Astra completed an initial bounded review. Usage limits interrupted followups. Root finished the raised temporary-file/link-boundary corrections and integration tests; no final independent Astra approval is claimed. See OVERSIGHT_REVIEW.md and RELEASE_REPORT.md.

## Startup repair checks

Four additional tests cover actual log/stdout stage output, exception/traceback capture with nonzero exit, a slow-start notice, and absence of the silent `-c` preflight in the batch launcher. An actual diagnostic-wrapper launch in Linux imported the application successfully, printed the desktop-window stage, then captured the expected missing-DISPLAY Tcl error in the log and console. This validates error visibility, not Windows GUI success.
