"""Dependency-free command builders and validators for BridgeLab.

Commands are always executed with subprocess argument arrays (shell=False).
Android's remote shell still needs quoting for URL values.
"""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import re
import shlex
from mirror_drop import normalize_mirror_drop_target


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    model: str

    @property
    def authorized(self) -> bool:
        return self.state == "device"

    @property
    def label(self) -> str:
        connection = "Wi-Fi/ADB" if ":" in self.serial else "USB/ADB"
        return f"{self.model}  |  {self.serial}  |  {connection}  |  {self.state}"


def parse_devices(output: str) -> list[Device]:
    devices = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("List of devices attached") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2 or parts[1] not in {"device", "offline", "unauthorized", "recovery", "sideload"}:
            continue
        model_match = re.search(r"(?:^|\s)model:([^\s]+)", line)
        model = model_match.group(1).replace("_", " ") if model_match else "Android device"
        devices.append(Device(parts[0], parts[1], model))
    return devices


def clean_url(raw: str) -> str:
    value = raw.strip()
    if not value or len(value) > 4096:
        raise ValueError("Enter a URL of at most 4096 characters.")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value) or any(ch.isspace() for ch in value):
        raise ValueError("URL may not include whitespace or control characters.")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc or not parsed.hostname:
        raise ValueError("Only complete http:// and https:// URLs are accepted.")
    # Keep the URL as given rather than normalizing or silently modifying query parameters.
    return value


def url_intent_shell_command(url: str) -> str:
    safe_url = clean_url(url)
    return "am start -a android.intent.action.VIEW -d " + shlex.quote(safe_url)


def validate_package_id(value: str) -> str:
    package_id = value.strip()
    if len(package_id) > 180 or not re.fullmatch(r"[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)+", package_id, re.ASCII):
        raise ValueError("Enter an Android package ID such as com.android.settings.")
    return package_id


def scrcpy_command(executable: str, serial: str, size: int, fps: int, audio: bool,
                   app_package: str | None = None, *, control_mode: str = "standard",
                   turn_screen_off: bool = False,
                   push_target: str | None = None) -> list[str]:
    if size not in {1024, 1280, 1600, 1920} or fps not in {30, 60, 90, 120}:
        raise ValueError("Invalid video settings.")
    if not serial or any(ch.isspace() for ch in serial):
        raise ValueError("Select a valid authorized Android device.")
    cmd = [executable, "-s", serial, f"--max-size={size}", f"--max-fps={fps}"]
    if push_target is not None:
        cmd.append("--push-target=" + normalize_mirror_drop_target(push_target))
    if not audio:
        cmd.append("--no-audio")
    if control_mode not in {"standard", "uhid"}:
        raise ValueError("Invalid input-control mode.")
    if control_mode == "uhid":
        cmd.extend(["--mouse=uhid", "--keyboard=uhid"])
    if turn_screen_off and app_package is None:
        cmd.extend(["--turn-screen-off", "--stay-awake"])
    if app_package is not None:
        cmd.extend(["--new-display=1280x800", "--start-app=" + validate_package_id(app_package)])
    return cmd


def new_authorized_connections(previous: set[str], current: list[Device]) -> set[str]:
    """Connections newly authorized since last observation, for opt-in auto-open."""
    return {device.serial for device in current if device.authorized} - previous


def safe_local_files(paths: list[str]) -> list[Path]:
    if not paths:
        raise ValueError("Choose one or more files.")
    files = [Path(p) for p in paths]
    if not all(p.is_file() for p in files):
        raise ValueError("Only existing regular files can be sent.")
    return files
