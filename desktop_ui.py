"""BridgeLab's desktop presentation layer; device work stays in the controller.

Uses only Tk/ttk. Every page scrolls, including at Windows display scaling.
The controller's existing variables and action buttons remain public contracts.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


BG = "#0b1120"
SIDEBAR = "#10182a"
SURFACE = "#151f33"
INPUT = "#202c43"
BORDER = "#29354d"
TEXT = "#f1f5ff"
MUTED = "#b0bed4"
ACCENT = "#a8b6ff"


def configure_style(app):
    root = app.root
    root.title("BridgeLab — Your phone, at your desk")
    # Leave room for the Windows taskbar on a 1366 × 768 laptop.
    width = min(1180, max(760, root.winfo_screenwidth() - 70))
    height = min(740, max(560, root.winfo_screenheight() - 85))
    root.geometry(f"{width}x{height}")
    root.minsize(760, 540)
    root.configure(background=BG)
    root.option_add("*Font", "{Segoe UI} 10")
    root.option_add("*TCombobox*Listbox.background", INPUT)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", "#3b4874")
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Segoe UI", 10), background=BG, foreground=TEXT)
    for name, color in (("TFrame", BG), ("Card.TFrame", SURFACE),
                        ("Side.TFrame", SIDEBAR), ("Inset.TFrame", INPUT)):
        style.configure(name, background=color)
    for name, bg, fg, font in (
        ("TLabel", BG, TEXT, ("Segoe UI", 10)),
        ("Card.TLabel", SURFACE, TEXT, ("Segoe UI", 10)),
        ("Hint.TLabel", SURFACE, MUTED, ("Segoe UI", 9)),
        ("Muted.TLabel", BG, MUTED, ("Segoe UI", 9)),
        ("Side.TLabel", SIDEBAR, MUTED, ("Segoe UI", 9)),
        ("Title.TLabel", BG, TEXT, ("Segoe UI Semibold", 23)),
        ("Section.TLabel", SURFACE, TEXT, ("Segoe UI Semibold", 14)),
        ("Eyebrow.TLabel", SURFACE, ACCENT, ("Segoe UI Semibold", 9)),
    ):
        style.configure(name, background=bg, foreground=fg, font=font)
    style.configure("TButton", padding=(14, 9), background=INPUT, foreground=TEXT,
                    font=("Segoe UI Semibold", 10), borderwidth=1, bordercolor=BORDER,
                    focusthickness=2, focuscolor=ACCENT)
    style.map("TButton", background=[("active", "#2b3955"), ("disabled", "#1c2639")],
              foreground=[("disabled", "#7e8ba3")])
    style.configure("Accent.TButton", background=ACCENT, foreground="#111936",
                    bordercolor=ACCENT)
    style.map("Accent.TButton", background=[("active", "#c1caff"), ("disabled", "#485779")],
              foreground=[("disabled", "#c0c9db")])
    style.configure("Quiet.TButton", background=SURFACE, bordercolor=SURFACE,
                    padding=(9, 7), foreground=MUTED)
    style.map("Quiet.TButton", background=[("active", INPUT)], foreground=[("active", TEXT)])
    style.configure("Nav.TButton", background=SIDEBAR, bordercolor=SIDEBAR,
                    foreground=MUTED, anchor="w", padding=(16, 13))
    style.map("Nav.TButton", background=[("active", "#1d2940")], foreground=[("active", TEXT)])
    style.configure("Selected.Nav.TButton", background="#29345c", bordercolor="#29345c",
                    foreground=TEXT)
    style.map("Selected.Nav.TButton", background=[("active", "#33416e")])
    style.configure("TEntry", padding=9, fieldbackground=INPUT, foreground=TEXT,
                    bordercolor=BORDER, insertcolor=TEXT, lightcolor=BORDER, darkcolor=BORDER)
    style.map("TEntry", bordercolor=[("focus", ACCENT)])
    style.configure("TCombobox", padding=8, fieldbackground=INPUT, background=INPUT,
                    foreground=TEXT, arrowcolor=MUTED, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, insertcolor=TEXT)
    style.map("TCombobox", fieldbackground=[("readonly", INPUT)],
              foreground=[("readonly", TEXT)], bordercolor=[("focus", ACCENT)])
    style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, padding=(0, 5),
                    indicatorbackground=INPUT, indicatorforeground=ACCENT)
    style.map("TCheckbutton", background=[("active", SURFACE)],
              indicatorbackground=[("selected", ACCENT), ("active", "#36456a")])
    style.configure("TSeparator", background=BORDER)
    style.configure("Vertical.TScrollbar", background=INPUT, troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED, width=12)


def _label(parent, text, *, style="Hint.TLabel", wrap=390, **pack):
    label = ttk.Label(parent, text=text, style=style, wraplength=wrap, justify="left")
    label.pack(anchor="w", **pack)
    # Adapt wrapping to the actual available card width on smaller displays.
    parent.bind("<Configure>", lambda event: label.configure(wraplength=max(120, event.width - 34)), add="+")
    return label


def _card(parent, title, subtitle=None):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=18)
    _label(frame, title, style="Section.TLabel", pady=(0, 6))
    if subtitle:
        _label(frame, subtitle, pady=(0, 12))
    return frame


def _friendly_folder(value):
    path = value.replace("\\", "/").rstrip("/")
    for prefix in ("/sdcard", "/storage/emulated/0"):
        if path == prefix or path.startswith(prefix + "/"):
            return "Internal storage" + (" / " + path[len(prefix):].strip("/").replace("/", " / ") if path[len(prefix):] else "")
    return path


def build_layout(app):
    root = app.root
    shell = ttk.Frame(root)
    shell.pack(fill="both", expand=True)
    shell.rowconfigure(0, weight=1)
    shell.columnconfigure(1, weight=1)

    sidebar = ttk.Frame(shell, style="Side.TFrame", padding=(14, 25, 14, 20), width=184)
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)
    sidebar.columnconfigure(0, weight=1)
    sidebar.rowconfigure(5, weight=1)
    ttk.Label(sidebar, text="B", background=ACCENT, foreground="#111936",
              font=("Segoe UI Semibold", 20), anchor="center", width=3).grid(row=0, column=0, sticky="w", padx=12)
    ttk.Label(sidebar, text="BridgeLab", background=SIDEBAR, foreground=TEXT,
              font=("Segoe UI Semibold", 18)).grid(row=1, column=0, sticky="w", padx=12, pady=(13, 3))
    ttk.Label(sidebar, text="PHONE + DESKTOP", style="Side.TLabel",
              font=("Segoe UI", 8)).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 30))
    nav = ttk.Frame(sidebar, style="Side.TFrame")
    nav.grid(row=3, column=0, sticky="ew")
    _side_footer = ttk.Label(sidebar, text="Made for your desk.\nYour data stays local.\n\nv0.5.1", style="Side.TLabel", justify="left")
    _side_footer.grid(row=6, column=0, sticky="sw", padx=12)

    workspace = ttk.Frame(shell, padding=(24, 20, 20, 12))
    workspace.grid(row=0, column=1, sticky="nsew")
    workspace.columnconfigure(0, weight=1)
    workspace.rowconfigure(2, weight=1)
    page_title = tk.StringVar(root, "Your phone, at your desk.")
    page_caption = tk.StringVar(root, "A little less switching. A little more flow.")
    ttk.Label(workspace, textvariable=page_title, style="Title.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(workspace, textvariable=page_caption, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 18))

    viewport = ttk.Frame(workspace)
    viewport.grid(row=2, column=0, sticky="nsew")
    viewport.rowconfigure(0, weight=1)
    viewport.columnconfigure(0, weight=1)
    canvas = tk.Canvas(viewport, background=BG, highlightthickness=0, borderwidth=0)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
    scrollbar.grid(row=0, column=1, sticky="ns", padx=(7, 0))
    canvas.configure(yscrollcommand=scrollbar.set)
    content = ttk.Frame(canvas)
    window_id = canvas.create_window((0, 0), window=content, anchor="nw")
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
    content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def scroll(event):
        # Scope scrolling to this workspace; child dialogs keep their own scrolling.
        if event.widget.winfo_toplevel() != root or not canvas.winfo_ismapped():
            return
        if canvas.bbox("all") and canvas.bbox("all")[3] > canvas.winfo_height():
            direction = (-1 if event.num == 4 else 1) if event.num in (4, 5) else (-1 if event.delta > 0 else 1)
            canvas.yview_scroll(direction * 3, "units")
    root.bind("<MouseWheel>", scroll, add="+")
    root.bind("<Button-4>", scroll, add="+")
    root.bind("<Button-5>", scroll, add="+")

    def reveal_focus(event):
        widget = event.widget
        if not str(widget).startswith(str(content) + ".") or not widget.winfo_ismapped():
            return
        full_height = max(1, content.winfo_height())
        top = widget.winfo_rooty() - content.winfo_rooty()
        bottom = top + widget.winfo_height()
        visible_top = canvas.canvasy(0)
        visible_bottom = visible_top + canvas.winfo_height()
        if top < visible_top:
            canvas.yview_moveto(max(0, top - 10) / full_height)
        elif bottom > visible_bottom:
            canvas.yview_moveto(max(0, bottom - canvas.winfo_height() + 10) / full_height)
    root.bind("<FocusIn>", reveal_focus, add="+")

    connection = ttk.Frame(content, style="Card.TFrame", padding=(16, 12))
    connection.pack(fill="x", pady=(0, 14))
    connection.columnconfigure(0, weight=1)
    ttk.Label(connection, textvariable=app.connection_var, style="Card.TLabel",
              font=("Segoe UI Semibold", 10)).grid(row=0, column=0, sticky="w")
    ttk.Label(connection, textvariable=app.battery_var, style="Hint.TLabel").grid(row=0, column=1, sticky="e", padx=(8, 0))
    app.device_box = ttk.Combobox(connection, textvariable=app.device_var, state="readonly", width=24)
    app.device_box.grid(row=1, column=0, sticky="ew", pady=(8, 0), padx=(0, 10))
    app.device_box.bind("<<ComboboxSelected>>", app._select_device)
    ttk.Button(connection, text="Refresh", style="Quiet.TButton", command=app._poll_devices).grid(row=1, column=1, pady=(8, 0))
    ttk.Button(connection, text="Phone setup", command=app.show_phone_setup).grid(row=1, column=2, rowspan=2, padx=(10, 0), pady=(8, 0))

    pages = {}
    nav_buttons = {}
    captions = {
        "Overview": ("Your phone, at your desk.", "A little less switching. A little more flow."),
        "Screen settings": ("Make yourself comfortable.", "Choose how your phone screen works on this PC."),
        "Help": ("A hand getting connected.", "Start with your phone. Advanced details are here when you need them."),
    }

    def select_page(name):
        for key, frame in pages.items():
            if key == name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
            nav_buttons[key].configure(style="Selected.Nav.TButton" if key == name else "Nav.TButton")
        page_title.set(captions[name][0])
        page_caption.set(captions[name][1])
        canvas.yview_moveto(0)

    for name in captions:
        pages[name] = ttk.Frame(content)
        nav_buttons[name] = ttk.Button(nav, text=name, style="Nav.TButton", command=lambda key=name: select_page(key))
        nav_buttons[name].pack(fill="x", pady=3)

    overview = pages["Overview"]
    screen = _card(overview, "Phone screen")
    screen.pack(fill="x", pady=(0, 12))
    screen.columnconfigure(0, weight=1)
    _label(screen, "See and control your phone in its own window.", pady=(0, 10))
    row = ttk.Frame(screen, style="Card.TFrame")
    row.pack(fill="x")
    app.mirror_button = ttk.Button(row, text="Open phone screen", style="Accent.TButton", command=app.start_mirror)
    app.mirror_button.pack(side="left")
    ttk.Button(row, text="Close screen", style="Quiet.TButton", command=app.stop_mirror).pack(side="left", padx=(8, 0))
    ttk.Button(row, text="Screen settings", style="Quiet.TButton", command=lambda: select_page("Screen settings")).pack(side="right")
    _label(screen, "Tip: drag files from your PC onto the open phone screen to send them to your download location.",
           style="Card.TLabel", pady=(12, 3))
    _label(screen, "Reopen the screen after changing the location. Files with the same name are replaced.", pady=(0, 3))
    _label(screen, "Dropping an APK installs the app. To copy an APK as a file, use Send files below.")

    grid = ttk.Frame(overview)
    grid.pack(fill="both", expand=True)
    grid.columnconfigure(0, weight=1, uniform="cards")
    grid.columnconfigure(1, weight=1, uniform="cards")
    files = _card(grid, "Send files", "Choose files on this PC and send a verified copy to your phone.")
    app.file_button = ttk.Button(files, text="Choose files to send", style="Accent.TButton", command=app.send_files)
    app.file_button.pack(anchor="w")
    destination = ttk.Frame(files, style="Card.TFrame")
    destination.pack(fill="x", pady=(12, 0))
    ttk.Label(destination, text="Download location", style="Hint.TLabel").pack(side="left")
    ttk.Button(destination, text="Change", style="Quiet.TButton", command=app.change_send_folder).pack(side="right")
    app.download_location_display = tk.StringVar(root)
    def update_folder(*_):
        app.download_location_display.set(_friendly_folder(app.send_folder_var.get()))
    update_folder()
    app.send_folder_var.trace_add("write", update_folder)
    folder_label = ttk.Label(files, textvariable=app.download_location_display, style="Card.TLabel", wraplength=340, justify="left")
    folder_label.pack(anchor="w", pady=(2, 5))
    files.bind("<Configure>", lambda e: folder_label.configure(wraplength=max(120, e.width - 36)), add="+")
    ttk.Button(files, text="More file options", style="Quiet.TButton", command=app.browse_phone).pack(anchor="w")
    _label(files, "Phone → PC files are available in More file options. Dragging from the phone screen to this PC is not supported.", pady=(5, 0))

    apps = _card(grid, "Phone apps", "Open a supported phone app in a separate window, using the data already on your phone.")
    app.app_button = ttk.Button(apps, text="Choose a phone app", command=app.open_app)
    app.app_button.pack(anchor="w")
    _label(apps, "BridgeLab checks the prerequisites. Your phone or app may still refuse a separate window.", pady=(13, 0))

    links = _card(grid, "Open a link", "Continue on your phone with a web link from this PC.")
    app.url_entry = ttk.Entry(links, textvariable=app.url_var)
    app.url_entry.pack(fill="x", pady=(0, 10))
    app.url_entry.bind("<Return>", lambda event: app.open_url())
    link_buttons = ttk.Frame(links, style="Card.TFrame")
    link_buttons.pack(fill="x")
    ttk.Button(link_buttons, text="Paste link", style="Quiet.TButton", command=app.paste_url).pack(side="left")
    app.url_button = ttk.Button(link_buttons, text="Open on phone", command=app.open_url)
    app.url_button.pack(side="right")

    calls = _card(grid, "Calls", "Prepare a number, then review and place the call on your phone.")
    ttk.Button(calls, text="Open phone dialer", command=app.show_calls).pack(anchor="w")
    _label(calls, "Call audio stays on your phone or its headset. PC call audio is unavailable in BridgeLab.", pady=(13, 0))

    # Reflow cards when the user resizes or uses larger display scaling.
    last_columns = [None]
    def reflow(event):
        columns = 2 if event.width >= 690 else 1
        if last_columns[0] == columns:
            return
        last_columns[0] = columns
        for index, card in enumerate((files, apps, links, calls)):
            card.grid(row=index // columns, column=index % columns, sticky="nsew",
                      padx=((0, 6) if columns == 2 and index % 2 == 0 else (6, 0) if columns == 2 else 0),
                      pady=(0, 12))
        grid.columnconfigure(1, weight=1 if columns == 2 else 0)
    grid.bind("<Configure>", reflow)

    settings = pages["Screen settings"]
    display = _card(settings, "Picture & sound", "These preferences apply the next time you open the phone screen.")
    display.pack(fill="x", pady=(0, 12))
    picture = ttk.Frame(display, style="Card.TFrame")
    picture.pack(fill="x", pady=(2, 12))
    for column, (label, variable, values) in enumerate((
        ("Screen resolution", app.size_var, ("1024", "1280", "1600", "1920")),
        ("Frames per second", app.fps_var, ("30", "60", "90", "120")),
    )):
        group = ttk.Frame(picture, style="Card.TFrame")
        group.pack(side="left", padx=(0, 25))
        ttk.Label(group, text=label, style="Hint.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Combobox(group, values=values, textvariable=variable, state="readonly", width=12).pack(anchor="w")
    ttk.Checkbutton(display, text="Play phone media audio on this PC", variable=app.audio_var,
                    command=app._save_settings).pack(anchor="w")
    _label(display, "Media sound depends on phone support. This setting does not enable PC call audio.", pady=(1, 8))
    ttk.Checkbutton(display, text="Turn off the phone display while its screen is open here", variable=app.off_var,
                    command=app._save_settings).pack(anchor="w")

    behavior = _card(settings, "Connection & controls")
    behavior.pack(fill="x", pady=(0, 12))
    ttk.Checkbutton(behavior, text="Open the phone screen when an approved phone connects", variable=app.auto_var,
                    command=app._save_settings).pack(anchor="w", pady=(0, 15))
    ttk.Label(behavior, text="Mouse & keyboard control", style="Hint.TLabel").pack(anchor="w", pady=(0, 5))
    app.control_mode_label = tk.StringVar(root)
    mode_labels = {"Standard": "Normal", "OPPO fallback (UHID)": "Compatibility"}
    app.control_mode_label.set(mode_labels.get(app.mode_var.get(), "Normal"))
    mode_box = ttk.Combobox(behavior, values=("Normal", "Compatibility"), textvariable=app.control_mode_label,
                            state="readonly", width=22)
    mode_box.pack(anchor="w")
    def select_mode(event=None):
        app.mode_var.set("OPPO fallback (UHID)" if app.control_mode_label.get() == "Compatibility" else "Standard")
    mode_box.bind("<<ComboboxSelected>>", select_mode)
    _label(behavior, "Try Compatibility if your phone does not respond to clicks. In this mode, press Alt to release your mouse pointer.", pady=(10, 0), wrap=760)
    for variable in (app.mode_var, app.size_var, app.fps_var):
        variable.trace_add("write", lambda *_: app._save_settings())

    help_page = pages["Help"]
    getting_started = _card(help_page, "Connect your phone", "Use a USB cable that supports data, unlock your phone, and follow the guided setup.")
    getting_started.pack(fill="x", pady=(0, 12))
    ttk.Button(getting_started, text="Open phone setup", style="Accent.TButton", command=app.show_phone_setup).pack(anchor="w")
    _label(getting_started, "Approve this PC on your phone only if you trust it. Your phone and files stay on your devices.", pady=(12, 0), wrap=760)
    advanced = _card(help_page, "Advanced help", "Check connection details or inspect local logs when something needs attention.")
    advanced.pack(fill="x", pady=(0, 12))
    advanced_buttons = ttk.Frame(advanced, style="Card.TFrame")
    advanced_buttons.pack(fill="x")
    ttk.Button(advanced_buttons, text="Run diagnostics", command=app.diagnose).pack(side="left", padx=(0, 8))
    ttk.Button(advanced_buttons, text="Open local logs", command=app.open_logs).pack(side="left")
    _label(advanced, "Diagnostics are read-only. BridgeLab does not upload your logs.", pady=(12, 0))

    footer = ttk.Frame(workspace, padding=(0, 10, 0, 0))
    footer.grid(row=3, column=0, sticky="ew")
    status = ttk.Label(footer, textvariable=app.status_var, style="Muted.TLabel", wraplength=740, justify="left")
    status.pack(fill="x")
    footer.bind("<Configure>", lambda e: status.configure(wraplength=max(200, e.width)))
    app._ui_select_page = select_page
    select_page("Overview")
