# BridgeLab development log

## v0.5.1 — visible startup and failure capture (2026-10-30)
- Remove silent unbounded Python/Tcl launcher probes; print progress immediately.
- Add lightweight diagnostic entry point before desktop imports, startup stage log/tracebacks and 20-second slow-start notice.
- Record unexpected Tk callback errors to ui-errors.log with a visible notice.
- Remove recursive installed-tool scanning from startup; retain bundled/static discovery.
- First-run setup routes through the same diagnostic entry point.
- Four additional regression tests; 116 pass and 2 optional-installer checks skip.
- Actual Windows blank-window cause remains unconfirmed. No GUI/hardware pass claimed.

## v0.5 — mirror drops and plain-language desktop (2026-10-30)
- Redesign normal UI with responsive navy/indigo cards, Overview/Screen settings/Help, keyboard scrolling and simple labels; remove tool browsing from normal controls.
- Configure fixed mirror-drop destination; validate shared storage, reject descendant links, create the folder and recheck destination/consent before session launch.
- Brand mirror/app windows with BridgeLab titles; keep file browser only as optional More file options fallback.
- Dashboard sends follow the same destination and retain byte-count verification; native mirror drops retain upstream transfer semantics including APK installation and possible same-name replacement.
- Add explicit phone-dialer handoff without automatic calling, PC audio, phone-number persistence or new phone permissions.
- Add normal-phone-screen app launch fallback for apps rejecting virtual displays, using validated launcher resolution.
- First-run runtime downloader verifies hash/signature, installs per user, uses unique temporary directories and unconditional cleanup; existing runtime launches directly without PowerShell. Machine policy is not overridden.
- Exact Android-file-manager-to-Explorer drag and full PC-headset cellular calling remain unimplemented; research/design and next gates are documented.
- Six roles assigned with initial Astra oversight; agent followups were interrupted by usage limit, so root finished corrections/integration. No Windows/hardware or rendered-UI pass claimed.

## v0.4 — reliability, phone files and app windows (2026-10-30)
- Test baseline first, then repair stale discovery/battery responses, pending-launch consent/Stop races and process watcher ownership.
- Defer root close during transfers/child shutdown; persist current size/FPS controls; offload tool validation with metadata-keyed cache.
- Screen-off main mirroring now requests temporary stay-awake; video defaults unchanged and no measured performance claim.
- Add shared-storage phone browser, no-overwrite staged push/pull with byte-count verification, Windows file drop-in and staged Explorer copy drag-out.
- Use portable shell hidden-file glob after a real host-shell regression caught parent-directory inclusion.
- Replace experimental raw app launcher with main app chooser: capability checks, launchable-app discovery, independent owned virtual display/session/log and safe stop.
- Add visible Phone setup explanation and settings shortcuts, without companion APK, permission grant, tethering or microphone access.
- Research cellular-call audio feasibility and document limits; do not advertise full-duplex headset calling.
- Six-role development/oversight and final integration tests; Windows native DND/OPPO app-window validation remains required.
- Slim release omits optional Python installer; existing runtime reused. Preserve all dependency notices/source materials.

## v0.3.2 — launch diagnosis and verified transfers (2026-10-30)
- Validate selected Windows executable filenames/PE headers and bundled tools against checksums before launching.
- WinError 193 includes exact selected path, size, architecture and hash with recovery guidance. Root cause on user hardware remains unconfirmed.
- Transfer into /sdcard/Download/BridgeLab, create directory, and verify remote byte count after each push.
- Best-effort media refresh (deprecated Android broadcast; no guarantee of category indexing).
- Confirm same-name overwrites before transfer; show destination and verified names on completion.
- Add Check files on phone for old Download and new BridgeLab directory listings.
- Six new regression tests; total 32 passed on Linux. No Windows/phone validation.

## v0.3.1 — bundled-tools packaging increment (2026-10-30)
- Clone upstream scrcpy tag v5.0.1 and verify official win64 release SHA-256.
- Include the complete official Windows x64 scrcpy/ADB runtime in tools/scrcpy.
- Prefer paired bundled tools, support frozen executable paths, and pin server location/working directory.
- Add executable-first launcher, pinned offline Windows PyInstaller builder, archive/runtime checks and build manifests.
- Add Windows CI recipe (not executed here), discovery/archive regressions and dependency notices.
- Add official Python installer and automatic per-user first-run runtime setup; verify SHA-256 and valid PSF Windows signature before installation. No elevation, PATH or file-association changes requested.
- No OPPO kernel driver or BridgeLab.exe in this candidate archive; setup scripts remain unexecuted on Windows.
- Python tests pass; Windows executable and real-device acceptance remain blocked/unrun.

## v0.3 — reliability increment (2026-10-30)
- Replaced accumulating poll timers with a single cancellable timer.
- Preserve authorization history through unknown/error observations; disable device actions until discovery succeeds.
- Isolate battery-query timeout from device discovery.
- Retain selected phone when absent; never silently redirect actions to another phone.
- Recheck auto-open consent/selection at execution time.
- Serialize file/link actions and display disabled controls while working.
- Close log handle if process launch fails; bounded asynchronous session shutdown.
- Handle files disappearing before size calculation and sanitize timeout messages.
- Add Python/Tk preflight and Windows DPI awareness.
- Add seven headless regression tests, real-device acceptance guide and future API security boundaries.
- Validation: 16 tests pass; compileall passes. Original GUI launch blocked by missing DISPLAY.
- No Windows execution, rendered UI validation, phone testing, installer, or automation API in this release.

## v0.2 — ASUS TUF + OPPO A79 5G focus
- Added OPPO UHID fallback input mode.
- Added explicit, opt-in auto-open after device authorization/reconnection.
- Added read-only phone/ADB/scrcpy diagnostics.
- Added optional turn-screen-off mode.
- Set scrcpy's ADB executable to the same path used by BridgeLab.
- Preserved prior file transfer, link handoff and experimental virtual-display features.

## v0.1 — initial Windows/Android utility
- Basic device selection, mirroring and file/link commands.
