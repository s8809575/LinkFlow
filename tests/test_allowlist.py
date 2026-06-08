import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python", "linkflow"))

from core.file_service import FileService


class TestAllowList(unittest.TestCase):
    def test_is_path_allowed_true_for_child(self):
        with tempfile.TemporaryDirectory() as root:
            child = os.path.join(root, "a", "b")
            os.makedirs(child)
            self.assertTrue(FileService.is_path_allowed(child, [root]))

    def test_is_path_allowed_false_for_outside(self):
        with tempfile.TemporaryDirectory() as root:
            with tempfile.TemporaryDirectory() as outside:
                self.assertFalse(FileService.is_path_allowed(outside, [root]))

