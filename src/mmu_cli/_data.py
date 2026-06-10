"""Locate MMU content (blueprints, prompts, launch kit, filled examples).

Resolution order:
1. A repo checkout containing this package (developing from a git clone).
2. The packaged copy bundled in the wheel under ``mmu_cli/data/``
   (kept in sync by ``scripts/sync_packaged_data.py``).

Both layouts mirror the repo structure (``docs/blueprints``, ``prompts``, ...)
so callers can treat the returned path exactly like a repo root.
"""

from __future__ import annotations

from pathlib import Path


def packaged_data_root() -> Path | None:
    """Return the bundled data dir shipped in the wheel, if present."""
    data_root = Path(__file__).resolve().parent / "data"
    if (data_root / "docs" / "blueprints").is_dir():
        return data_root
    return None


def find_content_root() -> Path | None:
    """Find a directory that contains docs/blueprints/ (checkout or wheel data)."""
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "docs" / "blueprints").is_dir():
        return checkout
    return packaged_data_root()
