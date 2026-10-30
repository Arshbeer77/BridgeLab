import os
from pathlib import Path
import queue
import shlex
import shutil
import subprocess
import tempfile
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from friendly_text import FriendlyStatusVar, friendly_status
from mirror_drop import prepare_mirror_drop
import test_reliability
from app_windows_ui import AppWindowsWindow


class V05IntegrationTests(unittest.TestCase):
    def test_plain_status_uses_real_tcl_variable_without_display(self):
        interpreter = tk.Tcl()
        value = FriendlyStatusVar(master=interpreter, value='ADB ready; scrcpy starting')
        self.assertNotIn('ADB', value.get())
        self.assertNotIn('scrcpy', value.get())
        value.set('file_push finished')
        self.assertEqual(value.get(), 'File transfer finished')

    def test_changed_mirror_destination_cancels_pending_launch(self):
        app = test_reliability.ReliabilityTests().app()
        app.launch_generation = 7
        app.adb_path = Mock(get=Mock(return_value='adb'))
        app.scrcpy_path = Mock(get=Mock(return_value='scrcpy'))
        app.send_folder_var = Mock(get=Mock(return_value='/sdcard/Pictures'))
        app._spawn_scrcpy = Mock()
        app._finish_launch(7, 'OPPO', ['--push-target=/sdcard/Download'], 'adb', 'scrcpy', None, None)
        app._spawn_scrcpy.assert_not_called()
        self.assertFalse(app.launch_pending)

    def test_destination_preparation_failure_never_opens_mirror(self):
        app = test_reliability.ReliabilityTests().app()
        app.events = queue.Queue()
        app._ready = Mock(return_value=('adb', __file__))
        app._spawn_scrcpy = Mock()
        app._launch_error = Mock()
        for name, value in [('size_var','1280'),('fps_var','60'),('mode_var','Standard'),('send_folder_var','/sdcard/Download/BridgeLab')]:
            setattr(app, name, Mock(get=Mock(return_value=value)))
        app.audio_var = Mock(get=Mock(return_value=False))
        app.off_var = Mock(get=Mock(return_value=False))
        app.adb_path = Mock(get=Mock(return_value='adb'))
        app.scrcpy_path = Mock(get=Mock(return_value=__file__))
        with patch('continuity_mvp.threading.Thread') as thread, patch('continuity_mvp.prepare_mirror_drop', side_effect=RuntimeError('folder denied')):
            app._launch_scrcpy(None)
            thread.call_args.kwargs['target']()
        kind, data = app.events.get_nowait()
        self.assertEqual(kind, 'launch_ready')
        app._finish_launch(*data)
        app._spawn_scrcpy.assert_not_called()
        app._launch_error.assert_called_once()

    def test_destination_canonical_mismatch_is_not_accepted(self):
        run = Mock(return_value=subprocess.CompletedProcess([],0,'/data/private',''))
        with self.assertRaises(RuntimeError):
            prepare_mirror_drop('adb','OPPO','/sdcard/Download',run)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('sh'), 'POSIX shell protocol check')
    def test_real_shell_folder_creation_quotes_names_and_rejects_links(self):
        target = "/sdcard/Download/Bob's files; $(touch HACK)"
        run = Mock(return_value=subprocess.CompletedProcess([],0,target,''))
        prepare_mirror_drop('adb','OPPO',target,run)
        script = run.call_args.args[0][-1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'phone'; root.mkdir()
            command = script.replace('p=/sdcard;', 'p='+shlex.quote(str(root))+';',1)
            cp = subprocess.run(['sh','-c',command],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            self.assertTrue((root/'Download'/"Bob's files; $(touch HACK)").is_dir())
            self.assertFalse((root/'HACK').exists())
            shutil.rmtree(root/'Download')
            outside=Path(directory)/'outside';outside.mkdir()
            (root/'Download').symlink_to(outside)
            cp = subprocess.run(['sh','-c',command],capture_output=True,text=True)
            self.assertNotEqual(cp.returncode,0)
            self.assertEqual(list(outside.iterdir()),[])

    def test_app_chooser_stays_open_during_phone_handoff(self):
        controller = AppWindowsWindow.__new__(AppWindowsWindow)
        controller.handoff_pending = True
        controller.close_requested = False
        controller.status=Mock();controller.window=Mock()
        self.assertFalse(controller.close())
        self.assertTrue(controller.close_requested)
        controller.window.destroy.assert_not_called()

    def test_bootstrap_has_unique_temporary_directory_and_final_cleanup(self):
        script = (Path(__file__).parent/'FIRST-RUN-WINDOWS.ps1').read_text()
        self.assertIn('[Guid]::NewGuid()',script)
        self.assertIn('} finally {',script)
        self.assertIn('Remove-Item -LiteralPath $installerDirectory -Recurse',script)
