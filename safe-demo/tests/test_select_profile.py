import importlib.util
import sys
import unittest
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "windows-agent"
sys.path.insert(0, str(DIR))
spec = importlib.util.spec_from_file_location("whitebird_selector", DIR / "select_profile.py")
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


class SelectorTests(unittest.TestCase):
    def setUp(self):
        self.data = {"accounts": [
            {"name": "Octo A", "browser": "octo", "profile_id": "octo-1"},
            {"name": "Dolphin B", "browser": "dolphin", "profile_id": "dolphin-1"},
        ]}

    def test_select_octo(self):
        result = selector.select_account(self.data, "octo a")
        self.assertEqual(result["browser"], "octo")
        self.assertEqual(result["profile_id"], "octo-1")
        self.assertEqual(result["status"], "selected_not_started")

    def test_select_dolphin(self):
        self.assertEqual(selector.select_account(self.data, "Dolphin B")["browser"], "dolphin")

    def test_unknown_account_rejected(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            selector.select_account(self.data, "Unknown")

    def test_duplicate_profile_rejected_before_selection(self):
        self.data["accounts"][1]["profile_id"] = "octo-1"
        self.data["accounts"][1]["browser"] = "octo"
        with self.assertRaisesRegex(ValueError, "duplicate browser profile"):
            selector.select_account(self.data, "Octo A")


if __name__ == "__main__":
    unittest.main()
