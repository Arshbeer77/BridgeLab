# BridgeLab v0.5.1 status

Software-tested Windows x64 source beta; no BridgeLab.exe was built, no Windows VM/device was accessible, and the redesigned UI was not rendered here. User reports v0.4 screen control and app windows working; this is evidence for the preceding release, not v0.5 acceptance.

Implemented: redesigned nontechnical desktop, configurable fixed mirror-drop folder with safe preparation, optional file browser, phone-dialer handoff, normal-phone app-launch fallback, automatic private-runtime downloader when needed and permitted by Windows policy. Existing runtime launches directly without PowerShell. Backend tools remain bundled/hidden from normal controls; technical reports are under Help.

Unimplemented: exact Android-file-manager-to-Explorer drag and full PC-headset cellular audio. These are explicitly described in RECEIVE_DESIGN.md / CALLING_RESEARCH.md. Neither was replaced by a feature falsely labelled equivalent.

Six roles were assigned including Astra initial oversight; agent followups encountered a usage limit. Root completed integration, the raised fixes and final tests. OVERSIGHT_REVIEW.md preserves the actual review scope, not a fabricated final Astra approval.

Final test counts and limitations are in TEST_REPORT.md; release changes and next steps are in RELEASE_REPORT.md. All original official scrcpy runtime bytes, source/license materials, and final saved-archive integrity are verified during packaging. No latency benchmark or universal app compatibility is claimed.

Startup diagnostics/removal of silent probes are tested; actual resolution of the reported Windows blank-window failure requires the user run or its startup log.
