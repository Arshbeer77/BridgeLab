# Phone files in v0.4

Open **Phone files** with one connected, authorized ADB phone selected. The browser starts in `Download` and shows the selected phone serial. It uses existing ADB access; it installs no APK and requests no Android storage permission.

- **PC → phone:** navigate to a folder, then drop regular PC files onto the browser window, or choose **Send PC files…**. The destination is the folder last successfully displayed, shown in the status. An APK is copied as an ordinary file, never installed. Destination conflicts stop the batch; existing files are never intentionally replaced.
- **Phone → PC / Explorer:** select regular phone files and choose **Download selected files…**. Choose a PC parent folder; BridgeLab creates a fresh `BridgeLab-received-*` batch folder. Once size checks finish, hold the drag area and drag into Windows Explorer. This second gesture starts a native Windows copy drag. **Open downloaded folder** provides a keyboard-accessible route to the same files.
- Downloads stay in the chosen PC folder after closing the browser. Dragging creates another copy; it does not remove the phone file or staged PC file. If a later file fails, earlier completed files may remain on either device. Use **Open downloaded folder** to inspect a partially completed download batch.

## Direct drag from the mirrored Android File Manager

**Not implemented.** Selecting or dragging an item inside the mirrored Android File Manager does not create a Windows Explorer file drag. scrcpy sends the phone's screen and receives pointer input, but its current protocol does not send the selected Android document identities, URI read grants or file streams back to Windows. Text clipboard synchronization does not provide that access.

The staged phone-browser download described above remains a secondary fallback. It does not satisfy direct File Manager → Explorer dragging. No OCR, filename guessing or automatic whole-storage scan is used to infer a selection. A source-app or platform integration and a Windows virtual-file data object would be needed before claiming the exact gesture. Public Android target APIs provide the selected `ClipData` only at Android drop, after release, so installing a plain drop-target companion alone does not resolve the handoff. See [RECEIVE_DESIGN.md](RECEIVE_DESIGN.md) for the public API constraints, prototype gates and acceptance criteria.

## Scope and requirements

Only ordinary files inside `/sdcard` or `/storage/emulated/0` are transferred. Folders can be browsed, but recursive folder copies, symlinks, app-private data and filenames containing control characters are unsupported. Windows-incompatible Android basenames are mapped to safe names with a deterministic suffix. Unicode, spaces, quotes and shell metacharacters are preserved where Windows permits them.

ADB shell must provide `readlink -f`, `stat -c %s` and `mv -n -T`. An unsupported command fails the operation; there is no unsafe replacement fallback. Files are checked by byte length, not by checksum. Browsing and copying do not guarantee a snapshot if another app changes phone storage concurrently. Android media categories may need refresh; browse the exact folder in the phone's file manager.

Windows Explorer drag-out uses the Windows Shell's `SHCreateDataObject` and `SHDoDragDrop`, initialized and invoked on the UI thread. Drop-in uses `WM_DROPFILES`; the window procedure only enqueues paths and is restored on close. ADB work runs in a worker that never calls Tk. The browser refuses close while work or a native drag is active. If the selected phone/session changes, reopen the browser before starting another operation. Drag-in can be unavailable across Windows elevation levels; run BridgeLab and Explorer at the same privilege level, or use the file picker.

## Validation

`python -m unittest test_phone_files -v` covers shared-root validation, NUL-delimited listings, unusual filenames, shell quoting, captured serials, destination conflicts, upload failure cleanup, size verification, safe local naming, symlink/folder refusal, exclusive local creation, partial-write cleanup, session change after dialogs, worker queuing and browser close behavior. Native sources compile and have been reviewed for pointer-width and ownership handling.

Actual Windows Explorer dragging and Android ADB behavior require Windows + phone acceptance testing; Linux unit tests do not establish those results. Test both directions with Unicode/spaces/quotes, existing destination files, a disconnect, a changed phone selection, an APK, and an active-operation close attempt. Verify that cancellation leaves staged files available and that no Android package is installed.
