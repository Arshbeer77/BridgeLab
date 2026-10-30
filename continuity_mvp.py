"""BridgeLab v0.5.1: a local-first Windows ↔ Android continuity prototype.

Requires Python 3.11+, tkinter, adb and scrcpy. No Android app or cloud account.
All subprocess calls use shell=False. The app never enables USB debugging itself.
"""
from __future__ import annotations

import csv
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from tkinter import Tk, StringVar, BooleanVar, filedialog, messagebox, ttk
import tkinter as tk

from phone_browser import open_phone_browser
from app_windows_ui import open_app_windows
from phone_setup import open_phone_setup
from phone_calls import open_phone_calls
from mirror_drop import DEFAULT_MIRROR_DROP_TARGET, normalize_mirror_drop_target, prepare_mirror_drop
from friendly_text import FriendlyStatusVar, device_name

from device_transfer import send_verified, PHONE_FOLDER
from tool_health import validate_windows_tool, tool_report, validate_bundle_files

from portable_tools import application_root, discover_tools, locate_tool

from bridge_core import (
    Device, clean_url, parse_devices, safe_local_files,
    scrcpy_command, url_intent_shell_command, new_authorized_connections,
)

APP_TITLE = "BridgeLab"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "BridgeLab"
SETTINGS_FILE = APP_DIR / "settings.json"
METRICS_FILE = APP_DIR / "actions.csv"
LOG_FILE = APP_DIR / "scrcpy-session.log"
BG, SURFACE, INPUT, TEXT, MUTED, ACCENT = (
    "#0d1422", "#182235", "#243149", "#f4f7fc", "#a8b7cf", "#70a4ff"
)


def load_settings() -> dict:
    try:
        result = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def run_command(args: list[str], timeout: int = 15, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    # Never invoke a shell on the Windows side; all values are discrete arguments.
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, errors="replace", timeout=timeout,
                          creationflags=flags, check=False, env=env)


class BridgeLab:
    def __init__(self, root: Tk, progress=None):
        self.root = root
        self.startup_progress = progress or (lambda message: None)
        self.startup_progress("Loading preferences")
        self.settings = load_settings()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.log_lock = threading.Lock()
        self.devices: list[Device] = []
        self.devices_adb = None
        self.selected_serial = str(self.settings.get("device_serial", ""))
        self.last_authorized_serials: set[str] = set()
        self.mirror_process: subprocess.Popen | None = None
        self.scrcpy_log_handle = None
        self.poll_running = False
        self.poll_number = 0
        self.poll_timer = None
        self.poll_requested = False
        self.launch_generation = 0
        self.launch_pending = False
        self.session_timer = None
        self.stopping_process = None
        self.closing = False
        self.busy_actions = 0
        self.child_controllers = []
        self.startup_progress("Locating bundled components")
        adb, scrcpy = discover_tools(str(self.settings.get("adb_path", "")),
                                     str(self.settings.get("scrcpy_path", "")))
        self.adb_path = StringVar(value=adb)
        self.scrcpy_path = StringVar(value=scrcpy)
        self.send_folder_var = StringVar(value=str(self.settings.get("send_folder", DEFAULT_MIRROR_DROP_TARGET)))
        try:
            self.send_folder_var.set(normalize_mirror_drop_target(self.send_folder_var.get()))
        except ValueError:
            self.send_folder_var.set(DEFAULT_MIRROR_DROP_TARGET)
        self.device_var = StringVar(value="No phone connected")
        self.connection_var = FriendlyStatusVar(value="Checking for a device…")
        self.battery_var = StringVar(value="Battery: —")
        self.url_var = StringVar()
        self.package_var = StringVar(value="com.android.settings")
        size = str(self.settings.get("max_size", "1280"))
        fps = str(self.settings.get("max_fps", "60"))
        self.size_var = StringVar(value=size if size in {"1024", "1280", "1600", "1920"} else "1280")
        self.fps_var = StringVar(value=fps if fps in {"30", "60", "90", "120"} else "60")
        self.audio_var = BooleanVar(value=bool(self.settings.get("audio", False)))
        self.mode_var = StringVar(value=str(self.settings.get("control_mode", "Standard")))
        if self.mode_var.get() not in {"Standard", "OPPO fallback (UHID)"}:
            self.mode_var.set("Standard")
        self.off_var = BooleanVar(value=bool(self.settings.get("screen_off", False)))
        self.auto_var = BooleanVar(value=bool(self.settings.get("auto_open", False)))
        bundled = application_root() / "tools" / "scrcpy"
        if adb and scrcpy and Path(adb).parent == bundled and Path(scrcpy).parent == bundled:
            setup_status = "Connect your phone with a USB cable, then follow Phone setup."
        elif adb and scrcpy:
            setup_status = "Connect your phone with a USB cable, then follow Phone setup."
        else:
            setup_status = "BridgeLab needs setup. Open Help to check the connection."
        self.status_var = FriendlyStatusVar(value=setup_status)
        self.startup_progress("Applying window style")
        self._style()
        self.startup_progress("Building dashboard")
        self._layout()
        self.startup_progress("Dashboard built")
        self.root.after(150, self._drain_events)
        self._schedule_poll(300)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _style(self):
        from desktop_ui import configure_style
        configure_style(self)

    def _card(self, parent, title: str, row: int, column: int = 0, columnspan: int = 1):
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=5, pady=6)
        ttk.Label(card, text=title, style="Card.TLabel", font=("Segoe UI Semibold", 13)).pack(anchor="w", pady=(0, 7))
        return card

    def _layout(self):
        from desktop_ui import build_layout
        build_layout(self)

    def _save_settings(self):
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(json.dumps({
                "adb_path": self.adb_path.get(), "scrcpy_path": self.scrcpy_path.get(),
                "device_serial": self.selected_serial,
                "control_mode": self.mode_var.get(),
                "screen_off": self.off_var.get(),
                "auto_open": self.auto_var.get(),
                "audio": self.audio_var.get(),
                "send_folder": self.send_folder_var.get(),
                "max_size": self.size_var.get(), "max_fps": self.fps_var.get(),
            }, indent=2), encoding="utf-8")
        except OSError as exc:
            self.status_var.set(f"Could not save preferences: {exc}")

    def _schedule_poll(self, delay=3500):
        if self.closing:
            return
        if self.poll_timer is not None:
            self.root.after_cancel(self.poll_timer)
        self.poll_timer = self.root.after(delay, self._poll_devices)

    def _poll_devices(self):
        if self.closing:
            return
        if self.poll_running:
            self.poll_requested = True
            return
        self.poll_requested = False
        if self.poll_timer is not None:
            self.root.after_cancel(self.poll_timer)
            self.poll_timer = None
        adb = self.adb_path.get().strip()
        if not adb or not Path(adb).is_file():
            self.connection_var.set("A connection component is missing — extract the full package again")
            self.battery_var.set("Battery: —")
            self.devices = []
            self.device_box["values"] = []
            self._schedule_poll()
            return
        self.poll_running = True
        self.poll_number += 1
        previous = self.selected_serial
        context = (adb, previous)
        check_battery = self.poll_number % 3 == 1

        def worker():
            try:
                cp = run_command([adb, "devices", "-l"], 8)
                if cp.returncode:
                    raise RuntimeError(cp.stderr.strip() or "ADB devices failed")
                devices = parse_devices(cp.stdout)
                level = None
                if previous and check_battery and any(d.serial == previous and d.authorized for d in devices):
                    try:
                        result = run_command([adb, "-s", previous, "shell", "dumpsys", "battery"], 6)
                    except (OSError, subprocess.TimeoutExpired):
                        result = subprocess.CompletedProcess([], 1, "", "")
                    match = re.search(r"^\s*level:\s*(\d+)", result.stdout, re.MULTILINE)
                    if result.returncode == 0 and match:
                        level = int(match.group(1))
                self.events.put(("devices", (devices, level, None, context)))
            except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
                self.events.put(("devices", ([], None, str(exc), context)))

        threading.Thread(target=worker, daemon=True).start()

    def _update_devices(self, devices: list[Device], battery, error, context=None):
        self.poll_running = False
        if self.closing:
            return
        if context is not None and context != (self.adb_path.get().strip(), self.selected_serial):
            # Never apply old tool/device observations or battery levels to a new selection.
            self._schedule_poll(0)
            return
        delay = 0 if getattr(self, "poll_requested", False) else 3500
        self.poll_requested = False
        if error:
            # An unknown observation is not a physical disconnect/reconnect.
            self.devices = []
            self.device_box["values"] = []
            self.device_var.set("Connection status unavailable")
            self.connection_var.set("ADB unavailable — check cable and run Diagnose")
            self.battery_var.set("Battery: —")
            self.status_var.set("Device discovery failed. Check ADB installation/authorization; retrying automatically.")
            self._schedule_poll(delay)
            return
        newly_authorized = new_authorized_connections(self.last_authorized_serials, devices)
        self.last_authorized_serials = {d.serial for d in devices if d.authorized}
        self.devices = devices
        if context is not None:
            self.devices_adb = context[0]
        labels = [device_name(d) for d in devices]
        self.device_box["values"] = labels
        if error:
            self.connection_var.set("ADB unavailable or timed out")
            self.status_var.set(str(error))
        elif not devices:
            self.connection_var.set("Connect your phone and approve this PC.")
        elif not any(d.authorized for d in devices):
            self.connection_var.set("Phone detected. Unlock it and approve this PC.")
        else:
            self.connection_var.set(f"{sum(d.authorized for d in devices)} authorized device(s) available")
        if devices and not self.selected_serial:
            good = next((d for d in devices if d.authorized), devices[0])
            self.selected_serial = good.serial
            self._save_settings()
        selected = next((d for d in devices if d.serial == self.selected_serial), None)
        if selected:
            self.device_var.set(device_name(selected))
        else:
            self.device_var.set("Selected phone disconnected" if self.selected_serial else "No device detected")
        if battery is not None:
            self.battery_var.set(f"Battery: {battery}%")
        elif not selected or not selected.authorized:
            self.battery_var.set("Battery: —")
        if (self.auto_var.get() and self.selected_serial in newly_authorized
                and self.selected_serial and selected and selected.authorized
                and (self.mirror_process is None or self.mirror_process.poll() is not None)):
            self.status_var.set("Authorized phone connected. Opening a mirror session…")
            serial = self.selected_serial
            generation = getattr(self, "launch_generation", 0)
            self.root.after(250, lambda: self._auto_start(serial, generation))
        self._schedule_poll(delay)

    def _auto_start(self, serial, generation=None):
        if generation is not None and generation != getattr(self, "launch_generation", 0):
            return
        if (not self.closing and self.auto_var.get() and serial == self.selected_serial
                and any(d.serial == serial and d.authorized for d in self.devices)
                and (self.mirror_process is None or self.mirror_process.poll() is not None)):
            self.start_mirror(auto=True)

    def _select_device(self, _event=None):
        index = self.device_box.current()
        if 0 <= index < len(self.devices):
            self.selected_serial = self.devices[index].serial
            self.launch_generation = getattr(self, "launch_generation", 0) + 1
            self.launch_pending = False
            self.poll_number = 0
            self.battery_var.set("Battery: updating…")
            self._save_settings()
            self._poll_devices()

    def _ready(self) -> tuple[str, str]:
        adb = self.adb_path.get().strip()
        scrcpy = self.scrcpy_path.get().strip()
        if not adb or not Path(adb).is_file():
            raise ValueError("A bundled connection component is missing. Extract the complete BridgeLab package into a new folder.")
        if getattr(self, "devices_adb", adb) != adb:
            raise ValueError("ADB selection changed. Refresh and authorize the selected phone first.")
        if not any(d.serial == self.selected_serial and d.authorized for d in self.devices):
            raise ValueError("Select an authorized Android device and refresh.")
        return adb, scrcpy

    def _launch_scrcpy(self, package: str | None, *, auto=False):
        try:
            if self.closing:
                return
            if getattr(self, "launch_pending", False):
                raise ValueError("A mirror session is starting. Wait or press Stop first.")
            if self.mirror_process and self.mirror_process.poll() is None:
                raise ValueError("A mirror session is already open. Press Stop first.")
            adb, scrcpy = self._ready()
            if not scrcpy or not Path(scrcpy).is_file():
                raise ValueError("A bundled screen component is missing. Extract the complete BridgeLab package into a new folder.")
            target = None
            if package is None and hasattr(self, "send_folder_var"):
                target = normalize_mirror_drop_target(self.send_folder_var.get())
            args = scrcpy_command(scrcpy, self.selected_serial, int(self.size_var.get()),
                                  int(self.fps_var.get()), self.audio_var.get(), package,
                                  control_mode="uhid" if self.mode_var.get() == "OPPO fallback (UHID)" else "standard",
                                  turn_screen_off=self.off_var.get(), push_target=target)
            if target is not None:
                args.append("--window-title=BridgeLab — Phone screen")
            self.launch_generation = getattr(self, "launch_generation", 0) + 1
            generation = self.launch_generation
            if os.name == "nt" or target is not None:
                self.launch_pending = True
                serial = self.selected_serial
                self.status_var.set("Getting your phone screen ready…")

                def validate():
                    error = None
                    try:
                        if os.name == "nt":
                            validate_bundle_files(application_root(), scrcpy)
                            validate_windows_tool(scrcpy, "scrcpy.exe")
                            validate_windows_tool(adb, "adb.exe")
                        if target is not None:
                            prepare_mirror_drop(adb, serial, target, run_command)
                    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                        error = exc
                    self.events.put(("launch_ready", (generation, serial, args, adb, scrcpy, package, error, auto)))

                threading.Thread(target=validate, daemon=True).start()
            else:
                self._spawn_scrcpy(args, adb, scrcpy, package)
        except (ValueError, OSError) as exc:
            self._launch_error(exc)

    def _finish_launch(self, generation, serial, args, adb, scrcpy, package, error, auto=False):
        if self.closing or generation != self.launch_generation:
            return
        self.launch_pending = False
        if auto and not self.auto_var.get():
            self.status_var.set("Automatic session start cancelled because auto-open was disabled.")
            return
        if (serial != self.selected_serial or adb != self.adb_path.get().strip()
                or scrcpy != self.scrcpy_path.get().strip()
                or not any(d.serial == serial and d.authorized for d in self.devices)):
            self.status_var.set("Launch cancelled because the selected device or tools changed. Open the screen again.")
            return
        expected_target = next((a.split("=", 1)[1] for a in args if a.startswith("--push-target=")), None)
        if expected_target is not None and self.send_folder_var.get() != expected_target:
            self.status_var.set("The file destination changed. Open your phone screen again to use it.")
            return
        if error is not None:
            self._launch_error(error)
            return
        self._spawn_scrcpy(args, adb, scrcpy, package)

    def _spawn_scrcpy(self, args, adb, scrcpy, package):
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            self._close_log_handle()
            self.scrcpy_log_handle = open(LOG_FILE, "ab")
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            start = time.perf_counter()
            # Ensure scrcpy and this UI use exactly the same ADB executable.
            runtime_env = dict(os.environ)
            runtime_env["ADB"] = adb
            server = Path(scrcpy).resolve().parent / "scrcpy-server"
            if server.is_file():
                runtime_env["SCRCPY_SERVER_PATH"] = str(server)
            self.mirror_process = subprocess.Popen(args, stdout=self.scrcpy_log_handle,
                                                   stderr=subprocess.STDOUT, creationflags=flags,
                                                   env=runtime_env, cwd=str(Path(scrcpy).resolve().parent))
            duration = int((time.perf_counter() - start) * 1000)
            self._metric("virtual_display" if package else "mirror_start", "launched", duration)
            self.status_var.set("Your phone screen is opening. Drag files onto that window to send them.")
            self._schedule_session_check(self.mirror_process, 1000)
        except (ValueError, OSError) as exc:
            self._launch_error(exc)

    def _launch_error(self, exc):
        if self.mirror_process is None or self.mirror_process.poll() is not None:
            self._close_log_handle()
        detail = str(exc)
        if isinstance(exc, OSError) and getattr(exc, "winerror", None) == 193:
            detail = ("Windows rejected the selected scrcpy executable or one of its dependencies. "
                      "This happens before contacting the phone; changing USB drivers will not fix this launch error.\n\n"
                      + tool_report(self.scrcpy_path.get()) +
                      "\n\nExtract the complete package to a fresh folder. Do not combine files from different downloads. "
                      "If this persists, share these details and the Help → Diagnostics report.")
        messagebox.showerror("Cannot launch", detail)

    def _schedule_session_check(self, proc, delay=1400):
        if getattr(self, "session_timer", None) is not None:
            self.root.after_cancel(self.session_timer)
        self.session_timer = self.root.after(delay, lambda: self._check_scrcpy(proc))

    def _check_scrcpy(self, expected_process=None):
        proc = self.mirror_process
        if self.closing or (expected_process is not None and proc is not expected_process):
            return
        self.session_timer = None
        if proc and proc.poll() is not None:
            code = proc.returncode
            self.mirror_process = None
            self._close_log_handle()
            stopped = proc is getattr(self, "stopping_process", None)
            self.stopping_process = None
            if code != 0 and not stopped:
                self._metric("scrcpy_exit", "failed", 0)
                self.status_var.set(f"scrcpy exited with code {code}. Open local logs to diagnose it.")
            else:
                self.status_var.set("scrcpy session closed.")
        elif proc:
            self._schedule_session_check(proc)

    def start_mirror(self, *, auto=False):
        self._launch_scrcpy(None, auto=auto)

    def open_app(self):
        try:
            adb, scrcpy = self._ready()
            if not scrcpy or not Path(scrcpy).is_file():
                raise ValueError("The screen component is missing. Extract the complete package again.")
            controller = open_app_windows(self.root, adb, scrcpy, self.selected_serial, run_command,
                size=int(self.size_var.get()), fps=int(self.fps_var.get()), audio=self.audio_var.get(),
                control_mode="uhid" if self.mode_var.get() == "OPPO fallback (UHID)" else "standard",
                log_dir=APP_DIR)
            self.child_controllers.append(controller)
        except (ValueError, OSError, tk.TclError) as exc:
            messagebox.showerror("Cannot open app chooser", str(exc))

    def browse_phone(self):
        try:
            adb, _ = self._ready()
            serial = self.selected_serial
            def is_current():
                return (not self.closing and self.selected_serial == serial
                        and self.adb_path.get().strip() == adb
                        and getattr(self, "devices_adb", adb) == adb
                        and any(d.serial == serial and d.authorized for d in self.devices))
            controller = open_phone_browser(self.root, adb, serial, run_command, is_current=is_current)
            self.child_controllers.append(controller)
        except (ValueError, OSError, tk.TclError) as exc:
            messagebox.showerror("Cannot browse phone", str(exc))

    def show_phone_setup(self):
        def connection():
            adb, _ = self._ready()
            return adb, self.selected_serial
        open_phone_setup(self.root, connection, run_command)

    def change_send_folder(self):
        from tkinter import simpledialog
        current = self.send_folder_var.get()
        initial = current[len("/sdcard/"):] if current.startswith("/sdcard/") else current
        value = simpledialog.askstring("Choose a phone folder", "Folder inside your phone's Internal storage.\nExample: Download/BridgeLab or Pictures\n\nThis applies to the next screen session. Existing files with the same name may be replaced.", initialvalue=initial, parent=self.root)
        if value is None:
            return
        value = value.strip()
        if not value.startswith("/"):
            value = "/sdcard/" + value
        try:
            target = normalize_mirror_drop_target(value)
        except ValueError as exc:
            messagebox.showerror("Choose another folder", str(exc), parent=self.root)
            return
        self.send_folder_var.set(target)
        self._save_settings()
        self.status_var.set("File destination saved. Close and reopen the phone screen to apply it.")

    def show_calls(self):
        def connection():
            adb, _ = self._ready()
            return adb, self.selected_serial
        try:
            open_phone_calls(self.root, connection, run_command)
        except (ValueError, OSError, tk.TclError) as exc:
            messagebox.showerror("Phone dialer", str(exc), parent=self.root)

    def stop_mirror(self):
        was_pending = getattr(self, "launch_pending", False)
        self.launch_generation = getattr(self, "launch_generation", 0) + 1
        self.launch_pending = False
        proc = self.mirror_process
        if proc and proc.poll() is None:
            self.stopping_process = proc
            self._terminate_process(proc)
            self.status_var.set("Stopping scrcpy…")
        else:
            self.status_var.set("Session start cancelled." if was_pending else "No active scrcpy session.")

    @staticmethod
    def _terminate_process(proc):
        def stop():
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
        threading.Thread(target=stop, daemon=True).start()

    def _close_log_handle(self):
        if self.scrcpy_log_handle is not None:
            self.scrcpy_log_handle.close()
            self.scrcpy_log_handle = None

    def _metric(self, action: str, result: str, elapsed_ms: int, byte_count: int = 0):
        # No URLs, file paths, notification contents or phone identifiers recorded.
        with self.log_lock:
            try:
                APP_DIR.mkdir(parents=True, exist_ok=True)
                new = not METRICS_FILE.exists()
                with METRICS_FILE.open("a", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    if new:
                        writer.writerow(["time_utc", "action", "result", "elapsed_ms", "bytes"])
                    writer.writerow([datetime.now(timezone.utc).isoformat(), action, result, elapsed_ms, byte_count])
            except OSError:
                pass

    def _background_action(self, action: str, fn, byte_count=0):
        if self.closing:
            return
        if self.busy_actions:
            self.status_var.set("Wait for the current transfer or handoff to finish.")
            return
        self.busy_actions += 1
        for button in (self.file_button, self.url_button):
            button.configure(state="disabled")
        self.status_var.set(f"Working: {action}…")

        def worker():
            start = time.perf_counter()
            try:
                result = fn()
                state = "success"
                message = result
            except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
                state = "failed"
                # Command exceptions include argv (potentially a private URL/path).
                message = ("Operation timed out. Check the phone and cable. A partial file may remain; inspect Downloads before retrying."
                           if isinstance(exc, subprocess.TimeoutExpired) else str(exc))
            duration = int((time.perf_counter() - start) * 1000)
            self._metric(action, state, duration, byte_count)
            self.events.put(("action", (action, state, message, duration)))

        threading.Thread(target=worker, daemon=True).start()

    def send_files(self):
        try:
            adb, _ = self._ready()
        except ValueError as exc:
            messagebox.showerror("Cannot transfer", str(exc))
            return
        serial = self.selected_serial
        try:
            folder = normalize_mirror_drop_target(self.send_folder_var.get())
        except ValueError as exc:
            messagebox.showerror("Choose another phone folder", str(exc))
            return
        selection = filedialog.askopenfilenames(title="Choose files to send to your phone")
        if not selection:
            return
        try:
            paths = safe_local_files(list(selection))
        except ValueError as exc:
            messagebox.showerror("Invalid files", str(exc))
            return
        if not messagebox.askokcancel("Send files", "Send to your selected phone folder?\nFiles with the same name in that folder will be replaced."):
            return
        try:
            current_adb, _ = self._ready()
            if self.closing or serial != self.selected_serial or adb != current_adb:
                raise ValueError("The selected phone or ADB changed. Choose files again for the current phone.")
            byte_count = sum(p.stat().st_size for p in paths)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Cannot read files", str(exc))
            return

        def task():
            return send_verified(adb, serial, paths, run_command, folder=folder)

        self._background_action("file_push", task, byte_count)

    def check_phone_files(self):
        try:
            adb, _ = self._ready()
        except ValueError as exc:
            messagebox.showerror("Cannot inspect phone folder", str(exc))
            return
        serial = self.selected_serial
        def task():
            cp = run_command([adb, "-s", serial, "shell", "ls -la /sdcard/Download/; if [ -d /sdcard/Download/BridgeLab ]; then ls -la /sdcard/Download/BridgeLab/; fi"], timeout=15)
            if cp.returncode:
                raise RuntimeError(cp.stderr.strip() or "Could not list phone Downloads")
            return "Selected phone's Internal storage / Download (old sends) and Download / BridgeLab (new sends):\n\n" + cp.stdout[-12000:]
        self._background_action("phone_folder", task)

    def paste_url(self):
        try:
            value = self.root.clipboard_get()
            self.url_var.set(clean_url(value))
        except (tk.TclError, ValueError) as exc:
            messagebox.showwarning("Clipboard", f"Clipboard does not contain a valid HTTP/HTTPS URL.\n{exc}")

    def open_url(self):
        try:
            adb, _ = self._ready()
            command = url_intent_shell_command(self.url_var.get())
        except ValueError as exc:
            messagebox.showerror("Cannot open link", str(exc))
            return
        serial = self.selected_serial

        def task():
            cp = run_command([adb, "-s", serial, "shell", command], timeout=15)
            if cp.returncode:
                raise RuntimeError(cp.stderr.strip() or cp.stdout.strip() or "Android could not open the link")
            return "Link sent to Android. The selected Android app should open it."

        self._background_action("open_url", task)

    def diagnose(self):
        """Read-only diagnostic; never alters Android settings or sends data externally."""
        adb = self.adb_path.get().strip()
        scrcpy = self.scrcpy_path.get().strip()
        serial = self.selected_serial
        selected = next((d for d in self.devices if d.serial == serial), None)
        if not adb or not Path(adb).is_file():
            messagebox.showerror("Diagnostics", "ADB is missing. Select its location first.")
            return
        self.status_var.set("Running read-only diagnostics…")

        def task():
            lines = ["ADB selection: " + adb, "scrcpy selection: " + scrcpy, "\nStatic scrcpy inspection:\n" + tool_report(scrcpy)]
            for label, argv in (("ADB", [adb, "version"]),
                                ("scrcpy", [scrcpy, "--version"] if scrcpy and Path(scrcpy).is_file() else None)):
                if argv is None:
                    lines.append(label + ": not installed or not selected")
                    continue
                cp = run_command(argv, timeout=8)
                version = (cp.stdout or cp.stderr).strip().splitlines()
                lines.append(label + ": " + (version[0][:160] if version else f"exit code {cp.returncode}"))
            if not selected or not selected.authorized:
                lines.append("PHONE: No authorized Android device selected.")
                lines.append("Action: unlock phone, approve USB debugging, and press Refresh.")
            else:
                for label, prop in (("Phone", "ro.product.model"),
                                    ("Android", "ro.build.version.release"),
                                    ("ColorOS (if available)", "ro.build.version.opporom")):
                    cp = run_command([adb, "-s", serial, "shell", "getprop", prop], timeout=8)
                    value = cp.stdout.strip() if cp.returncode == 0 else ""
                    lines.append(label + ": " + (value or "unknown"))
                lines.append("Connection: " + ("Wi-Fi/ADB" if ":" in serial else "USB/ADB"))
            lines.append("\nStandard input fails? Try OPPO fallback (UHID).")
            lines.append("If UHID captures the pointer, press Alt to release it.")
            lines.append("Protected/DRM screens may be blank even when normal mirroring works.")
            return "\n".join(lines)

        def worker():
            try:
                report = task()
            except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
                report = "Diagnostics failed: " + str(exc)
            self.events.put(("diagnostics", report))

        threading.Thread(target=worker, daemon=True).start()

    def _show_diagnostics(self, report: str):
        window = tk.Toplevel(self.root)
        window.title("BridgeLab — Device diagnostics")
        window.geometry("670x340")
        window.configure(background=BG)
        body = tk.Text(window, background=SURFACE, foreground=TEXT, insertbackground=TEXT,
                       font=("Consolas", 10), padx=14, pady=12, wrap="word", relief="flat")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.insert("1.0", report)
        body.configure(state="disabled")
        self.status_var.set("Diagnostics complete. No data was uploaded.")

    def open_logs(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(APP_DIR))
            else:
                self.status_var.set(f"Local log folder: {APP_DIR}")
        except OSError as exc:
            messagebox.showerror("Cannot open folder", str(exc))

    def _drain_events(self):
        if self.closing:
            return
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "devices":
                    self._update_devices(*data)
                elif kind == "launch_ready":
                    self._finish_launch(*data)
                elif kind == "diagnostics":
                    self._show_diagnostics(str(data))
                elif kind == "action":
                    action, state, message, duration = data
                    self.busy_actions = max(0, self.busy_actions - 1)
                    for button in (self.file_button, self.url_button):
                        button.configure(state="normal")
                    self.status_var.set(f"{action}: {message} ({duration} ms)")
                    if state == "success" and action in {"file_push", "phone_folder"}:
                        self._show_diagnostics(str(message))
                    if state == "failed":
                        messagebox.showerror("Operation failed", message)
        except queue.Empty:
            pass
        if not self.closing:
            self.root.after(180, self._drain_events)

    def _on_close(self):
        if getattr(self, "busy_actions", 0):
            messagebox.showinfo("Operation in progress", "Wait for the current transfer or handoff to finish, then close BridgeLab.")
            return
        for controller in getattr(self, "child_controllers", []):
            if controller.close() is False:
                self.status_var.set("A phone-file operation or app-window stop is still active. Wait, then close BridgeLab again.")
                return
        if self.mirror_process and self.mirror_process.poll() is None:
            if getattr(self, "stopping_process", None) is not self.mirror_process:
                self.stop_mirror()
            self.status_var.set("Stopping the mirror before closing…")
            self.root.after(200, self._on_close)
            return
        self.closing = True
        self.launch_generation = getattr(self, "launch_generation", 0) + 1
        self._save_settings()
        if self.mirror_process and self.mirror_process.poll() is None:
            self._terminate_process(self.mirror_process)
        self._close_log_handle()
        if self.poll_timer is not None:
            self.root.after_cancel(self.poll_timer)
        if getattr(self, "session_timer", None) is not None:
            self.root.after_cancel(self.session_timer)
        self.root.destroy()


def portable_self_check(destination: str) -> int:
    """Build-time smoke check; does not contact a phone or start ADB."""
    result = {"version": "0.5.1", "frozen": bool(getattr(sys, "frozen", False)),
              "root": str(application_root()), "ok": False}
    try:
        root = Tk()
        root.withdraw()
        result["tk_version"] = str(root.tk.call("info", "patchlevel"))
        root.destroy()
        adb, scrcpy = discover_tools()
        if not adb or not scrcpy:
            raise RuntimeError("Portable adb/scrcpy tools are missing")
        result.update(adb=adb, scrcpy=scrcpy, ok=True)
    except Exception as exc:
        result["error"] = str(exc)
    Path(destination).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["ok"] else 1


def _report_ui_error(root, kind, value, tb):
    import traceback
    import logging
    detail = ''.join(traceback.format_exception(kind, value, tb))
    # Separate file: ordinary Tk callback exceptions otherwise go only to a console.
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with (APP_DIR / 'ui-errors.log').open('a', encoding='utf-8') as handle:
            handle.write(detail + '\n')
    except OSError:
        pass
    print(detail, file=sys.stderr, flush=True)
    messagebox.showerror('BridgeLab needs attention', 'A window error occurred. Details are in the local ui-errors.log file.\n\n' + str(value), parent=root)


def main(progress=None):
    progress = progress or (lambda message: None)
    if len(sys.argv) == 3 and sys.argv[1] == "--self-check-file":
        raise SystemExit(portable_self_check(sys.argv[2]))
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    progress("Creating desktop window")
    root = Tk()
    root.report_callback_exception = lambda kind, value, tb: _report_ui_error(root, kind, value, tb)
    app = BridgeLab(root, progress=progress)
    root._bridgelab_application = app
    from window_visibility import schedule_presentation
    schedule_presentation(root, progress)
    progress("Starting window event loop")
    root.mainloop()


if __name__ == "__main__":
    main()
