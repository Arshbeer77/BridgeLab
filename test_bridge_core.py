import unittest
from bridge_core import (
    clean_url, parse_devices, safe_local_files, scrcpy_command,
    url_intent_shell_command, validate_package_id, new_authorized_connections,
)


class CommandTests(unittest.TestCase):
    def test_device_parse(self):
        output = "List of devices attached\nR58NA device product:x model:Pixel_8 transport_id:1\n101 unauthorized transport_id:2\n"
        devices = parse_devices(output)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].model, "Pixel 8")
        self.assertFalse(devices[1].authorized)

    def test_url_quoting(self):
        url = "https://example.com/?q=one&next=two"
        command = url_intent_shell_command(url)
        self.assertIn("'https://example.com/?q=one&next=two'", command)

    def test_url_rejects_shell_payload_and_non_web_schemes(self):
        for candidate in ("javascript:alert(1)", "https://ok.com/\nrm -rf /", "https://bad site.com", "not a url"):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                clean_url(candidate)

    def test_scrcpy_base(self):
        self.assertEqual(scrcpy_command("scrcpy", "device1", 1280, 60, False),
                         ["scrcpy", "-s", "device1", "--max-size=1280", "--max-fps=60", "--no-audio"])

    def test_oppo_uhid_fallback(self):
        cmd = scrcpy_command("scrcpy", "oppo", 1600, 60, False, control_mode="uhid")
        self.assertIn("--mouse=uhid", cmd)
        self.assertIn("--keyboard=uhid", cmd)
        self.assertNotIn("--turn-screen-off", cmd)

    def test_screen_off_main_display_only(self):
        cmd = scrcpy_command("scrcpy", "oppo", 1280, 60, False, turn_screen_off=True)
        self.assertIn("--turn-screen-off", cmd)
        self.assertIn("--stay-awake", cmd)
        virtual = scrcpy_command("scrcpy", "oppo", 1280, 60, False, "com.android.settings", turn_screen_off=True)
        self.assertNotIn("--turn-screen-off", virtual)
        self.assertNotIn("--stay-awake", virtual)

    def test_reject_unknown_control_mode(self):
        with self.assertRaises(ValueError):
            scrcpy_command("scrcpy", "oppo", 1280, 60, False, control_mode="root")

    def test_opt_in_reconnect_diff(self):
        devices = parse_devices("List of devices attached\nOPPO1 device model:OPPO_A79_5G\nX2 unauthorized\n")
        self.assertEqual(new_authorized_connections(set(), devices), {"OPPO1"})
        self.assertEqual(new_authorized_connections({"OPPO1"}, devices), set())

    def test_virtual_app(self):
        cmd = scrcpy_command("scrcpy", "device1", 1280, 60, True, "com.android.settings")
        self.assertIn("--new-display=1280x800", cmd)
        self.assertIn("--start-app=com.android.settings", cmd)
        with self.assertRaises(ValueError):
            validate_package_id("com.foo; rm -rf / ")


if __name__ == "__main__":
    unittest.main()
