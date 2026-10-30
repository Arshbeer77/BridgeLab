"""Regression coverage for lifecycle issues found during the v0.4 audit."""
import queue
import threading
import unittest
from unittest.mock import Mock, patch

from continuity_mvp import BridgeLab


class LifecycleRegressionTests(unittest.TestCase):
    def test_close_is_deferred_until_background_action_finishes(self):
        """Keep the UI alive so an active phone action can finish visibly."""
        app = BridgeLab.__new__(BridgeLab)
        app.closing = False
        app.busy_actions = 0
        app.events = queue.Queue()
        app.status_var = Mock()
        app.file_button = Mock()
        app.url_button = Mock()
        app.log_lock = threading.Lock()
        app.root = Mock()
        app.mirror_process = None
        app.scrcpy_log_handle = None
        app.poll_timer = None
        app._save_settings = Mock()
        app._close_log_handle = Mock()
        app._metric = Mock()
        app.session_timer = None

        started = threading.Event()
        release = threading.Event()
        completed = threading.Event()

        def action():
            started.set()
            release.wait(2)
            completed.set()
            return "finished"

        app._background_action("open_url", action)
        self.assertTrue(started.wait(1))
        with patch("continuity_mvp.messagebox.showinfo") as showinfo:
            app._on_close()
        showinfo.assert_called_once()
        self.assertFalse(app.closing)
        app.root.destroy.assert_not_called()
        release.set()
        self.assertTrue(completed.wait(1))
        # Completion precedes the worker metric/event publication.
        # Wait for the UI event instead of racing the background thread.
        event = app.events.get(timeout=1)
        app.events.put(event)
        app._drain_events()
        self.assertEqual(app.busy_actions, 0)
        app._save_settings = Mock()
        app.root.reset_mock()
        app._on_close()
        self.assertTrue(app.closing)
        app.root.destroy.assert_called_once()

    def test_closed_app_rejects_new_background_action(self):
        app = BridgeLab.__new__(BridgeLab)
        app.closing = True
        callback = Mock()
        app._background_action("file_push", callback)
        callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
