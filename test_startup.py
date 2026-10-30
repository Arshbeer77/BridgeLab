import contextlib
import io
from pathlib import Path
import tempfile
import time
import unittest
from launch_bridge import run_app

class StartupTests(unittest.TestCase):
    def test_stage_messages_are_visible_and_recorded(self):
        def application(progress):
            progress('Creating desktop window')
            progress('Window ready')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_app(application, tmp), 0)
            log = (Path(tmp)/'startup.log').read_text()
            self.assertIn('Window ready', log)
            self.assertIn('Starting.', output.getvalue())

    def test_import_or_layout_failure_leaves_traceback_and_nonzero_exit(self):
        def broken(progress):
            progress('Building dashboard')
            raise RuntimeError('example layout failure')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_app(broken, tmp), 1)
            log=(Path(tmp)/'startup.log').read_text()
            self.assertIn('Building dashboard',log)
            self.assertIn('RuntimeError: example layout failure',log)
            self.assertIn('could not start',output.getvalue())

    def test_slow_start_reports_instead_of_remaining_blank(self):
        def slow(progress):
            time.sleep(0.08)
            progress('Window ready')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_app(slow,tmp,readiness_timeout=0.01),0)
            self.assertIn('taking longer than expected',output.getvalue())

    def test_launcher_has_no_silent_unbounded_python_preflight(self):
        launcher=(Path(__file__).parent/'START-WINDOWS.bat').read_text()
        self.assertIn('BridgeLab is starting...',launcher)
        self.assertIn('-u "%~dp0launch_bridge.py"',launcher)
        self.assertNotIn(' -c ',launcher)
