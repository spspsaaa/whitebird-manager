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
        app.DOLPHIN_ACCOUNT_IDS = frozenset()
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

    def test_account_browser_cannot_change_implicitly(self):
        app.bind_profile(1, "dolphin", "d-1")
        with self.assertRaises(ValueError):
            app.bind_profile(1, "octo", "o-1")
        self.assertEqual(app.profile(1), ("dolphin", "d-1"))

    def test_locked_dolphin_inventory(self):
        app.DOLPHIN_ACCOUNT_IDS = frozenset({1, 2, 3, 4})
        with self.assertRaises(ValueError):
            app.bind_profile(5, "dolphin", "d-5")
        with self.assertRaises(ValueError):
            app.bind_profile(1, "octo", "o-1")
        app.bind_profile(1, "dolphin", "d-1")

    def test_update_retries_after_exception(self):
        original = app._dispatch_update
        calls = []
        def failing(update):
            calls.append(update["update_id"])
            if len(calls) == 1:
                raise RuntimeError("temporary")
        app._dispatch_update = failing
        try:
            with self.assertRaises(RuntimeError):
                app.handle_update({"update_id": 123})
            app.handle_update({"update_id": 123})
            app.handle_update({"update_id": 123})
            self.assertEqual(calls, [123, 123])
        finally:
            app._dispatch_update = original

    def test_no_seed_by_default(self):
        self.assertFalse(app.DEMO_SEED_ENABLED)

    def test_nonexistent_account_rejected(self):
        with self.assertRaises(ValueError):
            app.bind_profile(999, "octo", "unknown")


if __name__ == "__main__":
    unittest.main()
