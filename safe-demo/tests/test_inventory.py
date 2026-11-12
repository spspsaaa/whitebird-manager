"""Tests for offline Windows agent inventory."""
import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "windows-agent" / "inventory.py"
spec = importlib.util.spec_from_file_location("whitebird_inventory", MODULE)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def test_valid_17_octo_4_dolphin(self):
        rows = [
            {"name": f"Octo {i}", "browser": "octo", "profile_id": f"o-{i}"}
            for i in range(17)
        ] + [
            {"name": f"Dolphin {i}", "browser": "dolphin", "profile_id": f"d-{i}"}
            for i in range(4)
        ]
        self.assertEqual(inventory.validate_inventory({"accounts": rows}),
                         {"accounts": 21, "octo": 17, "dolphin": 4, "valid": True})

    def test_duplicate_profile(self):
        row = {"name": "First", "browser": "octo", "profile_id": "same"}
        with self.assertRaisesRegex(ValueError, "duplicate browser profile"):
            inventory.validate_inventory({"accounts": [row, {**row, "name": "Second"}]})

    def test_dolphin_limit(self):
        rows = [{"name": str(i), "browser": "dolphin", "profile_id": str(i)} for i in range(5)]
        with self.assertRaisesRegex(ValueError, "Dolphin limit"):
            inventory.validate_inventory({"accounts": rows})

    def test_reject_bad_browser(self):
        with self.assertRaisesRegex(ValueError, "unknown browser"):
            inventory.validate_inventory({"accounts": [{"name": "A", "browser": "unknown", "profile_id": "x"}]})

    def test_reject_invalid_input(self):
        for data in ([], {}, {"accounts": "bad"}, {"accounts": [None]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                inventory.validate_inventory(data)


if __name__ == "__main__":
    unittest.main()
