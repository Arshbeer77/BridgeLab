"""One captured phone, one independent app-window session; Tk on main thread."""
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from friendly_text import FriendlyStatusVar

from app_windows import preflight, list_apps, app_window_command, scrcpy_environment, open_on_phone


class AppWindowsWindow:
    def __init__(self, parent, adb, scrcpy, serial, run, *, size=1280, fps=60,
                 audio=False, control_mode='standard', log_dir=None):
        self.adb, self.scrcpy, self.serial, self.run = adb, scrcpy, serial, run
        self.options = dict(size=size, fps=fps, audio=audio, control_mode=control_mode)
        self.process = None
        self.stop_pending = False
        self.log_handle = None
        self.log_path = None
        self.closed = False
        self.close_requested = False
        self.handoff_pending = False
        self.apps = []
        self.events = queue.Queue()
        self.log_dir = Path(log_dir or Path.home() / 'BridgeLab')
        self.window = tk.Toplevel(parent)
        self.window.title('App windows — device check required')
        self.window.geometry('720x540')
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        frame = ttk.Frame(self.window, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='App windows · software-tested beta', font=('', 13, 'bold')).pack(anchor='w')
        ttk.Label(frame, text=f'Phone: {serial} (fixed for this window)').pack(anchor='w', pady=(8, 4))
        ttk.Label(frame, text='Runs an installed app on this phone’s virtual display.\n'
                  'Shares phone data; no separate Android instance. OEM/app compatibility needs device testing.',
                  wraplength=610).pack(anchor='w')
        self.status = FriendlyStatusVar(value='Finding apps on your phone…')
        ttk.Label(frame, textvariable=self.status, wraplength=610).pack(anchor='w', pady=10)
        self.listbox = tk.Listbox(frame, exportselection=False, height=10)
        self.listbox.pack(fill='both', expand=True)
        controls = ttk.Frame(frame)
        controls.pack(fill='x', pady=(10, 0))
        self.start_button = ttk.Button(controls, text='Open selected app', command=self.launch, state='disabled')
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        self.start_button.grid(row=0, column=0, sticky='ew', padx=(0, 5), pady=4)
        self.phone_button = ttk.Button(controls, text='Open on phone instead', command=self.open_selected_on_phone)
        self.phone_button.grid(row=0, column=1, sticky='ew', padx=(5, 0), pady=4)
        self.stop_button = ttk.Button(controls, text='Stop app window', command=self.stop, state='disabled')
        self.stop_button.grid(row=1, column=0, sticky='ew', padx=(0, 5), pady=4)
        self.refresh_button = ttk.Button(controls, text='Refresh apps', command=self.refresh, state='disabled')
        self.refresh_button.grid(row=1, column=1, sticky='ew', padx=(5, 0), pady=4)
        self.after_id = self.window.after(100, self._poll)
        self.refresh()

    def refresh(self):
        self.start_button.configure(state='disabled')
        self.refresh_button.configure(state='disabled')
        self.status.set('Checking capabilities and reading launchable apps…')
        def worker():
            try:
                capability = preflight(self.adb, self.scrcpy, self.serial, self.run)
                if not capability.supported:
                    raise RuntimeError(capability.diagnostics)
                apps = list_apps(self.adb, self.scrcpy, self.serial, self.run, capability)
                self.events.put(('apps', (capability, apps)))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        if self.closed:
            return
        try:
            while True:
                kind, value = self.events.get_nowait()
                if self.close_requested and kind in {'apps', 'error'}:
                    continue
                if kind == 'apps':
                    capability, self.apps = value
                    self.listbox.delete(0, 'end')
                    for app in self.apps:
                        self.listbox.insert('end', app.label)
                    if self.apps:
                        self.listbox.selection_set(0)
                    self.status.set(f'{len(self.apps)} phone apps ready. Choose one to open.')
                    self.start_button.configure(state='normal' if self.apps else 'disabled')
                elif kind == 'handoff':
                    self.handoff_pending = False
                    self.status.set(value)
                    continue
                elif kind == 'stopped':
                    self.stop_pending = False
                    if self.process is value:
                        self.process = None
                        self._close_log()
                    self.stop_button.configure(state='disabled')
                    self.status.set('App window stopped. Its virtual display is removed; Android may close apps on it.')
                    continue
                elif kind == 'stop_failed':
                    self.stop_pending = False
                    self.status.set(value)
                    self.stop_button.configure(state='normal')
                    continue
                else:
                    self.apps = []
                    self.listbox.delete(0, 'end')
                    self.status.set(value)
                self.refresh_button.configure(state='normal')
        except queue.Empty:
            pass
        if self.process is not None and self.process.poll() is not None:
            code = self.process.returncode
            self.process = None
            self._close_log()
            self.stop_button.configure(state='disabled')
            self.status.set(f'App window exited ({code}). Log: {self.log_path}. '
                            'If launch failed, the selected app or phone may reject secondary displays.')
        if (self.close_requested and not self.stop_pending and not self.handoff_pending
                and (self.process is None or self.process.poll() is not None)):
            self.close()
            return
        self.after_id = self.window.after(200, self._poll)

    def launch(self):
        if self.close_requested:
            return
        if self.stop_pending or (self.process is not None and self.process.poll() is None):
            messagebox.showinfo('App window open', 'Stop the current app window before opening another.', parent=self.window)
            return
        selected = self.listbox.curselection()
        if not selected or selected[0] >= len(self.apps):
            return
        try:
            args = app_window_command(self.scrcpy, self.serial, self.apps[selected[0]].package, **self.options)
            args.append('--window-title=BridgeLab — ' + self.apps[selected[0]].name[:100].replace('\n', ' '))
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._close_log()
            self.log_path = self.log_dir / f'app-window-{time.time_ns()}.log'
            self.log_handle = open(self.log_path, 'ab')
            self.process = subprocess.Popen(args, stdout=self.log_handle, stderr=subprocess.STDOUT,
                env=scrcpy_environment(self.adb, self.scrcpy), cwd=str(Path(self.scrcpy).resolve().parent),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.stop_button.configure(state='normal')
            self.status.set(f'App-window process started for {self.serial}; confirm its window works. Log: {self.log_path}')
        except (OSError, ValueError) as exc:
            self._close_log()
            self.status.set(f'Cannot start app window: {exc}')

    def open_selected_on_phone(self):
        if self.closed or self.close_requested or getattr(self, 'handoff_pending', False):
            return
        selected = self.listbox.curselection()
        if not selected or selected[0] >= len(self.apps):
            self.status.set('Select a phone app first.')
            return
        package = self.apps[selected[0]].package
        self.handoff_pending = True
        self.status.set('Opening the selected app on the phone screen…')
        def worker():
            try:
                result = open_on_phone(self.adb, self.serial, package, self.run)
            except subprocess.TimeoutExpired:
                result = 'Request timed out. Check the phone; the app may already be open.'
            except (OSError, ValueError, RuntimeError) as exc:
                result = 'Could not open this app on the phone. ' + str(exc)
            self.events.put(('handoff', result))
        threading.Thread(target=worker, daemon=True).start()

    def _close_log(self):
        if self.log_handle is not None:
            self.log_handle.close()
            self.log_handle = None

    def stop(self):
        proc = self.process
        if self.stop_pending:
            return
        if proc is None or proc.poll() is not None:
            self.process = None
            self._close_log()
            if not self.closed:
                self.stop_button.configure(state='disabled')
                self.status.set('App window stopped.')
            return
        self.stop_pending = True
        # Signal synchronously; bounded waiting/escalation stays off the Tk thread.
        try:
            proc.terminate()
        except OSError:
            pass
        handle = self.log_handle
        if not self.closed:
            self.stop_button.configure(state='disabled')
            self.status.set('Stopping app window…')
        def finish_stop():
            try:
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
                if handle is not None:
                    handle.close()
                self.events.put(('stopped', proc))
            except (OSError, subprocess.TimeoutExpired) as exc:
                # Keep self.process until an observed exit; do not allow overlap.
                self.events.put(('stop_failed', f'App process has not confirmed exit: {exc}'))
        threading.Thread(target=finish_stop, daemon=True).start()

    def close(self):
        """Return False while the parent must keep Tk alive for child cleanup."""
        if getattr(self, 'handoff_pending', False):
            self.close_requested = True
            self.status.set('Waiting for the phone request to finish before closing…')
            return False
        if self.closed:
            return True
        self.close_requested = True
        self.start_button.configure(state='disabled')
        self.refresh_button.configure(state='disabled')
        if self.stop_pending or (self.process is not None and self.process.poll() is None):
            self.stop()
            return False
        self.closed = True
        self.window.after_cancel(self.after_id)
        self._close_log()
        self.window.destroy()
        return True


def open_app_windows(parent, adb, scrcpy, serial, run, **options):
    return AppWindowsWindow(parent, adb, scrcpy, serial, run, **options)
