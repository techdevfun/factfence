# Contributing to factfence

Thanks for looking. This project stays deliberately small: a CLI you can
read in one sitting, with no dependencies beyond the standard library.

## Ground rules

- **Zero dependencies.** If a feature needs a third-party package, it
  doesn't belong in core. Propose it as a separate tool instead.
- **Heuristics must be testable offline.** Every new extraction or matching
  rule needs a unit test using the local fixture server in `tests/`
  (`tests/_server.py`) — never a live website.
- **Honest verdicts.** The tool reports what it can check, not what it
  wishes were true. Don't add verdicts that imply semantic understanding
  the code doesn't have.

## Workflow

1. Fork and branch from `main`.
2. Add tests first (`python3 -m unittest discover -s tests`).
3. Keep the demo reproducible: `bash examples/run-demo.sh` output must
   match `examples/expected-output.txt` — regenerate the file if your
   change alters the demo, and say so in the PR.
4. Update the README's verdict table / limitations when behavior changes.

## Reporting issues

A good issue includes: the input text (or a minimal excerpt), the verdict
you got, and the verdict you expected. Screenshots of terminal output are
welcome; please don't paste API keys or private URLs.
