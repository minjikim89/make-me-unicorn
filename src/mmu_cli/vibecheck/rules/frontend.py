"""Frontend rules: tokens kept in browser storage."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.engine import Finding, _read, _rel

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
    for path in js_files:
        text = _read(path)
        if _JWT_LOCALSTORAGE_PATTERN.search(text):
            offenders.append(_rel(path, root))
    if offenders:
        return Finding(
            check="jwt-localstorage",
            severity="P1",
            status="warn",
            message=f"JWT or access token stored in localStorage/sessionStorage in {len(offenders)} file(s)",
            hint="Tokens stored in localStorage/sessionStorage can be stolen via XSS. Use secure httpOnly cookies for session storage instead.",
            files=sorted(set(offenders)),
        )
    return Finding("jwt-localstorage", "P1", "ok", "no JWT localStorage storage detected")
