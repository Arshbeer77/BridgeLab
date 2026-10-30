import subprocess
import unittest
from unittest.mock import Mock

from phone_calls import dialer_command, normalize_number, request_dialer


class PhoneCallsTests(unittest.TestCase):
    def test_dial_handoff_targets_selected_phone_without_auto_call(self):
        args = dialer_command('C:/tools/adb.exe', 'selected-phone', '+44 (20) 1234-5678')
        self.assertEqual(args, ['C:/tools/adb.exe', '-s', 'selected-phone', 'shell',
                               'am start -a android.intent.action.DIAL -d tel:+442012345678'])

    def test_blank_number_opens_empty_dialer(self):
        self.assertTrue(dialer_command('adb', 'phone', '')[-1].endswith('tel:'))

    def test_rejects_shell_injection_service_codes_and_uri_extras(self):
        for number in ('1; reboot', '1 && reboot', '$(id)', '`id`', '*#06#',
                       'tel:123', '123?x=y', '+', '12+3', '１２３', '123\n456', '1' * 33):
            with self.subTest(number=number), self.assertRaises(ValueError):
                dialer_command('adb', 'phone', number)

    def test_invalid_number_never_reaches_runner(self):
        run = Mock()
        with self.assertRaises(ValueError):
            request_dialer('adb', 'phone', '1; reboot', run)
        run.assert_not_called()

    def test_android_error_with_zero_exit_not_reported_as_success(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, '', 'Error: Activity not started'))
        self.assertIn('could not open', request_dialer('adb', 'phone', '123', run))
        self.assertEqual(run.call_args.kwargs, {'timeout': 12})

    def test_timeout_is_ambiguous_and_never_retried(self):
        run = Mock(side_effect=subprocess.TimeoutExpired('adb', 12))
        self.assertIn('may already be open', request_dialer('adb', 'phone', '', run))
        self.assertEqual(run.call_count, 1)

    def test_success_is_only_a_dialer_request_and_no_number_echo(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, 'Starting: Intent', ''))
        message = request_dialer('adb', 'phone', '123456', run)
        self.assertIn('Audio stays on the phone', message)
        self.assertNotIn('123456', message)


if __name__ == '__main__':
    unittest.main()
