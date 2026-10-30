"""Headless orchestration regressions; no phone or rendered Tk window."""
import queue
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from bridge_core import Device
from continuity_mvp import BridgeLab


class ReliabilityTests(unittest.TestCase):
    def app(self):
        app = BridgeLab.__new__(BridgeLab)
        app.root = Mock()
        app.closing = False
        app.poll_timer = None
        app.poll_running = False
        app.selected_serial = 'OPPO'
        app.last_authorized_serials = {'OPPO'}
        app.devices = [Device('OPPO', 'device', 'OPPO')]
        for name in ('device_var', 'connection_var', 'battery_var', 'status_var', 'auto_var'):
            setattr(app, name, Mock())
        app.device_box = {}
        app.mirror_process = None
        app.auto_var.get.return_value = True
        app._save_settings = Mock()
        return app

    def test_refresh_replaces_pending_timer(self):
        app = self.app()
        app.root.after.return_value = 'timer1'
        app._schedule_poll()
        app._schedule_poll()
        app.root.after_cancel.assert_called_once_with('timer1')

    def test_adb_failure_does_not_create_reconnect(self):
        app = self.app()
        app._update_devices([], None, 'timeout')
        self.assertEqual(app.last_authorized_serials, {'OPPO'})
        self.assertEqual(app.devices, [])
        app.root.reset_mock()
        app._update_devices([Device('OPPO', 'device', 'OPPO')], None, None)
        self.assertEqual(app.root.after.call_count, 1)  # poll only, no auto-start

    def test_does_not_switch_to_other_phone(self):
        app = self.app()
        app._update_devices([Device('OTHER', 'device', 'Other')], None, None)
        self.assertEqual(app.selected_serial, 'OPPO')
        app._save_settings.assert_not_called()

    def test_auto_start_rechecks_consent_and_device(self):
        app = self.app()
        app.start_mirror = Mock()
        app._auto_start('OTHER')
        app.auto_var.get.return_value = False
        app._auto_start('OPPO')
        app.start_mirror.assert_not_called()
        app.auto_var.get.return_value = True
        app._auto_start('OPPO')
        app.start_mirror.assert_called_once()

    def test_confirmed_disconnect_allows_reconnect(self):
        app = self.app()
        app._update_devices([], None, None)
        app.root.reset_mock()
        app._update_devices([Device('OPPO', 'device', 'OPPO')], None, None)
        self.assertEqual(app.root.after.call_count, 2)

    def test_old_device_or_adb_observation_is_discarded(self):
        for context in [('old-adb', 'OPPO'), ('adb', 'OLD-PHONE')]:
            with self.subTest(context=context):
                app = self.app()
                app.adb_path = Mock(get=Mock(return_value='adb'))
                app.poll_running = True
                app._update_devices([Device('OTHER', 'device', 'Other')], 87, None, context)
                self.assertFalse(app.poll_running)
                self.assertEqual(app.devices[0].serial, 'OPPO')
                app.battery_var.set.assert_not_called()
                self.assertEqual(app.root.after.call_args.args[0], 0)

    def test_refresh_while_polling_requests_one_followup(self):
        app = self.app()
        app.poll_running = True
        app._poll_devices()
        app._poll_devices()
        app.root.after.assert_not_called()
        app._update_devices(app.devices, None, None)
        self.assertEqual(app.root.after.call_count, 1)
        self.assertEqual(app.root.after.call_args.args[0], 0)

    def test_stop_invalidates_queued_auto_start(self):
        app = self.app()
        app.start_mirror = Mock()
        app.launch_generation = 8
        app.stop_mirror()
        app._auto_start('OPPO', 8)
        app.start_mirror.assert_not_called()

    def test_stop_invalidates_pending_tool_validation(self):
        app = self.app()
        app.launch_generation = 8
        app.launch_pending = True
        app._spawn_scrcpy = Mock()
        app.stop_mirror()
        app._finish_launch(8, 'OPPO', [], 'adb', 'scrcpy', None, None)
        app._spawn_scrcpy.assert_not_called()
        self.assertFalse(app.launch_pending)

    def test_pending_launch_rejects_changed_tools(self):
        app = self.app()
        app.launch_generation = 8
        app.launch_pending = True
        app.adb_path = Mock(get=Mock(return_value='new-adb'))
        app.scrcpy_path = Mock(get=Mock(return_value='scrcpy'))
        app._spawn_scrcpy = Mock()
        app._finish_launch(8, 'OPPO', [], 'old-adb', 'scrcpy', None, None)
        app._spawn_scrcpy.assert_not_called()
        self.assertFalse(app.launch_pending)

    def test_auto_consent_revoked_during_validation_cancels_launch(self):
        app = self.app()
        app.launch_generation = 8
        app.launch_pending = True
        app.auto_var.get.return_value = False
        app._spawn_scrcpy = Mock()
        app._finish_launch(8, 'OPPO', [], 'adb', 'scrcpy', None, None, auto=True)
        app._spawn_scrcpy.assert_not_called()
        self.assertFalse(app.launch_pending)

    def test_old_session_watcher_cannot_touch_replacement(self):
        app = self.app()
        old = Mock()
        app.mirror_process = Mock()
        app._close_log_handle = Mock()
        app._check_scrcpy(old)
        app._close_log_handle.assert_not_called()
        app.root.after.assert_not_called()
        app.mirror_process.poll.assert_not_called()

    def test_intentional_stop_does_not_record_failed_exit(self):
        app = self.app()
        proc = Mock(returncode=-15)
        proc.poll.return_value = -15
        app.mirror_process = app.stopping_process = proc
        app._metric = Mock()
        app._close_log_handle = Mock()
        app._check_scrcpy(proc)
        app._metric.assert_not_called()
        app._close_log_handle.assert_called_once()
        self.assertIsNone(app.mirror_process)

    def test_no_background_action_after_close(self):
        app = self.app()
        app.closing = True
        fn = Mock()
        with patch('continuity_mvp.threading.Thread') as thread:
            app._background_action('file_push', fn)
        thread.assert_not_called()
        fn.assert_not_called()

    def test_windows_validation_runs_off_ui_thread(self):
        app = self.app()
        app.events = queue.Queue()
        app._ready = Mock(return_value=('adb', __file__))
        app._spawn_scrcpy = Mock()
        for name, value in [('size_var', '1280'), ('fps_var', '60'), ('mode_var', 'Standard')]:
            setattr(app, name, Mock(get=Mock(return_value=value)))
        app.audio_var = Mock(get=Mock(return_value=False))
        app.off_var = Mock(get=Mock(return_value=False))
        with patch('continuity_mvp.os', SimpleNamespace(name='nt')), \
             patch('continuity_mvp.validate_bundle_files') as bundle, \
             patch('continuity_mvp.validate_windows_tool') as pe, \
             patch('continuity_mvp.threading.Thread') as thread:
            app._launch_scrcpy(None)
            bundle.assert_not_called()
            pe.assert_not_called()
            app._spawn_scrcpy.assert_not_called()
            self.assertTrue(app.launch_pending)
            thread.call_args.kwargs['target']()
            bundle.assert_called_once()
            self.assertEqual(pe.call_count, 2)
            kind, data = app.events.get_nowait()
            self.assertEqual(kind, 'launch_ready')
            self.assertEqual(data[1], 'OPPO')
            self.assertIsNone(data[-2])
            self.assertFalse(data[-1])

    def test_busy_action_not_started_twice(self):
        app = self.app()
        app.busy_actions = 1
        task = Mock()
        app._background_action('file_push', task)
        task.assert_not_called()

    def test_failed_launch_closes_log(self):
        app = self.app()
        app._ready = Mock(return_value=('adb', __file__))
        for name, value in [('size_var','1280'), ('fps_var','60'), ('mode_var','Standard')]:
            setattr(app, name, Mock(get=Mock(return_value=value)))
        app.audio_var = Mock(get=Mock(return_value=False))
        app.off_var = Mock(get=Mock(return_value=False))
        app.scrcpy_log_handle = None
        with patch('continuity_mvp.APP_DIR', Mock()), patch('continuity_mvp.open', create=True) as opened, patch('continuity_mvp.subprocess.Popen', side_effect=OSError('failed')), patch('continuity_mvp.messagebox.showerror'):
            app._launch_scrcpy(None)
            opened.return_value.close.assert_called_once()
            self.assertIsNone(app.scrcpy_log_handle)


if __name__ == '__main__':
    unittest.main()
