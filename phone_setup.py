"""Visible setup navigation; never toggles settings or grants permissions."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

SETTINGS_ACTIONS = {
    'developer': 'android.settings.APPLICATION_DEVELOPMENT_SETTINGS',
    'settings': 'android.settings.SETTINGS',
}


def settings_command(adb, serial, page):
    if page not in SETTINGS_ACTIONS:
        raise ValueError('Unsupported settings page.')
    return [adb, '-s', serial, 'shell', 'am start -a ' + SETTINGS_ACTIONS[page]]


def open_phone_setup(parent, get_connection, run):
    window = tk.Toplevel(parent)
    window.title('BridgeLab — Phone setup and access')
    window.geometry('650x470')
    window.transient(parent)
    frame = ttk.Frame(window, padding=18)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='What BridgeLab uses', font=('Segoe UI Semibold', 15)).pack(anchor='w')
    text = (
        'No BridgeLab Android app is installed for these features.\n\n'
        'USB debugging / ADB authorization: discovers the phone, mirrors it, runs app windows, '
        'and copies files in shared storage. Android trusts this computer as an ADB host; '
        'this approval cannot be restricted to BridgeLab alone. Authorize only your own computer.\n\n'
        'Phone microphone, contacts, call log and call permissions: not requested. '
        'USB tethering, Accessibility service and All files access: not required.\n\n'
        'First connection: enable Developer options and USB debugging on the phone, '
        'unlock it, and approve the computer fingerprint. This first approval must happen '
        'on the phone. Once authorized, the shortcuts below can open Settings; '
        'they never grant permission or switch settings for you.\n\n'
        'To end access, disconnect and disable USB debugging, or revoke USB debugging '
        'authorizations in Developer options. Revoke removes trust for other ADB tools too.'
    )
    ttk.Label(frame, text=text, wraplength=605, justify='left').pack(anchor='w', pady=10)
    status = tk.StringVar(value='No phone settings have been changed.')
    ttk.Label(frame, textvariable=status, wraplength=605).pack(anchor='w', pady=8)
    events = queue.Queue()
    alive = True
    busy = False
    def open_page(page):
        nonlocal busy
        if busy:
            return
        try:
            adb, serial = get_connection()
        except (ValueError, OSError) as exc:
            status.set('Authorize USB debugging manually first. ' + str(exc))
            return
        busy = True
        status.set('Opening settings on the selected phone…')
        def worker():
            try:
                cp = run(settings_command(adb, serial, page), timeout=12)
                output = ((cp.stdout or '') + '\n' + (cp.stderr or '')).strip()
                if cp.returncode or 'Error:' in output or 'Exception' in output:
                    events.put('Phone could not open that page. Use Settings on the phone manually. ' + output[:220])
                else:
                    events.put('Settings opened on the phone. Read the page and choose any changes yourself.')
            except Exception as exc:
                import subprocess
                if isinstance(exc, subprocess.TimeoutExpired):
                    events.put('Settings request timed out. Check the phone; it may already be open.')
                else:
                    events.put('Could not open settings: ' + str(exc))
        threading.Thread(target=worker, daemon=True).start()
    row = ttk.Frame(frame)
    row.pack(fill='x', pady=8)
    first = ttk.Button(row, text='Open Developer options on phone', command=lambda: open_page('developer'))
    first.pack(side='left', padx=(0, 8))
    ttk.Button(row, text='Open phone Settings', command=lambda: open_page('settings')).pack(side='left')
    def drain():
        nonlocal busy
        if not alive:
            return
        try:
            while True:
                status.set(events.get_nowait())
                busy = False
        except queue.Empty:
            pass
        window.after(120, drain)
    def close():
        nonlocal alive
        alive = False
        window.destroy()
    window.protocol('WM_DELETE_WINDOW', close)
    window.after(120, drain)
    first.focus_set()
    return window
