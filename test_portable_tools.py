"""Filesystem and discovery checks for source and portable layouts."""
import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import portable_tools
import continuity_mvp


def touch(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test executable", encoding="utf-8")
    return str(path)


def executable(directory: Path, name: str) -> Path:
    return directory / portable_tools._exe(name)


class ToolDiscoveryTests(unittest.TestCase):
    def test_bundle_pair_overrides_stale_settings_and_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "BridgeLab"
            bundled_adb = touch(executable(root / "tools" / "scrcpy", "adb"))
            bundled_scrcpy = touch(executable(root / "tools" / "scrcpy", "scrcpy"))
            stale_adb = touch(executable(Path(tmp) / "old", "adb"))
            stale_scrcpy = touch(executable(Path(tmp) / "old", "scrcpy"))
            with patch.object(portable_tools, "application_root", return_value=root), \
                 patch.object(portable_tools.shutil, "which", side_effect=lambda n: f"/path/{n}"):
                self.assertEqual(
                    portable_tools.discover_tools(stale_adb, stale_scrcpy),
                    (str(Path(bundled_adb).resolve()), str(Path(bundled_scrcpy).resolve())),
                )

    def test_scrcpy_sibling_adb_keeps_versions_paired_unless_adb_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            scrcpy_dir = Path(tmp) / "scrcpy-install"
            scrcpy = touch(executable(scrcpy_dir, "scrcpy"))
            sibling_adb = touch(executable(scrcpy_dir, "adb"))
            explicit_adb = touch(executable(Path(tmp) / "custom", "adb"))
            with patch.object(portable_tools, "application_root", return_value=root), \
                 patch.object(portable_tools.shutil, "which", side_effect=lambda n: f"/path/{n}"):
                self.assertEqual(
                    portable_tools.discover_tools("", scrcpy),
                    (str(Path(sibling_adb).resolve()), str(Path(scrcpy).resolve())),
                )
                self.assertEqual(
                    portable_tools.discover_tools(explicit_adb, scrcpy),
                    (str(Path(explicit_adb).resolve()), str(Path(scrcpy).resolve())),
                )

    def test_stale_saved_paths_fall_back_to_path_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "app"
            path_adb = touch(executable(Path(tmp) / "path", "adb"))
            path_scrcpy = touch(executable(Path(tmp) / "path", "scrcpy"))
            with patch.object(portable_tools, "application_root", return_value=root), \
                 patch.object(portable_tools.shutil, "which", side_effect=lambda n: path_adb if n == "adb" else path_scrcpy):
                adb, scrcpy = portable_tools.discover_tools(
                    str(Path(tmp) / "missing-adb"), str(Path(tmp) / "missing-scrcpy"))
            self.assertEqual((adb, scrcpy), (str(Path(path_adb).resolve()), str(Path(path_scrcpy).resolve())))

    def test_application_root_uses_executable_location_when_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            expected = Path(tmp).resolve()
            executable_file = expected / "BridgeLab.exe"
            executable_file.touch()
            with patch.object(portable_tools.sys, "frozen", True, create=True), \
                 patch.object(portable_tools.sys, "executable", str(executable_file)):
                self.assertEqual(portable_tools.application_root(), expected)

    def test_portable_self_check_writes_success_result_without_device_access(self):
        class FakeTk:
            class Tcl:
                @staticmethod
                def call(*_args):
                    return "8.6.13"

            tk = Tcl()

            def withdraw(self):
                pass

            def destroy(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            result_file = Path(tmp) / "self-check.json"
            with patch.object(continuity_mvp, "Tk", FakeTk), \
                 patch.object(continuity_mvp, "application_root", return_value=Path(tmp)), \
                 patch.object(continuity_mvp, "discover_tools", return_value=("/bundle/adb", "/bundle/scrcpy")):
                self.assertEqual(continuity_mvp.portable_self_check(str(result_file)), 0)
            result = json.loads(result_file.read_text(encoding="utf-8"))
            self.assertTrue(result["ok"])
            self.assertEqual(result["tk_version"], "8.6.13")
            self.assertEqual((result["adb"], result["scrcpy"]), ("/bundle/adb", "/bundle/scrcpy"))


if __name__ == "__main__":
    unittest.main()
