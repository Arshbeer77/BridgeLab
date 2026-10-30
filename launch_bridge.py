"""Visible source-launch diagnostics, before importing the desktop application."""
from pathlib import Path
import logging
import os
import sys
import threading
import traceback


def run_app(entry=None, log_directory=None, readiness_timeout=20):
    destination = Path(log_directory or (Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'BridgeLab'))
    try:
        destination.mkdir(parents=True, exist_ok=True)
        log_path = destination / 'startup.log'
        handler = logging.FileHandler(log_path, encoding='utf-8', mode='w')
    except OSError:
        import tempfile
        log_path = Path(tempfile.gettempdir()) / 'BridgeLab-startup.log'
        handler = logging.FileHandler(log_path, encoding='utf-8', mode='w')
    logger = logging.Logger('BridgeLab-startup')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    finished = threading.Event()
    ready = threading.Event()

    def progress(message):
        logger.info(message)
        print('[BridgeLab] ' + message, flush=True)
        if message == 'Window ready':
            ready.set()

    def watchdog():
        if not finished.wait(readiness_timeout) and not ready.is_set():
            progress('Startup is taking longer than expected. Last step and details are in: ' + str(log_path))
            print('Please share startup.log if no window appears. Do not open more copies yet.', flush=True)
    threading.Thread(target=watchdog, name='BridgeLab-startup-watchdog', daemon=True).start()
    try:
        progress('Starting. Diagnostic log: ' + str(log_path))
        progress('Python: ' + sys.version.split()[0] + ' at ' + sys.executable)
        if sys.version_info < (3, 11):
            raise RuntimeError('Python 3.11 or newer is required.')
        if entry is None:
            progress('Loading application modules')
            from continuity_mvp import main
            entry = main
        entry(progress=progress)
        progress('Application closed')
        return 0
    except Exception:
        detail = traceback.format_exc()
        logger.error('Startup or application failed\n' + detail)
        print('\nBridgeLab could not start.\n' + detail + '\nSaved details: ' + str(log_path), flush=True)
        return 1
    finally:
        finished.set()
        handler.flush()
        handler.close()


if __name__ == '__main__':
    raise SystemExit(run_app())
