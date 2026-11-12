import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

DIR = Path(__file__).resolve().parents[1] / "windows-agent"
sys.path.insert(0, str(DIR))
spec = importlib.util.spec_from_file_location("whitebird_cli", DIR / "whitebird_agent.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "accounts.json"
        self.path.write_text(json.dumps({"accounts": [
            {"name": "Octo A", "browser": "octo", "profile_id": "p1"},
            {"name": "Dolphin B", "browser": "dolphin", "profile_id": "p2"}
        ]}), encoding="utf-8")

    def test_open_dispatch(self):
        with patch.object(cli, "start_selected", return_value={"status": "start_requested"}) as start:
            self.assertEqual(cli.main(["--inventory", str(self.path), "open", "Octo A"]), 0)
            self.assertEqual(start.call_args.args[1], "Octo A")

    def test_preflight(self):
        self.assertEqual(cli.main(["--inventory", str(self.path), "check"]), 0)

    def test_accounts(self):
        self.assertEqual(cli.main(["--inventory", str(self.path), "accounts"]), 0)

    def test_selection(self):
        self.assertEqual(cli.main(["--inventory", str(self.path), "select", "Dolphin B"]), 0)

    def test_unknown_selection(self):
        self.assertEqual(cli.main(["--inventory", str(self.path), "select", "Missing"]), 1)

    def test_report(self):
        balances = Path(self.tmp.name) / "balances.json"
        balances.write_text(json.dumps({"balances": [{"account": "Octo A", "RUB.wb": "10.25", "USDT": "2.00"}]}), encoding="utf-8")
        self.assertEqual(cli.main(["--inventory", str(self.path), "report", "--balances", str(balances)]), 0)

    def test_report_rejects_unknown_account(self):
        balances = Path(self.tmp.name) / "balances.json"
        balances.write_text(json.dumps({"balances": [{"account": "Unknown", "RUB.wb": "1", "USDT": "1"}]}), encoding="utf-8")
        self.assertEqual(cli.main(["--inventory", str(self.path), "report", "--balances", str(balances)]), 1)

    def test_status(self):
        with patch.object(cli, "build_report", return_value={"mode": "read_only"}):
            self.assertEqual(cli.main(["--inventory", str(self.path), "status"]), 0)


if __name__ == "__main__":
    unittest.main()
