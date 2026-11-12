import importlib.util
import json
import sys
import unittest
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "windows-agent"
sys.path.insert(0, str(DIR))
spec = importlib.util.spec_from_file_location("whitebird_upload", DIR / "agent_upload.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.data = {"balances": [{"account": "A", "RUB.wb": "1.00", "USDT": "2.00"}]}

    def test_reject_http(self):
        with self.assertRaises(ValueError):
            module.upload_observations(self.data, ["A"], url="http://example.com/agent/balances", secret="x"*32)

    def test_reject_short_secret(self):
        with self.assertRaises(ValueError):
            module.upload_observations(self.data, ["A"], url="https://example.com/agent/balances", secret="short")

    def test_payload_contains_only_balances(self):
        def fake_open(request, timeout):
            payload = json.loads(request.data)
            self.assertEqual(list(payload), ["balances"])
            self.assertNotIn("profile_id", str(payload))
            self.assertEqual(timeout, 12)
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, *args): return b'{"ok":true,"stored":1}'
            return Response()
        result = module.upload_observations(self.data, ["A"], url="https://example.com/agent/balances", secret="x"*32, opener=fake_open)
        self.assertEqual(result["uploaded"], 1)


if __name__ == "__main__":
    unittest.main()
