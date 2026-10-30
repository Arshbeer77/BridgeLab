"""Regression checks for the slim source package's automatic Windows setup."""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parent
SCRIPT = (SOURCE / "FIRST-RUN-WINDOWS.ps1").read_text(encoding="utf-8")
LAUNCHER = (SOURCE / "START-WINDOWS.bat").read_text(encoding="utf-8")


class FirstRunPackagingTests(unittest.TestCase):
    def test_launcher_invokes_first_run_bootstrap(self):
        self.assertIn('FIRST-RUN-WINDOWS.ps1', LAUNCHER)
        self.assertRegex(LAUNCHER, r'powershell\.exe[^\r\n]*-File')
        self.assertNotIn('-ExecutionPolicy', LAUNCHER)

    def test_official_python_download_has_fixed_hash_and_url(self):
        self.assertIn('https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe', SCRIPT)
        match = re.search(r"\$expected\s*=\s*'([0-9a-f]{64})'", SCRIPT)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb')

    def test_authenticode_hash_and_per_user_install_checks_precede_execution(self):
        self.assertIn('Get-AuthenticodeSignature', SCRIPT)
        self.assertIn("$signature.Status -ne 'Valid'", SCRIPT)
        self.assertIn('Python Software Foundation', SCRIPT)
        self.assertLess(SCRIPT.index('Get-FileHash'), SCRIPT.index('Start-Process -FilePath $installer'))
        self.assertLess(SCRIPT.index('Get-AuthenticodeSignature'), SCRIPT.index('Start-Process -FilePath $installer'))
        self.assertIn('InstallAllUsers=0', SCRIPT)
        self.assertIn('PrependPath=0', SCRIPT)
        self.assertIn("TargetDir=\"' + $runtime + '\"", SCRIPT)

    def test_installer_is_downloaded_only_when_python_is_missing(self):
        self.assertLess(SCRIPT.index('if (-not (Test-BridgePython $python)) {', SCRIPT.index('foreach ($command')), SCRIPT.index('Invoke-WebRequest'))
        self.assertNotIn('runtime-setup\\python-3.12.10-amd64.exe', SCRIPT)


if __name__ == '__main__':
    unittest.main()
