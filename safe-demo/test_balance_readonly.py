"""Offline tests for the read-only balance boundary."""
import importlib.util
import os
import unittest
from datetime import datetime, timezone

spec = importlib.util.spec_from_file_location("balance_readonly", os.path.join(os.path.dirname(__file__), "balance_readonly.py"))
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class ReadOnlyTests(unittest.TestCase):
    def payload(self):
        return {"account_id": 1, "rub": "125.25", "usdt": "8.75", "observed_at": datetime.now(timezone.utc).isoformat(), "source": "approved_read_only_provider"}

    def test_valid(self):
        self.assertEqual(str(module.validate_snapshot(1, self.payload()).usdt), "8.75")

    def test_reject_wrong_account(self):
        with self.assertRaises(ValueError):
            module.validate_snapshot(2, self.payload())

    def test_reject_negative(self):
        p = self.payload()
        p["usdt"] = "-1"
        with self.assertRaises(ValueError):
            module.validate_snapshot(1, p)

    def test_reject_unapproved_source(self):
        p = self.payload()
        p["source"] = "browser_scrape"
        with self.assertRaises(ValueError):
            module.validate_snapshot(1, p)

    def test_unconfigured_provider_is_unavailable(self):
        with self.assertRaises(module.BalanceUnavailable):
            module.ReadOnlyBalanceProvider().fetch(1)

if __name__ == "__main__":
    unittest.main()
