"""End-to-end HTTP tests for the agent's read-only balance endpoint.

Starts a temporary server bound only to 127.0.0.1; no internet, no Telegram calls.
"""
import importlib.util
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app.py"
SECRET = "test-only-secret-" + "x" * 48


class BridgeHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {"DEMO_DB_PATH": str(Path(self.tmp.name) / "test.sqlite3"),
               "TELEGRAM_OWNER_ID": "123", "AGENT_REPORT_SECRET": SECRET,
               "DEMO_SEED_ENABLED": "false"}
        with patch.dict(os.environ, env):
            spec = importlib.util.spec_from_file_location("whitebird_bridge_http", APP)
            self.app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.app)
        with self.app.db() as connection:
            connection.execute("INSERT INTO accounts(name) VALUES (?)", ("Account 01",))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = "http://127.0.0.1:%d/agent/balances" % self.server.server_port

    def post(self, payload, secret=None):
        request = Request(self.url, data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json",
                                   "X-WhiteBird-Agent-Secret": secret or ""},
                          method="POST")
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    def test_valid_authenticated_report(self):
        status, result = self.post({"balances": [
            {"account": "Account 01", "RUB.wb": "12.34", "USDT": "5.00"}]}, SECRET)
        self.assertEqual(status, 200)
        self.assertEqual(result["stored"], 1)
        with self.app.db() as connection:
            self.assertEqual(connection.execute(
                "SELECT rub,usdt FROM agent_balances WHERE account_name='Account 01'"
            ).fetchone(), ("12.34", "5.00"))

    def test_missing_secret_is_forbidden(self):
        status, _ = self.post({"balances": []})
        self.assertEqual(status, 403)

    def test_wrong_secret_is_forbidden(self):
        status, _ = self.post({"balances": []}, "wrong")
        self.assertEqual(status, 403)

    def test_invalid_report_is_rejected_without_storage(self):
        status, _ = self.post({"balances": [
            {"account": "Account 01", "RUB.wb": "-10", "USDT": "1"}]}, SECRET)
        self.assertEqual(status, 400)
        with self.app.db() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM agent_balances").fetchone()[0], 0)

    def test_telegram_webhook_is_not_agent_endpoint(self):
        request = Request("http://127.0.0.1:%d/telegram" % self.server.server_port,
                          data=b"{}", headers={"X-WhiteBird-Agent-Secret": SECRET}, method="POST")
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=3)
        self.assertEqual(caught.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
