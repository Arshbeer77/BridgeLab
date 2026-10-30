# BridgeLab v0.4 baseline bug audit

Audit scope: desktop orchestration, thread/poll/reconnect/session lifecycle, and local privacy behavior. No phone or Windows hardware was used; findings below are based on source inspection and headless reproduction.

## Baseline tests

Ran `python -m unittest discover -v` in a fresh isolated virtual environment from `source/BridgeLab-v0.4`: **32 tests passed**.

## Reproduced issue and lifecycle fix

### Background phone actions continue after the app closes

On the original baseline, `_background_action` launched a daemon worker and `_on_close` destroyed Tk without waiting for an in-flight transfer/link handoff. A multi-file send could continue issuing ADB commands after the UI exited, while its completion/error event was no longer handled.

Added `test_bug_regressions.py` with deterministic blocked-action coverage. The chosen fix defers closing while a background action is active, leaving the UI available to report its result; the user can close again after the action finishes. It also rejects starting new actions after shutdown begins. This avoids pretending that arbitrary Python callbacks or already-running ADB subprocesses can be safely interrupted.

After the fix and the other parallel additions, `python -m unittest discover -v` in the isolated virtual environment: **72 tests passed** (including the two lifecycle regressions).

## Privacy observations

- `actions.csv` records action names/results/timing/byte counts, not URLs, filenames, or device serials.
- The scrcpy session log is intentionally local and may contain tool diagnostics; users should inspect it before sharing.

No additional concrete poll/reconnect defect was reproduced in this bounded audit. Existing reliability tests cover transient ADB errors, explicit device selection, newly authorized reconnects, and auto-start consent rechecks.
