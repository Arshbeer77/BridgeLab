"""Offline Windows portable build; run with CPython 3.12 x64 + PyInstaller 6.16.0.

Example: python build_windows.py --scrcpy-zip C:\\inputs\\scrcpy-win64-v5.0.1.zip
    --notices-dir C:\\inputs\\third-party-notices

No downloads, driver installs, device access, or elevation. The supplied notices
must cover the binaries being redistributed; this script does not establish
license compliance. Output must not exist. Byte-identical EXEs are not promised.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile

VERSION = "0.5.1"
PYINSTALLER_VERSION = "6.16.0"
SCRCPY_SHA256 = "b12a2c4ee8be317422451fc7dcf8ee20a71b5ea7ef9ad73ddd825a25316227a5"
REQUIRED_TOOLS = ("scrcpy.exe", "adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll", "libusb-1.0.dll", "scrcpy-server", "LICENSE.txt")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_tools(folder: Path) -> None:
    missing = [name for name in REQUIRED_TOOLS if not (folder / name).is_file()]
    for pattern in ("SDL*.dll", "avcodec-*.dll", "avformat-*.dll", "avutil-*.dll", "swresample-*.dll"):
        if not list(folder.glob(pattern)):
            missing.append(pattern)
    if missing:
        raise ValueError("Incomplete scrcpy runtime: " + ", ".join(missing))


def extract_archive(archive: Path, target: Path) -> Path:
    """Reject traversal, symbolic links and oversized ZIPs before extraction."""
    with zipfile.ZipFile(archive) as source:
        if sum(info.file_size for info in source.infolist()) > 2 * 1024**3:
            raise ValueError("scrcpy ZIP expands beyond 2 GiB")
        for info in source.infolist():
            path = PurePosixPath(info.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts or any(":" in part for part in path.parts):
                raise ValueError("Unsafe ZIP path: " + info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("ZIP symbolic links are unsupported")
        source.extractall(target)
    matches = list(target.rglob("scrcpy.exe"))
    if len(matches) != 1:
        raise ValueError("Expected exactly one scrcpy.exe in the official ZIP")
    folder = matches[0].parent
    validate_tools(folder)
    return folder


def run(args: list[str], *, cwd: Path | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True,
                          text=True, errors="replace", timeout=timeout)


def verify_runtime(bundle: Path) -> dict:
    internal = bundle / "_internal"
    for path in (bundle / "BridgeLab.exe", internal / "python312.dll", internal / "_tkinter.pyd"):
        if not path.is_file():
            raise ValueError("Missing frozen runtime file: " + str(path))
    for name in ("_tcl_data", "_tk_data"):
        if not (internal / name).is_dir():
            raise ValueError("Missing Tcl/Tk runtime directory: " + name)
    validate_tools(bundle / "tools" / "scrcpy")
    with tempfile.TemporaryDirectory(prefix="bridgelab-smoke-") as directory:
        report = Path(directory) / "smoke.json"
        run([str(bundle / "BridgeLab.exe"), "--self-check-file", str(report)], cwd=bundle, timeout=45)
        result = json.loads(report.read_text(encoding="utf-8"))
    if not result.get("ok") or not result.get("frozen"):
        raise ValueError("Frozen application self-check failed: " + str(result))
    result["adb_version"] = run([str(bundle / "tools" / "scrcpy" / "adb.exe"), "version"], timeout=15).stdout.strip()
    scrcpy = run([str(bundle / "tools" / "scrcpy" / "scrcpy.exe"), "--version"], cwd=bundle / "tools" / "scrcpy", timeout=15)
    result["scrcpy_version"] = (scrcpy.stdout + scrcpy.stderr).strip()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scrcpy-zip", required=True, type=Path, help="Local official Windows x64 release ZIP")
    parser.add_argument("--scrcpy-sha256", default=SCRCPY_SHA256, help="Expected SHA256 (default: official scrcpy v5.0.1 win64)")
    parser.add_argument("--notices-dir", type=Path, default=Path(__file__).resolve().parent / "licenses",
                        help="Reviewed third-party notices (default: source licenses directory)")
    parser.add_argument("--output", type=Path, default=Path("dist") / f"BridgeLab-v{VERSION}-portable")
    args = parser.parse_args()
    if os.name != "nt" or sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8 or platform.machine().lower() not in {"amd64", "x86_64"}:
        parser.error("Build on Windows x64 with CPython 3.12 x64 (including Tcl/Tk).")
    try:
        if importlib.metadata.version("pyinstaller") != PYINSTALLER_VERSION:
            raise ValueError(f"Use preinstalled PyInstaller=={PYINSTALLER_VERSION}")
        import tkinter
        tkinter.Tcl()  # Fail before build if the builder lacks Tcl.
        archive = args.scrcpy_zip.resolve(strict=True)
        expected = args.scrcpy_sha256.lower()
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise ValueError("--scrcpy-sha256 must be 64 hexadecimal characters")
        if sha256(archive) != expected:
            raise ValueError("scrcpy ZIP SHA256 mismatch; no build was produced")
        notices = args.notices_dir.resolve(strict=True)
        if not notices.is_dir() or not any(path.is_file() for path in notices.rglob("*")):
            raise ValueError("Provide a nonempty reviewed third-party notices directory")
        output = args.output.resolve()
        if output.exists() or output.with_suffix(".zip").exists():
            raise ValueError("Output directory/ZIP already exists; choose a new --output")
        source = Path(__file__).resolve().parent
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="bridgelab-build-", dir=output.parent) as directory:
            work = Path(directory)
            tool_source = extract_archive(archive, work / "scrcpy")
            command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                       "--name", "BridgeLab", "--distpath", str(work / "dist"), "--workpath", str(work / "work"),
                       "--specpath", str(work), str(source / "continuity_mvp.py")]
            build = run(command, cwd=source, timeout=600)
            bundle = work / "dist" / "BridgeLab"
            shutil.copytree(tool_source, bundle / "tools" / "scrcpy")
            shutil.copytree(notices, bundle / "THIRD-PARTY-NOTICES")
            python_license = Path(sys.base_prefix) / "LICENSE.txt"
            if not python_license.is_file():
                raise ValueError("Builder Python LICENSE.txt missing; retain runtime redistribution license")
            shutil.copy2(python_license, bundle / "THIRD-PARTY-NOTICES" / "Python-LICENSE.txt")
            for name in ("START-WINDOWS.bat", "FIRST-RUN-WINDOWS.ps1", "README.md", "LICENSE_NOTES.md", "CHANGELOG.md", "REAL_DEVICE_TEST.md", "THIRD_PARTY_NOTICES.md", "FILE_TRANSFER.md", "APP_WINDOWS.md", "PERMISSIONS.md", "CALLING_RESEARCH.md", "TEST_REPORT.md", "OVERSIGHT_REVIEW.md", "RELEASE_REPORT.md", "RECEIVE_DESIGN.md"):
                if (source / name).is_file():
                    shutil.copy2(source / name, bundle / name)
            tool_hashes = {path.relative_to(bundle).as_posix(): sha256(path)
                           for path in sorted((bundle / "tools" / "scrcpy").rglob("*")) if path.is_file()}
            (bundle / "PACKAGE_SHA256.json").write_text(json.dumps(tool_hashes, indent=2), encoding="utf-8")
            smoke = verify_runtime(bundle)
            (bundle / "build-log.txt").write_text(build.stdout + build.stderr, encoding="utf-8")
            manifest = {"version": VERSION, "python": sys.version, "pyinstaller": PYINSTALLER_VERSION,
                        "scrcpy_archive": archive.name, "scrcpy_sha256": expected,
                        "source_sha256": {name: sha256(source / name) for name in
                                          ("continuity_mvp.py", "bridge_core.py", "portable_tools.py", "tool_health.py", "device_transfer.py", "phone_files.py", "phone_browser.py", "native_drag.py", "app_windows.py", "app_windows_ui.py", "phone_setup.py", "launch_bridge.py", "phone_calls.py", "desktop_ui.py", "friendly_text.py", "mirror_drop.py", "build_windows.py", "FIRST-RUN-WINDOWS.ps1", "START-WINDOWS.bat")},
                        "smoke_check": smoke,
                        "files_sha256": {path.relative_to(bundle).as_posix(): sha256(path)
                                         for path in sorted(bundle.rglob("*")) if path.is_file()}}
            (bundle / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            shutil.move(str(bundle), str(output))
        shutil.make_archive(str(output), "zip", root_dir=output.parent, base_dir=output.name)
        print(f"Verified portable folder: {output}\nZIP: {output}.zip")
        return 0
    except (OSError, ValueError, importlib.metadata.PackageNotFoundError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stdout or "", file=sys.stderr)
            print(exc.stderr or "", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
