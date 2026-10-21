# factfence

Check the numbers in AI-generated prose against their cited sources.

AI assistants now write with total confidence about statistics that were
never true: a plausible percentage, a named report, a link that 404s or —
worse — a link to a real page that never contained that number. Human
reviewers skim past them because each claim *looks* sourced.

`factfence` is a small, zero-dependency CLI that reads a markdown or text
file, pulls out every quantitative claim, fetches each citation, and tells
you whether the cited page actually contains the numbers. It takes about
ten seconds to run and tells you exactly which three sentences deserve
your skepticism.

## Quick start

```bash
# zero dependencies — Python 3.10+ stdlib only
git clone https://github.com/techdevfun/factfence.git
cd factfence

# 1. point it at any AI-generated text
python3 -m factfence draft.md

# 2. read the verdicts (exit code 1 = something needs review)
# 3. pipe it into CI
python3 -m factfence --json draft.md | python3 -m json.tool
```

Or install it as a command:

```bash
pip install .
factfence draft.md
```

## What it does

Given a file like this (a typical AI-drafted paragraph):

```markdown
According to the 2026 State of DevTools Survey, 73% of developers say
AI-generated code needs human review before merging
([survey](http://127.0.0.1:18347/source-a.html)).

Some teams claim 99.9% of AI suggestions are production-ready, citing an
internal study (http://127.0.0.1:18347/source-b.html).

It is often repeated that 60% of all code will be AI-written by 2027,
though nobody cites a source.
```

`factfence` reports (real output from `examples/run-demo.sh`):

```
[✓ SUPPORTED]
  According to the 2026 State of DevTools Survey, 73% of developers say AI-
  generated code needs human review before merging
  ([survey](http://127.0.0.1:18347/source-a.html)).
    ↳ http://127.0.0.1:18347/source-a.html
      HTTP 200, matched 73%
    cited page contains 73%

[? UNVERIFIED]
  Some teams claim 99.9% of AI suggestions are production-ready, citing an
  internal study (http://127.0.0.1:18347/source-b.html).
    ↳ http://127.0.0.1:18347/source-b.html
      HTTP 200
    cited page(s) fetched but contain none of the claim's numbers

[! UNCITED]
  It is often repeated that 60% of all code will be AI-written by 2027,
  though nobody cites a source.
    quantitative claim with no citation — verify by hand

6 claim(s) checked: 2 supported, 1 cited, 1 unverified, 1 broken, 1 uncited. 3 need review.
```

## The five verdicts

| Verdict | Meaning |
|---|---|
| `SUPPORTED` | A cited page loaded and contains the claim's numbers. |
| `CITED` | A source-less assertion ("studies show…") with a working link — nothing numeric to cross-check. |
| `UNVERIFIED` | The cited page loads but doesn't contain the numbers. The classic AI hallucination shape. |
| `BROKEN` | Every cited link failed (404, timeout, DNS). |
| `UNCITED` | A quantitative claim with no citation at all. |

`factfence` deliberately does **not** judge whether a source is *right* —
only whether the numbers appear in it. A `SUPPORTED` claim can still be
wrong; the tool catches the far more common failure of confident numbers
with dead, irrelevant, or missing citations.

## How it works

1. **Extract** — code blocks are stripped, prose is split into sentences,
   and sentences with strong numbers (percentages, money, large counts,
   multipliers, ratios) become *statistic* claims; "studies show…" /
   "according to…" sentences become *assertion* claims. Citations are
   detected as inline links, reference links, footnotes, and bare URLs.
2. **Fetch** — each unique URL is fetched once (8s timeout, 1.5MB cap,
   polite user-agent), reduced to plain text, and normalized the same way
   the claim's numbers are normalized.
3. **Verify** — a claim is `SUPPORTED` if any fetched page contains any of
   its signature numbers. Best verdict wins when several URLs are cited.

Exit codes: `0` clean · `1` something needs review · `2` usage/IO error —
so `factfence --json draft.md` drops straight into CI.

## Honest limitations

- Heuristic sentence splitting; English-focused. Tables, PDFs, and
  non-English prose are out of scope.
- Number matching is textual, not semantic: "a 73% increase" won't match a
  page that says "rose by nearly three quarters".
- Pages behind login walls, JS-rendered apps, and PDFs can't be checked
  (reported as fetch failures, not as verdicts on truth).
- It verifies *citation support*, not truth. Always read the source
  yourself before publishing a number.

## Related work

Existing citation checkers (Citely, CiteProof, academic DOI verifiers)
mostly verify that a *reference exists* — aimed at bibliographies and
legal briefs, usually as paid web services. `factfence` asks the narrower
question for everyday prose: **does the cited page contain the actual
numbers?** — as a free, local, offline-friendly CLI you can run before you
hit publish.

## Roadmap

- [ ] `--offline` mode (report citation presence without fetching)
- [ ] DOI / arXiv identifier resolution
- [ ] Markdown table cell support
- [ ] Optional LLM-free "number paraphrase" matching (73% ≈ "nearly three quarters")

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
