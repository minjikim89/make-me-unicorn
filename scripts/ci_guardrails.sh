#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Doctor runs as advisory in CI — codebase checks may not apply to the
# MMU repo itself (it checks *user* projects, not itself).
./scripts/mmu.sh doctor || echo "Doctor reported issues (non-blocking in CI)"

TARGET_FILE="docs/ops/gate_targets.txt"
if [[ ! -f "$TARGET_FILE" ]]; then
  echo "No gate target file found. Skipping stage gate enforcement."
  exit 0
fi

STAGES="$(grep -E '^[[:space:]]*M[0-9]+[[:space:]]*$' "$TARGET_FILE" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g' || true)"
if [[ -z "$STAGES" ]]; then
  echo "No active gate targets configured. Skipping stage gate enforcement."
  exit 0
fi

echo "Enforcing configured gates:"
echo "$STAGES" | sed 's/^/  - /'
while IFS= read -r stage; do
  [[ -z "$stage" ]] && continue
  ./scripts/mmu.sh gate --stage "$stage"
done <<< "$STAGES"
