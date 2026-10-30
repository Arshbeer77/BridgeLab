"""One-shot window recovery and factual Tk mapping diagnostics."""
import json
import tkinter as tk


def snapshot(root):
    return {
        'state': root.state(), 'mapped': bool(root.winfo_ismapped()),
        'viewable': bool(root.winfo_viewable()), 'geometry': root.geometry(),
        'position': [root.winfo_rootx(), root.winfo_rooty()],
        'screen': [root.winfo_screenwidth(), root.winfo_screenheight()],
    }


def present_window(root, progress):
    """Centre and raise once after launch; never keep the app always-on-top."""
    if not root.winfo_exists():
        return
    try:
        width = min(1180, max(500, root.winfo_screenwidth() - 80))
        height = min(740, max(420, root.winfo_screenheight() - 100))
        x = max(0, (root.winfo_screenwidth() - width) // 2)
        y = max(0, (root.winfo_screenheight() - height) // 2)
        root.minsize(min(760, width), min(540, height))
        root.geometry(f'{width}x{height}+{x}+{y}')
        root.deiconify()
        root.state('normal')
        root.lift()
        root.attributes('-topmost', True)
        root.focus_force()
        progress('Window presentation requested: centred, restored and raised')
    except tk.TclError as exc:
        progress('Window presentation request failed: ' + str(exc))

    def release_topmost():
        if root.winfo_exists():
            try:
                root.attributes('-topmost', False)
            except tk.TclError:
                pass
    root.after(400, release_topmost)


def report_window(root, progress):
    if not root.winfo_exists():
        return
    try:
        state = snapshot(root)
        progress('Window state: ' + json.dumps(state, sort_keys=True))
        if state['mapped'] and state['viewable']:
            progress('Window ready')
        else:
            progress('Window is not mapped/viewable; please share this startup log')
    except tk.TclError as exc:
        progress('Window inspection failed: ' + str(exc))


def schedule_presentation(root, progress):
    root.after(0, lambda: present_window(root, progress))
    root.after(600, lambda: report_window(root, progress))
    root.after(2500, lambda: report_window(root, progress))
