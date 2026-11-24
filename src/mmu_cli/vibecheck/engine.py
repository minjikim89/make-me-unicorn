"""Vibecheck engine: finding/location/rule types, the rule registry, and the runner.

Pipeline: run every check -> apply suppressions (inline `mmu-ignore[...]` and
`.mmu/config.toml`) -> downgrade test-only P0s -> filter to the requested scope.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

SCHEMA = "mmu.vibecheck/v1"
INFORMATION_URI = "https://github.com/minjikim89/make-me-unicorn"

# Conservative secret signatures: prefixes that only appear in real
# credentials, not in placeholder-style docs (`sk_live_...` etc. with
# enough trailing payload to rule out truncated examples).
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Stripe live secret key", re.compile(r"sk_live_[0-9a-zA-Z]{20,}")),
    ("Stripe test secret key", re.compile(r"sk_test_[0-9a-zA-Z]{20,}")),
    ("Anthropic API key", re.compile(r"sk-ant-[0-9a-zA-Z_-]{20,}")),
    ("OpenAI API key", re.compile(r"sk-proj-[0-9a-zA-Z_-]{20,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[0-9a-zA-Z]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9a-zA-Z-]{20,}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]
_JWT = re.compile(r"\beyJ[0-9A-Za-z_-]{10,}\.eyJ[0-9A-Za-z_-]{10,}\.[0-9A-Za-z_-]{10,}\b")

_SNIPPET_MAX = 160

_SERVER_HINTS = [
    "express", "fastapi", "flask", "django", "koa", "hono", "nestjs",
    "next.config", "rails", "sinatra", "gin-gonic", "fiber",
]


class ScanError(Exception):
    """A usage/runtime error (exit code 2): bad root, git unavailable, unknown rule id."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Rule:
    """Static metadata of one rule. `id` is stable and is what suppressions refer to."""

    id: str
    title: str
    severity: str  # default severity: "P0" (blocks) | "P1" (warns)
    summary: str  # one sentence: what it detects and why it matters
    fix: str  # concrete, agent-actionable instructions (<= ~4 lines)
    ref: str = ""  # incident data or authoritative documentation
    tags: tuple[str, ...] = ()
    confidence: str = "medium"  # "high" (exact pattern) | "medium" | "low" (absence-of-marker heuristic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "summary": self.summary,
            "fix": self.fix,
            "ref": self.ref,
            "tags": list(self.tags),
            "confidence": self.confidence,
        }


RULES: dict[str, Rule] = {}


def register(rule: Rule) -> Rule:
    RULES[rule.id] = rule
    return rule


def all_rules() -> list[Rule]:
    from mmu_cli.vibecheck import rules  # noqa: F401  (importing registers every rule)

    return sorted(RULES.values(), key=lambda rule: (rule.severity, rule.id))


def get_rule(rule_id: str) -> Rule:
    all_rules()
    rule = RULES.get(rule_id)
    if rule is None:
        raise ScanError("unknown-rule", f"unknown rule id: {rule_id!r} (see `mmu vibecheck --list-rules`)")
    return rule


@dataclass
class Location:
    path: str  # relative to the scan root, forward slashes
    line: int | None = None  # 1-based; None = the file as a whole
    end_line: int | None = None
    snippet: str = ""  # trimmed source line, secret values redacted

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "line": self.line, "end_line": self.end_line, "snippet": self.snippet}

    def label(self) -> str:
        return f"{self.path}:{self.line}" if self.line else self.path


@dataclass
class Finding:
    check: str  # rule id
    severity: str  # "P0" | "P1"
    status: str  # "fail" | "warn" | "ok" | "skip" | "suppressed"
    message: str
    hint: str = ""  # fix instructions; defaults to the rule's `fix`
    files: list[str] = field(default_factory=list)
    ref: str = ""  # URL of the real-world incident / dataset that motivates the check
    locations: list[Location] = field(default_factory=list)
    title: str = ""
    confidence: str = ""
    suppress_reason: str = ""
    suppress_source: str = ""  # "inline" | "config"
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        rule = RULES.get(self.check)
        if rule is not None:
            self.hint = self.hint or rule.fix
            self.ref = self.ref or rule.ref
            self.title = self.title or rule.title
            self.confidence = self.confidence or rule.confidence
        if not self.files and self.locations:
            self.files = _unique(loc.path for loc in self.locations)

    @property
    def rule_id(self) -> str:
        return self.check

    @property
    def fix(self) -> str:
        return self.hint

    def to_dict(self) -> dict[str, Any]:
        """The `mmu.vibecheck/v1` finding object (see docs/vibecheck-json-schema.md)."""
        suppression = None
        if self.status == "suppressed":
            suppression = {"reason": self.suppress_reason, "source": self.suppress_source}
        return {
            "rule_id": self.check,
            "check": self.check,  # deprecated alias of rule_id
            "severity": self.severity,
            "status": self.status,
            "title": self.title,
            "message": self.message,
            "locations": [loc.to_dict() for loc in self.locations],
            "files": list(self.files),
            "fix": self.hint,
            "hint": self.hint,  # deprecated alias of fix
            "ref": self.ref,
            "confidence": self.confidence or "medium",
            "suppression": suppression,
            "notes": list(self.notes),
        }


@dataclass
class ScanResult:
    root: Path
    findings: list[Finding]
    scope: dict[str, Any] = field(default_factory=lambda: {"mode": "all"})

    def summary(self) -> dict[str, int]:
        count = {s: 0 for s in ("fail", "warn", "ok", "skip", "suppressed")}
        for f in self.findings:
            count[f.status] = count.get(f.status, 0) + 1
        return {
            "blocking": count["fail"],
            "warnings": count["warn"],
            "passed": count["ok"],
            "skipped": count["skip"],
            "suppressed": count["suppressed"],
        }

    def exit_code(self, fail_on: str = "P0") -> int:
        """0 = nothing at or above the `fail_on` threshold, 1 = blocking findings."""
        if fail_on == "never":
            return 0
        blocking = {"fail"} if fail_on == "P0" else {"fail", "warn"}
        return 1 if any(f.status in blocking for f in self.findings) else 0


def tool_version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("make-me-unicorn")
        except PackageNotFoundError:
            return "unknown"
    except ImportError:  # pragma: no cover
        return "unknown"


def _unique(items: Any) -> list[str]:
    return list(dict.fromkeys(items))


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


# --- Locations -------------------------------------------------------------

def mask(value: str) -> str:
    """Redacted form of a secret value: first 6 chars, never more than a third of it."""
    keep = min(6, len(value) // 3)
    return value[:keep] + "\u2026"


def redact(text: str) -> str:
    """Mask anything in `text` that matches a known secret signature."""
    for _, pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: mask(m.group(0)), text)
    return _JWT.sub(lambda m: mask(m.group(0)), text)


def clean_snippet(line: str) -> str:
    snippet = redact(line.strip())
    return snippet if len(snippet) <= _SNIPPET_MAX else snippet[: _SNIPPET_MAX - 1] + "\u2026"


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def line_text(text: str, lineno: int) -> str:
    lines = text.splitlines()
    return lines[lineno - 1] if 0 < lineno <= len(lines) else ""


def loc_at(path: Path, root: Path, text: str, pos: int, snippet: str | None = None) -> Location:
    """Location of character offset `pos` in `text` (the content of `path`)."""
    lineno = line_of(text, pos)
    if snippet is None:
        start = text.rfind("\n", 0, pos) + 1
        end = text.find("\n", pos)
        snippet = clean_snippet(text[start: end if end >= 0 else len(text)])
    return Location(_rel(path, root), lineno, snippet=snippet)


def loc_line(path: Path, root: Path, lineno: int, text: str | None = None) -> Location:
    text = _read(path) if text is None else text
    return Location(_rel(path, root), lineno, snippet=clean_snippet(line_text(text, lineno)))


def first_match_loc(path: Path, root: Path, pattern: re.Pattern[str]) -> Location:
    """Anchor for an absence finding: the first line matching `pattern`, else line 1."""
    text = _read(path)
    m = pattern.search(text)
    return loc_at(path, root, text, m.start()) if m else loc_line(path, root, 1, text)


def dedupe_locations(locations: list[Location]) -> list[Location]:
    seen: set[tuple[str, int | None]] = set()
    out: list[Location] = []
    for loc in locations:
        key = (loc.path, loc.line)
        if key not in seen:
            seen.add(key)
            out.append(loc)
    return out


_SERVER_ENTRY = re.compile(
    r"\b(?:FastAPI|Flask|Sanic|Starlette|Quart)\(|\bexpress\(\)|\bnew\s+(?:Hono|Koa|Elysia)\(|\bfastify\(|"
    r"\bgin\.(?:Default|New)\(|\bfiber\.New\(|\bhttp\.createServer\(|\bNestFactory\.create\(|\bcreateServer\("
)
_MANIFESTS = ("package.json", "requirements.txt", "pyproject.toml")


def server_anchor(root: Path, code_files: list[Path], hints: list[str] | None = None) -> Location | None:
    """Where a project-wide obligation (rate limiting, error monitoring) is anchored.

    Preference: the line that creates the server app, then the manifest line that
    declares the server framework, then a Next.js config, then any manifest.
    """
    for path in code_files[:400]:
        text = _read(path)
        m = _SERVER_ENTRY.search(text)
        if m:
            return loc_at(path, root, text, m.start())
    if hints:
        for name in _MANIFESTS:
            text = _read(root / name)
            for i, line in enumerate(text.splitlines(), 1):
                low = line.lower()
                if any(h in low for h in hints):
                    return Location(name, i, snippet=clean_snippet(line))
    for name in ("next.config.js", "next.config.mjs", "next.config.ts"):
        if (root / name).is_file():
            return Location(name, 1, snippet=clean_snippet(line_text(_read(root / name), 1)))
    for name in _MANIFESTS:
        if (root / name).is_file():
            return Location(name, None)
    return None


# --- Evidence refs: checks point at the data that motivated them. ---
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


# --- Suppressions ----------------------------------------------------------

# `mmu-ignore[rule-id]: reason` in any comment syntax; several ids may be comma-separated.
_IGNORE = re.compile(r"mmu-ignore\[([^\]\n]+)\](?:[ \t]*:[ \t]*([^\n]*))?")
_COMMENT_CLOSERS = re.compile(r"\s*(?:\*/\}?|-->|#\}|%>)\s*$")
_ACTIVE = {"fail", "warn"}


def _inline_ignores(text: str) -> dict[int, list[tuple[set[str], str, bool]]]:
    """line number -> [(rule ids, reason, standalone)] for every `mmu-ignore[...]` marker in `text`.

    `standalone` = the marker sits on a comment-only line, so it applies to the line below it.
    """
    out: dict[int, list[tuple[set[str], str, bool]]] = {}
    if "mmu-ignore[" not in text:
        return out
    for m in _IGNORE.finditer(text):
        ids = {part.strip() for part in m.group(1).split(",") if part.strip()}
        reason = _COMMENT_CLOSERS.sub("", (m.group(2) or "").strip()).strip()
        prefix = text[text.rfind("\n", 0, m.start()) + 1: m.start()]
        standalone = re.fullmatch(r"[^\w\"'`]*", prefix) is not None
        out.setdefault(line_of(text, m.start()), []).append((ids, reason, standalone))
    return out


def _inline_ignore_for(root: Path, loc: Location, rule_id: str) -> tuple[bool, str] | None:
    """(suppressed, reason) when a marker for `rule_id` sits on the location's line or alone on the line above."""
    if not loc.line:
        return None
    path = Path(loc.path)
    ignores = _inline_ignores(_read(path if path.is_absolute() else root / path))
    found: tuple[bool, str] | None = None
    for lineno in (loc.line, loc.line - 1):
        for ids, reason, standalone in ignores.get(lineno, []):
            if rule_id in ids and (standalone or lineno == loc.line):
                if reason:
                    return True, reason
                found = (False, "")
    return found


def load_config_ignores(root: Path) -> list[tuple[str, str]]:
    """`[vibecheck] ignore` entries of `.mmu/config.toml` as (path glob or "", rule id)."""
    from mmu_cli.cli import load_config

    section = load_config(root).get("vibecheck")
    entries = section.get("ignore") if isinstance(section, dict) else None
    out: list[tuple[str, str]] = []
    if not isinstance(entries, list):
        return out
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            continue
        glob, sep, rule_id = entry.strip().rpartition(":")
        out.append((glob.strip() if sep else "", rule_id.strip()))
    return out


def _glob_match(path: str, glob: str) -> bool:
    return fnmatch.fnmatchcase(path, glob) or ("**/" in glob and fnmatch.fnmatchcase(path, glob.replace("**/", "")))


def apply_suppressions(
    findings: list[Finding], root: Path, config_ignores: list[tuple[str, str]] | None = None
) -> list[Finding]:
    """Turn suppressed findings (or the suppressed part of their locations) into status `suppressed`.

    Inline markers need a reason; one without a reason leaves the finding active and adds a note.
    A finding whose locations are only partly suppressed is split: the active part keeps its
    status, the suppressed part follows it as a separate `suppressed` finding.
    """
    config_ignores = config_ignores or []
    out: list[Finding] = []
    for f in findings:
        if f.status not in _ACTIVE:
            out.append(f)
            continue
        globs = [glob for glob, rule_id in config_ignores if rule_id == f.check]
        if "" in globs:
            f.status, f.suppress_source = "suppressed", "config"
            f.suppress_reason = "rule ignored in .mmu/config.toml"
            out.append(f)
            continue
        active: list[Location] = []
        suppressed: list[Location] = []
        reasons: list[str] = []
        sources: list[str] = []
        for loc in f.locations:
            glob = next((g for g in globs if _glob_match(loc.path, g)), None)
            if glob is not None:
                suppressed.append(loc)
                reasons.append(f"path ignored in .mmu/config.toml ({glob})")
                sources.append("config")
                continue
            inline = _inline_ignore_for(root, loc, f.check)
            if inline and inline[0]:
                suppressed.append(loc)
                reasons.append(inline[1])
                sources.append("inline")
                continue
            if inline:
                f.notes.append(
                    f"mmu-ignore[{f.check}] near {loc.label()} has no reason and was not applied; "
                    f"write `mmu-ignore[{f.check}]: <reason>`"
                )
            active.append(loc)
        if not suppressed:
            out.append(f)
            continue
        reason = "; ".join(_unique(reasons))
        source = "inline" if "inline" in sources else "config"
        if not active:
            f.status, f.suppress_reason, f.suppress_source = "suppressed", reason, source
            out.append(f)
            continue
        active_paths = {loc.path for loc in active}
        gone = replace(
            f,
            status="suppressed",
            locations=suppressed,
            files=_unique(loc.path for loc in suppressed),
            suppress_reason=reason,
            suppress_source=source,
            notes=[],
        )
        f.locations = active
        f.files = [p for p in f.files if p in active_paths]
        out.extend([f, gone])
    return out


# --- Scoping ---------------------------------------------------------------

def _git(root: Path, *args: str) -> str:
    # core.fsmonitor=false: never let the scanned repo's own config run a command through us.
    cmd = ["git", "-c", "core.fsmonitor=false", "-C", str(root), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        raise ScanError("git-unavailable", "git is not installed; --changed/--staged/--since need it") from None
    except subprocess.TimeoutExpired:
        raise ScanError("git-failed", f"`git {' '.join(args)}` timed out") from None
    if proc.returncode != 0:
        detail = (proc.stderr.strip().splitlines() or ["no output"])[-1]
        raise ScanError("git-failed", f"`git {' '.join(args)}` failed: {detail}")
    return proc.stdout


def scoped_files(root: Path, mode: str, since: str | None = None) -> set[str]:
    """Root-relative paths in scope. `changed` = tracked changes vs HEAD + untracked files."""
    try:
        inside = _git(root, "rev-parse", "--is-inside-work-tree").strip()
    except ScanError as exc:
        if exc.code == "git-unavailable":
            raise
        raise ScanError("not-a-git-repo", f"{root} is not a git repository; scoped scans need one") from None
    if inside != "true":
        raise ScanError("not-a-git-repo", f"{root} is not inside a git work tree; scoped scans need one")
    diff = ["diff", "--name-only", "-z", "--relative", "--diff-filter=d"]
    untracked = ["ls-files", "--others", "--exclude-standard", "-z"]
    if mode == "staged":
        raw = _git(root, *diff, "--cached")
    elif mode == "since":
        if not since:
            raise ScanError("usage", "--since needs a git ref")
        try:
            _git(root, "rev-parse", "--verify", "--quiet", f"{since}^{{commit}}")
        except ScanError:
            raise ScanError("bad-ref", f"--since: {since!r} is not a commit in this repository") from None
        raw = _git(root, *diff, since) + _git(root, *untracked)
    elif mode == "changed":
        try:
            _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
            raw = _git(root, *diff, "HEAD")
        except ScanError:  # no commits yet: everything staged or modified counts
            raw = _git(root, *diff, "--cached") + _git(root, *diff)
        raw += _git(root, *untracked)
    else:
        raise ScanError("usage", f"unknown scope: {mode!r}")
    return {p for p in raw.split("\0") if p}


def apply_scope(findings: list[Finding], files: set[str]) -> list[Finding]:
    """Keep active/suppressed findings only where a location is in `files`; trim their locations to it."""
    out: list[Finding] = []
    for f in findings:
        if f.status not in _ACTIVE and f.status != "suppressed":
            out.append(f)
            continue
        kept = [loc for loc in f.locations if loc.path in files]
        if kept:
            f.locations = kept
            f.files = [p for p in f.files if p in files] or _unique(loc.path for loc in kept)
            out.append(f)
    return out


# --- Runner ----------------------------------------------------------------

def scan(root: Path, scope: str = "all", since: str | None = None) -> ScanResult:
    """Run every rule on `root` and return findings for `scope` (all | changed | staged | since)."""
    from mmu_cli.cli import doctor_skip_paths, gather_code_files
    from mmu_cli.vibecheck import rules

    if not root.is_dir():
        raise ScanError("bad-root", f"--root {root} is not a directory")
    scope_info: dict[str, Any] = {"mode": scope}
    files: set[str] | None = None
    if scope != "all":
        files = scoped_files(root, scope, since)
        if scope == "since":
            scope_info["since"] = since
        scope_info["files"] = len(files)

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
    findings = apply_suppressions(findings, root, load_config_ignores(root))
    findings = downgrade_test_only_findings(findings)
    if files is not None:
        findings = apply_scope(findings, files)
    return ScanResult(root=root, findings=findings, scope=scope_info)


def run_vibecheck(root: Path) -> list[Finding]:
    return scan(root).findings
