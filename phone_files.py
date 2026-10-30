"""ADB shared-storage file copies. No Android package or extra permission required.

Files only: directory recursion, private app data and symlinks are deliberately
unsupported. All operations use a captured ADB serial; callers run them off Tk.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import shlex
import uuid

ROOTS = ('/sdcard', '/storage/emulated/0')
DEFAULT_DIRECTORY = '/sdcard/Download'


def remote_path(value):
    if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Unsupported control character in phone path.')
    if '..' in value.split('/') or not any(value == r or value.startswith(r + '/') for r in ROOTS):
        raise ValueError('Choose a directory inside /sdcard or /storage/emulated/0.')
    return value.rstrip('/')


def filename(value):
    if not value or value in ('.', '..') or '/' in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Unsupported phone filename.')
    return value


def local_filename(value):
    """Map Android names to one safe Windows basename, retaining Unicode."""
    filename(value)
    result = re.sub(r'[<>:"/\\|?*]', '_', value).rstrip(' .')
    if not result:
        result = 'file'
    if result.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        result = '_' + result
    if result != value or len(result) > 160:
        digest = hashlib.sha256(value.encode('utf-8')).hexdigest()[:10]
        result = result[:145] + '-' + digest
    return result


@dataclass(frozen=True)
class PhoneEntry:
    name: str
    kind: str
    size: int = 0


def parse_listing(output):
    fields = output.split('\0')
    if not fields or fields[-1] != '' or (len(fields) - 1) % 3:
        raise RuntimeError('Phone returned an incomplete directory listing.')
    entries = []
    for index in range(0, len(fields) - 1, 3):
        kind, size, name = fields[index:index + 3]
        filename(name)
        if kind not in ('d', 'f', 'l') or not size.isascii() or not size.isdigit():
            raise RuntimeError('Phone returned an invalid directory listing.')
        entries.append(PhoneEntry(name, kind, int(size)))
    return sorted(entries, key=lambda e: (e.kind != 'd', e.name.casefold()))


class PhoneFiles:
    def __init__(self, adb, serial, run_command):
        if not serial:
            raise ValueError('Select a connected phone first.')
        self.adb, self.serial, self.run = adb, serial, run_command

    def shell(self, command, timeout=20):
        cp = self.run([self.adb, '-s', self.serial, 'shell', command], timeout=timeout)
        if cp.returncode:
            raise RuntimeError((cp.stderr or cp.stdout or 'Phone command failed').strip()[:500])
        return cp.stdout

    def directory(self, path):
        path = remote_path(path)
        canonical = self.shell('readlink -f ' + shlex.quote(path)).strip()
        remote_path(canonical)
        self.shell('test -d ' + shlex.quote(canonical))
        return canonical

    def list(self, path):
        path = self.directory(path)
        # NUL fields preserve spaces, quotes, non-ASCII and shell metacharacters.
        command = ('cd ' + shlex.quote(path) + ' || exit; '
                   'for f in .[!.]* ..?* *; do '
                   '[ -e "$f" ] || [ -L "$f" ] || continue; '
                   'if [ -L "$f" ]; then printf "l\\0000\\000%s\\000" "$f"; '
                   'elif [ -d "$f" ]; then printf "d\\0000\\000%s\\000" "$f"; '
                   'elif [ -f "$f" ]; then n=$(stat -c %s "./$f") || exit; '
                   'printf "f\\000%s\\000%s\\000" "$n" "$f"; fi; done')
        return path, parse_listing(self.shell(command, timeout=30))

    def push(self, paths, directory, progress=lambda text: None):
        target = self.directory(directory)
        sources = []
        names = set()
        for raw in paths:
            source = Path(raw)
            if source.is_symlink() or not source.is_file():
                raise ValueError('Only regular files can be sent; folders and links are unsupported.')
            filename(source.name)
            if source.name in names:
                raise ValueError('Two selected files have the same destination name.')
            names.add(source.name)
            sources.append(source)
        if not sources:
            raise ValueError('Select at least one file.')
        # Preflight every destination, so ordinary conflicts cannot partially copy a batch.
        for source in sources:
            dest = shlex.quote(target + '/' + source.name)
            self.shell('if [ -e ' + dest + ' ] || [ -L ' + dest + ' ]; then echo "A destination file already exists; nothing is overwritten." >&2; exit 17; fi')
        sent = []
        for index, source in enumerate(sources, 1):
            progress(f'Sending {index}/{len(sources)}: {source.name}')
            temp = target + '/.bridgelab-upload-' + uuid.uuid4().hex
            dest = target + '/' + source.name
            size = source.stat().st_size
            try:
                cp = self.run([self.adb, '-s', self.serial, 'push', str(source.resolve()), temp], timeout=600)
                if cp.returncode:
                    raise RuntimeError((cp.stderr or cp.stdout or 'ADB push failed').strip()[:400])
                if self.shell('stat -c %s ' + shlex.quote(temp)).strip() != str(size):
                    raise RuntimeError('Uploaded size did not match; destination was not published.')
                # -n refuses replacement if a destination appeared after preflight.
                self.shell('mv -n -T ' + shlex.quote(temp) + ' ' + shlex.quote(dest) + '; test ! -e ' + shlex.quote(temp))
                if self.shell('stat -c %s ' + shlex.quote(dest)).strip() != str(size):
                    raise RuntimeError('Final phone file size verification failed.')
                sent.append(source.name)
            except Exception as exc:
                raise RuntimeError(f'{len(sent)} of {len(sources)} files completed. {exc}') from exc
            finally:
                try:
                    self.shell('rm -f ' + shlex.quote(temp))
                except Exception:
                    pass
        return sent

    def pull(self, entries, directory, local_directory, progress=lambda text: None):
        target = self.directory(directory)
        entries = list(entries)
        if not entries or any(e.kind != 'f' for e in entries):
            raise ValueError('Select regular files only; folders and links cannot be downloaded.')
        # The UI creates this unique batch folder. Existing destinations are never replaced.
        local = Path(local_directory).resolve(strict=True)
        if not local.is_dir():
            raise ValueError('Download destination must be a directory.')
        completed = []
        for index, entry in enumerate(entries, 1):
            filename(entry.name)
            destination = local / local_filename(entry.name)
            if destination.exists() or destination.is_symlink():
                raise FileExistsError('Download destination already exists: ' + destination.name)
            remote = target + '/' + entry.name
            # Reject symlinks (including files changed since the directory listing).
            q = shlex.quote(remote)
            size_text = self.shell('test ! -L ' + q + ' && test -f ' + q + ' && stat -c %s ' + q).strip()
            if size_text != str(entry.size):
                raise RuntimeError('Phone file changed; refresh and select it again: ' + entry.name)
            progress(f'Downloading {index}/{len(entries)}: {entry.name} ({entry.size:,} bytes)')
            temp = local / ('.bridgelab-part-' + uuid.uuid4().hex)
            created = False
            try:
                cp = self.run([self.adb, '-s', self.serial, 'pull', remote, str(temp)], timeout=600)
                if cp.returncode:
                    raise RuntimeError((cp.stderr or cp.stdout or 'ADB pull failed').strip()[:400])
                if temp.is_symlink() or not temp.is_file() or temp.stat().st_size != entry.size:
                    raise RuntimeError('Downloaded file failed size verification.')
                # Exclusive creation also protects against a destination appearing mid-copy.
                with temp.open('rb') as src, destination.open('xb') as dst:
                    created = True
                    import shutil
                    shutil.copyfileobj(src, dst)
                completed.append(destination)
            except Exception:
                if created:
                    destination.unlink(missing_ok=True)
                raise
            finally:
                temp.unlink(missing_ok=True)
        return completed
