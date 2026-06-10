#!/usr/bin/env python3
"""Sync canonical repo content into src/mmu_cli/data/ for wheel packaging.

The CLI and MCP server read blueprints, prompts, launch templates, and the
filled example from the repo checkout when available, and fall back to the
packaged copy under mmu_cli/data/ after a plain `pip install`.

Usage:
    python scripts/sync_packaged_data.py            # copy canonical -> packaged
    python scripts/sync_packaged_data.py --check    # exit 1 if out of sync (CI)
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "src" / "mmu_cli" / "data"

# Relative directories whose *.md files are bundled into the wheel.
# Structure is mirrored so the data dir can stand in for the repo root.
SYNC_DIRS = [
    "docs/blueprints",
    "docs/blueprints/industry",
    "docs/launch",
    "prompts",
    "examples/filled/tasknote/docs/core",
]


def canonical_files() -> list[Path]:
    files: list[Path] = []
    for rel in SYNC_DIRS:
        src_dir = REPO_ROOT / rel
        if not src_dir.is_dir():
            continue
        files.extend(p for p in sorted(src_dir.glob("*.md")) if p.is_file())
    return files


def sync() -> int:
    if DATA_ROOT.is_dir():
        shutil.rmtree(DATA_ROOT)
    for src in canonical_files():
        rel = src.relative_to(REPO_ROOT)
        dst = DATA_ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    count = len(canonical_files())
    print(f"Synced {count} files into {DATA_ROOT.relative_to(REPO_ROOT)}")
    return 0


def check() -> int:
    problems: list[str] = []
    expected = {p.relative_to(REPO_ROOT) for p in canonical_files()}
    for rel in expected:
        dst = DATA_ROOT / rel
        if not dst.is_file():
            problems.append(f"missing packaged copy: {rel}")
        elif not filecmp.cmp(REPO_ROOT / rel, dst, shallow=False):
            problems.append(f"stale packaged copy: {rel}")
    if DATA_ROOT.is_dir():
        for dst in DATA_ROOT.rglob("*.md"):
            rel = dst.relative_to(DATA_ROOT)
            if rel not in expected:
                problems.append(f"orphan packaged file (no canonical source): {rel}")
    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(
            "\nPackaged data is out of sync. Run: python scripts/sync_packaged_data.py",
            file=sys.stderr,
        )
        return 1
    print("Packaged data is in sync.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify sync without writing")
    args = parser.parse_args()
    return check() if args.check else sync()


if __name__ == "__main__":
    raise SystemExit(main())
