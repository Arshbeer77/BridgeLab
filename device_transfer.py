"""Explicit destinations and remote verification; no automatic action replay."""
from pathlib import Path
import shlex
import subprocess
from urllib.parse import quote

PHONE_FOLDER = '/sdcard/Download/BridgeLab'

def send_verified(adb, serial, paths, run, *, folder=PHONE_FOLDER):
    from mirror_drop import normalize_mirror_drop_target
    folder = normalize_mirror_drop_target(folder)
    def shell(command, timeout=15):
        cp = run([adb, '-s', serial, 'shell', command], timeout=timeout)
        if cp.returncode:
            raise RuntimeError((cp.stderr or cp.stdout or 'Android command failed').strip()[:250])
        return cp.stdout.strip()
    shell('mkdir -p ' + shlex.quote(folder))
    verified = []
    scan_warnings = 0
    for index, raw in enumerate(paths, 1):
        path = Path(raw).resolve()
        if any(ord(c) < 32 or ord(c) == 127 for c in path.name):
            raise ValueError('Filenames containing control characters are unsupported.')
        remote = folder + '/' + path.name
        size = path.stat().st_size
        cp = run([adb, '-s', serial, 'push', str(path), remote], timeout=300)
        if cp.returncode:
            raise RuntimeError(f'File {index}/{len(paths)} failed. Earlier files may have arrived. ' + (cp.stderr or cp.stdout).strip()[:200])
        actual = shell('stat -c %s ' + shlex.quote(remote))
        if actual != str(size):
            raise RuntimeError(f'File {index}: remote size verification failed. Inspect {folder} before retrying.')
        verified.append(path.name)
        # Best effort only: modern Android/OEMs may ignore this deprecated action.
        try:
            cp = run([adb, '-s', serial, 'shell', 'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d ' + shlex.quote('file://' + quote(remote, safe='/'))], timeout=8)
            scan_warnings += bool(cp.returncode)
        except (OSError, subprocess.TimeoutExpired):
            scan_warnings += 1
    text = (f'Verified {len(verified)} file(s) on the selected phone by size.\n'
            'On phone: Files / File Manager → Internal storage → ' + folder[len('/sdcard/'):].replace('/', ' → ') + '\n'
            f'Exact path: {folder}\n\n' + '\n'.join(verified) +
            '\n\nExisting files with the same name are replaced. Categories/Recents may not refresh; browse Internal storage directly.')
    if scan_warnings:
        text += '\nMedia refresh was unavailable; the files were still verified on storage.'
    return text
