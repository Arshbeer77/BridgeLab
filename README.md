# BridgeLab v0.5.1 — your phone, at your desk

Software-tested Windows x64 **source beta** with the phone-connection/mirroring components bundled. The user reports v0.4 mirroring and app windows working on ASUS TUF + OPPO A79. This does not establish hardware validation for the v0.5 changes.

## Startup repair in v0.5.1

The launcher no longer runs silent Python/Tcl probes before opening the app. It prints its progress immediately and launches a small diagnostic wrapper. Startup stages and tracebacks are saved to `%LOCALAPPDATA%\BridgeLab\startup.log`; later Tk callback errors go to `ui-errors.log`. If no main window appears after 20 seconds, a visible message points to the startup log. A recursive installed-tool search has also been removed from startup.

The exact cause of the user's v0.5 blank-command-window failure has not been reproduced on Windows. This update removes one possible silent stall and makes the remaining cause observable; it does not claim the Windows GUI failure is definitively fixed. Close all old blank windows before trying it. If it still fails, share startup.log from the same attempt.

## Start

Extract the entire ZIP into a new folder and run **START-WINDOWS.bat**. It uses your existing private BridgeLab runtime or installed Python 3.11+ with Tcl/Tk. If absent, a first-run script can download the official runtime, verify its pinned SHA-256 and Python Software Foundation signature, and install it per user without administrator/PATH changes.

**Not a universal offline plug-and-play executable:** no BridgeLab.exe is built in this source package. First-time runtime setup needs internet and a Windows policy that permits the script; it does not override that policy. Your existing runtime launches directly without PowerShell. A frozen Windows build recipe is included but has not been executed here. Device unlocking, USB debugging approval and any required OEM USB driver remain device/Windows setup steps.

## The new interface

Overview puts Phone screen, Send files, Phone apps, Open a link and the Phone dialer in one scrollable workspace. Screen settings has picture, media sound and compatibility controls. Help contains phone setup, diagnostics and logs. Technical component paths and tool browsing have been removed from normal controls; bundled services are selected internally. Diagnostic reports retain technical details for troubleshooting.

The dark navy/indigo layout reflows cards on narrow windows, wraps instructions and scrolls keyboard-focused controls into view. Visual appearance, Windows scaling and screen-reader behavior still require real desktop testing; no screenshot/rendered-UI approval is claimed here.

## Drop a PC file onto the phone screen

1. Open **Phone screen**.
2. Drag a regular file from Explorer onto that mirrored screen window. No dashboard file selection is needed.
3. Find it in **Internal storage → Download → BridgeLab**, unless you changed Download location.

Use **Change** beside Download location for another shared phone folder, e.g. `Pictures` or `Download/My files`. Close and reopen the phone screen to apply it. This is a fixed session destination; it does not follow the folder currently displayed inside Android's file manager. BridgeLab prepares/checks the destination before opening the screen. Linked destinations and app-private folders are rejected.

**Same-name mirror drops may replace files. Dropping an APK onto the mirrored screen installs that app**, as upstream's native drop mechanism does. Use Choose files to send if you want to copy an APK as a file instead. Native mirror drops use the backend's own transfer/logging path; they do not use the dashboard's byte-count verification or show its completion dialog. Use Help → local logs if a mirror drop is unclear.

Choose files to send also follows your chosen destination and verifies remote byte count. More file options retains the v0.4 browser as an optional fallback, rather than the primary workflow.

## Phone → PC: exact drag is not implemented

Dragging directly from an arbitrary Android file manager in the mirror into Explorer is **not supported in this release**. The screen/input stream does not carry selected-file/content-URI metadata to Windows. Standard Android drag permissions alone do not provide a generic continuous cross-OS gesture. No OCR/filename guessing, unrestricted companion access or pretend receiver was added.

The optional More file options fallback still downloads files to a unique PC folder, then lets you drag those staged copies to Explorer. This is not the exact requested gesture. See RECEIVE_DESIGN.md for a concrete source-app/OEM integration path and the tests needed before promising it.

## Phone apps

Choose a phone app opens a separately owned phone virtual display, alongside the main mirror. Apps share the real phone's accounts and data; this is not an independent Android installation. No promise of compatibility with all apps can be made.

If a separate window is refused, select **Open on phone instead** in the chooser. This resolves the selected app's launcher and requests a normal phone-screen launch; use the main mirror to control it. It is a fallback, not a fix to Android/OEM restrictions. Save work before closing an app window.

## Dialer and call audio

Open phone dialer prepares a number without saving it. You review and press Call on the phone or its mirrored screen. Audio stays on the phone or its connected headset. It does not route cellular audio to/from the PC headset/microphone.

Real Windows Bluetooth phone-transport APIs exist but need a separately packaged native prototype and hardware validation. Full call audio was **not** implemented. CALLING_RESEARCH.md records the verified API constraints and next prototype. No microphone, contacts or call permission is requested for this dialer handoff.

## Access and privacy

No Android companion is installed. USB debugging authorizes the PC's ADB host, not BridgeLab exclusively; Phone setup explains that boundary and opens settings only after authorization. No setting or permission is silently granted. Disable/revoke debugging when you want to end host access.

Settings/action metadata/logs stay under `%LOCALAPPDATA%\BridgeLab`. Metrics omit file/URL/number contents; technical logs may include device/app/file details. Review before sharing. No telemetry upload, remote control server or unrestricted automation API is enabled.

## Validation and reports

Run `python -m unittest discover -v` and `python -m compileall -q .`. See TEST_REPORT.md and RELEASE_REPORT.md for the actual results, remaining gaps and next steps. REAL_DEVICE_TEST.md is the separate hardware acceptance checklist.

The Windows executable builder and manual GitHub workflow remain unexecuted recipes. All official scrcpy 5.0.1 runtime files and required notices/source materials are retained; see THIRD_PARTY_NOTICES.md.
