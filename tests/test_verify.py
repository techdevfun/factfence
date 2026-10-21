"""Tests for verdict logic (fake fetcher + one local-server integration)."""

import pathlib
import unittest

from _server import start_server
from factfence.extract import extract_claims
from factfence.fetch import FetchResult
from factfence.verify import verify_claim, verify_claims

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def fake_fetch(mapping):
    def fetch_one(url):
        return mapping.get(url, FetchResult(url, False, None, "", "unreachable"))
    return fetch_one


def ok(url, text):
    return FetchResult(url, True, 200, text, None)


class VerdictTest(unittest.TestCase):
    def test_supported(self):
        claims = extract_claims("Growth was 73% (https://a.example/r).")
        result = verify_claim(claims[0], fake_fetch({
            "https://a.example/r": ok("https://a.example/r", "growthwas73%indeed"),
        }))
        self.assertEqual(result.verdict, "SUPPORTED")
        self.assertIn("73%", result.detail)

    def test_unverified(self):
        claims = extract_claims("Growth was 99.9% (https://a.example/r).")
        result = verify_claim(claims[0], fake_fetch({
            "https://a.example/r": ok("https://a.example/r", "nothingrelevant"),
        }))
        self.assertEqual(result.verdict, "UNVERIFIED")

    def test_broken(self):
        claims = extract_claims("Growth was 73% (https://a.example/r).")
        result = verify_claim(claims[0], fake_fetch({}))
        self.assertEqual(result.verdict, "BROKEN")

    def test_uncited_statistic(self):
        claims = extract_claims("Growth was 73% this year.")
        result = verify_claim(claims[0], fake_fetch({}))
        self.assertEqual(result.verdict, "UNCITED")
        self.assertEqual(result.checks, [])

    def test_cited_assertion(self):
        claims = extract_claims("Studies show remote work is rising (https://a.example/r).")
        result = verify_claim(claims[0], fake_fetch({
            "https://a.example/r": ok("https://a.example/r", "whatever"),
        }))
        self.assertEqual(result.verdict, "CITED")

    def test_best_verdict_wins(self):
        claims = extract_claims("Growth was 73% (https://a.example/r and https://b.example/r).")
        result = verify_claim(claims[0], fake_fetch({
            "https://a.example/r": ok("https://a.example/r", "nothing"),
            "https://b.example/r": ok("https://b.example/r", "itwas73%ok"),
        }))
        self.assertEqual(result.verdict, "SUPPORTED")

class IntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.port = start_server(FIXTURES)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_end_to_end_local(self):
        text = (
            "It was 73% (http://127.0.0.1:PORT/source-a.html). "
            "It was 99.9% (http://127.0.0.1:PORT/source-b.html). "
            "It was 11% (http://127.0.0.1:PORT/missing.html). "
            "It was 22% with no source."
        ).replace("PORT", str(self.port))
        claims = extract_claims(text)
        results = verify_claims(claims, timeout=5)
        verdicts = [r.verdict for r in results]
        self.assertEqual(verdicts, ["SUPPORTED", "UNVERIFIED", "BROKEN", "UNCITED"])


if __name__ == "__main__":
    unittest.main()
