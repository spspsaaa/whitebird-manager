import importlib.util
import json
import sys
import unittest
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "windows-agent"
sys.path.insert(0, str(DIR))
spec = importlib.util.spec_from_file_location("whitebird_launcher", DIR / "browser_launch.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def opener(request, timeout):
            self.calls.append((request, timeout))
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, *args): return b'{"success":true}'
            return Response()
        self.opener = opener

    def test_octo_local_post(self):
        result = launcher.start_profile("octo", "abc-123", opener=self.opener)
        req, timeout = self.calls[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:58888/api/profiles/start")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data)["uuid"], "abc-123")
        self.assertEqual(timeout, 90)
        self.assertEqual(result["status"], "start_requested")

    def test_dolphin_local_get(self):
        launcher.start_profile("dolphin", "12345", opener=self.opener, dolphin_port=3001)
        req, _ = self.calls[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:3001/v1.0/browser_profiles/12345/start?automation=1")
        self.assertEqual(req.get_method(), "GET")

    def test_invalid_id_does_not_call_api(self):
        for profile_id in ("../secret", "x/y", "", "a?b"):
            with self.subTest(profile_id=profile_id), self.assertRaises(ValueError):
                launcher.start_profile("octo", profile_id, opener=self.opener)
        self.assertFalse(self.calls)

    def test_selected_profile(self):
        data = {"accounts": [{"name": "Account 01", "browser": "octo", "profile_id": "p-1"}]}
        result = launcher.start_selected(data, "Account 01", opener=self.opener)
        self.assertEqual(result["profile_id"], "p-1")


if __name__ == "__main__":
    unittest.main()
