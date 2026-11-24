"""Auth-surface rules: password reset flow and rate limiting."""

from __future__ import annotations

from pathlib import Path

from mmu_cli.vibecheck.engine import Finding, _read, _rel

_RATE_LIMIT_MARKERS = [
    "rate_limit", "ratelimit", "rate-limit", "limiter", "slowapi",
    "express-rate-limit", "upstash", "throttle", "throttling",
]


_AUTH_FILE_HINTS = ("auth", "login", "signin", "sign-in", "session", "account")
_RESET_MARKERS = ["password reset", "reset password", "forgot password", "resetpassword", "forgot-password", "passwordreset"]


_SERVER_HINTS = [
    "express", "fastapi", "flask", "django", "koa", "hono", "nestjs",
    "next.config", "rails", "sinatra", "gin-gonic", "fiber",
]


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
        files=[_rel(p, root) for p in auth_files],
    )


def check_rate_limiting(root: Path, code_files: list[Path]) -> Finding:
    from mmu_cli.cli import detect_nextjs

    corpus_paths = code_files[:400]
    server_detected = detect_nextjs(root)
    pkg = _read(root / "package.json") + _read(root / "requirements.txt") + _read(root / "pyproject.toml")
    if any(h in pkg.lower() for h in _SERVER_HINTS):
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
