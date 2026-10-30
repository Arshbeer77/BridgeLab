"""Windows file drop-in and Explorer copy drag-out, using only stdlib ctypes.

All entry points belong on the UI thread. Native callbacks only enqueue paths.
Shell PIDLs/data objects own the Windows drag protocol; no Python COM server.
"""
import ctypes
import os
from pathlib import Path
import uuid

_RETAINED_HOOKS = set()


def _windows():
    if os.name != 'nt':
        raise OSError('Native file dragging is available on Windows only.')
    from ctypes import wintypes
    return wintypes, ctypes.WinDLL('user32', use_last_error=True), ctypes.WinDLL('shell32'), ctypes.OleDLL('ole32')


def window_handle(widget):
    wt, user, _, _ = _windows()
    user.GetAncestor.argtypes = [wt.HWND, wt.UINT]
    user.GetAncestor.restype = wt.HWND
    return user.GetAncestor(widget.winfo_id(), 2) or widget.winfo_id()


class FileDropTarget:
    """WM_DROPFILES subclass. enqueue must not touch Tk or block."""
    def __init__(self, hwnd, enqueue):
        wt, self.user, self.shell, _ = _windows()
        self.hwnd = hwnd
        self.enqueue = enqueue
        self.old = None
        self.closed = False
        self.proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
        long_type = ctypes.c_ssize_t
        self.get_long = getattr(self.user, 'GetWindowLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'GetWindowLongW')
        self.set_long = getattr(self.user, 'SetWindowLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'SetWindowLongW')
        self.get_long.argtypes = [wt.HWND, ctypes.c_int]
        self.get_long.restype = long_type
        self.set_long.argtypes = [wt.HWND, ctypes.c_int, long_type]
        self.set_long.restype = long_type
        self.user.CallWindowProcW.argtypes = [ctypes.c_void_p, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
        self.user.CallWindowProcW.restype = long_type
        self.shell.DragAcceptFiles.argtypes = [wt.HWND, wt.BOOL]
        self.shell.DragAcceptFiles.restype = None
        self.shell.DragQueryFileW.argtypes = [wt.HANDLE, wt.UINT, wt.LPWSTR, wt.UINT]
        self.shell.DragQueryFileW.restype = wt.UINT
        self.shell.DragFinish.argtypes = [wt.HANDLE]
        self.shell.DragFinish.restype = None

        def wndproc(hwnd_, message, wparam, lparam):
            if message == 0x0233:  # WM_DROPFILES
                try:
                    count = self.shell.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                    if not self.closed and count <= 1000:
                        paths = []
                        for i in range(count):
                            length = self.shell.DragQueryFileW(wparam, i, None, 0)
                            if length > 32767:
                                raise ValueError('Dropped path is too long.')
                            buf = ctypes.create_unicode_buffer(length + 1)
                            self.shell.DragQueryFileW(wparam, i, buf, length + 1)
                            paths.append(buf.value)
                        self.enqueue(paths)
                except Exception:
                    # Never allow an exception through a Windows callback boundary.
                    pass
                finally:
                    self.shell.DragFinish(wparam)
                return 0
            result = self.user.CallWindowProcW(self.old, hwnd_, message, wparam, lparam)
            if message == 0x0082:  # WM_NCDESTROY, final native notification
                _RETAINED_HOOKS.discard(self)
            return result

        self.callback = self.proc_type(wndproc)
        self.address = ctypes.cast(self.callback, ctypes.c_void_p).value
        ctypes.set_last_error(0)
        self.old = self.set_long(hwnd, -4, self.address)
        if not self.old and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        _RETAINED_HOOKS.add(self)
        self.shell.DragAcceptFiles(hwnd, True)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.shell.DragAcceptFiles(self.hwnd, False)
        if self.get_long(self.hwnd, -4) == self.address:
            ctypes.set_last_error(0)
            result = self.set_long(self.hwnd, -4, self.old)
            if not result and ctypes.get_last_error():
                raise ctypes.WinError(ctypes.get_last_error())
            _RETAINED_HOOKS.discard(self)
        # If a later subclass owns the top slot, retain our callback until HWND
        # destruction rather than replacing that subclass or leaving a dangling pointer.


def drag_files(hwnd, paths):
    """Run a COPY-only native drag while the user holds the left mouse button.

    Paths must already be downloaded regular files in one batch directory.
    Returns True on a completed drop, False on cancellation. Runs on UI thread.
    """
    wt, _, shell, ole = _windows()
    paths = [Path(p).resolve(strict=True) for p in paths]
    if not paths or any(not p.is_file() for p in paths):
        raise ValueError('Download regular files before dragging.')
    if len({p.parent for p in paths}) != 1:
        raise ValueError('Drag files must share one downloaded batch directory.')

    class GUID(ctypes.Structure):
        _fields_ = [('data', ctypes.c_ubyte * 16)]

    iid = GUID((ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID('0000010e-0000-0000-c000-000000000046').bytes_le))
    shell.ILCreateFromPathW.argtypes = [wt.LPCWSTR]
    shell.ILCreateFromPathW.restype = ctypes.c_void_p
    shell.ILFindLastID.argtypes = [ctypes.c_void_p]
    shell.ILFindLastID.restype = ctypes.c_void_p
    shell.ILFree.argtypes = [ctypes.c_void_p]
    shell.ILFree.restype = None
    shell.SHCreateDataObject.argtypes = [ctypes.c_void_p, wt.UINT, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    shell.SHCreateDataObject.restype = ctypes.c_long
    shell.SHDoDragDrop.argtypes = [wt.HWND, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
    shell.SHDoDragDrop.restype = ctypes.c_long
    ole.OleInitialize.argtypes = [ctypes.c_void_p]
    ole.OleInitialize.restype = ctypes.c_long
    ole.OleUninitialize.argtypes = []
    ole.OleUninitialize.restype = None
    hr = ole.OleInitialize(None)
    if hr < 0:
        raise OSError(f'Windows could not initialize file dragging (0x{hr & 0xffffffff:08X}).')
    pidls = []
    data = ctypes.c_void_p()
    try:
        for path in [paths[0].parent, *paths]:
            ptr = shell.ILCreateFromPathW(str(path))
            if not ptr:
                raise OSError('Windows could not prepare a downloaded file for dragging.')
            pidls.append(ptr)
        children = (ctypes.c_void_p * len(paths))(*(shell.ILFindLastID(p) for p in pidls[1:]))
        hr = shell.SHCreateDataObject(pidls[0], len(paths), children, None, ctypes.byref(iid), ctypes.byref(data))
        if hr < 0:
            raise OSError(f'Windows could not prepare file data (0x{hr & 0xffffffff:08X}).')
        effect = wt.DWORD()
        hr = shell.SHDoDragDrop(hwnd, data, None, 1, ctypes.byref(effect))  # DROPEFFECT_COPY
        if hr < 0:
            raise OSError(f'Windows file drag failed (0x{hr & 0xffffffff:08X}).')
        return hr == 0x00040100 and bool(effect.value & 1)
    finally:
        if data.value:
            vtable = ctypes.cast(data, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            release = ctypes.WINFUNCTYPE(wt.ULONG, ctypes.c_void_p)(vtable[2])
            release(data)
        for pidl in reversed(pidls):
            shell.ILFree(pidl)
        ole.OleUninitialize()
