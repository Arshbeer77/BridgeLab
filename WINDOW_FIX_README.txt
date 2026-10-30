BridgeLab v0.5.1 window visibility patch

Close all old BridgeLab command windows. Extract this ZIP's CONTENTS into the existing BridgeLab v0.5.1 folder, beside START-WINDOWS.bat. Allow continuity_mvp.py to be replaced. The new window_visibility.py must sit in the same folder. Run START-WINDOWS.bat again.

The window is restored, centred and raised once. Its brief always-on-top flag is released after 400 ms. Startup logging now reports state, mapping/viewability, position, dimensions and screen size; the old Window ready event did not verify these.

The Windows cause is unconfirmed. If still invisible, share the fresh startup.log. Win+R command:
notepad "%LOCALAPPDATA%\BridgeLab\startup.log"

120 combined tests passed; 2 optional-installer checks skipped. Four new tests cover centring/restore, topmost release, actual-mapping readiness and closed-window safety. No Windows GUI/hardware test was performed.
