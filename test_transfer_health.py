import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import tool_health
from device_transfer import send_verified
from tool_health import pe_machine, validate_windows_tool, validate_bundle_files

class TransferHealthTests(unittest.TestCase):
    def test_transfer_verifies_remote_and_quotes_name(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"a ' $(oops).txt";p.write_bytes(b'abc')
            commands=[]
            def run(args, timeout):
                commands.append(args)
                return subprocess.CompletedProcess(args,0,'3' if 'stat -c' in args[-1] else '', '')
            result=send_verified('adb','PHONE',[p],run)
            self.assertIn('Verified 1',result)
            self.assertIn('Download → BridgeLab',result)
            self.assertEqual(commands[1][-1],"/sdcard/Download/BridgeLab/a ' $(oops).txt")
            self.assertIn("'\"'\"'",commands[2][-1])
    def test_size_mismatch_is_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test';p.write_bytes(b'123')
            def run(args,timeout):return subprocess.CompletedProcess(args,0,'2','')
            with self.assertRaisesRegex(RuntimeError,'verification failed'):send_verified('adb','p',[p],run)
    def test_push_failure_no_success_claim(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test';p.write_bytes(b'123')
            def run(args,timeout):return subprocess.CompletedProcess(args,1 if 'push' in args else 0,'','offline')
            with self.assertRaisesRegex(RuntimeError,'Earlier files'):send_verified('adb','p',[p],run)
    def test_scan_timeout_keeps_verified_success(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test';p.write_bytes(b'123')
            def run(args,timeout):
                if 'am broadcast' in args[-1]:raise subprocess.TimeoutExpired(args,timeout)
                return subprocess.CompletedProcess(args,0,'3','')
            self.assertIn('refresh was unavailable',send_verified('adb','p',[p],run))
    def test_non_executable_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'scrcpy.exe';p.write_bytes(b'not an exe')
            with self.assertRaisesRegex(ValueError,'Not a Windows executable'):pe_machine(p)
            with self.assertRaisesRegex(ValueError,'Wrong tool'):validate_windows_tool(p.with_name('scrcpy-server'),'scrcpy.exe')
    def test_bundle_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);tool=root/'tools/scrcpy/scrcpy.exe';tool.parent.mkdir(parents=True);tool.write_bytes(b'original')
            (root/'PACKAGE_SHA256.json').write_text(json.dumps({'tools/scrcpy/scrcpy.exe':hashlib.sha256(b'original').hexdigest()}))
            validate_bundle_files(root,tool)
            tool.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'damaged'):validate_bundle_files(root,tool)

    def test_bundle_hash_cache_invalidates_on_tool_and_manifest_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            tool = root / 'tools/scrcpy/scrcpy.exe'
            tool.parent.mkdir(parents=True)
            tool.write_bytes(b'first')
            manifest = root / 'PACKAGE_SHA256.json'
            manifest.write_text(json.dumps({'tools/scrcpy/scrcpy.exe': hashlib.sha256(b'first').hexdigest()}))
            with patch('tool_health._sha256_file', wraps=tool_health._sha256_file) as digest:
                validate_bundle_files(root, tool)
                validate_bundle_files(root, tool)
                self.assertEqual(digest.call_count, 1)
                tool.write_bytes(b'other')  # same length still requires rehash
                with self.assertRaisesRegex(ValueError, 'damaged'):
                    validate_bundle_files(root, tool)
                self.assertEqual(digest.call_count, 2)
                manifest.write_text(json.dumps({'tools/scrcpy/scrcpy.exe': hashlib.sha256(b'other').hexdigest()}))
                validate_bundle_files(root, tool)
                self.assertEqual(digest.call_count, 3)
