# Phone → Explorer: exact gesture feasibility

Status: **direct native drag from Android's mirrored File Manager into Explorer is not implemented**. The existing PC file browser and staged Windows file drag do not meet that requirement. This document describes the missing integration; it does not advertise an available feature.

## What the current transport actually carries

The inspected upstream scrcpy checkout is commit `a60891aea193d92e7e5c3942700eca63f9d19a5f`.

* `app/src/control_msg.h` defines mouse/touch injection and text clipboard messages. It does not define Android drag-start, selected-file, content-URI or file-stream messages.
* `app/src/device_msg.h` defines three device-to-PC messages: clipboard text, clipboard acknowledgement and UHID output. The clipboard payload is `char *text`.
* `server/src/main/java/com/genymobile/scrcpy/control/DeviceMessageWriter.java` serializes clipboard text as UTF-8; it does not export Android `ClipData` content URIs or their permission grants.
* `doc/control.md`, “File drop”, documents dropping a PC file onto the scrcpy window to push it to the phone. It does not document reverse dragging from an Android app.

The desktop can observe pointer coordinates, but those coordinates do not identify a selected document or grant access to its bytes. Hooking the scrcpy window or beginning a Windows OLE drag cannot supply the missing identity. A filename displayed on screen is also insufficient: filenames need not be unique, documents may be virtual, and a provider's `content://` URI need not have an accessible filesystem path. OCR, title matching, clipboard-text guessing and scanning for a matching filename must not be used as substitutes.

Windows Explorer needs a native data object containing either already accessible local files or a correctly implemented virtual-file data object that can stream the selected bytes. `native_drag.drag_files()` supports the first case after files have arrived on the PC. That function cannot recover Android's selection or retrospectively turn an Android gesture into an uninterrupted Windows drag.

## A lower-friction alternative that would still be a different feature

An Android companion could register as an `ACTION_SEND` / `ACTION_SEND_MULTIPLE` Sharesheet destination. In the mirrored File Manager the user would select files, choose **Share → BridgeLab**, review a transfer, and send those explicitly shared items to the selected PC. A PC receipt window could then offer native dragging of the downloaded copies into Explorer. This avoids browsing a second file tree on the PC, but it is **Share → PC → drag**, not direct File Manager → Explorer drag.

A minimal implementation would need all of the following before it could be shipped:

1. A signed Android companion APK with a deliberately visible Sharesheet activity. It must accept only explicitly granted `content://` streams, read through `ContentResolver`, handle absent or inaccurate size metadata, and reject unsupported folders. No All files access, Accessibility service, microphone or contacts permission is needed for this route. Do not persist URI permission grants by default.
2. Explicit pairing with the chosen ADB serial. A PC receiver bound only to `127.0.0.1`, with a fresh unpredictable session token and an exact app-owned `adb reverse tcp:<port> tcp:<port>` mapping, would avoid a LAN listener. Loopback alone is not authentication: any process on the phone may reach a reversed port. The token and bounded session lifetime remain required. Do not remove other apps' reverse mappings when closing.
3. A framed manifest and bounded streaming protocol with per-item byte limits, count/total limits, timeouts, cancellation, filename normalization and exclusive creation in a unique local batch directory. Publish completed files only after verifying the received bytes; close/delete partial files on failure. Android display names are untrusted input and must never become arbitrary Windows paths.
4. A desktop receipt UI on the Tk thread, with network/file work off that thread. Start an Explorer drag only from a fresh user gesture after files are available. Preserve downloaded copies if the Explorer copy is cancelled, and show where they are stored.
5. A clear disconnect/close lifecycle: invalidate the session token, stop the receiver, cancel in-progress work and remove only the reverse mapping owned by this session. The companion must release streams and its temporary grant access when the activity finishes.

An arbitrary Android app is not guaranteed to offer sharing, allow export or grant readable streams. Protected provider content and revoked grants must fail visibly. Background restrictions, screen lock and OEM behavior require device testing.

## What would be required for the exact drag gesture

The first gate is an Android integration that receives an actual drag's `ClipData` and scoped read access to its selected items from the source File Manager. Ordinary screen mirroring does not provide this. A companion Sharesheet activity does not satisfy this gate. A custom File Manager could control its own export gestures, but that replaces the user's File Manager and does not establish support for arbitrary existing apps.

The public Android drag APIs impose another important timing constraint:

| Event/API | What a regular receiving Android view can use |
| --- | --- |
| `ACTION_DRAG_STARTED` | `getClipDescription()` MIME metadata; return `true` to receive later events. This does not provide the selected items. |
| `ACTION_DRAG_ENTERED`, `ACTION_DRAG_LOCATION`, `ACTION_DRAG_EXITED` | Android target/position lifecycle; not readable `ClipData` items. |
| `ACTION_DROP` | `getClipData()` is valid. Request `Activity.requestDragAndDropPermissions(event)`, then read granted items via `ContentResolver`. |
| `ACTION_DRAG_ENDED` | Result and cleanup; not the selected `ClipData`. |

The source app must initiate a global drag with `View.startDragAndDrop(...)`, `DRAG_FLAG_GLOBAL`, and the appropriate URI access flag such as `DRAG_FLAG_GLOBAL_URI_READ`. A plain long-press selection or app-internal reorder gesture is not necessarily an Android global file drag. The target cannot make an uncooperative File Manager export a global drag or add missing grants.

Android documents `getClipData()` as valid only at `ACTION_DROP`, which follows release on an Android target. Thus a regular companion target cannot obtain selected URIs at drag-start and automatically pass them to Windows while the original mouse button remains held. Receiving a real drop in a visible companion is a useful experiment for supported sources, but the resulting transfer requires another gesture and does not establish the requested seamless drag. These conclusions follow from the documented event contract; no OEM-specific drag integration has been measured.

### Smallest meaningful prototype, with stop conditions

1. Build an instrumentation companion with a visible drop view and event logging, using public Android APIs. Log action/MIME/item-count/grant results, avoiding URI and filename contents in shared logs. Put it beside the **actual OPPO File Manager** in Android multi-window mode. Test a mouse drag through the mirror. **Stop** if the File Manager offers only selection, app-local dragging, no global drop, or no readable URI grant. An alternate file manager passing does not establish OPPO File Manager support.
2. Verify the selected bytes at `ACTION_DROP` through `ContentResolver.openInputStream()` or `openFileDescriptor()`. Keep the activity/grant alive through streaming and release `DragAndDropPermissions` afterwards. This proves only Android app-to-app export, not an uninterrupted PC drag.
3. For an uninterrupted drag, first obtain an integration with the **source app** that can provide immutable selected-document metadata and scoped streaming access before Windows OLE initiation; alternatively research an explicit OEM/system integration. Do not assume shell ADB authorization grants another app's provider URI permissions, or that a normal overlay can inspect another app's private selection. Source-app cooperation makes the prototype app-specific. A generic route would require demonstrated platform support on each supported system; it is not established here.
4. Only after gate 3, add an authenticated, versioned transport with export-start, metadata, stream request/chunk, cancel, failure and export-end events. Pin every event to a selected ADB serial plus session/export identifiers. Coordinate Android pointer cancellation/handoff and Windows drag while the original physical button is still down. Do not synthesize button-up and start a second gesture while reporting a continuous drag.
5. On Windows, implement a real COM `IDataObject` offering registered `CFSTR_FILEDESCRIPTORW` (`FILEGROUPDESCRIPTORW` plus per-item `FILEDESCRIPTORW`) and `CFSTR_FILECONTENTS`. Each `FORMATETC.lindex` is the zero-based selected item; `GetData` supplies its `STGMEDIUM`, normally `TYMED_ISTREAM`. Correctly implement enumeration/query, COM reference ownership, `IStream` read/seek/stat behavior as supported by the backing stream, media release, failure and repeated requests. Unknown-size/sequential Android streams may need local spooling rather than pretending they are seekable. Do not advertise `CF_HDROP` paths before real files exist.
6. Run OLE on an initialized Windows UI apartment using `IDataObject`, `IDropSource` and `DoDragDrop`/`SHDoDragDrop`, permitting `DROPEFFECT_COPY` only. Handle `QueryContinueDrag`, escape/cancellation and mouse release. Keep transfer objects and provider permissions alive for as long as Explorer still owns their streams. An OLE accepted-drop result alone is not proof that all bytes were successfully copied; the stream can still fail during consumption. Verify files independently in acceptance testing.

Only after demonstrating real selected-content access should a coordinated scrcpy client/server extension be designed for drag lifecycle, cancellation, metadata and file streaming. The Windows side would then need OLE drag initiation across the mirror boundary and either staging or a robust virtual-file data object. Slow transfers, mouse release before preparation, disconnects, multiple files and Explorer cancellation all need defined behavior. A custom Android integration plus a rebuilt Windows scrcpy client would be a new maintained transport, not a desktop-only patch to the present application.

## Build and acceptance gates

No Android compiler/SDK (`javac`, Gradle, `sdkmanager`, `aapt` or `android.jar`) was found in the current build environment. No companion APK has been built, signed, installed or tested. No Android share receiver, desktop network receiver or permission flow has been added in this release. A disconnected receiver without a built companion would not provide a usable transfer feature.

Before calling either route implemented, test on the actual OPPO/ColorOS device and Windows Explorer: duplicate and Unicode names, unknown-size streams, multi-selection, large files, grant revocation, refused pairing, disconnect mid-stream, timeout, cancellation, destination collision, and application exit. The exact-drag route additionally needs evidence that the original selected File Manager items reach Explorer without opening a separate PC file browser or requiring a new drag gesture.

## Primary references

Reviewed 2026-10-30. Android API behavior and Windows interfaces below support the design constraints, not a claim of a tested integration.

* [Android DragEvent event contract](https://developer.android.com/reference/android/view/DragEvent): validity table and `getClipData()` at `ACTION_DROP`.
* [Android cross-app drag and URI permissions](https://developer.android.com/develop/ui/views/touch-and-input/drag-drop/multi-window): global flags, URI grant request and release lifecycle.
* [Windows Shell clipboard formats](https://learn.microsoft.com/en-us/windows/win32/shell/clipboard): existing-file `CF_HDROP`, virtual `CFSTR_FILEDESCRIPTOR` / `CFSTR_FILECONTENTS`, stream medium and item index.
* [Windows DoDragDrop](https://learn.microsoft.com/en-us/windows/win32/api/ole2/nf-ole2-dodragdrop): initialization, source/data interfaces, drag loop and cancellation.
* [Inspected scrcpy protocol source](https://github.com/Genymobile/scrcpy/blob/a60891aea193d92e7e5c3942700eca63f9d19a5f/app/src/device_msg.h) and [file-drop documentation](https://github.com/Genymobile/scrcpy/blob/a60891aea193d92e7e5c3942700eca63f9d19a5f/doc/control.md).
