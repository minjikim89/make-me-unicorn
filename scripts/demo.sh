#!/usr/bin/env bash
# Demo script for Make Me Unicorn — use with asciinema or similar recorder.
#
# Usage:
#   asciinema rec demo.cast -c "./scripts/demo.sh"
#
# Or run directly to see the workflow:
#   ./scripts/demo.sh

set -euo pipefail

DEMO_DIR=$(mktemp -d)
trap 'rm -rf "$DEMO_DIR"' EXIT

# Simulate typing effect
type_cmd() {
  local cmd="$1"
  printf "\n\033[1;33m❯\033[0m "
  for (( i=0; i<${#cmd}; i++ )); do
    printf "%s" "${cmd:$i:1}"
    sleep 0.04
  done
  printf "\n"
  sleep 0.3
}

banner() {
  printf "\n\033[1;36m── %s ──\033[0m\n" "$1"
  sleep 1
}

# ─── Demo Start ───

clear
printf "\033[1;35m"
cat << 'ART'

    Make Me Unicorn — Demo
    ══════════════════════

ART
printf "\033[0m"
sleep 2

# Step 1: Init
banner "Step 1: Initialize your project"
type_cmd "mmu init --root $DEMO_DIR"
mmu init --root "$DEMO_DIR" 2>&1
sleep 2

# Step 2: Scan
banner "Step 2: Auto-detect your tech stack"
type_cmd "mmu scan --root $DEMO_DIR"
mmu scan --root "$DEMO_DIR" 2>&1
sleep 2

# Step 3: Dashboard
banner "Step 3: See your dashboard"
type_cmd "mmu --root $DEMO_DIR"
mmu --root "$DEMO_DIR" 2>&1
sleep 3

# Step 4: Show a category
banner "Step 4: Drill into a category"
type_cmd "mmu show frontend --root $DEMO_DIR"
mmu show frontend --root "$DEMO_DIR" 2>&1
sleep 2

# Step 5: Check items
banner "Step 5: Mark items as done"
type_cmd "mmu check frontend 1 --root $DEMO_DIR"
mmu check frontend 1 --root "$DEMO_DIR" 2>&1
sleep 1
type_cmd "mmu check frontend 2 --root $DEMO_DIR"
mmu check frontend 2 --root "$DEMO_DIR" 2>&1
sleep 2

# Step 6: Gate check
banner "Step 6: Verify launch readiness"
type_cmd "mmu gate --stage M0 --root $DEMO_DIR"
mmu gate --stage M0 --root "$DEMO_DIR" 2>&1
sleep 2

# Step 7: Doctor
banner "Step 7: Run health checks"
type_cmd "mmu doctor --root $DEMO_DIR"
mmu doctor --root "$DEMO_DIR" 2>&1
sleep 2

# Outro
printf "\n\033[1;35m"
cat << 'ART'

    ✓ That's Make Me Unicorn.
    534+ items. 15 categories. Zero guesswork.

    pip install make-me-unicorn
    github.com/minjikim89/make-me-unicorn

ART
printf "\033[0m"
sleep 3
