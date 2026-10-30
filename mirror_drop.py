"""Prepare scrcpy's fixed shared-storage destination for native file drops.

Upstream scrcpy installs dropped lowercase ``.apk`` files instead of pushing
them. This destination only applies to its ordinary file-push action.
"""
import shlex


DEFAULT_MIRROR_DROP_TARGET = "/sdcard/Download/BridgeLab"
_SHARED_ROOTS = ("/sdcard", "/storage/emulated/0", "/storage/self/primary")


def normalize_mirror_drop_target(target: str) -> str:
    """Return a canonical /sdcard path, rejecting private and ambiguous paths.

    Only the primary user's shared storage aliases are supported. Parent and
    current-directory segments are rejected rather than silently resolved.
    Shell punctuation and spaces in filenames remain safe through shell quoting.
    """
    if not isinstance(target, str) or not target or len(target) > 1024:
        raise ValueError("Choose a shared-storage folder of at most 1024 characters.")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in target) or "\\" in target:
        raise ValueError("Folder paths cannot contain control characters or backslashes.")
    parts = target.split("/")
    if any(part in {".", ".."} for part in parts):
        raise ValueError("Folder paths cannot contain . or .. segments.")
    # Collapse repeated/trailing separators, without expanding user or shell text.
    path = "/".join(part for part in parts if part)
    path = "/" + path if target.startswith("/") else path
    for root in _SHARED_ROOTS:
        if path == root or path.startswith(root + "/"):
            relative = path[len(root):]
            break
    else:
        raise ValueError("Choose a folder under /sdcard (primary shared storage).")
    segments = relative.strip("/").split("/")
    if len(segments) >= 2 and segments[0].casefold() == "android" and segments[1].casefold() in {"data", "obb"}:
        raise ValueError("Android/data and Android/obb are private app folders; choose a shared folder.")
    return "/sdcard" + relative


def prepare_mirror_drop(adb, serial, target, run):
    """Create a validated destination before launching the main mirror.

    ``run`` is the app's bounded subprocess wrapper. Exceptions propagate so a
    failed preparation cannot silently launch with a different destination.
    """
    normalized = normalize_mirror_drop_target(target)
    if not serial or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in serial):
        raise ValueError("Select a valid authorized Android device.")
    # /sdcard itself is Android's shared-storage alias. Reject links in every
    # user-selected descendant before creating anything beneath that component.
    parts = normalized[len("/sdcard"):].strip("/").split("/")
    parts = [part for part in parts if part]
    if parts:
        command = ('p=/sdcard; for part in ' + ' '.join(shlex.quote(part) for part in parts) +
                   '; do p="$p/$part"; '
                   'if [ -L "$p" ]; then echo "Linked destination folders are unsupported" >&2; exit 17; fi; '
                   'if [ -e "$p" ]; then test -d "$p" || exit 18; else mkdir "$p" || exit; fi; '
                   'done; readlink -f "$p"')
    else:
        command = 'test -d /sdcard && readlink -f /sdcard'
    result = run([adb, "-s", serial, "shell", command], timeout=15)
    if result.returncode:
        detail = (result.stderr or result.stdout or "Android could not create the folder.").strip()[:250]
        raise RuntimeError("Could not prepare mirror drop folder: " + detail)
    try:
        actual = normalize_mirror_drop_target(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("The phone could not confirm a shared-storage destination.") from exc
    if actual != normalized:
        raise RuntimeError("The destination resolved to a different folder. Choose a folder without links.")
    return normalized
