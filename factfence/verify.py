"""Turn claims into verdicts by checking citations.

Verdicts:

- SUPPORTED   — a cited page was fetched and contains at least one of the
                claim's signature numbers.
- CITED       — an assertion (no hard numbers) with at least one working
                citation; there is nothing numeric to cross-check.
- UNVERIFIED  — cited page(s) fetched fine, but none contains the numbers.
- BROKEN      — every cited URL failed to fetch.
- UNCITED     — a checkable claim with no citation at all.

This is deliberately shallow: it checks *whether the numbers appear in
the cited source*, not whether the source itself is right. A SUPPORTED
claim can still be wrong — the point is to catch the common AI failure
mode of confident numbers with dead, irrelevant, or missing citations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .extract import Claim, normalize_number
from .fetch import FetchResult, fetch_text


@dataclass
class UrlCheck:
    url: str
    ok: bool
    status: int | None
    matched: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ClaimResult:
    claim: Claim
    verdict: str
    detail: str
    checks: list[UrlCheck] = field(default_factory=list)


def _page_supports(page_text: str, numbers: list[str]) -> list[str]:
    # Claim numbers are stored normalized (no spaces or commas, lowercase,
    # "42%" not "42 percent") while fetched page text is raw. Normalize
    # the page the same way, or a page that says "$10 million" would never
    # match the "$10million" signature — a false UNVERIFIED.
    norm_page = normalize_number(page_text)
    return [n for n in numbers if n and n in norm_page]


def verify_claim(
    claim: Claim,
    fetch_one: Callable[[str], FetchResult],
) -> ClaimResult:
    checks: list[UrlCheck] = []
    for citation in claim.citations:
        result = fetch_one(citation.url)
        matched: list[str] = []
        if result.ok and claim.kind == "statistic":
            matched = _page_supports(result.text, claim.numbers)
        checks.append(
            UrlCheck(
                url=citation.url,
                ok=result.ok,
                status=result.status,
                matched=matched,
                error=result.error,
            )
        )

    if not checks:
        if claim.kind == "statistic":
            return ClaimResult(claim, "UNCITED",
                               "quantitative claim with no citation — verify by hand")
        return ClaimResult(claim, "UNCITED",
                           "assertion names no resolvable source — verify by hand")

    working = [c for c in checks if c.ok]
    if not working:
        first_error = checks[0].error or "fetch failed"
        return ClaimResult(claim, "BROKEN",
                           f"all {len(checks)} citation(s) failed: {first_error}", checks)

    if claim.kind == "assertion":
        return ClaimResult(claim, "CITED",
                           f"{len(working)} citation(s) resolve; nothing numeric to cross-check",
                           checks)

    supported = [c for c in working if c.matched]
    if supported:
        nums = sorted({n for c in supported for n in c.matched})
        return ClaimResult(
            claim, "SUPPORTED",
            f"cited page contains {', '.join(nums)}", checks)

    return ClaimResult(
        claim, "UNVERIFIED",
        "cited page(s) fetched but contain none of the claim's numbers", checks)


def verify_claims(
    claims: list[Claim],
    timeout: float = 8.0,
    max_bytes: int = 1_500_000,
) -> list[ClaimResult]:
    """Verify every claim; fetched pages are cached per run."""
    cache: dict[str, FetchResult] = {}

    def fetch_one(url: str) -> FetchResult:
        if url not in cache:
            cache[url] = fetch_text(url, timeout=timeout, max_bytes=max_bytes)
        return cache[url]

    return [verify_claim(claim, fetch_one) for claim in claims]
