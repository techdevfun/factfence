"""Extract checkable claims and their citations from prose.

A *claim* is a sentence that states something verifiable:

- ``statistic`` — the sentence carries at least one strong number
  (percentage, money amount, large count, multiplier, ratio).
- ``assertion`` — the sentence leans on an external source
  ("studies show ...", "according to ...") but states no hard number.

Fenced code blocks and inline code are stripped first, so ``x = 42``
inside an example never becomes a "claim". Headings, tables and
non-English text are out of scope — this is a heuristic helper for a
human reviewer, not a fact-checking oracle.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Citation:
    url: str
    kind: str  # inline | reference | footnote | bare


@dataclass
class Claim:
    text: str
    kind: str  # statistic | assertion
    numbers: list[str] = field(default_factory=list)  # normalized signature numbers
    raw_numbers: list[str] = field(default_factory=list)  # as written in the text
    citations: list[Citation] = field(default_factory=list)
    named_source: str | None = None


_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

_INLINE_LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*(https?://[^)\s]+)\s*\)")
_REF_LINK_RE = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")
_REF_DEF_RE = re.compile(r"(?m)^\[([^\]]+)\]:\s*(https?://\S+)\s*$")
_FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]]+)\]")
_FOOTNOTE_DEF_RE = re.compile(r"(?m)^\[\^([^\]]+)\]:\s*(https?://\S+)\s*$")
_BARE_URL_RE = re.compile(r"https?://[^\s\)\]>\"']+")

_NAMED_SOURCE_RE = re.compile(
    r"(?:according to|per)\s+([A-Z][\w&.'\- ]{1,60}?)(?=[,.;:!?]|$)"
    r"|([A-Z][\w&.'\- ]{1,40}?)\s+"
    r"(?:reports?|reported|says|said|finds?|found|shows?|showed|claims?|claimed|"
    r"estimates?|estimated|puts?|reveals?|revealed)",
    re.IGNORECASE,
)

# (kind, pattern). "year" is weak on purpose: a bare year is not a claim,
# it only rides along once a strong number is present.
_NUMBER_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("percent", re.compile(r"\d[\d,]*(?:\.\d+)?\s?(?:%|percent(?:age)?\b)", re.IGNORECASE)),
    ("money", re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion|thousand|[mbk]))?\b", re.IGNORECASE)),
    ("big", re.compile(r"\d[\d,]*(?:\.\d+)?\s?(?:million|billion|thousand)\b", re.IGNORECASE)),
    ("mult", re.compile(r"\d(?:\.\d+)?\s?[x×]\b|\d+(?:\.\d+)?-fold\b", re.IGNORECASE)),
    ("ratio", re.compile(r"\d[\d,]*\s?(?:out of|/)\s?\d[\d,]*")),
    ("year", re.compile(r"\b(?:19|20)\d{2}\b")),
]
_STRONG_KINDS = {"percent", "money", "big", "mult", "ratio"}

_ASSERTION_RE = re.compile(
    r"\b(study|studies|research|report|reports|survey|analysis|paper|papers)\b"
    r".{0,40}?\b(show|shows|find|finds|found|say|says|indicate|indicates|"
    r"claim|claims|suggest|suggests)\b",
    re.IGNORECASE,
)


def strip_code(text: str) -> str:
    """Remove fenced code blocks and inline code spans."""
    text = _CODE_FENCE_RE.sub(" ", text)
    return _INLINE_CODE_RE.sub(" ", text)


def split_sentences(text: str) -> list[str]:
    """Split prose into rough sentences (heuristic, English-focused).

    Blank lines separate paragraphs; single newlines inside a paragraph
    are treated as soft wraps (so a citation on the next line still
    belongs to its sentence).
    """
    sentences: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        lines: list[str] = []
        for raw in paragraph.splitlines():
            line = raw.strip()
            # drop list markers / blockquote markers, keep the content
            line = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+|>\s*)+", "", line).strip()
            if line:
                lines.append(line)
        joined = " ".join(lines)
        if not joined:
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", joined)
        sentences.extend(p.strip() for p in parts if p.strip())
    return sentences


def _clean_url(url: str) -> str:
    return url.rstrip(".,;:!?\"'*)")


def _find_citations(sentence: str, ref_defs: dict[str, str]) -> list[Citation]:
    found: list[Citation] = []
    seen: set[str] = set()

    def add(url: str, kind: str) -> None:
        url = _clean_url(url)
        if url and url not in seen:
            seen.add(url)
            found.append(Citation(url=url, kind=kind))

    for match in _INLINE_LINK_RE.finditer(sentence):
        add(match.group(2), "inline")
    for match in _REF_LINK_RE.finditer(sentence):
        key = match.group(2) or match.group(1)
        if key in ref_defs:
            add(ref_defs[key], "reference")
    for match in _FOOTNOTE_REF_RE.finditer(sentence):
        if match.group(1) in ref_defs:
            add(ref_defs[match.group(1)], "footnote")
    for match in _BARE_URL_RE.finditer(sentence):
        add(match.group(0), "bare")
    return found


def _find_numbers(sentence: str) -> list[str]:
    """Return the strong raw numbers in a sentence (years don't count)."""
    strong: list[str] = []
    spans: list[tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        return any(start < e and end > s for s, e in spans)

    for kind, pattern in _NUMBER_PATTERNS:
        for match in pattern.finditer(sentence):
            if overlaps(match.start(), match.end()):
                continue
            spans.append((match.start(), match.end()))
            if kind in _STRONG_KINDS:
                strong.append(match.group(0).strip())
    return strong


def normalize_number(raw: str) -> str:
    """Normalize a number string so prose and page text compare equal."""
    s = raw.lower()
    s = s.replace("percentage", "%").replace("percent", "%")
    s = s.replace("×", "x")
    s = re.sub(r"[\s,]+", "", s)
    return s


def _named_source(sentence: str) -> str | None:
    match = _NAMED_SOURCE_RE.search(sentence)
    if not match:
        return None
    return (match.group(1) or match.group(2) or "").strip() or None


def extract_claims(text: str) -> list[Claim]:
    """Extract claims from markdown/plain text, in document order."""
    clean = strip_code(text)

    ref_defs: dict[str, str] = {}
    for match in _REF_DEF_RE.finditer(clean):
        ref_defs[match.group(1)] = _clean_url(match.group(2))
    for match in _FOOTNOTE_DEF_RE.finditer(clean):
        ref_defs[match.group(1)] = _clean_url(match.group(2))

    claims: list[Claim] = []
    for sentence in split_sentences(clean):
        # reference-definition lines are bookkeeping, not claims
        if _REF_DEF_RE.match(sentence) or _FOOTNOTE_DEF_RE.match(sentence):
            continue
        strong = _find_numbers(sentence)
        citations = _find_citations(sentence, ref_defs)
        named = _named_source(sentence)

        if strong:
            claims.append(
                Claim(
                    text=sentence,
                    kind="statistic",
                    numbers=[normalize_number(n) for n in strong],
                    raw_numbers=strong,
                    citations=citations,
                    named_source=named,
                )
            )
        elif _ASSERTION_RE.search(sentence) or named:
            claims.append(
                Claim(
                    text=sentence,
                    kind="assertion",
                    citations=citations,
                    named_source=named,
                )
            )
    return claims
