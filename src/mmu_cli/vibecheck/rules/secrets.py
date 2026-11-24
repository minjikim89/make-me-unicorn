"""Secret-leak rules: hardcoded credentials and secrets behind public env prefixes."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from mmu_cli.vibecheck.engine import (
    _ENV_SCAN_DEPTH,
    _JWT,
    _REF_REEVE_AUG_2026,
    _SECRET_PATTERNS,
    Finding,
    Location,
    Rule,
    _read,
    _rel,
    _walk_shallow,
    dedupe_locations,
    loc_at,
    mask,
    register,
)

register(Rule(
    id="secrets",
    title="Hardcoded secret",
    severity="P0",
    summary="A live credential is written into source or an untracked-but-unignored .env, so it ships with the repo and its history.",
    fix=(
        "Replace the literal with an environment lookup (os.environ[\"NAME\"] / process.env.NAME), keep the value "
        "in an untracked .env, and add `.env` to .gitignore.\n"
        "Rotate the key at the provider: a value that reached git history stays compromised after removal."
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
    tags=("secrets",),
    confidence="high",
))

register(Rule(
    id="client-bundle-secrets",
    title="Secret behind a public env prefix",
    severity="P0",
    summary="Env vars prefixed NEXT_PUBLIC_/VITE_/REACT_APP_ are inlined into the JavaScript every visitor downloads, so a secret named that way is public.",
    fix=(
        "Rename the variable without the public prefix and read it only in server code (route handler, server "
        "action, API endpoint); have the browser call that endpoint instead of using the secret directly.\n"
        "Rotate the value: anything built into a client bundle is already public."
    ),
    ref=_REF_REEVE_AUG_2026,
    tags=("secrets", "frontend"),
    confidence="high",
))

_PUBLIC_ENV_PREFIXES = ("NEXT_PUBLIC_", "VITE_", "REACT_APP_", "EXPO_PUBLIC_", "NUXT_PUBLIC_", "PUBLIC_", "GATSBY_")
# Name tokens (split on "_") that mean "this value is a credential". Whole tokens only,
# so PRIVATE_BETA / SECRETARY_EMAIL / SK_TEST_MODE do not match.
_SECRET_TOKEN_SEQS = (
    ("SECRET",), ("SERVICE", "ROLE"), ("SERVICE", "KEY"), ("PRIVATE", "KEY"),
    ("SIGNING", "KEY"), ("ACCESS", "TOKEN"), ("REFRESH", "TOKEN"),
)
_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)$", re.MULTILINE)


_PUBLIC_ENV_IN_CODE = re.compile(
    r"(?:process\.env|import\.meta\.env)\.((?:" + "|".join(_PUBLIC_ENV_PREFIXES) + r")[A-Z0-9_]+)"
)


def check_secrets(root: Path, code_files: list[Path]) -> Finding:
    offenders: list[str] = []
    details: list[str] = []
    locations: list[Location] = []
    env_file = root / ".env"
    for path in code_files:
        text = _read(path)
        if not text:
            continue
        first_label = ""
        for label, pattern in _SECRET_PATTERNS:
            for m in pattern.finditer(text):
                first_label = first_label or label
                locations.append(loc_at(path, root, text, m.start()))
        if first_label:
            offenders.append(_rel(path, root))
            details.append(first_label)
    if env_file.is_file():
        gitignore = _read(root / ".gitignore")
        ignored = any(line.strip() in {".env", "*.env", ".env*"} for line in gitignore.splitlines())
        if not ignored:
            offenders.append(".env")
            details.append(".env exists but .gitignore does not cover it")
            locations.append(Location(".env"))
    if offenders:
        return Finding(
            check="secrets",
            severity="P0",
            status="fail",
            message=f"possible hardcoded secrets in {len(offenders)} file(s): " + "; ".join(sorted(set(details))),
            files=sorted(set(offenders)),
            locations=sorted(dedupe_locations(locations), key=lambda loc: (loc.path, loc.line or 0)),
        )
    return Finding("secrets", "P0", "ok", "no hardcoded secret signatures detected")


def _jwt_role(token: str) -> str:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8", errors="ignore"))
        return str(data.get("role", ""))
    except (ValueError, IndexError, UnicodeDecodeError):
        return ""


def _env_files(root: Path) -> list[Path]:
    """Dotenv files at the root and in nested app packages (monorepos)."""
    out: list[Path] = []
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        try:
            for p in d.iterdir():
                if not p.is_file() or not p.name.startswith(".env"):
                    continue
                if p.name == ".envrc" or p.name.endswith((".example", ".sample", ".template")):
                    continue
                out.append(p)
        except OSError:
            continue
    return sorted(out)


def _dotenv_value(raw: str) -> str:
    """Value part of a dotenv line: honour quotes, drop inline ` # comment`."""
    raw = raw.strip()
    if raw[:1] in {"'", '"'}:
        q = raw[0]
        end = raw.find(q, 1)
        return raw[1:end] if end > 0 else raw[1:]
    return re.split(r"\s+#", raw, maxsplit=1)[0].strip()


def _secretish_name(name: str) -> bool:
    tokens = tuple(name.upper().split("_"))
    for seq in _SECRET_TOKEN_SEQS:
        n = len(seq)
        if any(tokens[i:i + n] == seq for i in range(len(tokens) - n + 1)):
            return True
    return False


def check_client_bundle_secrets(root: Path, code_files: list[Path]) -> Finding:
    """Secrets that the framework will inline into the browser bundle.

    Public-prefixed env vars (NEXT_PUBLIC_, VITE_, …) are shipped to every visitor.
    Reeve's Aug-2026 scan: 1 in 23 live vibe-coded apps shipped a secret this way.
    """
    locations: list[Location] = []
    details: set[str] = set()
    for env in _env_files(root):
        text = _read(env)
        for m in _ENV_LINE.finditer(text):
            name, raw = m.group(1), m.group(2)
            if not name.startswith(_PUBLIC_ENV_PREFIXES):
                continue
            value = _dotenv_value(raw)
            if _JWT.fullmatch(value) and _jwt_role(value) == "service_role":
                details.add(f"{name} (Supabase service_role JWT)")
            elif any(pat.search(value) for _, pat in _SECRET_PATTERNS):
                details.add(f"{name} (matches a known secret signature)")
            elif value and _secretish_name(name):
                details.add(f"{name} (secret-looking name with a public prefix)")
            else:
                continue
            locations.append(loc_at(env, root, text, m.start(1), snippet=f"{name}={mask(value)}"))
    for path in code_files:
        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".mts", ".cjs"}:
            continue
        text = _read(path)
        for m in _PUBLIC_ENV_IN_CODE.finditer(text):
            if _secretish_name(m.group(1)):
                details.add(f"{m.group(1)} (read in client code)")
                locations.append(loc_at(path, root, text, m.start()))
    if locations:
        locations = dedupe_locations(locations)
        files = sorted({loc.path for loc in locations})
        return Finding(
            "client-bundle-secrets",
            "P0",
            "fail",
            f"secret shipped to the browser bundle via public env prefix in {len(files)} file(s): " + "; ".join(sorted(details)),
            files=files,
            locations=locations,
        )
    return Finding("client-bundle-secrets", "P0", "ok", "no secrets behind public env prefixes")
