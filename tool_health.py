"""Static executable checks; these do not prove Windows loader compatibility."""
import hashlib
from pathlib import Path
import struct
import threading


_bundle_cache = {}
_bundle_cache_lock = threading.Lock()


def _file_signature(path):
    stat = path.stat()
    return (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino)


def _sha256_file(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def pe_machine(path):
    path = Path(path)
    with path.open('rb') as f:
        if f.read(2) != b'MZ':
            raise ValueError(f'Not a Windows executable: {path}\nSelect scrcpy.exe, never scrcpy-server or a DLL.')
        f.seek(60)
        offset = f.read(4)
        if len(offset) != 4:
            raise ValueError(f'Truncated executable: {path}')
        f.seek(struct.unpack('<I', offset)[0])
        if f.read(4) != b'PE\0\0':
            raise ValueError(f'Invalid Windows PE header: {path}')
        header = f.read(20)
        if len(header) != 20:
            raise ValueError(f'Truncated PE header: {path}')
        machine, sections, _, _, _, optional_size, characteristics = struct.unpack('<HHIIIHH', header)
        if not sections or not optional_size or not characteristics & 2:
            raise ValueError(f'Invalid executable metadata: {path}')
        return machine, bool(characteristics & 0x2000)


def validate_windows_tool(path, expected_name):
    p = Path(path)
    if p.name.lower() != expected_name.lower():
        raise ValueError(f'Wrong tool selected: {p}\nSelect {expected_name} using Tool locations.')
    machine, dll = pe_machine(p)
    if dll or machine not in {0x14c, 0x8664, 0xaa64}:
        raise ValueError(f'Unsupported executable type: {p}')
    return machine


def tool_report(path):
    p = Path(path)
    try:
        machine, dll = pe_machine(p)
        return f'{p}\nSize: {p.stat().st_size} bytes; PE machine: {machine:#06x}; DLL: {dll}\nSHA256: {_sha256_file(p)}'
    except (OSError, ValueError, struct.error) as exc:
        return f'{p}\nInspection failed: {exc}'


def validate_bundle_files(root, executable):
    """Verify release tools against the packaged hash manifest, when selected."""
    import json
    root = Path(root).resolve()
    exe = Path(executable).resolve()
    bundle = root / 'tools' / 'scrcpy'
    if exe.parent != bundle:
        return
    manifest_path = root / 'PACKAGE_SHA256.json'
    if not manifest_path.is_file():
        raise ValueError('Package checksum manifest missing. Extract the complete BridgeLab ZIP again.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict):
        raise ValueError('Invalid package checksum manifest.')
    entries = []
    for name, expected in manifest.items():
        if not isinstance(name, str) or not name.startswith('tools/scrcpy/'):
            continue
        relative = Path(name)
        if '..' in relative.parts or relative.is_absolute():
            raise ValueError('Invalid checksum manifest path.')
        entries.append((root / relative, expected))
    if not entries or exe not in {path for path, _ in entries}:
        raise ValueError('Package manifest does not contain the selected bundled tool. Extract the complete package.')
    # Every launch stats all recorded tools. Rehash only when the manifest or any
    # file changes; this is an accidental-corruption check, not a security boundary.
    with _bundle_cache_lock:
        signature = (_file_signature(manifest_path), tuple((str(path), expected, _file_signature(path))
                                                          for path, expected in entries))
        key = (str(root), str(exe))
        if _bundle_cache.get(key) == signature:
            return
        for path, expected in entries:
            if not path.is_file() or _sha256_file(path) != expected:
                raise ValueError(f'Bundled tool is missing or damaged: {path}\nExtract the complete package into a fresh folder; do not mix DLLs from other releases.')
        # Do not cache a successful check if files changed during hashing.
        after = (_file_signature(manifest_path), tuple((str(path), expected, _file_signature(path))
                                                      for path, expected in entries))
        if after != signature:
            raise ValueError('Bundled tools changed during validation. Retry after extraction finishes.')
        _bundle_cache[key] = signature
