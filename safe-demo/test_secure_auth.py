"""Offline tests for secure_auth. No credentials or network access."""
import os
import tempfile
import unittest
from secure_auth import ApprovalStore, WithdrawalIntent


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "approvals.db")
        self.store = ApprovalStore(self.path, owner_id=42)
        self.intent = WithdrawalIntent(1, "USDT", "10.00", "TESTNET", "TEST-DESTINATION", "0.50")

    def tearDown(self):
        self.temp.cleanup()

    def test_one_time_across_restart(self):
        ticket = self.store.prepare(42, self.intent)
        restarted = ApprovalStore(self.path, owner_id=42)
        self.assertTrue(restarted.consume(42, ticket, self.intent))
        self.assertFalse(self.store.consume(42, ticket, self.intent))

    def test_changed_destination_rejected(self):
        ticket = self.store.prepare(42, self.intent)
        changed = WithdrawalIntent(1, "USDT", "10.00", "TESTNET", "TEST-OTHER", "0.50")
        self.assertFalse(self.store.consume(42, ticket, changed))
        self.assertTrue(self.store.consume(42, ticket, self.intent))

    def test_changed_amount_rejected(self):
        ticket = self.store.prepare(42, self.intent)
        changed = WithdrawalIntent(1, "USDT", "11.00", "TESTNET", "TEST-DESTINATION", "0.50")
        self.assertFalse(self.store.consume(42, ticket, changed))

    def test_non_owner_rejected(self):
        with self.assertRaises(PermissionError):
            self.store.prepare(99, self.intent)

    def test_invalid_amount_rejected(self):
        with self.assertRaises(ValueError):
            WithdrawalIntent(1, "USDT", "NaN", "TESTNET", "TEST-DESTINATION", "0").canonical()


if __name__ == "__main__":
    unittest.main()
