import shlex
import subprocess
import unittest
from unittest.mock import Mock

from bridge_core import scrcpy_command
from mirror_drop import (
    DEFAULT_MIRROR_DROP_TARGET, normalize_mirror_drop_target, prepare_mirror_drop,
)


class MirrorDropTests(unittest.TestCase):
    def test_default_and_shared_aliases(self):
        self.assertEqual(normalize_mirror_drop_target(DEFAULT_MIRROR_DROP_TARGET),
                         "/sdcard/Download/BridgeLab")
        for target in ("/storage/emulated/0/Download/My Files/",
                       "/storage/self/primary/Download//My Files",
                       "/sdcard//Download/My Files"):
            with self.subTest(target=target):
                self.assertEqual(normalize_mirror_drop_target(target), "/sdcard/Download/My Files")

    def test_private_traversal_and_invalid_paths_rejected(self):
        for target in ("", None, "Download/BridgeLab", "/data/local/tmp",
                       "/sdcard2/Download", "/storage/emulated/10/Download",
                       "/sdcard/../data", "/sdcard/Download/./BridgeLab",
                       "/sdcard/Android/data", "/sdcard/Android/obb/game",
                       "/storage/emulated/0/ANDROID/DATA/game",
                       "/sdcard/a\nb", "/sdcard/a\x00b", "/sdcard/a\x7fb",
                       "/sdcard/a\\..\\data", "/sdcard/" + "a" * 1024):
            with self.subTest(target=target), self.assertRaises(ValueError):
                normalize_mirror_drop_target(target)

    def test_mkdir_is_bounded_and_targets_selected_phone(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, DEFAULT_MIRROR_DROP_TARGET, ""))
        target = prepare_mirror_drop("my-adb", "PHONE1", DEFAULT_MIRROR_DROP_TARGET, run)
        self.assertEqual(target, DEFAULT_MIRROR_DROP_TARGET)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][:4], ["my-adb", "-s", "PHONE1", "shell"])
        self.assertEqual(run.call_args.kwargs["timeout"], 15)
        self.assertIn('if [ -L "$p" ]', run.call_args.args[0][-1])

    def test_spaces_and_shell_punctuation_are_one_literal_path(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, DEFAULT_MIRROR_DROP_TARGET, ""))
        target = "/sdcard/Download/Bob's files; $(touch nope) `id` & more"
        run.return_value.stdout = target
        self.assertEqual(prepare_mirror_drop("adb", "PHONE1", target, run), target)
        command = run.call_args.args[0][-1]
        self.assertIn(shlex.quote(target.rsplit("/", 1)[-1]), command)
        cmd = scrcpy_command("scrcpy", "PHONE1", 1280, 60, False, push_target=target)
        self.assertEqual([arg for arg in cmd if arg.startswith("--push-target=")],
                         ["--push-target=" + target])

    def test_failed_mkdir_is_reported(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 1, "", "Permission denied"))
        with self.assertRaisesRegex(RuntimeError, "Permission denied"):
            prepare_mirror_drop("adb", "PHONE1", DEFAULT_MIRROR_DROP_TARGET, run)

    def test_timeout_and_missing_adb_propagate(self):
        for error in (subprocess.TimeoutExpired("adb", 15), FileNotFoundError("adb")):
            with self.subTest(error=error), self.assertRaises(type(error)):
                prepare_mirror_drop("adb", "PHONE1", DEFAULT_MIRROR_DROP_TARGET,
                                    Mock(side_effect=error))

    def test_invalid_target_or_serial_never_runs_adb(self):
        run = Mock()
        for target, serial in (("/data/private", "PHONE1"),
                               (DEFAULT_MIRROR_DROP_TARGET, ""),
                               (DEFAULT_MIRROR_DROP_TARGET, "PHONE 1")):
            with self.subTest(target=target, serial=serial), self.assertRaises(ValueError):
                prepare_mirror_drop("adb", serial, target, run)
        run.assert_not_called()

    def test_push_target_optional_preserves_main_and_app_defaults(self):
        for package in (None, "com.android.settings"):
            cmd = scrcpy_command("scrcpy", "PHONE1", 1280, 60, False, package)
            self.assertFalse(any(arg.startswith("--push-target=") for arg in cmd))
        cmd = scrcpy_command("scrcpy", "PHONE1", 1280, 60, False,
                             push_target="/storage/emulated/0/Download/BridgeLab/")
        self.assertIn("--push-target=" + DEFAULT_MIRROR_DROP_TARGET, cmd)

    def test_command_builder_cannot_bypass_path_validation(self):
        with self.assertRaises(ValueError):
            scrcpy_command("scrcpy", "PHONE1", 1280, 60, False,
                           push_target="/sdcard/../data")


if __name__ == "__main__":
    unittest.main()
