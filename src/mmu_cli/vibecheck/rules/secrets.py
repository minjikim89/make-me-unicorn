"""Secret-leak rules: hardcoded credentials and secrets behind public env prefixes."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from mmu_cli.vibecheck.engine import _ENV_SCAN_DEPTH, _REF_REEVE_AUG_2026, Finding, _read, _rel, _walk_shallow

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


_PUBLIC_ENV_PREFIXES = ("NEXT_PUBLIC_", "VITE_", "REACT_APP_", "EXPO_PUBLIC_", "NUXT_PUBLIC_", "PUBLIC_", "GATSBY_")
# Name tokens (split on "_") that mean "this value is a credential". Whole tokens only,
# so PRIVATE_BETA / SECRETARY_EMAIL / SK_TEST_MODE do not match.
_SECRET_TOKEN_SEQS = (
    ("SECRET",), ("SERVICE", "ROLE"), ("SERVICE", "KEY"), ("PRIVATE", "KEY"),
    ("SIGNING", "KEY"), ("ACCESS", "TOKEN"), ("REFRESH", "TOKEN"),
)
_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)$", re.MULTILINE)


_JWT = re.compile(r"\beyJ[0-9A-Za-z_-]{10,}\.eyJ[0-9A-Za-z_-]{10,}\.[0-9A-Za-z_-]{10,}\b")
_PUBLIC_ENV_IN_CODE = re.compile(
    r"(?:process\.env|import\.meta\.env)\.((?:" + "|".join(_PUBLIC_ENV_PREFIXES) + r")[A-Z0-9_]+)"
)


def check_secrets(root: Path, code_files: list[Path]) -> Finding:
    offenders: list[str] = []
    details: list[str] = []
    env_file = root / ".env"
    for path in code_files:
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
    offenders: list[str] = []
    details: set[str] = set()
    for env in _env_files(root):
        for name, raw in _ENV_LINE.findall(_read(env)):
            if not name.startswith(_PUBLIC_ENV_PREFIXES):
                continue
            value = _dotenv_value(raw)
            if _JWT.fullmatch(value) and _jwt_role(value) == "service_role":
                details.add(f"{name} (Supabase service_role JWT)")
                offenders.append(_rel(env, root))
            elif any(pat.search(value) for _, pat in _SECRET_PATTERNS):
                details.add(f"{name} (matches a known secret signature)")
                offenders.append(_rel(env, root))
            elif value and _secretish_name(name):
                details.add(f"{name} (secret-looking name with a public prefix)")
                offenders.append(_rel(env, root))
    for path in code_files:
        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".mts", ".cjs"}:
            continue
        for name in _PUBLIC_ENV_IN_CODE.findall(_read(path)):
            if _secretish_name(name):
                details.add(f"{name} (read in client code)")
                offenders.append(_rel(path, root))
    if offenders:
        return Finding(
            "client-bundle-secrets",
            "P0",
            "fail",
            f"secret shipped to the browser bundle via public env prefix in {len(set(offenders))} file(s): " + "; ".join(sorted(details)),
            hint="Anything prefixed NEXT_PUBLIC_/VITE_/REACT_APP_ is inlined into the JS every visitor downloads. Move it server-side and rotate it.",
            files=sorted(set(offenders)),
            ref=_REF_REEVE_AUG_2026,
        )
    return Finding("client-bundle-secrets", "P0", "ok", "no secrets behind public env prefixes")
