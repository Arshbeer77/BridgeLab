# Windows packaging report — v0.5 bootstrap

The source ZIP stays slim by downloading the official CPython 3.12.10 x64 installer only when first launch finds no usable per-user BridgeLab runtime and no existing Python 3.11+ with Tcl/Tk. The bootstrap downloads from python.org to the user's temporary directory, checks the pinned SHA-256 (`67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb`), requires a valid Authenticode signature from the Python Software Foundation, then installs into `%LOCALAPPDATA%\BridgeLab\runtime\Python312`. The unattended install is per-user; it does not request elevation, alter PATH, or set file associations. The temporary installer is removed after setup or verification failure.

A working internet connection is needed on first launch only when no compatible Python/Tk runtime is already available. Existing private BridgeLab runtime and suitable `py`/`python` installs are reused first. After setup, BridgeLab is launched from the extracted package. The official runtime installer is not bundled, preserving the existing ZIP size constraint.

## Checks run in this environment

- `python -m unittest test_build_windows test_first_run_packaging -v`: 9 tests discovered, 7 passed, 2 expected skips (the optional installer is not in the package).
- `python -m py_compile build_windows.py test_first_run_packaging.py`: passed.
- These checks validate packaging source logic and launcher wiring; PowerShell execution, Authenticode evaluation, Windows runtime setup, frozen build, and Windows UI behavior were not run here.

`build_windows.py` now packages the first-run PowerShell bootstrap and declares v0.5 output. The existing Windows CI workflow remains a manual, unexecuted build recipe; no Windows executable or actual package-size claim is made by this report. The launcher does not override PowerShell execution policy.

Integrator correction: the batch launcher now tests/reuses existing runtimes directly, avoiding dependence on PowerShell script policy for an already working installation. Only missing-runtime setup invokes the .ps1; first-time setup may still be blocked by policy. A unique temporary installer directory with finally cleanup avoids download collisions. These remain source-reviewed, not Windows-executed, changes.
