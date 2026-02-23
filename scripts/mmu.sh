#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if command -v mmu >/dev/null 2>&1; then
  exec mmu "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec env PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m mmu_cli "$@"
fi

echo "Python 3 is required. Install it and run again." >&2
exit 1
