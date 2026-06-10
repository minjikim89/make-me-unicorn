"""`mmu vibecheck` — fast scan for the failure modes AI-generated code ships most.

Heuristic, zero-dependency, read-only. Each check answers one question a solo
builder forgets to ask before launch: leaked secrets, unverified webhooks,
missing password reset, no rate limiting, wildcard CORS, f-string SQL,
debug mode left on, no error monitoring.

Severities: P0 findings exit non-zero (block launch), P1 findings warn.
Checks that find no relevant surface (e.g. no webhook handlers) report SKIP.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

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

_RATE_LIMIT_MARKERS = [
    "rate_limit", "ratelimit", "rate-limit", "limiter", "slowapi",
    "express-rate-limit", "upstash", "throttle", "throttling",
]

_CORS_WILDCARD_MARKERS = [
    'access-control-allow-origin", "*"',
    "access-control-allow-origin': '*'",
    'access-control-allow-origin: *',
    'allow_origins=["*"]',
    "allow_origins=['*']",
    'origin: "*"',
    "origin: '*'",
    "cors_allow_all",
]

_MONITORING_MARKERS = [
    "sentry", "rollbar", "bugsnag", "honeybadger", "datadog",
    "new relic", "newrelic", "appsignal", "glitchtip", "highlight.io",
]

_AUTH_FILE_HINTS = ("auth", "login", "signin", "sign-in", "session", "account")
_RESET_MARKERS = ["password reset", "reset password", "forgot password", "resetpassword", "forgot-password", "passwordreset"]

_SQL_FSTRING = re.compile(r"""f["']\s*(?:SELECT|INSERT|UPDATE|DELETE)\b""", re.IGNORECASE)

_SERVER_HINTS = [
    "express", "fastapi", "flask", "django", "koa", "hono", "nestjs",
    "next.config", "rails", "sinatra", "gin-gonic", "fiber",
]


@dataclass
class Finding:
    check: str
    severity: str  # "P0" | "P1"
    status: str  # "fail" | "warn" | "ok" | "skip"
    message: str
    hint: str = ""
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "check": self.check,
            "severity": self.severity,
            "status": self.status,
            "message": self.message,
            "hint": self.hint,
            "files": self.files,
        }


def _read(path: Path) -> str:
    try:
        return path.read_bytes()[:2_000_000].decode("utf-8", errors="ignore")
    except OSError:
        return ""


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def check_secrets(root: Path, code_files: list[Path]) -> Finding:
    offenders: list[str] = []
    details: list[str] = []
    scan_files = list(code_files)
    env_file = root / ".env"
    for path in scan_files:
        text = _read(path)
        if not text:
            continue
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                offenders.append(_rel(path, root))
                details.append(label)
                break
    if env_file.is_file():
        gitignore = _read(root / ".gitignore")
        ignored = any(line.strip() in {".env", "*.env", ".env*"} for line in gitignore.splitlines())
        if not ignored:
            offenders.append(".env")
            details.append(".env exists but .gitignore does not cover it")
    if offenders:
        return Finding(
            check="secrets",
            severity="P0",
            status="fail",
            message=f"possible hardcoded secrets in {len(offenders)} file(s): " + "; ".join(sorted(set(details))),
            hint="Move keys to environment variables, rotate anything that was committed, add .env to .gitignore.",
            files=sorted(set(offenders)),
        )
    return Finding("secrets", "P0", "ok", "no hardcoded secret signatures detected")


def check_webhooks(root: Path, code_files: list[Path]) -> list[Finding]:
    from mmu_cli.cli import check_webhook_safety, detect_webhook_files

    webhook_files = detect_webhook_files(root, code_files)
    if not webhook_files:
        return [Finding("webhook-safety", "P0", "skip", "no webhook handlers detected")]
    errors: list[str] = []
    has_sig, has_idem = check_webhook_safety(webhook_files, errors)
    rels = [_rel(p, root) for p in webhook_files]
    findings = []
    if has_sig:
        findings.append(Finding("webhook-signature", "P0", "ok", "webhook signature verification markers found"))
    else:
        findings.append(
            Finding(
                "webhook-signature",
                "P0",
                "fail",
                "webhook handlers found but no signature verification markers",
                hint="Verify provider signatures (e.g. stripe.webhooks.constructEvent) or attackers can forge payment events.",
                files=rels,
            )
        )
    if has_idem:
        findings.append(Finding("webhook-idempotency", "P0", "ok", "webhook idempotency markers found"))
    else:
        findings.append(
            Finding(
                "webhook-idempotency",
                "P0",
                "fail",
                "webhook handlers found but no idempotency markers",
                hint="Store processed event IDs — providers retry deliveries, and double-processing a payment event is a refund ticket.",
                files=rels,
            )
        )
    return findings


def check_password_reset(root: Path, code_files: list[Path]) -> Finding:
    auth_files = [
        p for p in code_files
        if any(h in p.name.lower() or h in _rel(p, root).lower() for h in _AUTH_FILE_HINTS)
    ]
    if not auth_files:
        return Finding("password-reset", "P0", "skip", "no auth-related files detected")
    corpus = " ".join(_read(p).lower() for p in auth_files[:200])
    if any(m in corpus for m in _RESET_MARKERS):
        return Finding("password-reset", "P0", "ok", "password reset markers found in auth code")
    return Finding(
        "password-reset",
        "P0",
        "fail",
        f"auth code detected ({len(auth_files)} file(s)) but no password reset flow markers",
        hint="The #1 day-one lockout: users who can log in but can never get back in. Ship forgot-password before launch.",
        files=[_rel(p, root) for p in auth_files[:10]],
    )


def check_rate_limiting(root: Path, code_files: list[Path]) -> Finding:
    corpus_paths = code_files[:400]
    server_detected = any(
        (root / name).exists() for name in ("next.config.js", "next.config.mjs", "next.config.ts")
    )
    pkg = _read(root / "package.json") + _read(root / "requirements.txt") + _read(root / "pyproject.toml")
    if '"next"' in pkg or any(h in pkg.lower() for h in _SERVER_HINTS):
        server_detected = True
    has_marker = False
    for path in corpus_paths:
        text = _read(path).lower()
        if not server_detected and any(h in text for h in _SERVER_HINTS):
            server_detected = True
        if any(m in text for m in _RATE_LIMIT_MARKERS):
            has_marker = True
            break
    if not server_detected:
        return Finding("rate-limiting", "P1", "skip", "no server framework detected")
    if has_marker:
        return Finding("rate-limiting", "P1", "ok", "rate limiting markers found")
    return Finding(
        "rate-limiting",
        "P1",
        "warn",
        "server framework detected but no rate limiting markers",
        hint="Login, signup, and AI endpoints without rate limits become a free compute faucet on launch day.",
    )


def check_cors(root: Path, code_files: list[Path]) -> Finding:
    offenders = []
    for path in code_files[:400]:
        text = _read(path).lower()
        if any(m in text for m in _CORS_WILDCARD_MARKERS):
            offenders.append(_rel(path, root))
    if offenders:
        return Finding(
            "cors-wildcard",
            "P1",
            "warn",
            f"wildcard CORS origin in {len(offenders)} file(s)",
            hint="Allow-all origins plus cookie/header auth lets any site call your API as your users. Pin allowed origins.",
            files=offenders,
        )
    return Finding("cors-wildcard", "P1", "ok", "no wildcard CORS origins detected")


def check_sql_strings(root: Path, code_files: list[Path]) -> Finding:
    offenders = []
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        if _SQL_FSTRING.search(_read(path)):
            offenders.append(_rel(path, root))
    if offenders:
        return Finding(
            "sql-fstring",
            "P0",
            "fail",
            f"f-string SQL queries in {len(offenders)} file(s)",
            hint="Interpolating values into SQL is the classic AI-generated injection hole. Use parameterized queries.",
            files=offenders,
        )
    return Finding("sql-fstring", "P0", "ok", "no f-string SQL queries detected")


def check_debug_mode(root: Path, code_files: list[Path]) -> Finding:
    pattern = re.compile(r"^\s*DEBUG\s*=\s*True\b", re.MULTILINE)
    offenders = []
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        if pattern.search(_read(path)):
            offenders.append(_rel(path, root))
    if offenders:
        return Finding(
            "debug-mode",
            "P1",
            "warn",
            f"DEBUG = True in {len(offenders)} file(s)",
            hint="Debug mode in production leaks stack traces, settings, and sometimes secrets. Gate it on an env var.",
            files=offenders,
        )
    return Finding("debug-mode", "P1", "ok", "no hardcoded DEBUG = True detected")


def check_error_monitoring(root: Path, code_files: list[Path]) -> Finding:
    pkg = (_read(root / "package.json") + _read(root / "requirements.txt") + _read(root / "pyproject.toml")).lower()
    if any(m in pkg for m in _MONITORING_MARKERS):
        return Finding("error-monitoring", "P1", "ok", "error monitoring dependency detected")
    for path in code_files[:400]:
        if any(m in _read(path).lower() for m in _MONITORING_MARKERS):
            return Finding("error-monitoring", "P1", "ok", "error monitoring markers found in code")
    return Finding(
        "error-monitoring",
        "P1",
        "warn",
        "no error monitoring (Sentry etc.) detected",
        hint="Without error tracking, your first signal of a production bug is a churned user. `sentry init` takes 10 minutes.",
    )


def run_vibecheck(root: Path) -> list[Finding]:
    from mmu_cli.cli import doctor_skip_paths, gather_code_files

    skip_paths = doctor_skip_paths(root)
    code_files = gather_code_files(root, skip_paths)

    findings: list[Finding] = []
    findings.append(check_secrets(root, code_files))
    findings.extend(check_webhooks(root, code_files))
    findings.append(check_password_reset(root, code_files))
    findings.append(check_sql_strings(root, code_files))
    findings.append(check_rate_limiting(root, code_files))
    findings.append(check_cors(root, code_files))
    findings.append(check_debug_mode(root, code_files))
    findings.append(check_error_monitoring(root, code_files))
    return findings


def format_findings(findings: list[Finding]) -> tuple[list[str], int]:
    """Render findings as message lines; return (lines, exit_code)."""
    icons = {"fail": "[fail]", "warn": "[warn]", "ok": "[ok]", "skip": "[skip]"}
    lines = ["Vibe check — what AI-generated code usually misses", ""]
    fails = [f for f in findings if f.status == "fail"]
    warns = [f for f in findings if f.status == "warn"]
    for f in findings:
        lines.append(f"  {icons[f.status]} ({f.severity}) {f.check}: {f.message}")
        if f.status in {"fail", "warn"}:
            if f.files:
                for rel in f.files[:5]:
                    lines.append(f"        - {rel}")
                if len(f.files) > 5:
                    lines.append(f"        - … and {len(f.files) - 5} more")
            if f.hint:
                lines.append(f"        ↳ {f.hint}")
    lines.append("")
    if fails:
        lines.append(f"Vibe check result: {len(fails)} launch-blocking issue(s), {len(warns)} warning(s)")
        return lines, 2
    if warns:
        lines.append(f"Vibe check result: no blockers, {len(warns)} warning(s)")
        return lines, 0
    lines.append("Vibe check result: clean ✨")
    return lines, 0
