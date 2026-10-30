import subprocess
import unittest
from unittest.mock import Mock, patch

from app_windows import (AppWindowCapability, app_window_command, list_apps,
                         parse_scrcpy_apps, preflight)


def cp(stdout='', returncode=0, stderr=''):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


HELP = '--new-display[=SIZE] --start-app=PKG --list-apps'


class AppWindowTests(unittest.TestCase):
    def test_capability_uses_real_android_sdk_and_selected_serial(self):
        run = Mock(side_effect=[cp(HELP), cp('34\n')])
        capability = preflight('adb', 'scrcpy', 'PHONE1', run)
        self.assertTrue(capability.supported)
        self.assertEqual(capability.serial, 'PHONE1')
        self.assertIn('device test', capability.diagnostics)
        self.assertEqual(run.call_args_list[1].args[0],
                         ['adb', '-s', 'PHONE1', 'shell', 'getprop', 'ro.build.version.sdk'])
        self.assertTrue(all(call.kwargs['timeout'] <= 10 for call in run.call_args_list))

    def test_old_android_or_missing_tool_features_block_launch(self):
        for results in ([cp(HELP), cp('28')], [cp('--new-display')], [cp(HELP), cp('unknown')]):
            with self.subTest(results=results):
                self.assertFalse(preflight('adb', 'scrcpy', 'PHONE', Mock(side_effect=results)).supported)

    def test_static_tool_validation_failure_prevents_execution(self):
        run = Mock()
        with patch('app_windows._validate_tools', side_effect=ValueError('Damaged bundled PE')):
            result = preflight('adb', 'scrcpy', 'PHONE', run)
        self.assertFalse(result.supported)
        self.assertIn('Damaged bundled PE', result.diagnostics)
        run.assert_not_called()

    def test_help_timeout_becomes_diagnostic(self):
        run = Mock(side_effect=subprocess.TimeoutExpired('scrcpy', 10))
        result = preflight('adb', 'scrcpy', 'PHONE', run)
        self.assertFalse(result.supported)
        self.assertIn('preflight failed', result.diagnostics)

    def test_help_option_substrings_do_not_pass(self):
        result = preflight('adb', 'scrcpy', 'PHONE', Mock(return_value=cp('--new-display-fake --start-app')))
        self.assertFalse(result.supported)

    def test_parser_supports_upstream_long_labels_and_deduplicates(self):
        result = parse_scrcpy_apps('INFO: List of apps:\n * Settings                       com.android.settings\n'
                                 ' - A very long application label that wraps\n                                  org.example.longname\n'
                                 ' - Settings                       com.android.settings\n - Malicious label foo;rm -rf\n')
        self.assertEqual({app.package for app in result}, {'com.android.settings', 'org.example.longname'})
        self.assertEqual(result[0].name, 'A very long application label that wraps')

    def test_listing_passes_exact_adb_environment(self):
        run = Mock(return_value=cp(' * Settings                       com.android.settings'))
        capability = AppWindowCapability('PHONE', 34, True, True, '')
        apps = list_apps('/bundle/adb', '/bundle/scrcpy', 'PHONE', run, capability)
        self.assertEqual(apps[0].package, 'com.android.settings')
        self.assertEqual(run.call_args.kwargs['env']['ADB'], '/bundle/adb')
        self.assertEqual(run.call_args.args[0], ['/bundle/scrcpy', '-s', 'PHONE', '--list-apps'])

    def test_failed_scrcpy_listing_falls_back_to_launchable_activity_query(self):
        run = Mock(side_effect=[cp(returncode=1, stderr='OEM failure'),
                                cp('2 activities found:\ncom.example.app/.Main\ncom.example.app/.Other\n')])
        capability = AppWindowCapability('PHONE', 34, True, True, '')
        apps = list_apps('adb', 'scrcpy', 'PHONE', run, capability)
        self.assertEqual([app.package for app in apps], ['com.example.app'])
        self.assertIn('android.intent.category.LAUNCHER', run.call_args.args[0])
        self.assertEqual(run.call_count, 2)

    def test_stale_capability_cannot_retarget_other_phone(self):
        run = Mock()
        with self.assertRaises(ValueError):
            list_apps('adb', 'scrcpy', 'NEW', run, AppWindowCapability('OLD', 34, True, True, ''))
        run.assert_not_called()

    def test_empty_or_failed_app_listing_does_not_invent_success(self):
        for result in [cp('Unknown command: query-activities'), cp('', 1, 'unauthorized')]:
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                list_apps('adb', 'scrcpy', 'PHONE', Mock(return_value=result),
                          AppWindowCapability('PHONE', 34, True, False, ''))

    def test_command_is_virtual_display_with_no_screen_off(self):
        args = app_window_command('scrcpy', 'PHONE', 'com.android.settings', control_mode='uhid')
        self.assertIn('--new-display=1280x800', args)
        self.assertIn('--start-app=com.android.settings', args)
        self.assertIn('--keyboard=uhid', args)
        self.assertNotIn('--turn-screen-off', args)
        self.assertNotIn('--no-vd-destroy-content', args)
        for bad in ('com.example.app; touch /tmp/x', '', '@settings'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                app_window_command('scrcpy', 'PHONE', bad)


class AppWindowLifecycleTests(unittest.TestCase):
    def controller(self):
        import queue
        from app_windows_ui import AppWindowsWindow
        controller = AppWindowsWindow.__new__(AppWindowsWindow)
        controller.process = Mock()
        controller.process.poll.return_value = None
        controller.stop_pending = False
        controller.closed = False
        controller.close_requested = False
        controller.window = Mock()
        controller.after_id = "tick"
        controller.start_button = Mock()
        controller.refresh_button = Mock()
        controller.log_handle = Mock()
        controller.events = queue.Queue()
        controller.stop_button = Mock()
        controller.status = Mock()
        return controller

    def test_stop_waits_off_tk_thread_and_retains_child_until_exit_event(self):
        controller = self.controller()
        process = controller.process
        with patch('app_windows_ui.threading.Thread') as thread:
            controller.stop()
            process.terminate.assert_called_once()
            process.wait.assert_not_called()
            self.assertIs(controller.process, process)
            thread.call_args.kwargs['target']()
        process.wait.assert_called_once_with(timeout=2)
        self.assertEqual(controller.events.get_nowait(), ('stopped', process))

    def test_close_defers_parent_destruction_until_child_exit(self):
        controller = self.controller()
        with patch('app_windows_ui.threading.Thread') as thread:
            self.assertFalse(controller.close())
            self.assertFalse(controller.closed)
            self.assertTrue(controller.close_requested)
            controller.window.destroy.assert_not_called()
            thread.call_args.kwargs['target']()
        controller.stop_pending = False  # delivered stopped event
        controller.process.poll.return_value = 0
        self.assertTrue(controller.close())
        self.assertTrue(controller.closed)
        controller.window.destroy.assert_called_once()
        self.assertTrue(controller.close())

    def test_failed_force_stop_does_not_lose_process_ownership(self):
        controller = self.controller()
        process = controller.process
        process.wait.side_effect = subprocess.TimeoutExpired('scrcpy', 2)
        with patch('app_windows_ui.threading.Thread') as thread:
            controller.stop()
            thread.call_args.kwargs['target']()
        process.kill.assert_called_once()
        self.assertIs(controller.process, process)
        controller.log_handle.close.assert_not_called()
        self.assertEqual(controller.events.get_nowait()[0], 'stop_failed')


if __name__ == '__main__':
    unittest.main()
