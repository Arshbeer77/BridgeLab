"""Open Android's dialer for an explicit user-confirmed call; no PC audio bridge."""
import queue
import re
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

PHONE_LINK_HELP = 'https://support.microsoft.com/en-us/windows/apps/phonelink/setting-up-calls-in-the-phone-link'


def normalize_number(number):
    """Accept ordinary phone numbers only, excluding service codes and URI extras."""
    if not isinstance(number, str) or len(number) > 100:
        raise ValueError('Enter a phone number using digits and an optional leading +.')
    number = number.strip()
    if number and not re.fullmatch(r'[0-9+ ().-]+', number):
        raise ValueError('Use digits, spaces, parentheses, hyphens and an optional leading +.')
    cleaned = re.sub(r'[ ().-]', '', number)
    if number and not re.fullmatch(r'\+?[0-9]{1,32}', cleaned):
        raise ValueError('Enter 1–32 digits with an optional leading +, or leave it blank.')
    return cleaned


def dialer_command(adb, serial, number=''):
    if not adb or not serial:
        raise ValueError('Connect and select an authorized phone first.')
    # One fixed Android shell command, with a strict ASCII allowlist for its data.
    # ACTION_DIAL opens the phone UI. Never use ACTION_CALL or synthesize Call taps.
    number = normalize_number(number)
    return [adb, '-s', serial, 'shell',
            'am start -a android.intent.action.DIAL -d tel:' + number]


def request_dialer(adb, serial, number, run):
    """Bounded request, no retries: a timeout may still have opened the dialer."""
    args = dialer_command(adb, serial, number)
    try:
        cp = run(args, timeout=12)
    except subprocess.TimeoutExpired:
        return 'The request timed out. Check the phone; the dialer may already be open.'
    except OSError:
        return 'Could not reach the phone. Check the cable and USB debugging authorization.'
    output = ((cp.stdout or '') + '\n' + (cp.stderr or '')).lower()
    # Android am can report an activity error while the ADB process exits zero.
    if cp.returncode or any(marker in output for marker in
                            ('error:', 'exception', 'unable to resolve intent', 'permission denial')):
        return 'The phone could not open its dialer. Unlock it and check its Phone app and USB connection.'
    return 'Dialer request sent. Review the number and press Call on the phone or its mirrored screen. Audio stays on the phone.'


def open_phone_calls(parent, get_connection, run):
    """get_connection returns the current (adb, selected_serial), on the UI thread."""
    connection = tuple(get_connection())
    dialer_command(*connection)
    window = tk.Toplevel(parent)
    window.title('BridgeLab — Phone dialer')
    window.geometry('650x580')
    window.minsize(650, 560)
    window.transient(parent)
    body = ttk.Frame(window, padding=18)
    body.pack(fill='both', expand=True)
    ttk.Label(body, text='Open the phone dialer', font=('Segoe UI Semibold', 16)).pack(anchor='w')
    ttk.Label(body, text='Selected phone: ' + connection[1], wraplength=595).pack(anchor='w', pady=(5, 0))
    ttk.Label(body, text='Prepare a number here, then review it and press Call on your phone or mirrored screen.',
              wraplength=595).pack(anchor='w', pady=(8, 14))
    ttk.Label(body, text='Phone number (optional)').pack(anchor='w')
    number = tk.StringVar()
    entry = ttk.Entry(body, textvariable=number, font=('Segoe UI', 14))
    entry.pack(fill='x', pady=(5, 8))
    ttk.Label(body, text='Call audio uses the phone or a headset connected to the phone. BridgeLab does not send your PC microphone or headset into cellular calls.',
              wraplength=595, justify='left').pack(anchor='w', pady=(6, 12))
    events = queue.Queue()
    busy = False
    alive = True
    timer = None
    status = tk.StringVar(value='No call is placed automatically. Your number is not saved by BridgeLab.')

    def submit():
        nonlocal busy
        if busy or not alive:
            return
        try:
            value = normalize_number(number.get())
            current = tuple(get_connection())
            if current != connection:
                raise ValueError('Phone selection changed. Close this dialer and reopen it for the selected phone.')
            adb, serial = connection
            dialer_command(adb, serial, value)
        except (ValueError, OSError) as exc:
            status.set(str(exc))
            return
        busy = True
        button.configure(state='disabled')
        status.set('Requesting the dialer on the selected phone…')

        def worker():
            try:
                result = request_dialer(adb, serial, value, run)
            except Exception:
                result = 'Could not open the dialer. Check the selected phone and try again.'
            events.put(result)
        threading.Thread(target=worker, daemon=True).start()

    button = ttk.Button(body, text='Open dialer on phone', command=submit)
    button.pack(anchor='w')
    entry.bind('<Return>', lambda event: submit())
    ttk.Label(body, textvariable=status, wraplength=595, justify='left').pack(anchor='w', pady=12)
    ttk.Separator(body).pack(fill='x', pady=8)
    ttk.Label(body, text='For PC calling: Microsoft Phone Link is a separate app with its own Bluetooth pairing and permissions. Microsoft documents a limitation for Bluetooth headsets connected to the PC. Check its setup guide and test your audio devices.',
              wraplength=595, justify='left').pack(anchor='w')
    ttk.Button(body, text='Read Microsoft Phone Link setup guide',
               command=lambda: webbrowser.open(PHONE_LINK_HELP)).pack(anchor='w', pady=9)

    def drain():
        nonlocal busy, timer
        if not alive:
            return
        try:
            while True:
                status.set(events.get_nowait())
                busy = False
                button.configure(state='normal')
        except queue.Empty:
            pass
        timer = window.after(120, drain)

    def close():
        nonlocal alive
        alive = False
        if timer is not None:
            window.after_cancel(timer)
        window.destroy()
    window.protocol('WM_DELETE_WINDOW', close)
    timer = window.after(120, drain)
    entry.focus_set()
    return window
