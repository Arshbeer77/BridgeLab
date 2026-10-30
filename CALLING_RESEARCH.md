# Windows headset and cellular-call feasibility

Research note for OPPO A79 5G / Android 15 and BridgeLab's Windows ADB + scrcpy workflow. Updated 2026-10-30. v0.5 implements a dialer handoff, not PC cellular-call audio.

## Conclusion

- **Opening the dialer is feasible without a companion app or call permission.** BridgeLab can ask Android to open the phone app with a number using `ACTION_DIAL`; Android displays the number and the user taps Call. `ACTION_CALL` would place the call directly and requires `CALL_PHONE`, so it is not the appropriate minimal-permission route.
- **scrcpy can mirror/control the screen and forward ordinary device playback, but it is not a supported full-duplex cellular-call audio bridge.** Its default output source forwards device audio; `--audio-source=mic` captures the phone microphone. Neither documents routing the Windows headset microphone to the cellular call uplink while returning the call downlink to that headset. Playback capture also cannot be assumed to include call audio.
- **Phone Link is the practical supported Windows calling route to try.** Microsoft supports PC calls over Bluetooth. It requires Bluetooth and its own user-authorized pairing/call setup. Microsoft currently documents that Phone Link does not relay an Android phone call to a Bluetooth headset attached to the PC. That limitation is material if the target is a PC headset for both sides of the call; verify the current Windows/Phone Link behavior on the actual setup before promising it.
- **Recommendation:** BridgeLab may offer an explicit “Open dialer” handoff (`ACTION_DIAL`). For full-duplex cellular calls, direct users to the phone's own audio route (phone or headset connected to phone) or evaluate Phone Link with its stated headset limitation. Do not claim scrcpy alone provides Windows-headset cellular calling.

## Why scrcpy playback is insufficient

The official scrcpy audio documentation describes forwarding device output by default and capturing the phone microphone with `--audio-source=mic`. Its `playback` source is app playback capture, which apps may opt out of. Android's playback-capture rules require eligible usages (`USAGE_MEDIA`, `USAGE_GAME`, or `USAGE_UNKNOWN`) and an allowing capture policy; voice-communication usage is outside that allowlist. The separate call-downlink source is protected by `CAPTURE_AUDIO_OUTPUT`, reserved for system components and unavailable to third-party apps. Therefore a successful scrcpy audio session does not establish access to cellular downlink, nor a return microphone path into the call.

## Exact Windows APIs and the remaining feasibility work

Windows does expose Bluetooth phone transport APIs; claiming that Windows provides no such APIs would be incorrect:

| API | Documented purpose | Gap for this release |
| --- | --- | --- |
| `Windows.ApplicationModel.Calls.PhoneLineTransportDevice` | Bluetooth-backed phone-line device; available starting Windows 10 1903. Enumerate with `GetDeviceSelector`, obtain with `FromId`, request access, register the app, and connect. | `RequestAccessAsync` and `RegisterApp` document `phoneLineTransportManagement`; permission, registration and actual device connection must all succeed. |
| `Windows.ApplicationModel.Calls.PhoneCall` | Call control and `ChangeAudioDevice`; documents `phoneCall`. | These are call-routing APIs, not evidence of arbitrary PCM capture/injection for a phone. A functioning phone-line transport and real device validation are prerequisites. |
| `Windows.Media.Audio.AudioPlaybackConnection` | Enable Bluetooth A2DP sink playback: remote device sends audio to Windows speakers/headphones. | One-way media playback provides no phone-call microphone uplink. |
| Windows Bluetooth HFP bypass driver interfaces | Driver-facing SCO/audio transport integration. | Not a drop-in Python application API; would require a separate driver/hardware project. |

`phoneLineTransportManagement` is a restricted capability. Microsoft's general guidance distinguishes sideloading from Store publication: declaring a restricted capability does not itself require Store approval for sideloading. It would be inaccurate to call this API categorically Microsoft-only or to claim that Store approval alone blocks a local prototype. Equally, declaration or an Allowed permission result does not prove registration, pairing, routing, or full-duplex audio works.

Engineering assessment: a packaged native Windows proof of concept using these APIs is a plausible next investigation, without a custom Android mic app or rooting the phone. It is not a verified portable Tk/ADB implementation. This environment has no Windows Bluetooth phone/headset hardware, so no two-way audio test was possible. v0.5 does not add an untested bridge or claim to fulfill PC-headset calls.

That future proof of concept must verify pairing, access denial, registration, phone-line enumeration, outgoing/incoming calls, both audio directions, mute/hangup, reconnection and interference from Phone Link. Wired/USB headsets and Bluetooth headsets need separate testing. Phone Link's Bluetooth-headset limitation must not be presented as a blanket ban on all PC microphones or wired headsets.

## v0.5 implementation boundary

`phone_calls.py` opens `android.intent.action.DIAL` on the selected authorized phone, optionally with a number. The user reviews the number and presses Call on the phone or mirrored screen. Call audio remains on the phone or a headset paired to the phone. There is no `ACTION_CALL`, synthesized Call tap, call-log/contact read, audio recording, Android permission grant, microphone-app installation, rooting, or automatic retry. Phone numbers are not written to BridgeLab settings/logs by this feature. Android's own dialer and call history remain under Android's control.

Numbers use an ASCII allowlist with optional leading `+`; formatted ordinary numbers are accepted, service codes, URI extras and shell syntax rejected. Requests run off the UI thread with a 12-second bound; timeout is reported as ambiguous because the dialer may have opened already. Both nonzero process exits and Android activity errors with zero exit are handled. Seven mocked tests validate these boundaries; actual OPPO dialer behavior remains a device check.

The dialog links to Microsoft's official Phone Link setup page as a separate option with separate pairing/permissions. No unofficial `ms-phone:` launch protocol is assumed.

## Sources (official / primary)

- [scrcpy audio documentation](https://github.com/Genymobile/scrcpy/blob/master/doc/audio.md) — Android 11+ audio forwarding; default output; `playback` and `mic` sources.
- [scrcpy project README](https://github.com/Genymobile/scrcpy) — official project, mirroring/control and audio forwarding; no app installed on device.
- [Android: Capture video and audio playback](https://developer.android.com/media/platform/av-capture) — MediaProjection/user approval and playback capture eligibility/policy.
- [Android: AudioPlaybackCaptureConfiguration](https://developer.android.com/reference/android/media/AudioPlaybackCaptureConfiguration) — eligible usages and capture policy.
- [Android: MediaRecorder.AudioSource](https://developer.android.com/reference/android/media/MediaRecorder.AudioSource) — call downlink requires system-only `CAPTURE_AUDIO_OUTPUT`.
- [Android: Common intents, initiate a phone call](https://developer.android.com/guide/components/intents-common#DialPhone) — `ACTION_DIAL` leaves call confirmation to user; `ACTION_CALL` places directly and needs `CALL_PHONE`.
- [Microsoft: Set up calls in Phone Link](https://support.microsoft.com/en-us/windows/apps/phonelink/setting-up-calls-in-the-phone-link) — Bluetooth requirement and Android 10+ requirement.
- [Microsoft: Make and receive phone calls from your PC](https://support.microsoft.com/en-us/windows/apps/make-and-receive-phone-calls-from-your-pc) — calls initiated/received in Phone Link on PC.
- [Microsoft: Troubleshoot calls in Phone Link](https://support.microsoft.com/en-gb/windows/apps/phonelink/troubleshooting-calls-in-the-phone-link) — states Android phone calls are not relayed to a Bluetooth headset connected to PC.
- [Windows: PhoneLineTransportDevice](https://learn.microsoft.com/en-us/uwp/api/windows.applicationmodel.calls.phonelinetransportdevice?view=winrt-26100) — Bluetooth transport and methods, Windows 10 1903 minimum.
- [Windows: RequestAccessAsync](https://learn.microsoft.com/en-us/uwp/api/windows.applicationmodel.calls.phonelinetransportdevice.requestaccessasync?view=winrt-26100) and [RegisterApp](https://learn.microsoft.com/en-us/uwp/api/windows.applicationmodel.calls.phonelinetransportdevice.registerapp?view=winrt-26100) — capability requirements.
- [Windows: App capability declarations](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations) — restricted capability declarations, sideloading versus Store review.
- [Windows: PhoneCall](https://learn.microsoft.com/en-us/uwp/api/windows.applicationmodel.calls.phonecall?view=winrt-26100) — call control, audio-device routing, `phoneCall` capability.
- [Windows: Enable remote Bluetooth audio playback](https://learn.microsoft.com/en-us/windows/apps/develop/media-playback/enable-remote-audio-playback) — A2DP sink, remote media output to PC.
- [Windows drivers: Bluetooth HFP bypass audio streaming](https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/bluetooth-hfp-bypass-audio-streaming) — driver integration context.
