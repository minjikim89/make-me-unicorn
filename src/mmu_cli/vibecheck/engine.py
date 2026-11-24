"""Vibecheck engine: finding types, shared file helpers, and the runner."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

@dataclass
class Finding:
    check: str
    severity: str  # "P0" | "P1"
    status: str  # "fail" | "warn" | "ok" | "skip"
    message: str
    hint: str = ""
    files: list[str] = field(default_factory=list)
    ref: str = ""  # URL of the real-world incident / dataset that motivates the check

    def to_dict(self) -> dict:
        return asdict(self)


# Per-run content cache: several checks scan the same files; one read each.
# Cleared at the start of run_vibecheck so long-lived processes stay fresh.
_READ_CACHE: dict[Path, str] = {}


def _read(path: Path) -> str:
    if path not in _READ_CACHE:
        try:
            _READ_CACHE[path] = path.read_bytes()[:2_000_000].decode("utf-8", errors="ignore")
        except OSError:
            _READ_CACHE[path] = ""
    return _READ_CACHE[path]


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


# --- Evidence refs: every new check points at the data that motivated it. ---
_REF_REEVE_AUG_2026 = "https://vibe-eval.com/updates/vibe-coding-security-monthly-aug-2026/"
_REF_GITSPAWN = "https://www.manifold.security/blog/ai-coding-agents-git-hijack"


_ENV_SCAN_DEPTH = 3  # apps/web/.env.local in a monorepo; deeper is build output or vendored code


_TEST_DIR_HINTS = ("tests", "test", "__tests__", "spec", "specs", "fixture", "fixtures", "testdata", "__mocks__")
_TEST_FILE_RE = re.compile(r"^(?:test_.*\.py|.*_test\.(?:py|go)|.*_spec\.rb|.*\.(?:test|spec)\.[cm]?[jt]sx?)$")


def _walk_shallow(root: Path, depth: int) -> list[Path]:
    """Directories from root down to `depth`, skipping pruned/skip dirs."""
    from mmu_cli.cli import PRUNE_DIR_NAMES

    out: list[Path] = [root]
    frontier = [root]
    for _ in range(depth):
        nxt: list[Path] = []
        for d in frontier:
            try:
                for child in d.iterdir():
                    if child.is_dir() and child.name not in PRUNE_DIR_NAMES and not child.name.startswith("."):
                        nxt.append(child)
            except OSError:
                continue
        out.extend(nxt)
        frontier = nxt
    return out


def _is_test_path(rel: str) -> bool:
    """Conservative: a directory literally named tests/fixtures/…, or a test-suffixed code file.

    Deliberately NOT matched: `examples/`, `mocks/` (MSW servers ship to prod), Next.js
    `app/test/route.ts` (a live route — `test` is only honoured when no `route.*`/`page.*`
    file name follows), and dotfiles such as `.env.test.local`.
    """
    parts = [p.lower() for p in Path(rel).parts]
    if not parts:
        return False
    name = parts[-1]
    dirs = parts[:-1]
    if name.startswith("."):
        return False
    for i, d in enumerate(dirs):
        if d in _TEST_DIR_HINTS:
            if d == "test" and name.split(".")[0] in {"route", "page", "layout"}:
                continue
            return True
    return bool(_TEST_FILE_RE.match(name))


def downgrade_test_only_findings(findings: list[Finding]) -> list[Finding]:
    """A P0 whose every offending file lives under tests/fixtures/examples becomes a P1 warn.

    Fixtures legitimately contain fake secrets and deliberately bad code; blocking the
    build on them trains people to ignore the tool.
    """
    for f in findings:
        if f.status != "fail" or not f.files:
            continue
        if all(_is_test_path(rel) for rel in f.files):
            f.severity = "P1"
            f.status = "warn"
            f.message += " (all in test/fixture paths — downgraded)"
    return findings


def run_vibecheck(root: Path) -> list[Finding]:
    from mmu_cli.cli import doctor_skip_paths, gather_code_files
    from mmu_cli.vibecheck import rules

    _READ_CACHE.clear()
    skip_paths = doctor_skip_paths(root)
    code_files = gather_code_files(root, skip_paths)

    findings: list[Finding] = []
    findings.append(rules.check_secrets(root, code_files))
    findings.extend(rules.check_webhooks(root, code_files))
    findings.append(rules.check_password_reset(root, code_files))
    findings.append(rules.check_sql_strings(root, code_files))
    findings.append(rules.check_unsafe_deserialization(root, code_files))
    findings.append(rules.check_rate_limiting(root, code_files))
    findings.append(rules.check_cors(root, code_files))
    findings.append(rules.check_debug_mode(root, code_files))
    findings.append(rules.check_error_monitoring(root, code_files))
    findings.append(rules.check_client_bundle_secrets(root, code_files))
    findings.append(rules.check_supabase_rls(root, code_files))
    findings.append(rules.check_sourcemaps(root, code_files))
    findings.append(rules.check_git_config_exec(root, code_files))
    findings.append(rules.check_disabled_ssl(root, code_files))
    findings.append(rules.check_jwt_localstorage(root, code_files))
    return downgrade_test_only_findings(findings)
