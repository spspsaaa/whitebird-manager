import unittest
from command_login_demo import CommandLoginDemo, FakeBrowser


class CommandLoginDemoTests(unittest.TestCase):
    def setUp(self):
        self.browser = FakeBrowser()
        self.demo = CommandLoginDemo(owner_id=101, browser=self.browser)

    def test_no_automatic_login(self):
        self.assertEqual(self.browser.events, [])
        self.assertEqual(self.demo.complete_login(101, 1, "TEST-123456").status, "not_requested")
        self.assertEqual(self.browser.events, [])

    def test_owner_command_allows_one_test_login_and_balance(self):
        self.assertEqual(self.demo.request_login(101, 1).status, "awaiting_test_code")
        result = self.demo.complete_login(101, 1, "TEST-123456")
        self.assertEqual((result.status, result.rub, result.usdt), ("balance_read", "1250.00", "42.50"))
        self.assertEqual(self.browser.events, [("open", 1), ("close", 1)])
        self.assertEqual(self.browser.opened, set())

    def test_invalid_code_closes_profile(self):
        self.demo.request_login(101, 2)
        self.assertEqual(self.demo.complete_login(101, 2, "wrong").status, "login_failed")
        self.assertEqual(self.browser.opened, set())

    def test_login_is_single_use(self):
        self.demo.request_login(101, 1)
        self.demo.complete_login(101, 1, "TEST-123456")
        self.assertEqual(self.demo.complete_login(101, 1, "TEST-123456").status, "not_requested")
        self.assertEqual(len(self.browser.events), 2)

    def test_duplicate_request(self):
        self.demo.request_login(101, 1)
        self.assertEqual(self.demo.request_login(101, 1).status, "already_pending")

    def test_other_user_cannot_request_or_complete(self):
        with self.assertRaises(PermissionError):
            self.demo.request_login(102, 1)
        self.demo.request_login(101, 1)
        with self.assertRaises(PermissionError):
            self.demo.complete_login(102, 1, "TEST-123456")
        self.assertEqual(self.browser.events, [])

    def test_withdrawals_are_disabled(self):
        with self.assertRaises(PermissionError):
            self.demo.withdraw(101, 1)

    def test_reject_invalid_ids(self):
        for account_id in (0, -1, True, "1"):
            with self.assertRaises(ValueError):
                self.demo.request_login(101, account_id)

    def test_provider_exception_closes_profile(self):
        class BrokenProvider:
            def login(self, account_id, code):
                raise RuntimeError("simulated outage")
        self.demo.provider = BrokenProvider()
        self.demo.request_login(101, 1)
        with self.assertRaises(RuntimeError):
            self.demo.complete_login(101, 1, "TEST-123456")
        self.assertEqual(self.browser.opened, set())


if __name__ == "__main__":
    unittest.main()
