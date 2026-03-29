#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="${LIVE:-0}"

cd "$ROOT_DIR"

echo "[1/2] Running unit tests"
python3 -m unittest discover -s tests -p 'test_*.py'

if [[ "$LIVE" == "1" ]]; then
  echo "[2/2] Running live ranking smoke test"
  python3 main.py --live
else
  echo "[2/2] Running dry-run smoke test"
  python3 main.py --dry-run
fi
