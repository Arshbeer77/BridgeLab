"""Shared-storage browser: Windows file drop-in, staged Explorer drag-out."""
import os
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from phone_files import DEFAULT_DIRECTORY, PhoneFiles, ROOTS, remote_path
from native_drag import FileDropTarget, drag_files, window_handle


class PhoneBrowser:
    def __init__(self, root, adb, serial, run_command, is_current=None):
        self.backend = PhoneFiles(adb, serial, run_command)
        self.is_current = is_current or (lambda: True)
        self.events = queue.Queue()
        self.busy = False
        self.dragging = False
        self.closed = False
        self.drop_target = None
        self.entries = {}
        self.downloaded = []
        self.download_folder = None
        self.directory = DEFAULT_DIRECTORY
        self.window = tk.Toplevel(root)
        self.window.title('Phone files — ' + serial)
        self.window.geometry('850x570')
        self.window.minsize(650, 440)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        body = ttk.Frame(self.window, padding=12)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Shared phone storage • ' + serial, font=('', 12, 'bold')).pack(anchor='w')
        ttk.Label(body, text='Browse folders. Drop PC files here to copy into the displayed folder. APKs are copied as files.').pack(anchor='w', pady=(5, 8))
        nav = ttk.Frame(body)
        nav.pack(fill='x')
        ttk.Button(nav, text='Up', command=self.up).pack(side='left')
        self.path = tk.StringVar(value=self.directory)
        entry = ttk.Entry(nav, textvariable=self.path)
        entry.pack(side='left', fill='x', expand=True, padx=6)
        entry.bind('<Return>', lambda event: self.refresh())
        ttk.Button(nav, text='Go / Refresh', command=self.refresh).pack(side='left')
        ttk.Button(nav, text='Download folder', command=lambda: self.navigate(DEFAULT_DIRECTORY)).pack(side='left', padx=(6, 0))
        listing = ttk.Frame(body)
        listing.pack(fill='both', expand=True, pady=9)
        self.tree = ttk.Treeview(listing, columns=('type', 'size'), show='tree headings', selectmode='extended')
        self.tree.heading('#0', text='Name (Enter or double-click opens folder)')
        self.tree.heading('type', text='Type')
        self.tree.heading('size', text='Bytes')
        self.tree.column('#0', width=430)
        self.tree.column('type', width=85, stretch=False)
        self.tree.column('size', width=110, anchor='e', stretch=False)
        scrollbar = ttk.Scrollbar(listing, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.tree.bind('<Double-1>', lambda event: self.open_selected())
        self.tree.bind('<Return>', lambda event: self.open_selected())
        actions = ttk.Frame(body)
        actions.pack(fill='x')
        ttk.Button(actions, text='Send PC files…', command=self.choose_upload).pack(side='left')
        ttk.Button(actions, text='Download selected files…', command=self.choose_download).pack(side='left', padx=6)
        self.open_button = ttk.Button(actions, text='Open downloaded folder', command=self.open_downloaded, state='disabled')
        self.open_button.pack(side='left')
        self.drag_handle = ttk.Label(body, text='2. After downloading: hold here and drag into Windows Explorer', relief='ridge', padding=10, cursor='hand2')
        self.drag_handle.pack(fill='x', pady=9)
        self.drag_handle.bind('<ButtonPress-1>', self.drag_press)
        self.drag_handle.bind('<B1-Motion>', self.drag_motion)
        self.drag_origin = None
        self.status = tk.StringVar(value='Loading…')
        ttk.Label(body, textvariable=self.status, wraplength=800).pack(anchor='w')
        ttk.Label(body, text='Files only • No silent replacement • Links and app-private data unavailable • Size verification, not a content checksum', wraplength=800).pack(anchor='w', pady=(7, 0))
        self.window.update_idletasks()
        if os.name == 'nt':
            try:
                self.drop_target = FileDropTarget(window_handle(self.window), lambda paths: self.events.put(('drop', paths)))
            except Exception as exc:
                self.status.set('Windows drop-in unavailable; use Send PC files. ' + str(exc))
        self.poll_id = self.window.after(80, self.poll)
        self.refresh()

    def allowed(self):
        if self.closed or self.busy or self.dragging:
            return False
        if not self.is_current():
            self.status.set('Phone selection or connection changed. Close this browser and reopen it for the current phone.')
            return False
        return True

    def launch(self, work, done):
        if not self.allowed():
            return
        self.busy = True
        self.status.set('Working…')
        def worker():
            try:
                value = work()
                self.events.put(('done', (done, value, None)))
            except Exception as exc:
                self.events.put(('done', (done, None, str(exc))))
        threading.Thread(target=worker, name='BridgeLab-phone-files', daemon=True).start()

    def progress(self, text):
        self.events.put(('progress', text))

    def poll(self):
        if self.closed:
            return
        for _ in range(200):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'progress':
                self.status.set(value)
            elif kind == 'drop':
                if self.allowed():
                    self.upload(value)
            elif kind == 'done':
                self.busy = False
                done, result, error = value
                if error:
                    self.status.set('Failed: ' + error)
                    messagebox.showerror('Phone files', error, parent=self.window)
                else:
                    done(result)
        if not self.closed:
            self.poll_id = self.window.after(80, self.poll)

    def navigate(self, path):
        if self.allowed():
            self.path.set(path)
            self.refresh()

    def refresh(self):
        if not self.allowed():
            return
        try:
            requested = remote_path(self.path.get())
        except ValueError as exc:
            self.status.set(str(exc))
            return
        def loaded(result):
            self.directory, entries = result
            self.path.set(self.directory)
            self.tree.delete(*self.tree.get_children())
            self.entries = {}
            for index, item in enumerate(entries):
                iid = str(index)
                self.entries[iid] = item
                self.tree.insert('', 'end', iid=iid, text=item.name, values=({'d': 'Folder', 'f': 'File', 'l': 'Link (blocked)'}[item.kind], f'{item.size:,}' if item.kind == 'f' else ''))
            self.status.set(f'{len(entries)} items. Drop files to: {self.directory}')
        self.launch(lambda: self.backend.list(requested), loaded)

    def up(self):
        path = self.directory
        if path not in ROOTS:
            self.navigate(path.rsplit('/', 1)[0])

    def open_selected(self):
        selected = self.tree.selection()
        if len(selected) == 1:
            item = self.entries.get(selected[0])
            if item and item.kind == 'd':
                self.navigate(self.directory + '/' + item.name)

    def choose_upload(self):
        if not self.allowed():
            return
        paths = filedialog.askopenfilenames(parent=self.window, title='Copy regular PC files into ' + self.directory)
        if paths and self.allowed():
            self.upload(paths)

    def upload(self, paths):
        if not self.allowed():
            return
        target = self.directory  # displayed successful listing, not uncommitted path text
        def done(names):
            self.status.set(f'Copied and size-verified {len(names)} file(s) into {target}. Refresh to see them.')
        self.launch(lambda: self.backend.push(paths, target, self.progress), done)

    def choose_download(self):
        if not self.allowed():
            return
        entries = [self.entries[i] for i in self.tree.selection() if i in self.entries]
        if not entries or any(e.kind != 'f' for e in entries):
            self.status.set('Select one or more regular files. Folder and link downloads are unsupported.')
            return
        destination = filedialog.askdirectory(parent=self.window, title='Choose PC parent folder (a new batch folder will be created)')
        if not destination or not self.allowed():
            return
        target = self.directory
        # mkdtemp exclusively creates the batch; downloads never replace existing files.
        try:
            folder = Path(tempfile.mkdtemp(prefix='BridgeLab-received-', dir=destination))
        except OSError as exc:
            self.status.set('Cannot create download folder: ' + str(exc))
            return
        self.downloaded = []
        self.download_folder = folder
        self.open_button.configure(state='normal')
        def done(paths):
            self.downloaded = paths
            self.download_folder = folder
            self.open_button.configure(state='normal')
            self.status.set(f'Downloaded and size-verified {len(paths)} file(s) to {folder}. Hold the drag area and drag to Explorer, or open this folder. Copies stay on both devices.')
        self.launch(lambda: self.backend.pull(entries, target, folder, self.progress), done)

    def open_downloaded(self):
        if self.download_folder and os.name == 'nt':
            os.startfile(str(self.download_folder))
        elif self.download_folder:
            self.status.set('Downloaded folder: ' + str(self.download_folder))

    def drag_press(self, event):
        self.drag_origin = (event.x_root, event.y_root) if self.allowed() else None

    def drag_motion(self, event):
        if not self.drag_origin or not self.allowed():
            return
        x, y = self.drag_origin
        if abs(event.x_root - x) + abs(event.y_root - y) < 8:
            return
        self.drag_origin = None
        if not self.downloaded:
            self.status.set('First select phone files and click Download selected files.')
            return
        self.dragging = True
        try:
            copied = drag_files(window_handle(self.window), self.downloaded)
            self.status.set('Explorer copy completed.' if copied else 'Drag cancelled. Downloaded files remain in the PC folder.')
        except Exception as exc:
            self.status.set(str(exc) + ' Use Open downloaded folder to copy files manually.')
        finally:
            self.dragging = False

    def close(self):
        if self.closed:
            return True
        if self.busy or self.dragging:
            self.status.set('Wait for the active file operation to finish before closing.')
            return False
        if self.drop_target:
            try:
                self.drop_target.close()
            except Exception as exc:
                self.status.set('Cannot detach Windows file drop handler: ' + str(exc))
                return False
        self.closed = True
        self.window.after_cancel(self.poll_id)
        self.window.destroy()
        return True


def open_phone_browser(root, adb, serial, run_command, is_current=None):
    return PhoneBrowser(root, adb, serial, run_command, is_current=is_current)
