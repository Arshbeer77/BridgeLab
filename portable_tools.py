"""Local executable discovery for source and PyInstaller portable distributions."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys


def application_root() -> Path:
    """External tools live beside the executable, never in PyInstaller's _internal."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _exe(name: str) -> str:
    return name + (".exe" if os.name == "nt" else "")


def locate_tool(name: str, configured: str = "") -> str:
    """Prefer distribution tools, then a saved selection, PATH and Winget."""
    root = application_root()
    candidates = [root / "tools" / "scrcpy" / _exe(name)]
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(root / _exe(name))
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        candidates.append(local / "Microsoft" / "WinGet" / "Links" / _exe(name))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return ""


def discover_tools(adb_configured: str = "", scrcpy_configured: str = "") -> tuple[str, str]:
    """Use bundled adb and scrcpy together, ignoring stale saved install paths.

    For a source installation, a scrcpy directory's adb takes precedence over
    PATH when the user has not explicitly selected a different existing adb.
    """
    bundle = application_root() / "tools" / "scrcpy"
    adb, scrcpy = bundle / _exe("adb"), bundle / _exe("scrcpy")
    if adb.is_file() and scrcpy.is_file():
        return str(adb.resolve()), str(scrcpy.resolve())
    scrcpy_path = locate_tool("scrcpy", scrcpy_configured)
    if scrcpy_path:
        sibling_adb = Path(scrcpy_path).parent / _exe("adb")
        if not (adb_configured and Path(adb_configured).is_file()) and sibling_adb.is_file():
            return str(sibling_adb.resolve()), scrcpy_path
    return locate_tool("adb", adb_configured), scrcpy_path
