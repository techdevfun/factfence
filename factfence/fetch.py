"""Fetch cited pages and reduce them to searchable plain text."""
from __future__ import annotations

import html as _html
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import __version__

_USER_AGENT = f"factfence/{__version__} (+https://github.com/techdevfun/factfence)"

_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int | None
    text: str  # normalized plain text, "" when not ok
    error: str | None


def html_to_text(page: str) -> str:
    """Strip tags/scripts, unescape entities, collapse whitespace."""
    page = _SCRIPT_STYLE_RE.sub(" ", page)
    page = _TAG_RE.sub(" ", page)
    page = _html.unescape(page)
    return _WS_RE.sub(" ", page).strip()


def normalize_for_match(text: str) -> str:
    """Normalize page text the same way claim numbers are normalized."""
    s = text.lower()
    s = s.replace("percentage", "%").replace("percent", "%")
    s = s.replace("×", "x")
    s = re.sub(r"[\s,]+", "", s)
    return s


def fetch_text(
    url: str,
    timeout: float = 8.0,
    max_bytes: int = 1_500_000,
) -> FetchResult:
    """Fetch *url* and return its normalized plain text (or an error)."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,text/plain,application/json;q=0.9,*/*;q=0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            kind = content_type.split(";")[0].strip().lower()
            if kind not in ("text/html", "text/plain", "application/json",
                             "application/xml", "text/xml", ""):
                return FetchResult(url, False, status, "",
                                   f"unsupported content type: {kind or 'unknown'}")
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raw = raw[:max_bytes]
            charset = response.headers.get_content_charset() or "utf-8"
            page = raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        return FetchResult(url, False, exc.code, "", f"HTTP {exc.code}")
    except urllib.error.URLError as exc:
        reason = getattr(exc.reason, "strerror", None) or str(exc.reason)
        return FetchResult(url, False, None, "", f"unreachable: {reason}"[:160])
    except (TimeoutError, ValueError, OSError) as exc:
        return FetchResult(url, False, None, "", f"fetch failed: {exc}"[:160])

    text = html_to_text(page) if "html" in kind or kind == "" else page
    return FetchResult(url, True, status, normalize_for_match(text), None)
