"""Tests for claim + citation extraction (no network)."""

import unittest

from factfence.extract import (
    Claim,
    extract_claims,
    normalize_number,
    split_sentences,
    strip_code,
)


class StripCodeTest(unittest.TestCase):
    def test_fenced_block_removed(self):
        text = "Intro.\n```python\nx = 42\n```\nOutro with 50%."
        stripped = strip_code(text)
        self.assertNotIn("x = 42", stripped)
        self.assertIn("Outro", stripped)

    def test_inline_code_removed(self):
        self.assertNotIn("99", strip_code("Use `retry=99` for 3 tries."))


class SplitSentencesTest(unittest.TestCase):
    def test_basic_split(self):
        sents = split_sentences("First claim with 10%. Second claim with 20%.")
        self.assertEqual(len(sents), 2)

    def test_list_markers_dropped(self):
        sents = split_sentences("- 30% of users agree.\n- 40% disagree.")
        self.assertEqual(len(sents), 2)
        self.assertTrue(all(not s.startswith("-") for s in sents))


class NumberExtractionTest(unittest.TestCase):
    def test_percent_statistic(self):
        claims = extract_claims("Revenue grew 40% last quarter.")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].kind, "statistic")
        self.assertIn("40%", claims[0].numbers)

    def test_money_statistic(self):
        claims = extract_claims("The deal was worth $4.2 million.")
        self.assertEqual(claims[0].kind, "statistic")
        self.assertIn("$4.2million", claims[0].numbers)

    def test_year_alone_is_not_a_claim(self):
        self.assertEqual(extract_claims("We launched in 2024."), [])

    def test_plain_sentence_ignored(self):
        self.assertEqual(extract_claims("The sky is blue and calm."), [])

    def test_assertion_without_numbers(self):
        claims = extract_claims("Studies show developers prefer dark mode.")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].kind, "assertion")

    def test_code_numbers_ignored(self):
        text = "```\nretry = 99\n```\nAll good."
        self.assertEqual(extract_claims(text), [])


class CitationExtractionTest(unittest.TestCase):
    def test_inline_link(self):
        claims = extract_claims("Growth was 25% ([report](https://example.com/r)).")
        self.assertEqual(claims[0].citations[0].url, "https://example.com/r")
        self.assertEqual(claims[0].citations[0].kind, "inline")

    def test_bare_url(self):
        claims = extract_claims("Growth was 25%, see https://example.com/r for details.")
        self.assertEqual(claims[0].citations[0].url, "https://example.com/r")
        self.assertEqual(claims[0].citations[0].kind, "bare")

    def test_reference_link(self):
        text = "Growth was 25% [see][1].\n\n[1]: https://example.com/r"
        claims = extract_claims(text)
        self.assertEqual(claims[0].citations[0].url, "https://example.com/r")
        self.assertEqual(claims[0].citations[0].kind, "reference")

    def test_footnote(self):
        text = "Growth was 25%.[^1]\n\n[^1]: https://example.com/r"
        claims = extract_claims(text)
        self.assertEqual(claims[0].citations[0].url, "https://example.com/r")

    def test_trailing_punctuation_stripped(self):
        claims = extract_claims("See https://example.com/r, it says 25%.")
        self.assertEqual(claims[0].citations[0].url, "https://example.com/r")

    def test_named_source(self):
        claims = extract_claims("According to Acme Research, growth was 25%.")
        self.assertEqual(claims[0].named_source, "Acme Research")


class NormalizeNumberTest(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(normalize_number("12 percent"), "12%")
        self.assertEqual(normalize_number("1,234"), "1234")
        self.assertEqual(normalize_number("$4.2 million"), "$4.2million")
        self.assertEqual(normalize_number("3×"), "3x")


if __name__ == "__main__":
    unittest.main()
