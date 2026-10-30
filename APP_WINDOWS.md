# Android app windows

This is a software-tested beta with capability checks. Real Android/OPPO hardware validation is still required; no claim of hardware certification or independent Android instances is made.

Open **App windows** after selecting an authorized phone. The chooser captures that phone’s serial and shows it at the top. Changing the main device selection does not retarget this chooser. Close it and open a new chooser to use another phone. Opening an app starts a separate scrcpy process and virtual display, independently of the ordinary mirror. Stop/close affects only that chooser’s owned app process. It never kills or restarts ADB.

The app runs on the connected phone, using its existing installed apps, accounts, storage, and Android permissions. Apps or OEM policies may reject a secondary display, keep content on the phone, restrict input, or show protected content as black. A running scrcpy process is not proof the app rendered successfully. Check its window on the actual device setup.

## Capability and app discovery

On Windows the worker first validates selected tool PE headers and bundled checksums before executing them. The read-only preflight checks the selected scrcpy’s `--help` for `--new-display` and `--start-app`, then reads `ro.build.version.sdk` from the captured phone. Android 10/API 29 or newer is required by scrcpy’s server. A passed preflight establishes prerequisites only.

Launchable apps are discovered with `scrcpy -s SERIAL --list-apps`, using the same selected ADB executable as the session. If unavailable or unsuccessful, one bounded `cmd package query-activities --brief --components -a android.intent.action.MAIN -c android.intent.category.LAUNCHER` query supplies launchable package IDs. The fallback has no app labels and may omit TV-only leanback launchers. No packages are installed, enabled, or modified. Timeouts are 10 seconds per preflight step, 25 seconds for scrcpy listing and 20 seconds for the optional fallback. Lists are limited to 3,000 apps and 2 MB parsed output.

The launch uses the documented supported route:

```text
scrcpy -s SERIAL --max-size=1280 --max-fps=60 --no-audio --new-display=1280x800 --start-app=com.android.settings
```

Current video/audio/input choices are captured when the chooser opens. No physical-screen-off flag is added to app windows. Ordinary mirror screen-off remains a separate option. The virtual display is destroyed on close; scrcpy’s default also destroys its app content, so save app work first. This does not delete the installed app or its stored account data.

Separate timestamped app-window logs are written to the configured BridgeLab log directory. The chooser displays the precise log path and process exit code; logs may contain package names and device information. Listing diagnostics are displayed in the chooser. No subprocess output pipe is left unread.

## Integration

`open_app_windows(parent, adb, scrcpy, serial, run, *, size=1280, fps=60, audio=False, control_mode='standard', log_dir=None)` in `app_windows_ui.py` returns a controller with `.window` and `.close()`. Retain it and call `.close()` before destroying the main root. If `.close()` returns `False`, keep the main event loop alive while its owned child stops; the chooser finalizes itself after exit, and a later parent close can proceed. A `True` return means it is safe to destroy the parent. `run` accepts `args`, `timeout`, and optional `env`, and returns `subprocess.CompletedProcess[str]`. Discovery workers only write to a queue; Tk callbacks process results on the UI thread and stop after close. Late probe results cannot launch anything or switch devices.

`app_windows.py` also exposes pure command/parsing helpers and injectable preflight/list APIs for headless verification. The controller owns its subprocess and log; it does not use the main mirror’s process or log handle.

## Verification

Run `python -m unittest test_app_windows -v`. Mocked probes verify Android/tool gates, serial stability, timeout diagnostics, upstream list formats including wrapped names, bounded launcher fallback, argument validation, exact ADB environment, and virtual-display arguments. These tests do not validate Android/OEM behavior or visible Tk layout. Before calling this stable on a device, test app launch/rendering, keyboard/mouse input, phone lock/unlock, switching phone apps, simultaneous mirror, disconnect, repeated stop/start, and app cleanup after close.

The implementation follows the bundled official scrcpy `doc/virtual-display.md`, `doc/device.md`, server API gate, and upstream app-list formatter. It does not use an emulator or an unofficial display-creation mechanism.

## v0.5 fallback

Open on phone instead resolves the selected package's launcher on the chooser's captured phone, validates the returned component, and opens it on the phone's normal screen. Use the main mirror to interact. Requests run off the UI thread; the chooser waits for an in-flight handoff before closing. This is not universal secondary-display support. Titles and controls are simplified, but Windows visual checks remain outstanding.
