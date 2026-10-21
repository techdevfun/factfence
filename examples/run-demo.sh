#!/usr/bin/env bash
# Reproducible demo: serves the fixture pages locally, then runs factfence
# on a fake AI-generated answer. No outside network traffic.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT=18347
python3 -m http.server "$PORT" --directory examples/fixtures >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
sleep 1

python3 -m factfence --no-color examples/sample-answer.md
