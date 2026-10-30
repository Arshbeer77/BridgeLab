import unittest
from unittest.mock import Mock
from window_visibility import present_window, report_window

class WindowVisibilityTests(unittest.TestCase):
    def root(self):
        root = Mock()
        root.winfo_exists.return_value=True
        root.winfo_screenwidth.return_value=1920
        root.winfo_screenheight.return_value=1080
        root.state.return_value='normal'
        root.geometry.return_value='1180x740+370+170'
        root.winfo_rootx.return_value=370
        root.winfo_rooty.return_value=170
        root.winfo_ismapped.return_value=True
        root.winfo_viewable.return_value=True
        return root
    def test_centres_restores_and_releases_always_on_top(self):
        root=self.root();progress=Mock()
        present_window(root,progress)
        root.geometry.assert_called_once_with('1180x740+370+170')
        root.deiconify.assert_called_once()
        root.lift.assert_called_once()
        root.attributes.assert_called_once_with('-topmost',True)
        root.after.call_args.args[1]()
        self.assertEqual(root.attributes.call_args.args,('-topmost',False))
    def test_ready_requires_actual_mapping(self):
        root=self.root();root.winfo_ismapped.return_value=False
        progress=Mock();report_window(root,progress)
        self.assertNotIn(('Window ready',),[call.args for call in progress.call_args_list])
        self.assertIn('"mapped": false',progress.call_args_list[0].args[0])
    def test_mapping_is_logged_before_ready(self):
        root=self.root();progress=Mock();report_window(root,progress)
        self.assertIn('Window state:',progress.call_args_list[0].args[0])
        self.assertEqual(progress.call_args_list[1].args,('Window ready',))
    def test_closed_window_is_not_reopened(self):
        root=self.root();root.winfo_exists.return_value=False
        present_window(root,Mock());root.deiconify.assert_not_called()
