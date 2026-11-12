import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "windows-agent" / "balance_import.py"
spec = importlib.util.spec_from_file_location("whitebird_balance_import", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BalanceImportTests(unittest.TestCase):
    def test_precise_totals(self):
        data = {"balances": [
            {"account": "A", "RUB.wb": "0.10", "USDT": "2.5"},
            {"account": "B", "RUB.wb": "0.20", "USDT": "0.5"}]}
        report = module.validate_balances(data, ["A", "B"])
        self.assertEqual(report["totals"]["RUB.wb"], "0.30")
        self.assertEqual(report["totals"]["USDT"], "3.0")

    def test_reject_duplicate(self):
        row = {"account": "A", "RUB.wb": "1", "USDT": "1"}
        with self.assertRaises(ValueError):
            module.validate_balances({"balances": [row, row]}, ["A"])

    def test_reject_exponent_and_negative(self):
        for value in ("-1", "1e8", "NaN", "1,50", "9999999999999"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.validate_balances(
                    {"balances": [{"account": "A", "RUB.wb": value, "USDT": "1"}]}, ["A"])

    def test_unknown_account(self):
        with self.assertRaises(ValueError):
            module.validate_balances(
                {"balances": [{"account": "X", "RUB.wb": "1", "USDT": "1"}]}, ["A"])


if __name__ == "__main__":
    unittest.main()
