import unittest
from decimal import Decimal
from offline_finance_flow import OfflineFinanceAgent


class OfflineFinanceFlowTests(unittest.TestCase):
    def setUp(self):
        self.agent = OfflineFinanceAgent(101)

    def login(self):
        self.assertTrue(self.agent.enter_test_code(101, 1, "TEST-123456"))

    def test_code_entry_and_balance(self):
        self.login()
        self.assertEqual(self.agent.balance(101, 1).rub, Decimal("1250.00"))
        self.assertEqual(self.agent._accounts[1].code_entries, ["[REDACTED]"])

    def test_wrong_code_blocks_balance(self):
        self.assertFalse(self.agent.enter_test_code(101, 1, "wrong"))
        with self.assertRaises(PermissionError):
            self.agent.balance(101, 1)

    def test_conversion(self):
        self.login()
        balance = self.agent.convert_all_rub(101, 1)
        self.assertEqual(balance, type(balance)(Decimal("0.00"), Decimal("55.00")))

    def test_no_withdrawal_without_confirmation(self):
        self.login()
        self.agent.convert_all_rub(101, 1)
        draft = self.agent.prepare_withdrawal(101, 1, "TEST-WALLET")
        self.assertEqual(self.agent.balance(101, 1).usdt, Decimal("55.00"))
        self.assertEqual(draft["amount"], Decimal("55.00"))

    def test_confirm_once(self):
        self.login()
        self.agent.convert_all_rub(101, 1)
        draft = self.agent.prepare_withdrawal(101, 1, "TEST-WALLET")
        result = self.agent.confirm_withdrawal(101, draft["request_id"])
        self.assertEqual(result["status"], "simulated_only")
        self.assertEqual(self.agent.balance(101, 1).usdt, Decimal("0.00"))
        self.assertEqual(self.agent.confirm_withdrawal(101, draft["request_id"])["status"], "already_completed")

    def test_owner_only(self):
        with self.assertRaises(PermissionError):
            self.agent.enter_test_code(102, 1, "TEST-123456")
        self.login()
        with self.assertRaises(PermissionError):
            self.agent.convert_all_rub(102, 1)

    def test_reject_real_destinations(self):
        self.login()
        with self.assertRaises(ValueError):
            self.agent.prepare_withdrawal(101, 1, "REAL-ADDRESS")

    def test_logout_invalidates_draft(self):
        self.login()
        draft = self.agent.prepare_withdrawal(101, 1, "TEST-WALLET")
        self.agent.logout(101, 1)
        with self.assertRaises(ValueError):
            self.agent.confirm_withdrawal(101, draft["request_id"])

    def test_conversion_requires_login(self):
        with self.assertRaises(PermissionError):
            self.agent.convert_all_rub(101, 1)

    def test_reject_duplicate_pending(self):
        self.login()
        self.agent.prepare_withdrawal(101, 1, "TEST-WALLET")
        with self.assertRaises(PermissionError):
            self.agent.prepare_withdrawal(101, 1, "TEST-WALLET")
        with self.assertRaises(PermissionError):
            self.agent.convert_all_rub(101, 1)


if __name__ == "__main__":
    unittest.main()
