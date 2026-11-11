"""Offline validation tests; no Octo or WhiteBird access."""
import importlib.util
import json
import os
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("local_octo_agent", os.path.join(os.path.dirname(__file__), "local_octo_agent.py"))
agent = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = agent
spec.loader.exec_module(agent)

class LocalOctoAgentTests(unittest.TestCase):
    def example(self):
        return {"account_id": 1, "browser": "octo", "profile_id": "example-profile"}

    def test_valid_profile(self):
        self.assertEqual(agent.parse_profile_config(self.example()).profile_id, "example-profile")

    def test_reject_secret_fields(self):
        item = self.example()
        item["password"] = "secret"
        with self.assertRaises(ValueError):
            agent.parse_profile_config(item)

    def test_reject_other_browser(self):
        item = self.example()
        item["browser"] = "dolphin"
        with self.assertRaises(ValueError):
            agent.parse_profile_config(item)

    def test_reject_invalid_account_id(self):
        item = self.example()
        item["account_id"] = True
        with self.assertRaises(ValueError):
            agent.parse_profile_config(item)

    def test_no_balance_claim(self):
        result = agent.status(agent.parse_profile_config(self.example()))
        self.assertFalse(result["balances_available"])
        self.assertFalse(result["browser_connected"])
        self.assertEqual(result["mode"], "read_only")

    def test_local_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "profile.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.example(), handle)
            self.assertEqual(agent.load_profile_config(path).account_id, 1)

if __name__ == "__main__":
    unittest.main()
