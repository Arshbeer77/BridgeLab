# v0.5 new-feature acceptance (not run here)

- Fresh extraction and START-WINDOWS.bat on the existing working runtime: no tool-location dialogs or technical labels in normal flow.
- Check Overview, Screen settings and Help at 100%, 125% and 150% scaling, keyboard Tab/Enter, mouse wheel, narrow window, and all popups. Ensure controls remain reachable; no rendered-UI test was done by developers.
- Open screen, drag a normal PC file onto it, find it under Internal storage / Download / BridgeLab. Change Download location, reopen screen, repeat; old current Android file-manager folder must not be implied as target.
- Try same-name native drop only with disposable files; expect replacement. Dropped APKs install apps; use Choose files to send for copying APKs instead.
- Cancel startup or change destination while preparation runs: no session with the wrong destination. Linked/private folder paths must fail clearly. Test disconnect/reconnect and ordinary mirror controls.
- Choose an app, open separate window, then test Open on phone instead. It must target that chooser's captured phone. Close during fallback request: wait safely; no unowned process.
- Phone dialer: type a test number, open it, verify no automatic Call and no number persistence. Phone selection change must refuse stale request. Audio stays on phone; PC headset route is not implemented.
- Exact reverse drag from Android screen to Explorer must not be advertised as available. Optional More file options still stages copies.
- On a clean disposable Windows user without Python: verify first-run download/hash/PSF signature/private install if policy permits; policy must not be overridden. Existing runtime should never need PowerShell to launch.

## Preserved v0.4 checks

# v0.4 ASUS TUF + OPPO A79 acceptance checklist

Status: NOT RUN by developers on Windows/phone. The user reported v0.3.2 mirroring/control working; this is not validation of the new features. Record Windows, Python, scrcpy, Android and ColorOS versions plus input mode before testing.

## Main mirror and connectivity

- Fresh extraction: no archive errors; launch, select OPPO, Diagnose.
- 1280/60, audio off: open/control the phone; record Standard vs UHID. Alt must release UHID capture.
- Screen-off checkbox: physical display dark while mirror remains usable; authentication still required as Android demands. Close and check normal phone sleep behavior returns.
- Refresh 20 times; change tool path during a discovery request, then restore. No wrong-device actions, extra polling loops or false auto-open.
- Enable auto-open, unplug/replug 10 times (allow 15s each); record success count. Very short events between polls can be missed. Close scrcpy manually and wait: no automatic reopening until an observed connection transition.
- Press Stop while validation is pending and turn off auto-open during validation. Neither may open a later unwanted session.
- Close during main transfer: app must remain available with a clear wait message. Close with mirror active: no leftover owned scrcpy process. Do not kill unrelated ADB clients.
- Record first-visible-frame times with a stopwatch/recording. actions.csv measures process launching, not frame latency.

## Phone files and native Windows dragging

1. Open Browse phone / drag files, confirm captured serial and folder, test Up, Enter, double-click and Tab navigation.
2. Browse Download and a nested folder. Check spaces, apostrophes, Unicode and hidden names. Links must be marked blocked; private paths/traversal rejected.
3. Drop PC files into the displayed folder. Verify location and content on phone. Repeat a filename: refuse overwrite. Drop APK: copy only, do not install.
4. Select phone files and Download selected files into a new batch folder. Compare SHA-256 manually after copy; app itself verifies size only.
5. Hold the drag area and drop into Windows Explorer. Test cancellation with Escape, non-ASCII names, multi-select, and Explorer copy completion. Copies must remain in staging and on phone.
6. Test Open downloaded folder / file-dialog fallback. Do not run BridgeLab as Administrator; Explorer drops across different elevation levels may be blocked by Windows.
7. Unplug during push/pull. Failure must be visible, completed copies retained, partial files cleaned where possible, and no automatic retry. Inspect both folders before retrying.
8. Switch selected phone during file dialogs. Existing browser must refuse new work and tell you to reopen it. Close browser/root during a transfer: defer until work finishes.
9. Test a large file and disk-full destination on a disposable volume. Observe bounded operation timeout and free space; individual file operations are not resumable.

## App windows

- Main entry must perform read-only scrcpy/Android checks and list launchable apps. Failed checks must not launch anything.
- Open Settings first, then another non-sensitive installed app. Confirm visible content and input, not just a process-start message.
- Keep ordinary mirror running; app window must have separate process/log/Stop ownership. Changes still share phone data/accounts.
- Test Standard/UHID, screen lock/unlock, disconnect/reconnect, app switching, five stop/start cycles and root close while app window active.
- Confirm chooser remains tied to displayed serial if main selection changes. Close/reopen to target another phone.
- Save work before closing: Android may close the app content on the removed virtual display. Some apps/OEM policies/DRM may reject the display; report the exact log and app package.

## Setup permissions and calls

- Phone setup must explain host-wide ADB authorization and list unused app permissions.
- Open Developer options/Settings only after authorization; the user chooses all settings changes. On unauthorized phone, clear manual-setup guidance.
- No Android APK, microphone/contact/call permission prompt, hidden permission grant or unrestricted automation listener.
- Full PC-headset cellular calling is absent; do not treat audio playback as proof of call audio routing.

Review TEST_REPORT.md, FILE_TRANSFER.md, APP_WINDOWS.md and CALLING_RESEARCH.md before reporting a passed device build.
