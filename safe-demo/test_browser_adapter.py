import unittest
from browser_adapter import (
    BrowserProfile, BrowserProfileManager, BrowserUnavailable, OfflineBrowserBridge,
)


class BrowserProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = BrowserProfile(1, "octo", "profile_1")
        self.bridge = OfflineBrowserBridge()
        self.manager = BrowserProfileManager(self.bridge, {1: self.profile})

    def test_opens_profile_once(self):
        self.assertEqual(self.manager.ensure_open(1), self.profile)
        self.assertEqual(self.manager.ensure_open(1), self.profile)
        self.assertEqual(len(self.bridge.open_calls), 1)

    def test_unknown_account_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.ensure_open(2)

    def test_invalid_profile_rejected(self):
        with self.assertRaises(ValueError):
            BrowserProfile(1, "octo", "../escape")

    def test_failure_stops(self):
        bridge = OfflineBrowserBridge(fail_to_open=True)
        manager = BrowserProfileManager(bridge, {1: self.profile})
        with self.assertRaises(BrowserUnavailable):
            manager.ensure_open(1)

    def test_dolphin_profile(self):
        profile = BrowserProfile(3, "dolphin", "profile-3")
        manager = BrowserProfileManager(self.bridge, {3: profile})
        self.assertEqual(manager.ensure_open(3), profile)


if __name__ == "__main__":
    unittest.main()
