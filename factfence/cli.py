"""Command-line interface for factfence.

Exit codes: 0 = clean (no claims, or nothing needing review),
1 = at least one claim needs review, 2 = usage / I/O error.
"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .extract import extract_claims
from .report import render_json, render_terminal, summarize
from .verify import verify_claims


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="factfence",
        description=(
            "Check the numbers in AI-generated prose against their cited sources. "
            "Extracts quantitative claims, fetches each citation, and reports "
            "whether the cited page actually contains the numbers."
        ),
    )
    parser.add_argument("paths", nargs="*", metavar="FILE",
                        help="markdown/text file(s) to check (default: stdin)")
    parser.add_argument("--text", metavar="TEXT",
                        help="check literal text instead of a file")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output (for CI)")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the summary line")
    parser.add_argument("--no-color", action="store_true",
                        help="disable ANSI colors")
    parser.add_argument("--timeout", type=float, default=8.0, metavar="SEC",
                        help="per-URL fetch timeout (default: 8)")
    parser.add_argument("--max-bytes", type=int, default=1_500_000, metavar="N",
                        help="max bytes read per cited page (default: 1500000)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _read_inputs(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.paths == ["-"]:
        return sys.stdin.read()
    if args.paths:
        chunks: list[str] = []
        for path in args.paths:
            try:
                with open(path, encoding="utf-8") as handle:
                    chunks.append(handle.read())
            except OSError as exc:
                print(f"factfence: cannot read {path}: {exc}", file=sys.stderr)
                raise SystemExit(2)
        return "\n".join(chunks)
    if sys.stdin.isatty():
        print("factfence: no input — pass FILE, --text, or pipe text on stdin",
              file=sys.stderr)
        raise SystemExit(2)
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = _read_inputs(args)
    except SystemExit as exc:
        return int(exc.code or 0)

    claims = extract_claims(text)
    results = verify_claims(claims, timeout=args.timeout, max_bytes=args.max_bytes)

    color = not args.no_color and sys.stdout.isatty()
    if args.json:
        print(render_json(results))
    else:
        print(render_terminal(results, color=color, quiet=args.quiet))

    return 0 if summarize(results)["needs_review"] == 0 else 1
