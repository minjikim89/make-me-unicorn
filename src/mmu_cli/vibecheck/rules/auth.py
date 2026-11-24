"""Auth-surface rules: password reset flow and rate limiting."""

from __future__ import annotations

from pathlib import Path

import re

from mmu_cli.vibecheck.engine import (
    _SERVER_HINTS,
    Finding,
    Location,
    Rule,
    _read,
    _rel,
    clean_snippet,
    first_match_loc,
    loc_at,
    register,
    server_anchor,
)

register(Rule(
    id="password-reset",
    title="Auth without a password reset flow",
    severity="P0",
    summary="Login code exists but nothing lets a user recover a forgotten password, which locks real users out from day one.",
    fix=(
        "Add a forgot-password flow next to the login code: a request endpoint that emails a single-use, expiring "
        "token (store only its hash) and a confirm endpoint that sets the new password and revokes the token and existing sessions.\n"
        "Supabase: supabase.auth.resetPasswordForEmail(email, {redirectTo}) then supabase.auth.updateUser({password}).\n"
        "Return the same response for unknown emails."
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html",
    tags=("auth",),
    confidence="low",
))

register(Rule(
    id="rate-limiting",
    title="Server without rate limiting",
    severity="P1",
    summary="Login, signup and AI endpoints without a rate limit allow credential stuffing and turn paid APIs into a free compute faucet.",
    fix=(
        "Add a limiter to login, signup, password-reset and any LLM/paid-API endpoint, keyed by IP and by user.\n"
        "FastAPI: slowapi (`@limiter.limit(\"5/minute\")`). Express: express-rate-limit middleware. "
        "Next.js: @upstash/ratelimit in middleware.ts or the route handler."
    ),
    ref="https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/",
    tags=("auth", "abuse"),
    confidence="low",
))

# The line an absence-of-reset finding is anchored to inside an auth file: the login
# handler or route when one is recognisable, else the first mention of login/password.
_LOGIN_HANDLER = re.compile(
    r"(?:def|function|func|const|class)\s+\w*(?:log_?in|sign_?in|authenticate)\w*|"
    r"[\"'`]/?[\w/-]*(?:login|signin|sign-in)[\"'`]",
    re.IGNORECASE,
)
_LOGIN_MENTION = re.compile(r"log_?in|sign_?in|authenticate|password", re.IGNORECASE)


def _auth_anchor(path: Path, root: Path) -> Location:
    text = _read(path)
    m = _LOGIN_HANDLER.search(text)
    return loc_at(path, root, text, m.start()) if m else first_match_loc(path, root, _LOGIN_MENTION)

_RATE_LIMIT_MARKERS = [
    "rate_limit", "ratelimit", "rate-limit", "limiter", "slowapi",
    "express-rate-limit", "upstash", "throttle", "throttling",
]


_AUTH_FILE_HINTS = ("auth", "login", "signin", "sign-in", "session", "account")
_RESET_MARKERS = ["password reset", "reset password", "forgot password", "resetpassword", "forgot-password", "passwordreset"]


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
        files=[_rel(p, root) for p in auth_files],
        locations=[_auth_anchor(p, root) for p in auth_files],
    )


def check_rate_limiting(root: Path, code_files: list[Path]) -> Finding:
    from mmu_cli.cli import detect_nextjs

    corpus_paths = code_files[:400]
    server_detected = detect_nextjs(root)
    pkg = _read(root / "package.json") + _read(root / "requirements.txt") + _read(root / "pyproject.toml")
    if any(h in pkg.lower() for h in _SERVER_HINTS):
        server_detected = True
    has_marker = False
    hint_file: Path | None = None
    for path in corpus_paths:
        text = _read(path).lower()
        if hint_file is None and any(h in text for h in _SERVER_HINTS):
            hint_file = path
        if not server_detected and any(h in text for h in _SERVER_HINTS):
            server_detected = True
        if any(m in text for m in _RATE_LIMIT_MARKERS):
            has_marker = True
            break
    if not server_detected:
        return Finding("rate-limiting", "P1", "skip", "no server framework detected")
    if has_marker:
        return Finding("rate-limiting", "P1", "ok", "rate limiting markers found")
    anchor = server_anchor(root, code_files, _SERVER_HINTS)
    if (anchor is None or anchor.line is None) and hint_file is not None:
        anchor = _first_hint_line(hint_file, root)
    return Finding(
        "rate-limiting",
        "P1",
        "warn",
        "server framework detected but no rate limiting markers",
        locations=[anchor] if anchor else [],
    )


def _first_hint_line(path: Path, root: Path) -> Location:
    for i, line in enumerate(_read(path).splitlines(), 1):
        if any(h in line.lower() for h in _SERVER_HINTS):
            return Location(_rel(path, root), i, snippet=clean_snippet(line))
    return Location(_rel(path, root), 1)
