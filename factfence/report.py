"""Render verification results for humans (terminal) and machines (JSON)."""
from __future__ import annotations

import json
import textwrap

from .verify import ClaimResult

_BADGES = {
    "SUPPORTED": ("✓", "32"),   # green
    "CITED": ("~", "36"),       # cyan
    "UNVERIFIED": ("?", "33"),  # yellow
    "BROKEN": ("✗", "31"),      # red
    "UNCITED": ("!", "35"),     # magenta
}

_ORDER = ["SUPPORTED", "CITED", "UNVERIFIED", "BROKEN", "UNCITED"]


def summarize(results: list[ClaimResult]) -> dict:
    counts = {v: 0 for v in _ORDER}
    for result in results:
        counts[result.verdict] += 1
    needs_review = counts["UNVERIFIED"] + counts["BROKEN"] + counts["UNCITED"]
    return {
        "total": len(results),
        "counts": counts,
        "needs_review": needs_review,
    }


def _badge(verdict: str, color: bool) -> str:
    symbol, code = _BADGES[verdict]
    label = f"[{symbol} {verdict}]"
    return f"\033[{code}m{label}\033[0m" if color else label


def render_terminal(
    results: list[ClaimResult],
    color: bool = True,
    quiet: bool = False,
) -> str:
    lines: list[str] = []
    summary = summarize(results)

    if not results:
        return "No checkable claims found — nothing to verify."

    if not quiet:
        for result in results:
            lines.append(_badge(result.verdict, color))
            wrapped = textwrap.wrap(result.claim.text, width=76,
                                    initial_indent="  ", subsequent_indent="  ")
            lines.extend(wrapped or ["  (empty)"])
            for check in result.checks:
                if check.ok:
                    status = f"HTTP {check.status}"
                    extra = f", matched {', '.join(check.matched)}" if check.matched else ""
                else:
                    status = check.error or "failed"
                    extra = ""
                lines.append(f"    ↳ {check.url}")
                lines.append(f"      {status}{extra}")
            if result.claim.named_source and not result.checks:
                lines.append(f"    named source: {result.claim.named_source} (no URL to check)")
            lines.append(f"    {result.detail}")
            lines.append("")

    counts = summary["counts"]
    parts = [f"{counts[v]} {v.lower()}" for v in _ORDER if counts[v]]
    lines.append(
        f"{summary['total']} claim(s) checked: "
        f"{', '.join(parts) if parts else 'none'}. "
        f"{summary['needs_review']} need{say(summary['needs_review'])} review."
    )
    return "\n".join(lines).rstrip()


def say(n: int) -> str:
    return "s" if n == 1 else ""


def render_json(results: list[ClaimResult]) -> str:
    summary = summarize(results)
    payload = {
        "summary": {
            "total": summary["total"],
            "counts": summary["counts"],
            "needs_review": summary["needs_review"],
        },
        "claims": [
            {
                "text": r.claim.text,
                "kind": r.claim.kind,
                "numbers": r.claim.raw_numbers,
                "named_source": r.claim.named_source,
                "verdict": r.verdict,
                "detail": r.detail,
                "citations": [
                    {
                        "url": c.url,
                        "ok": c.ok,
                        "status": c.status,
                        "matched_numbers": c.matched,
                        "error": c.error,
                    }
                    for c in r.checks
                ],
            }
            for r in results
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
