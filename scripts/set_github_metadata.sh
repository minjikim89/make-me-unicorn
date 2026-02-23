#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required." >&2
  exit 1
fi

REPO="${1:-minjikim89/make-me-unicorn}"
DESCRIPTION="AI-built SaaS blind-spot catcher: context, stage gates, and reliability checks for solo builders."
TOPICS=(
  saas
  solo-founder
  developer-tools
  productivity
  checklist
  llm
  ai-coding
  reliability
  devops
  startup
)

echo "Updating description for ${REPO}"
gh repo edit "$REPO" --description "$DESCRIPTION"

echo "Applying topics"
for t in "${TOPICS[@]}"; do
  gh repo edit "$REPO" --add-topic "$t"
done

echo "Done. Verify settings in GitHub UI (including Social Preview)."
