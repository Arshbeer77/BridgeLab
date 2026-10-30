import subprocess
import unittest
from unittest.mock import Mock

from app_windows import MAX_OUTPUT, open_on_phone


def cp(stdout='', returncode=0, stderr=''):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class AppWindowFallbackTests(unittest.TestCase):
    def test_resolve_then_explicit_launch_on_captured_phone(self):
        run = Mock(side_effect=[cp('priority=0 preferredOrder=0\ncom.example.app/.Main\n'),
                                cp('Starting: Intent')])
        result = open_on_phone('adb', 'OPPO', 'com.example.app', run)
        self.assertIn('on the phone', result)
        self.assertEqual(run.call_count, 2)
        first, second = [call.args[0] for call in run.call_args_list]
        self.assertEqual(first[:4], ['adb', '-s', 'OPPO', 'shell'])
        self.assertIn('resolve-activity', first)
        self.assertEqual(first[-2:], ['-p', 'com.example.app'])
        self.assertEqual(second[:4], first[:4])
        self.assertIn('-n com.example.app/.Main', second[-1])
        self.assertTrue(all(call.kwargs['timeout'] == 12 for call in run.call_args_list))

    def test_nested_java_activity_is_shell_quoted(self):
        run = Mock(side_effect=[cp('com.example.app/com.example.Main$Nested'), cp()])
        open_on_phone('adb', 'OPPO', 'com.example.app', run)
        self.assertIn("'com.example.app/com.example.Main$Nested'", run.call_args.args[0][-1])

    def test_package_control_chars_or_injection_never_execute(self):
        for package in ('com.example.app\n', 'com.example.app;id', 'com.example.$x', 'x' * 181):
            run = Mock()
            with self.subTest(package=package), self.assertRaises(ValueError):
                open_on_phone('adb', 'OPPO', package, run)
            run.assert_not_called()

    def test_untrusted_resolver_cannot_inject_or_retarget(self):
        for output in ('com.other.app/.Main', 'com.example.app/.Main;id',
                       'com.example.app/.Main\x00', 'com.example.app/.Main\ncom.example.app/.Other',
                       'No activity found', 'x' * (MAX_OUTPUT + 1)):
            run = Mock(return_value=cp(output))
            with self.subTest(output=output[:70]), self.assertRaises(RuntimeError):
                open_on_phone('adb', 'OPPO', 'com.example.app', run)
            self.assertEqual(run.call_count, 1)

    def test_zero_exit_activity_failure_is_not_success(self):
        run = Mock(side_effect=[cp('com.example.app/.Main'), cp(stderr='Error: Permission Denial')])
        with self.assertRaises(RuntimeError):
            open_on_phone('adb', 'OPPO', 'com.example.app', run)
        self.assertEqual(run.call_count, 2)

    def test_timeout_propagates_without_automatic_retry(self):
        run = Mock(side_effect=[cp('com.example.app/.Main'), subprocess.TimeoutExpired('adb', 12)])
        with self.assertRaises(subprocess.TimeoutExpired):
            open_on_phone('adb', 'OPPO', 'com.example.app', run)
        self.assertEqual(run.call_count, 2)


if __name__ == '__main__':
    unittest.main()
