import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

DIR = Path(__file__).resolve().parents[1] / "windows-agent"
sys.path.insert(0, str(DIR))
spec = importlib.util.spec_from_file_location("whitebird_unified", DIR / "unified_status.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class UnifiedStatusTests(unittest.TestCase):
    def test_local_only_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "accounts.json"
            file.write_text('{"accounts":[{"name":"One","browser":"octo","profile_id":"id-1"}]}', encoding="utf-8")
            with patch.object(module, "octo_port_status", return_value="reachable"):
                result = module.build_report(file)
        self.assertEqual(result["inventory"]["octo"], 1)
        self.assertEqual(result["octo_local_api"], "reachable")
        self.assertEqual(result["dolphin_local_api"], "not_configured")
        self.assertNotIn("id-1", str(result))

    def test_skip_network_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "accounts.json"
            file.write_text('{"accounts":[]}', encoding="utf-8")
            with patch.object(module, "octo_port_status", side_effect=AssertionError("must not call")):
                result = module.build_report(file, check_port=False)
        self.assertEqual(result["octo_local_api"], "not_checked")


if __name__ == "__main__":
    unittest.main()
