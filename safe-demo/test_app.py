"""Offline tests for the demo's account-to-browser assignment rules."""
import importlib.util
import os
import tempfile
import unittest

APP_PATH = os.path.join(os.path.dirname(__file__), "app.py")
spec = importlib.util.spec_from_file_location("safe_demo_app", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class ProfileBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB_PATH = os.path.join(self.tmp.name, "test.sqlite")
        with app.db() as con:
            con.executemany("INSERT INTO accounts(name) VALUES (?)", [(f"test-{i}",) for i in range(1, 8)])

    def tearDown(self):
        self.tmp.cleanup()

    def test_dolphin_limit_four(self):
        for i in range(1, 5):
            app.bind_profile(i, "dolphin", f"d-{i}")
        with self.assertRaises(ValueError):
            app.bind_profile(5, "dolphin", "d-5")

    def test_octo_unlimited_within_inventory(self):
        for i in range(1, 8):
            app.bind_profile(i, "octo", f"o-{i}")
        self.assertEqual(app.profile(7), ("octo", "o-7"))

    def test_profile_unique_within_browser(self):
        app.bind_profile(1, "octo", "shared")
        with self.assertRaises(Exception):
            app.bind_profile(2, "octo", "shared")

    def test_account_has_single_binding(self):
        app.bind_profile(1, "dolphin", "d-1")
        app.bind_profile(1, "octo", "o-1")
        self.assertEqual(app.profile(1), ("octo", "o-1"))

    def test_nonexistent_account_rejected(self):
        with self.assertRaises(ValueError):
            app.bind_profile(999, "octo", "unknown")


if __name__ == "__main__":
    unittest.main()
