"""Real host-shell protocol check and integrated shutdown guards; no phone."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
from continuity_mvp import BridgeLab
from phone_files import PhoneFiles

class IntegratedReleaseTests(unittest.TestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('sh'), 'POSIX host-shell protocol check')
    def test_listing_protocol_survives_real_shell_and_unicode_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['a b.txt', "quotes'and$dollars.txt", '日本語.txt', '-leading.txt', '.hidden']
            for name in names:
                (root / name).write_bytes(b'123')
            (root/'folder').mkdir()
            (root/'link').symlink_to(root/'a b.txt')
            class LocalListing(PhoneFiles):
                def directory(self, path): return str(root)
            calls=[]
            def run(args, timeout):
                calls.append(args)
                return subprocess.run(['sh','-c',args[-1]],capture_output=True,text=True,timeout=timeout)
            folder, entries = LocalListing('test-adb', 'test-phone', run).list('/sdcard/Download')
            self.assertEqual({e.name for e in entries}, {*names, 'folder', 'link'})
            self.assertEqual({e.size for e in entries if e.kind=='f'}, {3})
            self.assertEqual(next(e.kind for e in entries if e.name=='link'),'l')
            self.assertEqual(calls[0][1:3],['-s','test-phone'])
    def test_root_waits_for_child_transfer_before_destroy(self):
        app = BridgeLab.__new__(BridgeLab)
        app.busy_actions=0
        app.root=Mock()
        app.status_var=Mock()
        child=Mock();child.close.return_value=False
        app.child_controllers=[child]
        app._save_settings=Mock()
        app._on_close()
        child.close.assert_called_once()
        app.root.destroy.assert_not_called()
        app._save_settings.assert_not_called()
    def test_root_waits_for_mirror_process_before_destroy(self):
        app=BridgeLab.__new__(BridgeLab)
        app.busy_actions=0;app.child_controllers=[]
        app.root=Mock();app.status_var=Mock()
        app.mirror_process=Mock();app.mirror_process.poll.return_value=None
        app.stopping_process=None
        app.stop_mirror=Mock()
        app._on_close()
        app.stop_mirror.assert_called_once()
        app.root.after.assert_called_once_with(200,app._on_close)
        app.root.destroy.assert_not_called()
