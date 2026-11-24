"""Frontend rules: tokens kept in browser storage."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.engine import Finding, Location, Rule, _read, _rel, loc_at, register

register(Rule(
    id="jwt-localstorage",
    title="Auth token in browser storage",
    severity="P1",
    summary="A token kept in localStorage/sessionStorage is readable by any script on the page, so one XSS bug becomes account takeover.",
    fix=(
        "Have the server set the session token in a cookie with HttpOnly, Secure and SameSite=Lax (or Strict), stop "
        "writing it to localStorage/sessionStorage, and send requests with credentials: \"include\".\n"
        "Add CSRF protection for state-changing requests once auth is cookie-based."
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#local-storage",
    tags=("frontend", "auth"),
    confidence="high",
))

_JWT_LOCALSTORAGE_PATTERN = re.compile(
    r"""(?:localStorage|sessionStorage)(?:\.setItem\(\s*['"`](?:jwt|token|access_token|id_token|auth_token|authToken)['"`]|\[\s*['"`](?:jwt|token|access_token|id_token|auth_token|authToken)['"`]\s*\]\s*=|\.(?:jwt|token|access_token|id_token|auth_token|authToken)\s*=)""",
    re.IGNORECASE
)


def check_jwt_localstorage(root: Path, code_files: list[Path]) -> Finding:
    js_files = [
        p for p in code_files
        if p.suffix.lower() in {".js", ".jsx", ".ts", ".tsx"}
    ]
    if not js_files:
        return Finding("jwt-localstorage", "P1", "skip", "no JS/TS frontend files detected")
    offenders: list[str] = []
    locations: list[Location] = []
    for path in js_files:
        text = _read(path)
        hits = [loc_at(path, root, text, m.start()) for m in _JWT_LOCALSTORAGE_PATTERN.finditer(text)]
        if hits:
            offenders.append(_rel(path, root))
            locations.extend(hits)
    if offenders:
        return Finding(
            check="jwt-localstorage",
            severity="P1",
            status="warn",
            message=f"JWT or access token stored in localStorage/sessionStorage in {len(offenders)} file(s)",
            files=sorted(set(offenders)),
            locations=locations,
        )
    return Finding("jwt-localstorage", "P1", "ok", "no JWT localStorage storage detected")
