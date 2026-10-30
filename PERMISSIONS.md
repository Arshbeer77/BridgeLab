# BridgeLab Android permission boundaries

Research note for the ADB + scrcpy desktop workflow. The v0.4 desktop tool does not require a persistent Android companion for its current file and link handoffs.

## Minimal-permission path

- **File transfer:** use ADB `push`/`pull` to the shared user storage location (for example, `Download/BridgeLab`). This does not require an Android app or an app-level storage permission. The user still enables USB debugging, unlocks the phone and approves the computer's ADB RSA key.
- **Open a browser link:** issue an Android `ACTION_VIEW` intent for the `http`/`https` URL. This hands the URL to an installed handler; it does not require a BridgeLab app or permission. The user sees/uses the browser.
- **Open a phone number for user confirmation:** use `ACTION_DIAL` with a `tel:` URI. This opens the dialer populated with the number; the user taps Call. It avoids `CALL_PHONE`.
- **If a companion is added later:** request no permissions for simple link launching; for user-selected files, prefer Android's Storage Access Framework document picker rather than broad storage access. Keep any future permission request tied to a concrete feature and request it only when that feature is used.

## Boundaries to communicate

1. **USB debugging authorization is for the ADB host.** Android requires the user to enable debugging and approve the host key. This enables ADB commands from that trusted computer. It does not turn a separate installed BridgeLab APK into a privileged/system app or automatically grant that app runtime permissions.
2. **ADB can run shell commands in the shell context.** ADB handoffs such as `am start` and file push/pull need no companion. Android documents `adb shell pm grant` for granting an app a runtime permission during testing when the app declares that permission and the permission is grantable; that is a distinct, explicit shell operation, not an automatic effect of approving the host. It cannot grant system-only permissions such as `CAPTURE_AUDIO_OUTPUT` to an ordinary app.
3. **Runtime and special permissions have separate user flows.** Dangerous runtime permissions, such as `RECORD_AUDIO` or `CALL_PHONE`, are declared by an app and requested at runtime, with a system permission prompt. Special app access is granted by the user on a Settings page; an app can link to the relevant Settings page but cannot silently toggle it. A Settings deep link is navigation, not consent.
4. **Do not request microphone or call permissions for dialer handoff.** `ACTION_DIAL` does not require `CALL_PHONE`; dialing via `ACTION_CALL` does. `RECORD_AUDIO` grants access to microphone input when approved; it does not supply a cellular-call audio route. System-only call audio capture remains unavailable to an ordinary companion app.

## Official sources

- [Android Debug Bridge (adb)](https://developer.android.com/tools/adb) — USB debugging and RSA host authorization prompt; wireless pairing/revocation.
- [Android: Common intents](https://developer.android.com/guide/components/intents-common#DialPhone) — `ACTION_DIAL` versus `ACTION_CALL` and `CALL_PHONE` requirement.
- [Android: Minimize your permission requests](https://developer.android.com/privacy-and-security/minimize-permission-requests) — recommends `ACTION_DIAL` for user-confirmed calls.
- [Android: Permissions overview](https://developer.android.com/guide/topics/permissions/overview) — install-time, runtime and special permissions.
- [Android: Request special permissions](https://developer.android.com/training/permissions/requesting-special) — user grants special app access from Settings; apps can launch the corresponding Settings screen.
- [Android: Request runtime permissions](https://developer.android.com/training/permissions/requesting) — runtime prompt and permission request flow.
- [Android: Access documents and other files](https://developer.android.com/training/data-storage/shared/documents-files) — Storage Access Framework and user-selected files.
- [Android: adb shell command reference](https://developer.android.com/tools/adb#pm) — Package Manager shell commands, including runtime permission management.
- [Android: MediaRecorder.AudioSource](https://developer.android.com/reference/android/media/MediaRecorder.AudioSource) — call downlink capture requires system-only `CAPTURE_AUDIO_OUTPUT`.
