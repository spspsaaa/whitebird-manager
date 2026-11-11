import unittest
from decimal import Decimal
from session_manager import (
    LoginRequired, VerificationRequired, OfflineDemoAdapter, SessionManager,
)


class SessionManagerTests(unittest.TestCase):
    def test_active_session_does_not_login_again(self):
        adapter = OfflineDemoAdapter({1: "25.50"}, {1})
        result = SessionManager(adapter).check_balance(1)
        self.assertEqual(result.balance, Decimal("25.50"))
        self.assertFalse(result.relogged)
        self.assertEqual(adapter.login_attempts, 0)

    def test_expired_session_logs_in(self):
        adapter = OfflineDemoAdapter({1: "25.50"})
        result = SessionManager(adapter).check_balance(1)
        self.assertTrue(result.relogged)
        self.assertEqual(adapter.login_attempts, 1)

    def test_verification_required_stops(self):
        adapter = OfflineDemoAdapter({1: "25.50"}, require_verification=True)
        with self.assertRaises(VerificationRequired):
            SessionManager(adapter).check_balance(1)

    def test_invalid_balance_rejected(self):
        adapter = OfflineDemoAdapter({1: "NaN"}, {1})
        with self.assertRaises(ValueError):
            SessionManager(adapter).check_balance(1)

    def test_invalid_account_rejected(self):
        with self.assertRaises(ValueError):
            SessionManager(OfflineDemoAdapter({})).check_balance(0)


if __name__ == "__main__":
    unittest.main()
