import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from phone_files import PhoneEntry, PhoneFiles, local_filename, parse_listing, remote_path


class FakePhone:
    def __init__(self):
        self.commands = []
        self.push_sizes = {}
        self.listing = ''
        self.pull_content = b'abc'
        self.fail_push = False
        self.fail_move = False
        self.conflict = False

    def __call__(self, args, timeout=20):
        self.commands.append(args)
        op = args[3]
        if op == 'push':
            if self.fail_push:
                return subprocess.CompletedProcess(args, 1, '', 'offline')
            self.push_sizes[args[-1]] = Path(args[-2]).stat().st_size
            return subprocess.CompletedProcess(args, 0, '', '')
        if op == 'pull':
            Path(args[-1]).write_bytes(self.pull_content)
            return subprocess.CompletedProcess(args, 0, '', '')
        command = args[4]
        output, rc = '', 0
        if command.startswith('readlink'):
            output = '/storage/emulated/0/Download\n'
        elif command.startswith('cd '):
            output = self.listing
        elif command.startswith('if [ -e') and self.conflict:
            rc = 17
            output = 'A destination file already exists'
        elif command.startswith('stat -c'):
            path = shlex.split(command)[-1]
            output = str(self.push_sizes.get(path, 3)) + '\n'
        elif command.startswith('test ! -L'):
            output = '3\n'
        elif command.startswith('mv -n -T'):
            if self.fail_move:
                rc = 1
            else:
                words = shlex.split(command)
                self.push_sizes[words[4].rstrip(';')] = self.push_sizes[words[3]]
        return subprocess.CompletedProcess(args, rc, output, '')


class PhoneFilesTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakePhone()
        self.phone = PhoneFiles('adb.exe', 'SERIAL-ONLY', self.fake)

    def test_path_rejects_traversal_controls_and_private_storage(self):
        for value in ('/data/user/0', '/sdcardish/foo', '/sdcard/../data', '/sdcard/a\nb', '/sdcard/a\0b'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                remote_path(value)
        self.assertEqual(remote_path('/sdcard/Download/'), '/sdcard/Download')

    def test_names_are_nul_delimited_and_keep_shell_characters(self):
        name = "report's $(touch nope); 中文.txt"
        entries = parse_listing('f\0003\0' + name + '\0d\0000\0Photos\0l\0000\0link\0')
        self.assertEqual(entries[0].kind, 'd')
        self.assertIn(PhoneEntry(name, 'f', 3), entries)
        for malformed in ('f\0003\0broken', 'x\0003\0bad\0', 'f\0oops\0bad\0', 'f\0003\0../bad\0', 'f\0003\0bad\nname\0'):
            with self.subTest(malformed=malformed), self.assertRaises((ValueError, RuntimeError)):
                parse_listing(malformed)
        self.assertEqual(parse_listing(''), [])

    def test_windows_names_are_safe_deterministic_and_distinct(self):
        for original in ('CON.txt', 'a:b.txt', 'trailing. ', 'a\\b', 'x' * 250):
            result = local_filename(original)
            self.assertNotIn(':', result)
            self.assertNotIn('\\', result)
            self.assertLessEqual(len(result), 160)
            self.assertFalse(result.endswith((' ', '.')))
            self.assertEqual(result, local_filename(original))
        self.assertNotEqual(local_filename('a:b'), local_filename('a?b'))
        self.assertEqual(local_filename('中文 notes.txt'), '中文 notes.txt')

    def test_canonical_path_cannot_escape_shared_storage(self):
        def runner(args, timeout=20):
            return subprocess.CompletedProcess(args, 0, '/data/private\n', '')
        with self.assertRaises(ValueError):
            PhoneFiles('adb', 's', runner).list('/sdcard/link')

    def test_upload_shell_quotes_and_serial_and_verifies_before_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "a'$(touch pwn); 中文.apk"
            p.write_bytes(b'abc')
            self.assertEqual(self.phone.push([p], '/sdcard/Download'), [p.name])
        commands = self.fake.commands
        self.assertTrue(all(cmd[1:3] == ['-s', 'SERIAL-ONLY'] for cmd in commands))
        self.assertTrue(all(cmd[3] != 'install' for cmd in commands))
        self.assertTrue(any(shlex.quote('/storage/emulated/0/Download/' + p.name) in cmd[-1] for cmd in commands if cmd[3] == 'shell'))
        push_index = next(i for i, cmd in enumerate(commands) if cmd[3] == 'push')
        move_index = next(i for i, cmd in enumerate(commands) if cmd[3] == 'shell' and cmd[-1].startswith('mv -n -T'))
        self.assertLess(push_index, move_index)
        self.assertTrue(any(cmd[-1].startswith('stat -c') for cmd in commands[push_index:move_index]))

    def test_upload_conflict_prevents_push(self):
        self.fake.conflict = True
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'hello.txt'
            p.write_bytes(b'abc')
            with self.assertRaises(RuntimeError):
                self.phone.push([p], '/sdcard/Download')
        self.assertFalse(any(cmd[3] == 'push' for cmd in self.fake.commands))

    def test_failed_upload_cleans_temporary_name(self):
        self.fake.fail_push = True
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'hello.txt'
            p.write_bytes(b'abc')
            with self.assertRaisesRegex(RuntimeError, '0 of 1'):
                self.phone.push([p], '/sdcard/Download')
        self.assertTrue(any(cmd[-1].startswith('rm -f ') for cmd in self.fake.commands))

    def test_no_target_directory_support_fails_without_publishing(self):
        self.fake.fail_move = True
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'hello.txt'
            p.write_bytes(b'abc')
            with self.assertRaises(RuntimeError):
                self.phone.push([p], '/sdcard/Download')

    def test_pull_uses_safe_name_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            entries = [PhoneEntry('CON:report.txt', 'f', 3)]
            files = self.phone.pull(entries, '/sdcard/Download', temp)
            self.assertEqual(files[0].read_bytes(), b'abc')
            with self.assertRaises(FileExistsError):
                self.phone.pull(entries, '/sdcard/Download', temp)
            self.assertEqual(files[0].read_bytes(), b'abc')
            self.assertEqual(len(list(Path(temp).iterdir())), 1)

    def test_pull_rejects_folders_links_and_changed_size(self):
        with tempfile.TemporaryDirectory() as temp:
            for kind in ('d', 'l'):
                with self.assertRaises(ValueError):
                    self.phone.pull([PhoneEntry('x', kind)], '/sdcard/Download', temp)
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                self.phone.pull([PhoneEntry('x', 'f', 5)], '/sdcard/Download', temp)
            self.assertFalse(any(cmd[3] == 'pull' for cmd in self.fake.commands))

    def test_pull_size_mismatch_cleans_partial_file(self):
        self.fake.pull_content = b'incomplete content'
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, 'verification'):
                self.phone.pull([PhoneEntry('x', 'f', 3)], '/sdcard/Download', temp)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_local_write_failure_cleans_own_partial_final(self):
        def fail_copy(src, dst):
            dst.write(b'a')
            raise OSError('disk full')
        with tempfile.TemporaryDirectory() as temp, patch('shutil.copyfileobj', fail_copy):
            with self.assertRaisesRegex(OSError, 'disk full'):
                self.phone.pull([PhoneEntry('x', 'f', 3)], '/sdcard/Download', temp)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_non_windows_native_drag_fails_explicitly(self):
        if os.name == 'nt':
            self.skipTest('Needs non-Windows host')
        from native_drag import drag_files
        with self.assertRaisesRegex(OSError, 'Windows only'):
            drag_files(0, [])


class BrowserLifecycleTests(unittest.TestCase):
    def browser(self):
        from phone_browser import PhoneBrowser
        from unittest.mock import Mock
        ui = PhoneBrowser.__new__(PhoneBrowser)
        ui.closed = False
        ui.busy = False
        ui.dragging = False
        ui.is_current = lambda: True
        ui.status = Mock()
        ui.window = Mock()
        ui.poll_id = 'timer'
        ui.drop_target = Mock()
        ui.events = __import__('queue').Queue()
        return ui

    def test_close_refuses_active_worker_and_active_drag(self):
        for attr in ('busy', 'dragging'):
            ui = self.browser()
            setattr(ui, attr, True)
            self.assertFalse(ui.close())
            ui.window.destroy.assert_not_called()
            ui.drop_target.close.assert_not_called()

    def test_close_detaches_native_hook_before_destroy(self):
        ui = self.browser()
        calls = []
        ui.drop_target.close.side_effect = lambda: calls.append('detach')
        ui.window.destroy.side_effect = lambda: calls.append('destroy')
        self.assertTrue(ui.close())
        self.assertTrue(ui.closed)
        self.assertEqual(calls, ['detach', 'destroy'])
        self.assertTrue(ui.close())

    def test_changed_phone_blocks_upload_after_file_dialog(self):
        ui = self.browser()
        ui.directory = '/sdcard/Download'
        checks = iter([True, False])
        ui.is_current = lambda: next(checks)
        with patch('phone_browser.filedialog.askopenfilenames', return_value=['x.txt']), patch.object(ui, 'upload') as upload:
            ui.choose_upload()
        upload.assert_not_called()

    def test_worker_uses_queue_and_main_thread_dispatches_completion(self):
        ui = self.browser()
        from unittest.mock import Mock
        from threading import Event, get_ident
        main_thread = get_ident()
        finished = Event()
        done = Mock()
        def work():
            self.assertNotEqual(get_ident(), main_thread)
            ui.progress('progress')
            finished.set()
            return 42
        ui.launch(work, done)
        self.assertTrue(finished.wait(2))
        # Join by waiting for queued completion, never call Tk in the worker.
        first = ui.events.get(timeout=2)
        second = ui.events.get(timeout=2)
        self.assertEqual(first, ('progress', 'progress'))
        self.assertEqual(second[0], 'done')
        self.assertEqual(second[1][1:], (42, None))
        done.assert_not_called()
        self.assertTrue(ui.busy)


if __name__ == '__main__':
    unittest.main()
