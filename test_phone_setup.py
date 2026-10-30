import unittest
from phone_setup import settings_command

class SetupCommandTests(unittest.TestCase):
    def test_open_settings_targets_selected_phone_without_grant(self):
        args = settings_command('adb', 'OPPO', 'developer')
        self.assertEqual(args, ['adb','-s','OPPO','shell','am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS'])
        self.assertNotIn('grant', ' '.join(args))
    def test_unknown_settings_page_rejected(self):
        with self.assertRaises(ValueError): settings_command('adb','OPPO','developer; pm grant evil')
