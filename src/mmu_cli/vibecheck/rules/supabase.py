"""Supabase rules: tables without Row Level Security."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.engine import _ENV_SCAN_DEPTH, _REF_REEVE_AUG_2026, Finding, _read, _rel, _walk_shallow

# Markers must be Supabase-specific: `createClient(` alone matches redis/viem/sanity/urql.
_SUPABASE_MARKERS = ("@supabase/supabase-js", "@supabase/ssr", "supabase.co", "supabase-py", "from supabase import", "supabase_py")
_SQL_IDENT = r"(?:\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?\.)?\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?"
_SQL_CREATE_TABLE = re.compile(r"create\s+(?:unlogged\s+)?table\s+(?:if\s+not\s+exists\s+)?" + _SQL_IDENT, re.IGNORECASE)
_SQL_ENABLE_RLS = re.compile(
    r"alter\s+table\s+(?:only\s+)?(?:if\s+exists\s+)?" + _SQL_IDENT + r"\s+enable\s+row\s+level\s+security", re.IGNORECASE
)
_SQL_LINE_COMMENT = re.compile(r"--[^\n]*")
_SQL_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _sql_files(root: Path) -> list[Path]:
    """SQL under any `supabase/` directory (root or nested app), pruned like the code walk.

    RLS is a Supabase/Postgres-policy concept; Prisma/Django/`db/` migrations for other
    databases are deliberately not read — a Redis project must never get a Supabase P0.
    """
    from mmu_cli.cli import PRUNE_DIR_NAMES

    out: list[Path] = []
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        sb = d / "supabase"
        if not sb.is_dir():
            continue
        for dirpath, dirnames, filenames in __import__("os").walk(sb):
            dirnames[:] = [x for x in dirnames if x not in PRUNE_DIR_NAMES and not x.startswith(".")]
            for fn in filenames:
                if fn.lower().endswith(".sql"):
                    out.append(Path(dirpath) / fn)
    return sorted(set(out))


def _strip_sql_comments(text: str) -> str:
    return _SQL_LINE_COMMENT.sub("", _SQL_BLOCK_COMMENT.sub("", text))


def _qualified(schema: str | None, name: str) -> str:
    return f"{(schema or 'public').lower()}.{name.lower()}"


def check_supabase_rls(root: Path, code_files: list[Path]) -> Finding:
    """Supabase tables created without Row Level Security.

    With the anon key in the browser, a table without RLS is readable (often writable)
    by anyone. Reeve Aug-2026: 57% of reachable Supabase-backed apps (2,096 of 3,680)
    allowed unauthenticated table reads.
    """
    pkg = (_read(root / "package.json") + _read(root / "requirements.txt") + _read(root / "pyproject.toml")).lower()
    uses_supabase = any(m.lower() in pkg for m in _SUPABASE_MARKERS) or (root / "supabase").is_dir()
    if not uses_supabase:
        for path in code_files[:400]:
            if any(m in _read(path) for m in _SUPABASE_MARKERS):
                uses_supabase = True
                break
    if not uses_supabase:
        return Finding("supabase-rls", "P0", "skip", "no Supabase usage detected")

    sql_files = _sql_files(root)
    if not sql_files:
        return Finding(
            "supabase-rls",
            "P1",
            "warn",
            "Supabase detected but no SQL under supabase/ — RLS cannot be verified from the repo",
            hint="If tables were created in the dashboard, confirm every public table has RLS enabled + a policy. `supabase db pull` brings the schema into the repo so this check can see it.",
            ref=_REF_REEVE_AUG_2026,
        )
    created: dict[str, str] = {}
    rls_enabled: set[str] = set()
    for sql in sql_files:
        text = _strip_sql_comments(_read(sql))
        for schema, name in _SQL_CREATE_TABLE.findall(text):
            created.setdefault(_qualified(schema, name), _rel(sql, root))
        for schema, name in _SQL_ENABLE_RLS.findall(text):
            rls_enabled.add(_qualified(schema, name))
    missing = sorted(t for t in created if t not in rls_enabled)
    if missing:
        return Finding(
            "supabase-rls",
            "P0",
            "fail",
            f"{len(missing)} table(s) created without ENABLE ROW LEVEL SECURITY: " + ", ".join(missing[:8]) + (" …" if len(missing) > 8 else ""),
            hint="Every table reachable with the anon key needs `alter table X enable row level security;` plus at least one policy — otherwise any visitor can read it.",
            files=sorted({created[t] for t in missing}),
            ref=_REF_REEVE_AUG_2026,
        )
    if not created:
        return Finding("supabase-rls", "P0", "ok", "no CREATE TABLE statements found in migrations")
    return Finding("supabase-rls", "P0", "ok", f"RLS enabled on all {len(created)} table(s) found in migrations")
