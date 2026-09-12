"""Unit tests for website classification rules."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.website_rules import OTHER_WEB, is_browser, parse_site  # noqa: E402


class WebsiteRulesTests(unittest.TestCase):
    def test_browser_detection(self):
        self.assertTrue(is_browser("chrome.exe"))
        self.assertTrue(is_browser("CHROME.EXE"))
        self.assertFalse(is_browser("code.exe"))

    def test_known_sites(self):
        cases = {
            "Lo-fi beats - YouTube - Google Chrome": "YouTube",
            "Inbox (12) - Gmail - Microsoft Edge": "Gmail",
            "facebook - Google Chrome": "Facebook",
            "GitHub where the world builds software": "GitHub",
            "instagram": "Instagram",
        }
        for title, expected in cases.items():
            self.assertEqual(parse_site(title), expected, title)

    def test_unknown_site(self):
        self.assertEqual(parse_site("Some Random Page - Opera"), OTHER_WEB)
        self.assertEqual(parse_site(""), OTHER_WEB)

    def test_case_insensitive(self):
        self.assertEqual(parse_site("GITHUB.COM"), "GitHub")


if __name__ == "__main__":
    unittest.main()
