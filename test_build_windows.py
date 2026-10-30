"""Platform-independent checks for archive validation in the Windows builder."""
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_windows

SOURCE = Path(__file__).resolve().parent
PYTHON_INSTALLER = SOURCE / "runtime-setup" / "python-3.12.10-amd64.exe"
PYTHON_HASH_FILE = SOURCE / "runtime-setup" / "python-installer.sha256"


class BuildArchiveTests(unittest.TestCase):
    def test_extracts_complete_scrcpy_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "scrcpy.zip"
            target = Path(tmp) / "extract"
            files = {
                "scrcpy-win64/scrcpy.exe": b"scrcpy",
                "scrcpy-win64/adb.exe": b"adb",
                "scrcpy-win64/AdbWinApi.dll": b"api",
                "scrcpy-win64/AdbWinUsbApi.dll": b"usb",
                "scrcpy-win64/libusb-1.0.dll": b"libusb",
                "scrcpy-win64/LICENSE.txt": b"licenses",
                "scrcpy-win64/scrcpy-server": b"server",
                "scrcpy-win64/SDL2.dll": b"sdl",
                "scrcpy-win64/avcodec-61.dll": b"codec",
                "scrcpy-win64/avformat-61.dll": b"format",
                "scrcpy-win64/avutil-59.dll": b"util",
                "scrcpy-win64/swresample-5.dll": b"resample",
            }
            with zipfile.ZipFile(archive, "w") as bundle:
                for name, contents in files.items():
                    bundle.writestr(name, contents)
            folder = build_windows.extract_archive(archive, target)
            self.assertEqual(folder, target / "scrcpy-win64")
            build_windows.validate_tools(folder)

    def test_rejects_path_traversal_before_extracting(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "malicious.zip"
            target = Path(tmp) / "extract"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../outside.txt", b"escape")
            with self.assertRaisesRegex(ValueError, "Unsafe ZIP path"):
                build_windows.extract_archive(archive, target)
            self.assertFalse((Path(tmp) / "outside.txt").exists())

    def test_rejects_incomplete_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Incomplete scrcpy runtime"):
                build_windows.validate_tools(Path(tmp))

    @unittest.skipUnless(PYTHON_INSTALLER.is_file() and PYTHON_HASH_FILE.is_file(),
                         "source archive does not include the optional runtime installer")
    def test_bundled_python_installer_matches_checked_in_sha256(self):
        expected = PYTHON_HASH_FILE.read_text(encoding="ascii").strip().split()[0].lower()
        actual = hashlib.sha256(PYTHON_INSTALLER.read_bytes()).hexdigest()
        self.assertRegex(expected, r"^[0-9a-f]{64}$")
        self.assertEqual(actual, expected)

    @unittest.skipUnless(PYTHON_INSTALLER.is_file(),
                         "source archive does not include the optional runtime installer")
    def test_bundled_python_amd64_installer_is_pe32_bootstrapper(self):
        data = PYTHON_INSTALLER.read_bytes()
        self.assertEqual(data[:2], b"MZ")
        pe_offset = int.from_bytes(data[0x3C:0x40], "little")
        self.assertEqual(data[pe_offset:pe_offset + 4], b"PE\0\0")
        # The official amd64 installer uses a 32-bit GUI bootstrapper stub;
        # its filename/package target does not make the outer PE x64.
        self.assertEqual(int.from_bytes(data[pe_offset + 4:pe_offset + 6], "little"), 0x014C)
        self.assertEqual(int.from_bytes(data[pe_offset + 24:pe_offset + 26], "little"), 0x010B)


if __name__ == "__main__":
    unittest.main()
