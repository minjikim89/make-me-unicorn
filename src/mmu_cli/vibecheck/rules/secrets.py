"""Secret-leak rules: hardcoded credentials and secrets behind public env prefixes."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from mmu_cli.vibecheck.analysis import JS_SUFFIXES, code, framework_of, low
from mmu_cli.vibecheck.engine import (
    _ENV_SCAN_DEPTH,
    _JWT,
    _REF_REEVE_AUG_2026,
    _SECRET_PATTERNS,
    Finding,
    Location,
    Rule,
    _is_test_path,
    _read,
    _rel,
    _walk_shallow,
    dedupe_locations,
    git_ignored,
    is_env_file,
    loc_at,
    mask,
    register,
)

register(Rule(
    id="secrets",
    title="Hardcoded secret",
    severity="P0",
    summary="A live credential is written into source, config or a dotenv file git does not ignore, so it ships with the repo and its history.",
    fix=(
        "Replace the literal with an environment lookup (os.environ[\"NAME\"] / process.env.NAME), keep the value "
        "in an untracked .env, and add `.env` to .gitignore.\n"
        "Rotate the key at the provider: a value that reached git history stays compromised after removal."
    ),
    fix_variants=(
        ("nextjs", (
            "Move the value to .env.local (git-ignored) and read it with process.env.NAME in server code only "
            "(route handler, server action, server component); never in a \"use client\" file.\n"
            "Rotate the key at the provider: a value that reached git history or a browser bundle stays compromised."
        )),
        ("express", (
            "Move the value to an untracked .env, load it at startup (node --env-file=.env or dotenv) and read process.env.NAME.\n"
            "Rotate the key at the provider: a value that reached git history stays compromised after removal."
        )),
        ("fastapi", (
            "Read the value from the environment (os.environ[\"NAME\"] or a pydantic-settings field without a default) "
            "and keep it in an untracked .env.\n"
            "Rotate the key at the provider: a value that reached git history stays compromised after removal."
        )),
        ("env", (
            "Add the file to .gitignore (`.env*` plus `!.env.example`) and, if it is tracked, run `git rm --cached <file>`.\n"
            "Rotate every key in it that was ever committed or pushed."
        )),
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
    tags=("secrets",),
    confidence="high",
))

register(Rule(
    id="env-not-ignored",
    title="Dotenv file not git-ignored",
    severity="P1",
    summary="A dotenv file with credential-named values is not covered by .gitignore, so the next `git add -A` commits it.",
    fix=(
        "Add `.env*` and `!.env.example` to .gitignore; if the file is already tracked run `git rm --cached <file>` "
        "and rotate the values it held.\n"
        "Keep a committed .env.example with empty values as documentation."
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
    tags=("secrets", "git"),
    confidence="medium",
    repo_level=True,
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


_PLACEHOLDER = re.compile(
    r"x{4,}|\*{3,}|\.{3,}|example|sample|placeholder|dummy|fake|your[_-]?|changeme|change[_-]?me|replace|redacted|todo|<|>|\$\{|\{\{",
    re.IGNORECASE,
)
_ENV_SECRET_TOKENS = {"SECRET", "PASSWORD", "PASSWD", "TOKEN", "KEY", "CREDENTIALS", "PRIVATE"}
_ENV_PUBLIC_TOKENS = {"PUBLIC", "PUBLISHABLE", "ANON", "ID", "URL", "NAME", "PATH", "FILE", "ALGORITHM", "EXPIRE", "EXPIRES", "TTL"}
_ENV_PLACEHOLDER_VALUE = re.compile(
    r"change|your|xxx|example|placeholder|todo|dummy|fake|insecure|<|>|\$\{|^(?:test|dev|secret|password|postgres|admin|root|local)",
    re.IGNORECASE,
)


def is_placeholder(value: str) -> bool:
    """Documentation-style values (a key body of repeated `x`, anything containing EXAMPLE): too uniform or self-described as fake."""
    body = value.rsplit("_", 1)[-1] if "_" in value else value
    return len(set(body)) < 5 or _PLACEHOLDER.search(value) is not None


def _jwt_claims(token: str) -> dict[str, object]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8", errors="ignore"))
        return data if isinstance(data, dict) else {}
    except (ValueError, IndexError, UnicodeDecodeError):
        return {}


def _jwt_role(token: str) -> str:
    return str(_jwt_claims(token).get("role", ""))


def _is_service_role_jwt(token: str) -> bool:
    """A Supabase service_role key. The `supabase start` demo key is public and identical on every machine."""
    claims = _jwt_claims(token)
    return claims.get("role") == "service_role" and claims.get("iss") != "supabase-demo"


# A literal every match of the pattern contains: skips the regex for the files that cannot match.
_SECRET_HINTS: dict[str, tuple[str, ...]] = {
    "Stripe live secret key": ("k_live_",),
    "Stripe test secret key": ("sk_test_",),
    "Stripe webhook signing secret": ("whsec_",),
    "Anthropic API key": ("sk-ant-",),
    "OpenAI API key": ("sk-proj-",),
    "AWS access key id": ("AKIA",),
    "GitHub token": ("ghp_", "gho_", "ghu_", "ghs_", "ghr_"),
    "Slack token": ("xox",),
    "SendGrid API key": ("SG.",),
    "GitLab token": ("glpat-",),
    "Private key block": ("PRIVATE KEY-----",),
}


def secret_hits(text: str) -> list[tuple[int, str]]:
    """(offset, label) of every credential in `text`: known key signatures and Supabase service_role JWTs."""
    hits: list[tuple[int, str]] = []
    for label, pattern in _SECRET_PATTERNS:
        hints = _SECRET_HINTS.get(label)
        if hints and not any(hint in text for hint in hints):
            continue
        for m in pattern.finditer(text):
            if label != "Private key block" and is_placeholder(m.group(0)):
                continue
            hits.append((m.start(), label))
    if "eyJ" in text:
        for m in _JWT.finditer(text):
            if _is_service_role_jwt(m.group(0)):
                hits.append((m.start(), "Supabase service_role JWT"))
    return sorted(hits)


_USE_CLIENT = re.compile(r"""^\s*["']use client["']""", re.MULTILINE)


def _unignored_env_files(root: Path, config_files: list[Path] | None) -> list[Path]:
    """Dotenv files with real values that git does not ignore."""
    envs = [p for p in (config_files or []) if is_env_file(p.name)]
    if config_files is None:
        envs = _env_files(root)
    rels = {_rel(p, root): p for p in envs}
    ignored = git_ignored(root, sorted(rels))
    return [p for rel, p in sorted(rels.items()) if rel not in ignored]


def check_secrets(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Credentials in source and config files, and in dotenv files git does not ignore."""
    offenders: list[str] = []
    details: list[str] = []
    locations: list[Location] = []
    env_files = _unignored_env_files(root, config_files)
    others = [p for p in (config_files or []) if not is_env_file(p.name)]
    client_leak = False
    for path in [*code_files, *others, *env_files]:
        text = _read(path)
        if not text:
            continue
        hits = secret_hits(text)
        if not hits:
            continue
        rel = _rel(path, root)
        offenders.append(rel)
        labels = list(dict.fromkeys(label for _, label in hits))
        if is_env_file(path.name):
            labels = [f"{label} in {rel}, which git does not ignore" for label in labels]
        elif "Supabase service_role JWT" in labels and _USE_CLIENT.search(text[:400]):
            client_leak = True
        details.extend(labels)
        locations.extend(loc_at(path, root, text, pos) for pos, _ in hits)
    if offenders:
        locations = sorted(dedupe_locations(locations), key=lambda loc: (loc.path, loc.line or 0))
        message = f"possible hardcoded secrets in {len(set(offenders))} file(s): " + "; ".join(sorted(set(details)))
        if client_leak:
            message += " (the service_role key is in a \"use client\" file: it bypasses RLS for every visitor)"
        first = root / locations[0].path
        return Finding(
            check="secrets",
            severity="P0",
            status="fail",
            message=message,
            files=sorted(set(offenders)),
            locations=locations,
            framework="env" if is_env_file(first.name) else framework_of(first, root),
        )
    return Finding("secrets", "P0", "ok", "no hardcoded secret signatures detected")


def _credential_name(name: str) -> bool:
    tokens = set(name.upper().split("_"))
    return bool(tokens & _ENV_SECRET_TOKENS) and not (tokens & _ENV_PUBLIC_TOKENS)


def check_env_ignored(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Dotenv files that hold credential-named values and are not git-ignored."""
    locations: list[Location] = []
    names: list[str] = []
    for env in _unignored_env_files(root, config_files):
        rel = _rel(env, root)
        if _is_test_path(rel.replace("/.", "/_")) or re.search(r"\.(?:test|testing|ci|e2e)\b", env.name):
            continue  # test fixtures: values for a throwaway environment
        text = _read(env)
        for m in _ENV_LINE.finditer(text):
            name, value = m.group(1), _dotenv_value(m.group(2))
            if name.startswith(_PUBLIC_ENV_PREFIXES) or not _credential_name(name):
                continue
            if len(value) < 8 or _ENV_PLACEHOLDER_VALUE.search(value):
                continue
            locations.append(loc_at(env, root, text, m.start(1), snippet=f"{name}={mask(value)}"))
            names.append(name)
            break  # one anchor per file is enough
    if locations:
        files = [loc.path for loc in locations]
        return Finding(
            "env-not-ignored",
            "P1",
            "warn",
            f"{len(files)} dotenv file(s) with credential-named values are not git-ignored: " + ", ".join(files[:5]),
            files=files,
            locations=locations,
        )
    return Finding("env-not-ignored", "P1", "ok", "dotenv files with credentials are git-ignored (or absent)")


def _env_files(root: Path) -> list[Path]:
    """Dotenv files at the root and in nested app packages (monorepos)."""
    out: list[Path] = []
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        try:
            for p in d.iterdir():
                if p.is_file() and is_env_file(p.name):
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


# Providers whose API keys are server-only: a public-prefixed name for one of them is always a leak.
# (Stripe, Firebase, PostHog, Supabase and map providers have keys meant for the browser, so they are not listed.)
_SERVER_ONLY_PROVIDERS = {
    "OPENAI", "ANTHROPIC", "CLAUDE", "GEMINI", "MISTRAL", "GROQ", "REPLICATE", "COHERE", "DEEPSEEK", "OPENROUTER",
    "ELEVENLABS", "HUGGINGFACE", "PINECONE", "RESEND", "SENDGRID", "MAILGUN", "POSTMARK", "TWILIO", "XAI", "PERPLEXITY",
    "TOGETHER", "FIREWORKS",
}


def _server_only_name(name: str) -> bool:
    tokens = set(name.upper().split("_"))
    return bool(tokens & _SERVER_ONLY_PROVIDERS) and bool(tokens & {"KEY", "TOKEN"})


def check_client_bundle_secrets(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
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
            if _JWT.fullmatch(value) and _is_service_role_jwt(value):
                details.add(f"{name} (Supabase service_role JWT)")
            elif any(pat.search(value) for _, pat in _SECRET_PATTERNS):
                details.add(f"{name} (matches a known secret signature)")
            elif value and _secretish_name(name):
                details.add(f"{name} (secret-looking name with a public prefix)")
            elif value and _server_only_name(name):
                details.add(f"{name} (server-only API key behind a public prefix)")
            else:
                continue
            locations.append(loc_at(env, root, text, m.start(1), snippet=f"{name}={mask(value)}"))
    for path in code_files:
        if path.suffix.lower() not in JS_SUFFIXES:
            continue
        text = code(path)
        for m in _PUBLIC_ENV_IN_CODE.finditer(text):
            if _secretish_name(m.group(1)) or _server_only_name(m.group(1)):
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
            framework=framework_of(root / locations[0].path, root),
        )
    return Finding("client-bundle-secrets", "P0", "ok", "no secrets behind public env prefixes")


register(Rule(
    id="jwt-secret-default",
    title="Signing secret with a hardcoded value or fallback",
    severity="P0",
    summary="A JWT/session secret that is a string literal, or falls back to one when the env var is missing, lets anyone who reads the code forge tokens for any user.",
    fix=(
        "Read the secret from the environment with no fallback and fail at startup when it is missing; "
        "generate the value with `openssl rand -hex 32` and rotate it if the literal was ever deployed."
    ),
    fix_variants=(
        ("fastapi", (
            "Declare the setting without a default so startup fails when it is missing: `jwt_secret: str` in a "
            "pydantic-settings class, or os.environ[\"JWT_SECRET\"]. Generate the value with `openssl rand -hex 32`."
        )),
        ("flask", "Use app.secret_key = os.environ[\"SECRET_KEY\"] (no default) and generate the value with `python -c 'import secrets; print(secrets.token_hex(32))'`."),
        ("django", "Use SECRET_KEY = os.environ[\"DJANGO_SECRET_KEY\"] (no default) and generate the value with `python -c 'from django.core.management.utils import get_random_secret_key as g; print(g())'`."),
        ("express", (
            "Read it once at startup and stop when it is missing: `const secret = process.env.JWT_SECRET; if (!secret) throw new Error(\"JWT_SECRET is not set\")`. "
            "Generate the value with `openssl rand -hex 32`."
        )),
        ("nextjs", (
            "Read process.env.AUTH_SECRET (or JWT_SECRET) with no `||` fallback and throw when it is missing; set it in "
            ".env.local and in the deployment environment. Generate the value with `openssl rand -hex 32`."
        )),
    ),
    ref="https://cwe.mitre.org/data/definitions/798.html",
    tags=("secrets", "auth"),
    confidence="high",
))

_SECRET_NAME = (
    r"(?:jwt|session|cookie|auth|token|signing|nextauth|app|flask|django|api|hmac|encryption|access_token|refresh_token)?"
    r"[_-]?(?:secret(?:[_-]?key)?|signing[_-]?key|private[_-]?key)"
)
_PY_SECRET_ASSIGN = re.compile(
    r"(?<![\w.\"'])(?P<name>(?:\w+\.)?" + _SECRET_NAME + r")\s*(?::\s*[\w\[\], |.]+?)?\s*=\s*(?P<q>[\"'])(?P<value>[^\"'\n]+)(?P=q)\s*(?:[,)#\n]|$)",
    re.IGNORECASE,
)
_PY_ENV_OR = re.compile(
    r"(?<![\w.])(?P<name>(?:\w+\.)?" + _SECRET_NAME + r")\s*(?::\s*[\w\[\], |.]+?)?\s*=\s*[^\n#]*?\b(?:environ|getenv|env|config)\b[^\n#]*?"
    r"\bor\s+(?P<q>[\"'])(?P<value>[^\"'\n]+)(?P=q)",
    re.IGNORECASE,
)
_PY_ENV_DEFAULT = re.compile(
    r"(?:os\.getenv|os\.environ\.get|environ\.get|env\.str|env\(|config\(|getenv)\(\s*[\"'](?P<name>\w*(?:SECRET|SIGNING_KEY)\w*)[\"']\s*,\s*"
    r"(?:default\s*=\s*)?(?P<q>[\"'])(?P<value>[^\"'\n]+)(?P=q)",
)
_JS_ENV_DEFAULT = re.compile(
    r"(?:process\.env|import\.meta\.env|env|Deno\.env)(?:\.|\[\s*[\"'])(?P<name>\w*(?:SECRET|SIGNING_KEY)\w*)(?:[\"']\s*\])?\s*(?:\|\||\?\?)\s*"
    r"(?P<q>[\"'`])(?P<value>[^\"'`\n$]+)(?P=q)"
)
_JS_SECRET_ASSIGN = re.compile(
    r"\b(?:const|let|var)\s+(?P<name>\w*(?:secret|signing_?key)\w*)\s*(?::\s*string\s*)?=\s*(?P<q>[\"'`])(?P<value>[^\"'`\n$]+)(?P=q)",
    re.IGNORECASE,
)
_JS_SIGN_LITERAL = re.compile(
    r"\bjwt\.(?:sign|verify)\(\s*[^,()]+(?:\([^()]*\))?\s*,\s*(?P<q>[\"'`])(?P<value>[^\"'`\n$]+)(?P=q)|"
    r"\bsession\(\s*\{[^}]{0,200}?\bsecret\s*:\s*(?P<q2>[\"'`])(?P<value2>[^\"'`\n$]+)(?P=q2)"
)
# Names that hold the *name* of a setting, a header or a public value rather than the secret itself.
_NOT_A_SECRET_NAME = re.compile(
    r"(?:_name|_env|_var|_header|_field|_id|_path|_file|_url|_uri|_alg|_algorithm|_prefix|_label|_type|_length|_param|_arn|name|header|label|public\w*)$",
    re.IGNORECASE,
)
_NOT_A_SECRET_VALUE = re.compile(r"^\s*$|[{}<>]|^(?:HS|RS|ES|PS)\d{3}$|^/|^\w+://|^(?:true|false|none|null)$", re.IGNORECASE)
_ENV_VAR_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")  # the value is the *name* of a variable, e.g. JWT_SECRET_ENV = "JWT_SECRET"


def _secret_default_hits(path: Path, text: str) -> list[tuple[int, str, str]]:
    suffix = path.suffix.lower()
    patterns = (_PY_SECRET_ASSIGN, _PY_ENV_DEFAULT, _PY_ENV_OR) if suffix == ".py" else (_JS_ENV_DEFAULT, _JS_SECRET_ASSIGN, _JS_SIGN_LITERAL)
    hits: list[tuple[int, str, str]] = []
    for pattern in patterns:
        for m in pattern.finditer(text):
            groups = m.groupdict()
            value = groups.get("value") or groups.get("value2") or ""
            name = groups.get("name") or "secret"
            if _NOT_A_SECRET_VALUE.search(value) or _ENV_VAR_NAME.match(value) or _NOT_A_SECRET_NAME.search(name):
                continue
            kind = "env fallback" if pattern in (_PY_ENV_DEFAULT, _PY_ENV_OR, _JS_ENV_DEFAULT) else "literal"
            hits.append((m.start(), f"{name.split('.')[-1]} ({kind})", value))
    return hits


def check_jwt_secret_default(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Signing secrets assigned a string literal, or read from the environment with a literal fallback."""
    locations: list[Location] = []
    details: list[str] = []
    for path in code_files:
        suffix = path.suffix.lower()
        if (suffix != ".py" and suffix not in JS_SUFFIXES) or _is_test_path(_rel(path, root)):
            continue
        lowered = low(path)
        if "secret" not in lowered and "signing" not in lowered and "private_key" not in lowered:
            continue
        text = code(path)
        for pos, detail, value in _secret_default_hits(path, text):
            start = text.rfind("\n", 0, pos) + 1
            end = text.find("\n", pos)
            line = text[start: end if end >= 0 else len(text)].strip()
            locations.append(loc_at(path, root, text, pos, snippet=line.replace(value, mask(value))[:160]))
            details.append(detail)
    if locations:
        locations = dedupe_locations(locations)
        files = sorted({loc.path for loc in locations})
        return Finding(
            "jwt-secret-default",
            "P0",
            "fail",
            f"signing secret hardcoded or given a literal fallback in {len(files)} file(s): " + ", ".join(sorted(set(details))[:6]),
            files=files,
            locations=locations,
            framework=framework_of(root / locations[0].path, root),
        )
    return Finding("jwt-secret-default", "P0", "ok", "no hardcoded signing secrets or literal fallbacks")
