"""Capability-checked Android app windows; process ownership stays with the UI.

`run` is injectable and returns CompletedProcess[str]. It must accept timeout
and (for scrcpy --list-apps only) env. No shell is invoked on the host.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shlex
import subprocess

from bridge_core import scrcpy_command, validate_package_id

MAX_APPS = 3000
MAX_OUTPUT = 2_000_000


@dataclass(frozen=True)
class AndroidApp:
    package: str
    name: str

    @property
    def label(self):
        return f"{self.name}  ({self.package})" if self.name != self.package else self.package


@dataclass(frozen=True)
class AppWindowCapability:
    serial: str
    android_sdk: int | None
    supported: bool
    list_apps_supported: bool
    diagnostics: str


def _serial(value):
    if not value or value.startswith('-') or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Select an authorized Android device.')
    return value


def scrcpy_environment(adb, scrcpy):
    env = dict(os.environ)
    env['ADB'] = str(adb)
    server = Path(scrcpy).resolve().parent / 'scrcpy-server'
    if server.is_file():
        env['SCRCPY_SERVER_PATH'] = str(server)
    return env


def _text(cp):
    return ((cp.stdout or '') + '\n' + (cp.stderr or ''))[:MAX_OUTPUT]


def _failure(cp, action):
    detail = _text(cp).strip()[-500:]
    return RuntimeError(f'{action} failed. {detail or "Check authorization and reconnect the selected phone."}')


def _validate_tools(adb, scrcpy):
    if os.name == 'nt':
        from portable_tools import application_root
        from tool_health import validate_bundle_files, validate_windows_tool
        validate_bundle_files(application_root(), scrcpy)
        validate_windows_tool(scrcpy, 'scrcpy.exe')
        validate_windows_tool(adb, 'adb.exe')


def preflight(adb, scrcpy, serial, run):
    """Read-only host help and phone API level; never launch an Android app.

    Passing means prerequisites were found, not that this OEM permits app windows.
    Exceptions (including timeouts) become useful diagnostic text.
    """
    _serial(serial)
    sdk = None
    try:
        _validate_tools(adb, scrcpy)
        help_cp = run([scrcpy, '--help'], timeout=10)
        if help_cp.returncode:
            raise _failure(help_cp, 'scrcpy capability check')
        help_text = _text(help_cp)
        options = set(re.findall(r'(?<![\w-])--[a-z][a-z0-9-]*', help_text))
        missing = {'--new-display', '--start-app'} - options
        if missing:
            return AppWindowCapability(serial, None, False, '--list-apps' in options,
                                       'Selected scrcpy lacks ' + ', '.join(sorted(missing)) + '. Install a current complete scrcpy release.')
        cp = run([adb, '-s', serial, 'shell', 'getprop', 'ro.build.version.sdk'], timeout=10)
        if cp.returncode:
            raise _failure(cp, 'Android capability check')
        raw = (cp.stdout or '').strip()
        if not re.fullmatch(r'\d{1,3}', raw):
            raise RuntimeError('Cannot read Android API level. Confirm USB debugging authorization for the selected phone.')
        sdk = int(raw)
        supported = sdk >= 29
        message = (f'Android API {sdk}; scrcpy supports --new-display and --start-app. '
                   'Prerequisites found. App/OEM launch and input behavior still require a device test.' if supported else
                   f'Android API {sdk}: app windows require Android 10 (API 29) or newer.')
        return AppWindowCapability(serial, sdk, supported, '--list-apps' in options, message)
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
        return AppWindowCapability(serial, sdk, False, False, f'App-window preflight failed: {exc}')


def parse_scrcpy_apps(output):
    """Parse upstream's `* label  package`/`- label  package` with wrapped labels."""
    if len(output) > MAX_OUTPUT:
        raise RuntimeError('App list exceeds the supported output limit.')
    apps = {}
    pending = None
    package_pattern = r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+'
    for line in output.splitlines():
        entry = re.match(r'^\s+[*-]\s+(.*)$', line)
        if entry:
            pending = entry.group(1).strip()
            match = re.fullmatch(r'(.*?)\s+(' + package_pattern + r')', pending, re.ASCII)
            if match:
                name, package = match.groups()
                apps[package] = AndroidApp(package, name.strip() or package)
                pending = None
        elif pending:
            match = re.fullmatch(r'\s+(' + package_pattern + r')\s*', line, re.ASCII)
            if match:
                package = match.group(1)
                apps[package] = AndroidApp(package, pending)
            pending = None
        if len(apps) > MAX_APPS:
            raise RuntimeError('Too many apps to display safely.')
    return sorted(apps.values(), key=lambda app: (app.name.casefold(), app.package))


def _query_launchable_apps(adb, serial, run):
    # Query launchable activities instead of pretending all installed packages launch.
    cp = run([adb, '-s', serial, 'shell', 'cmd', 'package', 'query-activities',
              '--brief', '--components', '-a', 'android.intent.action.MAIN',
              '-c', 'android.intent.category.LAUNCHER'], timeout=20)
    if cp.returncode:
        raise _failure(cp, 'Launchable-app query')
    output = _text(cp)
    if len((cp.stdout or '') + (cp.stderr or '')) > MAX_OUTPUT:
        raise RuntimeError('App list exceeds the supported output limit.')
    packages = set()
    for line in output.splitlines():
        match = re.fullmatch(r'\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)/[^\s]+\s*', line, re.ASCII)
        if match:
            packages.add(validate_package_id(match.group(1)))
    if len(packages) > MAX_APPS:
        raise RuntimeError('Too many apps to display safely.')
    return [AndroidApp(package, package) for package in sorted(packages)]


def list_apps(adb, scrcpy, serial, run, capability):
    """List launchable apps for the captured serial. Bound total work to two calls.

    scrcpy lists current-user enabled launchable apps with labels. Older tools or
    failed listings fall back to Android's launcher activity query (package IDs).
    Caller must ignore results after changing device selection.
    """
    _serial(serial)
    if capability.serial != serial:
        raise ValueError('Device selection changed. Run app-window checks again.')
    if not capability.supported:
        raise ValueError(capability.diagnostics)
    first_error = ''
    if capability.list_apps_supported:
        try:
            cp = run([scrcpy, '-s', serial, '--list-apps'], timeout=25,
                     env=scrcpy_environment(adb, scrcpy))
            if cp.returncode:
                raise _failure(cp, 'scrcpy app listing')
            apps = parse_scrcpy_apps((cp.stdout or '') + '\n' + (cp.stderr or ''))
            if apps:
                return apps
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            first_error = str(exc)
    apps = _query_launchable_apps(adb, serial, run)
    if not apps:
        raise RuntimeError('No launchable apps were returned for this phone. ' + first_error)
    return apps


def app_window_command(scrcpy, serial, package, size=1280, fps=60,
                       audio=False, control_mode='standard'):
    """Separate virtual-display command. Never powers off the physical display."""
    _serial(serial)
    return scrcpy_command(scrcpy, serial, size, fps, audio,
                          validate_package_id(package), control_mode=control_mode,
                          turn_screen_off=False)


def open_on_phone(adb, serial, package, run):
    """Explicit fallback to the phone's normal display; at most two bounded calls.

    This requests an activity launch, not a virtual-display compatibility fix or
    a PC audio route. Caller captures and rechecks device selection before work.
    """
    if not isinstance(serial, str) or len(serial) > 512:
        raise ValueError('Select an authorized Android device.')
    _serial(serial)
    if not isinstance(package, str) or any(ord(c) < 32 or ord(c) == 127 for c in package):
        raise ValueError('Select a valid Android app.')
    package = validate_package_id(package)
    prefix = [adb, '-s', serial, 'shell']
    cp = run(prefix + ['cmd', 'package', 'resolve-activity', '--brief',
                       '--user', 'current', '-a', 'android.intent.action.MAIN',
                       '-c', 'android.intent.category.LAUNCHER', '-p', package], timeout=12)
    raw = (cp.stdout or '') + '\n' + (cp.stderr or '')
    if len(raw) > MAX_OUTPUT:
        raise RuntimeError('Phone launcher response exceeds the supported output limit.')
    if cp.returncode or any(marker in raw.lower() for marker in
                            ('error:', 'exception', 'permission denial')):
        raise RuntimeError('Could not find the app launcher. Check the selected phone and authorization.')
    if any(ord(c) < 32 and c not in '\r\n\t' or ord(c) == 127 for c in raw):
        raise RuntimeError('Phone returned an invalid launcher response.')
    # A resolver may include priority metadata. Only one exact component belonging
    # to the selected package is accepted; never execute raw resolver output.
    components = [line.strip() for line in (cp.stdout or '').splitlines() if '/' in line]
    pattern = re.escape(package) + r'/\.?[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*'
    if len(components) != 1 or len(components[0]) > 512 or not re.fullmatch(pattern, components[0], re.ASCII):
        raise RuntimeError('No valid launcher activity was found for this app on the selected phone.')
    # adb joins remote arguments through Android's shell. Quote even a validated
    # component because legitimate nested Java class names can contain `$`.
    command = ('am start --user current -a android.intent.action.MAIN '
               '-c android.intent.category.LAUNCHER -n ' + shlex.quote(components[0]))
    cp = run(prefix + [command], timeout=12)
    raw = (cp.stdout or '') + '\n' + (cp.stderr or '')
    if len(raw) > MAX_OUTPUT or cp.returncode or any(marker in raw.lower() for marker in
            ('error:', 'exception', 'permission denial', 'unable to resolve intent', 'no activity found')):
        raise RuntimeError('The phone could not open this app. Check its screen for a permission or app restriction.')
    return 'App launch requested on the phone. Use the phone or its mirrored screen; some apps may still restrict access.'
