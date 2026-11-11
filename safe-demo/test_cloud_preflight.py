import unittest
from cloud_preflight import _memory_gib, assess


class PreflightTests(unittest.TestCase):
    def test_parses_linux_memory(self):
        self.assertEqual(_memory_gib("MemTotal:       8388608 kB\n"), 8.0)

    def test_missing_memory(self):
        self.assertIsNone(_memory_gib("Other: 1\n"))

    def test_ready(self):
        result = assess("Linux", 8, 40, 2, True)
        self.assertTrue(result["ready_for_manual_browser_trial"])

    def test_no_display(self):
        result = assess("Linux", 16, 80, 4, False)
        self.assertFalse(result["ready_for_manual_browser_trial"])

    def test_low_memory(self):
        result = assess("Linux", 1, 80, 4, True)
        self.assertFalse(result["ready_for_manual_browser_trial"])


if __name__ == "__main__":
    unittest.main()
