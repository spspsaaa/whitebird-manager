import unittest
from local_balance_window import make_observation, parse_amount


class ManualBalanceTests(unittest.TestCase):
    def test_decimal_comma(self):
        self.assertEqual(parse_amount("12,50"), "12.50")

    def test_hidden_has_no_amount(self):
        result = make_observation("Octo test", "balance_hidden", "", "")
        self.assertNotIn("rub", result)

    def test_login_required_has_no_amount(self):
        result = make_observation("Octo test", "login_required", "", "")
        self.assertNotIn("usdt", result)

    def test_visible_has_values(self):
        result = make_observation("Octo test", "authorized", "100.50", "2")
        self.assertEqual(result["rub"], "100.50")

    def test_rejects_invalid_amount(self):
        with self.assertRaises(ValueError):
            make_observation("Octo test", "authorized", "-1", "0")


if __name__ == "__main__":
    unittest.main()
