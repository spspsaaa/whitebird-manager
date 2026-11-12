"""Offline regression tests: no Telegram, browser, or financial API calls."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app.py"


class BotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = {
            "DEMO_DB_PATH": str(Path(self.temp.name) / "test.sqlite3"),
            "TELEGRAM_OWNER_ID": "123456789",
            "TELEGRAM_BOT_TOKEN": "",
            "TELEGRAM_WEBHOOK_SECRET": "",
            "DEMO_SEED_ENABLED": "false",
            "DOLPHIN_ACCOUNT_IDS": "",
        }
        with patch.dict(os.environ, env):
            spec = importlib.util.spec_from_file_location("whitebird_test_app", APP)
            self.app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.app)
        self.messages = []
        self.app.telegram_api = self.fake_telegram_api

    def fake_telegram_api(self, method, payload):
        self.messages.append((method, payload))
        if method == "getChat":
            return {}
        if method == "sendMessage":
            return {"message_id": len(self.messages)}
        return True

    def add_account(self, name="Test account"):
        with self.app.db() as connection:
            return connection.execute("INSERT INTO accounts(name) VALUES (?)", (name,)).lastrowid

    def send(self, text):
        self.app._dispatch_update({
            "message": {"from": {"id": 123456789}, "chat": {"id": 123456789}, "text": text}
        })

    def test_dolphin_max_four_profiles(self):
        ids = [self.add_account(str(i)) for i in range(5)]
        for i in ids[:4]:
            self.app.bind_profile(i, "dolphin", "profile-" + str(i))
        with self.assertRaises(ValueError):
            self.app.bind_profile(ids[4], "dolphin", "profile-" + str(ids[4]))

    def test_duplicate_profile_rejected(self):
        a, b = self.add_account("A"), self.add_account("B")
        self.app.bind_profile(a, "octo", "same")
        with self.assertRaises(self.app.sqlite3.IntegrityError):
            self.app.bind_profile(b, "octo", "same")

    def test_draft_decimal_and_preview(self):
        account = self.add_account()
        chat = 123456789
        self.app.STATES[chat] = ("draft_amount:USDT", account)
        self.send("0,5")
        self.assertTrue(self.app.STATES[chat][0].startswith("draft_recipient:USDT:0.5"))
        self.send("Recipient label")
        self.assertNotIn(chat, self.app.STATES)
        previews = [payload["text"] for method, payload in self.messages if method == "sendMessage"]
        self.assertTrue(any("0.5" in p and "Recipient label" in p and chr(10) in p for p in previews))
        self.assertFalse(any("transfer" in method.lower() for method, _ in self.messages))

    def test_invalid_amount_rejected(self):
        account = self.add_account()
        chat = 123456789
        self.app.STATES[chat] = ("draft_amount:USDT", account)
        self.send("-1")
        self.assertEqual(self.app.STATES[chat], ("draft_amount:USDT", account))
        self.assertTrue(self.messages)

    def test_non_owner_ignored(self):
        self.app._dispatch_update({
            "message": {"from": {"id": 999}, "chat": {"id": 999}, "text": "/start"}
        })
        self.assertEqual(self.messages, [])


    def test_profile_change_requires_migration(self):
        account = self.add_account()
        self.app.bind_profile(account, "octo", "profile-1")
        with self.assertRaises(ValueError):
            self.app.bind_profile(account, "dolphin", "profile-2")

    def test_unknown_account_profile_rejected(self):
        with self.assertRaises(ValueError):
            self.app.bind_profile(99999, "octo", "not-real")

    def test_empty_and_oversized_profile_id_rejected(self):
        account = self.add_account()
        for profile_id in ("", " ", "x" * 121):
            with self.subTest(profile_id_length=len(profile_id)):
                with self.assertRaises(ValueError):
                    self.app.bind_profile(account, "octo", profile_id)

    def test_update_idempotency(self):
        update = {
            "update_id": 100,
            "message": {"from": {"id": 123456789}, "chat": {"id": 123456789}, "text": "/start"},
        }
        self.app.handle_update(update)
        count = len(self.messages)
        self.app.handle_update(update)
        self.assertEqual(len(self.messages), count)

    def test_no_secret_required_for_offline_draft(self):
        account = self.add_account()
        chat = 123456789
        self.app.STATES[chat] = ("draft_amount:RUB.wb", account)
        self.send("100")
        self.send("Saved recipient label")
        all_messages = " ".join(str(item) for item in self.messages)
        self.assertIn("Saved recipient label", all_messages)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", all_messages)

if __name__ == "__main__":
    unittest.main()
