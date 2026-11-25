"""Turn a committed benchmark fixture into a scannable project.

Fixtures are committed without anything that looks like a credential, so secret
scanners and push protection stay quiet. Two conventions make that possible:

- `{{SECRET:<kind>}}` (optionally `{{SECRET:<kind>:<seed>}}`) is replaced by a synthetic,
  deterministic value with the real key's shape. The values are generated here at run
  time and never existed at any provider.
- A file or directory named `_dot_<name>` is written as `.<name>` (`_dot_env` -> `.env`,
  `_dot_gitignore` -> `.gitignore`, `_dot_git/config` -> `.git/config`), so the fixtures
  do not change how git treats this repository.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import string
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
_PLACEHOLDER = re.compile(r"\{\{SECRET:([a-z_]+)(?::([\w-]+))?\}\}")
_ALNUM = string.ascii_letters + string.digits


def _chars(seed: str, n: int, alphabet: str = _ALNUM) -> str:
    out: list[str] = []
    counter = 0
    while len(out) < n:
        digest = hashlib.sha256(f"{seed}:{counter}".encode()).digest()
        out.extend(alphabet[b % len(alphabet)] for b in digest)
        counter += 1
    return "".join(out[:n])


def _b64(data: dict[str, str]) -> str:
    return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")


def _jwt(role: str, seed: str) -> str:
    header = _b64({"alg": "HS256", "typ": "JWT"})
    payload = _b64({"role": role, "iss": "supabase", "ref": _chars(seed + "ref", 20, string.ascii_lowercase)})
    return f"{header}.{payload}.{_chars(seed + 'sig', 43)}"


def synthetic_secret(kind: str, seed: str = "") -> str:
    """A fake credential of the given kind. Prefixes are assembled from parts on purpose."""
    seed = f"{kind}:{seed}"
    if kind == "stripe_live":
        return "sk_" + "live_" + _chars(seed, 32)
    if kind == "stripe_test":
        return "sk_" + "test_" + _chars(seed, 32)
    if kind == "stripe_whsec":
        return "whsec" + "_" + _chars(seed, 32)
    if kind == "openai":
        return "sk-" + "proj-" + _chars(seed, 48)
    if kind == "anthropic":
        return "sk-" + "ant-" + "api03-" + _chars(seed, 40)
    if kind == "github":
        return "gh" + "p_" + _chars(seed, 36)
    if kind == "aws":
        return "AK" + "IA" + _chars(seed, 16, string.ascii_uppercase + "234567")
    if kind == "slack":
        return "xo" + "xb-" + _chars(seed, 12, string.digits) + "-" + _chars(seed + "b", 24)
    if kind == "supabase_service_role":
        return _jwt("service_role", seed)
    if kind == "supabase_anon":
        return _jwt("anon", seed)
    if kind == "private_key":
        return "-----BEGIN " + "PRIVATE KEY-----"
    raise ValueError(f"unknown secret kind: {kind}")


def fill(text: str) -> str:
    return _PLACEHOLDER.sub(lambda m: synthetic_secret(m.group(1), m.group(2) or ""), text)


def _real_name(name: str) -> str:
    return "." + name[len("_dot_"):] if name.startswith("_dot_") else name


def materialize(fixture: str | Path, dest: Path) -> Path:
    """Copy a fixture into `dest` (created, must not exist) with secrets filled in and dotfiles restored."""
    src = Path(fixture) if Path(fixture).is_dir() else FIXTURES / str(fixture)
    if not src.is_dir():
        raise FileNotFoundError(f"no such fixture: {fixture}")
    for path in sorted(src.rglob("*")):
        rel = Path(*[_real_name(part) for part in path.relative_to(src).parts])
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(fill(path.read_text(encoding="utf-8")), encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copyfile(path, target)
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def fixture_names() -> list[str]:
    return sorted(p.name for p in FIXTURES.iterdir() if p.is_dir())
