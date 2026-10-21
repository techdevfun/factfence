"""Tests for page fetching (local server only, no outside traffic)."""

import pathlib
import unittest

from _server import start_server
from factfence.fetch import fetch_text, html_to_text, normalize_for_match

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class HtmlToTextTest(unittest.TestCase):
    def test_strips_tags_and_scripts(self):
        page = "<html><head><style>.x{}</style></head><body><p>Hello <b>42%</b></p><script>evil()</script></body></html>"
        self.assertEqual(html_to_text(page), "Hello 42%")

    def test_unescapes_entities(self):
        self.assertEqual(html_to_text("<p>A &amp; B</p>"), "A & B")


class NormalizeForMatchTest(unittest.TestCase):
    def test_matches_number_variants(self):
        page = normalize_for_match("The cost was $4.2 million (12 percent).")
        self.assertIn("$4.2million", page)
        self.assertIn("12%", page)


class FetchTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.port = start_server(FIXTURES)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def url(self, name):
        return f"http://127.0.0.1:{self.port}/{name}"

    def test_ok_page(self):
        result = fetch_text(self.url("source-a.html"))
        self.assertTrue(result.ok)
        self.assertEqual(result.status, 200)
        self.assertIn("73%", result.text)

    def test_404(self):
        result = fetch_text(self.url("missing.html"))
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 404)
        self.assertIn("404", result.error)

    def test_unreachable_host(self):
        result = fetch_text("http://127.0.0.1:1/nope", timeout=2)
        self.assertFalse(result.ok)
        self.assertIsNone(result.status)


if __name__ == "__main__":
    unittest.main()
