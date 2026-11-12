"""Offline checks for authenticated balance report storage."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app.py"


class AgentBalanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with patch.dict(os.environ, {"DEMO_DB_PATH": str(Path(self.tmp.name) / "bot.sqlite3"),
                                  "TELEGRAM_OWNER_ID": "123", "DEMO_SEED_ENABLED": "false"}):
            spec = importlib.util.spec_from_file_location("whitebird_agent_bot_test", APP)
            self.app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.app)
        with self.app.db() as connection:
            connection.execute("INSERT INTO accounts(name) VALUES (?)", ("Account 01",))

    def test_store_observations(self):
        count = self.app.store_agent_balances({"balances": [
            {"account": "Account 01", "RUB.wb": "10.50", "USDT": "2.00"}]})
        self.assertEqual(count, 1)
        with self.app.db() as connection:
            row = connection.execute("SELECT rub,usdt FROM agent_balances WHERE account_name=?", ("Account 01",)).fetchone()
        self.assertEqual(row, ("10.50", "2.00"))

    def test_unknown_account_rejected(self):
        with self.assertRaises(ValueError):
            self.app.store_agent_balances({"balances": [
                {"account": "Not known", "RUB.wb": "1", "USDT": "2"}]})

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            self.app.store_agent_balances({"balances": [
                {"account": "Account 01", "RUB.wb": "-1", "USDT": "2"}]})

    def test_duplicate_rejected(self):
        row = {"account": "Account 01", "RUB.wb": "1", "USDT": "2"}
        with self.assertRaises(ValueError):
            self.app.store_agent_balances({"balances": [row, row]})


if __name__ == "__main__":
    unittest.main()
