"""`mmu vibecheck` — fast scan for the failure modes AI-generated code ships most.

Heuristic, zero-dependency, read-only. Each check answers one question a solo
builder forgets to ask before launch: leaked secrets, unverified webhooks,
missing password reset, no rate limiting, wildcard CORS, f-string SQL,
debug mode left on, no error monitoring, secrets behind public env prefixes,
Supabase tables without RLS, production source maps, command-executing
`.git/config` keys.

Checks carry a `ref` — the incident report or dataset that motivated them — so a
finding is never "the tool says so" but "here is what happened to people who shipped this".

Severities: P0 findings exit non-zero (block launch), P1 findings warn.
Checks that find no relevant surface (e.g. no webhook handlers) report SKIP.
"""

from __future__ import annotations

import ast
import base64
import json
import re
from dataclasses import asdict, dataclass, field
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
    'access-control-allow-origin", "*"',  # header tuple form: ("...", "*")
    'access-control-allow-origin": "*"',  # dict form: {"...": "*"}
    "access-control-allow-origin': '*'",
    "access-control-allow-origin'] = '*'",
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
    ref: str = ""  # URL of the real-world incident / dataset that motivates the check

    def to_dict(self) -> dict:
        return asdict(self)


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


def _is_safe_yaml_loader(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id in {"SafeLoader", "CSafeLoader"}
    if isinstance(node, ast.Attribute):
        return node.attr in {"SafeLoader", "CSafeLoader"}
    return False


class _UnsafeDeserializationVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.pickle_modules = {"pickle"}
        self.pickle_loaders: dict[str, str] = {}
        self.yaml_modules = {"yaml"}
        self.yaml_loaders: set[str] = set()
        self.details: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            imported_as = alias.asname or alias.name
            if alias.name == "pickle":
                self.pickle_modules.add(imported_as)
            elif alias.name == "yaml":
                self.yaml_modules.add(imported_as)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "pickle":
            for alias in node.names:
                if alias.name in {"load", "loads"}:
                    self.pickle_loaders[alias.asname or alias.name] = alias.name
        elif node.module == "yaml":
            for alias in node.names:
                if alias.name == "load":
                    self.yaml_loaders.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_pickle_loader_call(node):
            self.details.add(self._pickle_label(node))
        elif self._is_unsafe_yaml_load_call(node):
            self.details.add("yaml.load without SafeLoader")
        self.generic_visit(node)

    def _is_pickle_loader_call(self, node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"load", "loads"}:
            return isinstance(func.value, ast.Name) and func.value.id in self.pickle_modules
        return isinstance(func, ast.Name) and func.id in self.pickle_loaders

    def _pickle_label(self, node: ast.Call) -> str:
        func = node.func
        if isinstance(func, ast.Attribute):
            return f"pickle.{func.attr}"
        if isinstance(func, ast.Name):
            return f"pickle.{self.pickle_loaders[func.id]}"
        return "pickle.load"

    def _is_unsafe_yaml_load_call(self, node: ast.Call) -> bool:
        func = node.func
        is_yaml_load = False
        if isinstance(func, ast.Attribute) and func.attr == "load":
            is_yaml_load = isinstance(func.value, ast.Name) and func.value.id in self.yaml_modules
        elif isinstance(func, ast.Name):
            is_yaml_load = func.id in self.yaml_loaders
        if not is_yaml_load:
            return False
        return not any(keyword.arg == "Loader" and _is_safe_yaml_loader(keyword.value) for keyword in node.keywords)


def _unsafe_deserialization_details(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    visitor = _UnsafeDeserializationVisitor()
    visitor.visit(tree)
    return visitor.details


def check_unsafe_deserialization(root: Path, code_files: list[Path]) -> Finding:
    offenders: list[str] = []
    details: list[str] = []
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        text = _read(path)
        file_details = _unsafe_deserialization_details(text)
        if file_details:
            offenders.append(_rel(path, root))
            details.extend(sorted(file_details))
    if offenders:
        return Finding(
            "unsafe-deserialization",
            "P0",
            "fail",
            f"unsafe deserialization in {len(offenders)} file(s): " + ", ".join(sorted(set(details))),
            hint="Do not deserialize untrusted input with pickle or unsafe YAML loaders. Prefer JSON or yaml.safe_load.",
            files=sorted(set(offenders)),
        )
    return Finding("unsafe-deserialization", "P0", "ok", "no unsafe Python deserialization detected")


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


# --- Evidence refs: every new check points at the data that motivated it. ---
_REF_REEVE_AUG_2026 = "https://vibe-eval.com/updates/vibe-coding-security-monthly-aug-2026/"
_REF_GITSPAWN = "https://www.manifold.security/blog/ai-coding-agents-git-hijack"

_PUBLIC_ENV_PREFIXES = ("NEXT_PUBLIC_", "VITE_", "REACT_APP_", "EXPO_PUBLIC_", "NUXT_PUBLIC_", "PUBLIC_", "GATSBY_")
# Name tokens (split on "_") that mean "this value is a credential". Whole tokens only,
# so PRIVATE_BETA / SECRETARY_EMAIL / SK_TEST_MODE do not match.
_SECRET_TOKEN_SEQS = (
    ("SECRET",), ("SERVICE", "ROLE"), ("SERVICE", "KEY"), ("PRIVATE", "KEY"),
    ("SIGNING", "KEY"), ("ACCESS", "TOKEN"), ("REFRESH", "TOKEN"),
)
_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)$", re.MULTILINE)
_ENV_SCAN_DEPTH = 3  # apps/web/.env.local in a monorepo; deeper is build output or vendored code
_JWT = re.compile(r"\beyJ[0-9A-Za-z_-]{10,}\.eyJ[0-9A-Za-z_-]{10,}\.[0-9A-Za-z_-]{10,}\b")
_PUBLIC_ENV_IN_CODE = re.compile(
    r"(?:process\.env|import\.meta\.env)\.((?:" + "|".join(_PUBLIC_ENV_PREFIXES) + r")[A-Z0-9_]+)"
)

# Markers must be Supabase-specific: `createClient(` alone matches redis/viem/sanity/urql.
_SUPABASE_MARKERS = ("@supabase/supabase-js", "@supabase/ssr", "supabase.co", "supabase-py", "from supabase import", "supabase_py")
_SQL_IDENT = r"(?:\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?\.)?\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?"
_SQL_CREATE_TABLE = re.compile(r"create\s+(?:unlogged\s+)?table\s+(?:if\s+not\s+exists\s+)?" + _SQL_IDENT, re.IGNORECASE)
_SQL_ENABLE_RLS = re.compile(
    r"alter\s+table\s+(?:only\s+)?(?:if\s+exists\s+)?" + _SQL_IDENT + r"\s+enable\s+row\s+level\s+security", re.IGNORECASE
)
_SQL_LINE_COMMENT = re.compile(r"--[^\n]*")
_SQL_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

_SOURCEMAP_SIGNALS: list[tuple[str, re.Pattern[str]]] = [
    ("vite build.sourcemap", re.compile(r"\bsourcemap\s*:\s*(?:true|['\"]inline['\"])")),
    ("next productionBrowserSourceMaps", re.compile(r"\bproductionBrowserSourceMaps\s*:\s*true\b")),
    ("webpack devtool", re.compile(r"\bdevtool\s*:\s*['\"](?:source-map|inline-source-map|eval-source-map)['\"]")),
]
_BUILD_CONFIG_NAMES = (
    "vite.config.ts", "vite.config.js", "vite.config.mts", "vite.config.mjs",
    "next.config.js", "next.config.mjs", "next.config.ts",
    "webpack.config.js", "webpack.config.ts", "webpack.config.mjs",
    "astro.config.mjs", "astro.config.ts", "nuxt.config.ts",
)

# `.git/config` keys that make git run a command when an agent (or you) opens the repo,
# with the values that are ordinary tooling rather than an attack.
_GIT_BOOL = {"true", "false", "1", "0", "yes", "no", "on", "off"}
_TEST_DIR_HINTS = ("tests", "test", "__tests__", "spec", "specs", "fixture", "fixtures", "testdata", "__mocks__")
_TEST_FILE_RE = re.compile(r"^(?:test_.*\.py|.*_test\.(?:py|go)|.*_spec\.rb|.*\.(?:test|spec)\.[cm]?[jt]sx?)$")


def _jwt_role(token: str) -> str:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8", errors="ignore"))
        return str(data.get("role", ""))
    except (ValueError, IndexError, UnicodeDecodeError):
        return ""


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


def _sql_files(root: Path) -> list[Path]:
    """SQL under any `supabase/` directory (root or nested app), pruned like the code walk.

    RLS is a Supabase/Postgres-policy concept; Prisma/Django/`db/` migrations for other
    databases are deliberately not read — a Redis project must never get a Supabase P0.
    """
    from mmu_cli.cli import PRUNE_DIR_NAMES

    out: list[Path] = []
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        sb = d / "supabase"
        if not sb.is_dir():
            continue
        for dirpath, dirnames, filenames in __import__("os").walk(sb):
            dirnames[:] = [x for x in dirnames if x not in PRUNE_DIR_NAMES and not x.startswith(".")]
            for fn in filenames:
                if fn.lower().endswith(".sql"):
                    out.append(Path(dirpath) / fn)
    return sorted(set(out))


def _strip_sql_comments(text: str) -> str:
    return _SQL_LINE_COMMENT.sub("", _SQL_BLOCK_COMMENT.sub("", text))


def _qualified(schema: str | None, name: str) -> str:
    return f"{(schema or 'public').lower()}.{name.lower()}"


def check_supabase_rls(root: Path, code_files: list[Path]) -> Finding:
    """Supabase tables created without Row Level Security.

    With the anon key in the browser, a table without RLS is readable (often writable)
    by anyone. Reeve Aug-2026: 57% of reachable Supabase-backed apps (2,096 of 3,680)
    allowed unauthenticated table reads.
    """
    pkg = (_read(root / "package.json") + _read(root / "requirements.txt") + _read(root / "pyproject.toml")).lower()
    uses_supabase = any(m.lower() in pkg for m in _SUPABASE_MARKERS) or (root / "supabase").is_dir()
    if not uses_supabase:
        for path in code_files[:400]:
            if any(m in _read(path) for m in _SUPABASE_MARKERS):
                uses_supabase = True
                break
    if not uses_supabase:
        return Finding("supabase-rls", "P0", "skip", "no Supabase usage detected")

    sql_files = _sql_files(root)
    if not sql_files:
        return Finding(
            "supabase-rls",
            "P1",
            "warn",
            "Supabase detected but no SQL under supabase/ — RLS cannot be verified from the repo",
            hint="If tables were created in the dashboard, confirm every public table has RLS enabled + a policy. `supabase db pull` brings the schema into the repo so this check can see it.",
            ref=_REF_REEVE_AUG_2026,
        )
    created: dict[str, str] = {}
    rls_enabled: set[str] = set()
    for sql in sql_files:
        text = _strip_sql_comments(_read(sql))
        for schema, name in _SQL_CREATE_TABLE.findall(text):
            created.setdefault(_qualified(schema, name), _rel(sql, root))
        for schema, name in _SQL_ENABLE_RLS.findall(text):
            rls_enabled.add(_qualified(schema, name))
    missing = sorted(t for t in created if t not in rls_enabled)
    if missing:
        return Finding(
            "supabase-rls",
            "P0",
            "fail",
            f"{len(missing)} table(s) created without ENABLE ROW LEVEL SECURITY: " + ", ".join(missing[:8]) + (" …" if len(missing) > 8 else ""),
            hint="Every table reachable with the anon key needs `alter table X enable row level security;` plus at least one policy — otherwise any visitor can read it.",
            files=sorted({created[t] for t in missing}),
            ref=_REF_REEVE_AUG_2026,
        )
    if not created:
        return Finding("supabase-rls", "P0", "ok", "no CREATE TABLE statements found in migrations")
    return Finding("supabase-rls", "P0", "ok", f"RLS enabled on all {len(created)} table(s) found in migrations")


def check_sourcemaps(root: Path, code_files: list[Path]) -> Finding:
    """Production source maps published alongside the bundle (Reeve Aug-2026: 13% of apps)."""
    offenders: list[str] = []
    details: set[str] = set()
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        for name in _BUILD_CONFIG_NAMES:
            cfg = d / name
            if not cfg.is_file():
                continue
            text = _read(cfg)
            for label, pat in _SOURCEMAP_SIGNALS:
                if pat.search(text):
                    offenders.append(_rel(cfg, root))
                    details.add(label)
    if offenders:
        return Finding(
            "sourcemaps-exposed",
            "P1",
            "warn",
            f"production source maps enabled in {len(set(offenders))} build config(s): " + ", ".join(sorted(details)),
            hint="Source maps let anyone read your original source (and the comments, TODOs, and internal URLs in it). Use `hidden` maps uploaded to your error tracker, or disable them for production.",
            files=sorted(set(offenders)),
            ref=_REF_REEVE_AUG_2026,
        )
    return Finding("sourcemaps-exposed", "P1", "ok", "no production source-map flags in build configs")


def _parse_git_config(text: str) -> list[tuple[str, str, str]]:
    """Return (section, key, value) triples; section is lower-cased and includes subsection (e.g. filter.lfs).

    Handles the one-line form `[core] fsmonitor = x` that git accepts.
    """
    out: list[tuple[str, str, str]] = []
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            close = line.find("]")
            header = line[1:close].strip() if close > 0 else line.strip("[]").strip()
            parts = header.split(None, 1)
            section = parts[0].lower()
            if len(parts) > 1:
                section += "." + parts[1].strip().strip('"').lower()
            line = line[close + 1:].strip() if close > 0 else ""
            if not line:
                continue
        if "=" in line:
            key, _, value = line.partition("=")
            out.append((section, key.strip().lower(), value.strip()))
    return out


def _git_config_path(root: Path) -> Path | None:
    """The config git would read for this checkout: `.git/config`, or via a `gitdir:` pointer (worktrees, submodules)."""
    dot_git = root / ".git"
    if dot_git.is_dir():
        cfg = dot_git / "config"
        return cfg if cfg.is_file() else None
    if dot_git.is_file():
        text = _read(dot_git).strip()
        if text.startswith("gitdir:"):
            gitdir = (root / text.split(":", 1)[1].strip()).resolve()
            common = gitdir / "commondir"
            if common.is_file():
                gitdir = (gitdir / _read(common).strip()).resolve()
            cfg = gitdir / "config"
            return cfg if cfg.is_file() else None
    return None


def _git_config_entries(cfg: Path, seen: set[Path] | None = None) -> list[tuple[str, str, str]]:
    """Entries of a config file plus one level of `include.path` files (relative to the config's directory)."""
    seen = seen if seen is not None else set()
    if cfg in seen or len(seen) > 8:
        return []
    seen.add(cfg)
    entries = _parse_git_config(_read(cfg))
    for section, key, value in list(entries):
        if section.split(".", 1)[0] in {"include", "includeif"} and key == "path":
            inc = (cfg.parent / Path(value).expanduser()).resolve()
            if inc.is_file():
                entries.extend(_git_config_entries(inc, seen))
    return entries


def _is_shellish(value: str) -> bool:
    return value.startswith("!") or any(ch in value for ch in "|;&$`")


def _git_config_exec_hit(root: Path, section: str, key: str, value: str) -> bool:
    """True when this entry runs a program on ordinary git use and is not a known-benign tool setting."""
    top = section.split(".", 1)[0]
    v = value.strip().strip('"').strip("'")
    if top == "core":
        if key == "fsmonitor":
            return v.lower() not in _GIT_BOOL  # `true` = builtin daemon; anything else is a command
        if key == "sshcommand":
            first = v.split(None, 1)[0].strip('"').strip("'").lower() if v else ""
            return not (Path(first).name in {"ssh", "plink", "putty"} and not _is_shellish(v))
        if key == "hookspath":
            # husky/lefthook point inside the repo (`.husky/_`); a path outside it or absolute is not yours
            return v.startswith(("/", "~")) or ".." in Path(v).parts
        return key == "askpass"
    if top == "alias":
        return v.startswith("!")
    if top == "credential" and key == "helper":
        return _is_shellish(v) or "/" in v
    if top == "filter" and key in {"clean", "smudge", "process", "required"} and key != "required":
        return not v.startswith("git-lfs ")  # `git lfs install --local` writes exactly these
    if top == "diff" and key == "external":
        return True
    if top == "merge" and key == "driver":
        return True
    return False


def check_git_config_exec(root: Path, code_files: list[Path]) -> Finding:
    """`.git/config` entries that execute commands when the repo is opened.

    GitSpawn (Sep 2026): coding agents run `git status` etc. on startup; keys like
    core.fsmonitor turn that into arbitrary code execution before any approval prompt.
    Follows `gitdir:` pointers (worktrees) and one level of `include.path`.
    """
    cfg = _git_config_path(root)
    if cfg is None:
        return Finding("git-config-exec", "P0", "skip", "no git config found for this checkout")
    hits: list[str] = []
    for section, key, value in _git_config_entries(cfg):
        if _git_config_exec_hit(root, section, key, value):
            hits.append(f"{section}.{key} = {value[:60]}")
    if hits:
        return Finding(
            "git-config-exec",
            "P0",
            "fail",
            f"git config contains {len(hits)} command-executing key(s): " + "; ".join(hits[:5]),
            hint="These keys run a program whenever git (or your coding agent) touches the repo. If you did not set them yourself, the repo you cloned/unzipped is hostile — remove them before opening it in an agent.",
            files=[_rel(cfg, root)],
            ref=_REF_GITSPAWN,
        )
    return Finding("git-config-exec", "P0", "ok", "no command-executing keys in git config")


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


def run_vibecheck(root: Path) -> list[Finding]:
    from mmu_cli.cli import doctor_skip_paths, gather_code_files

    _READ_CACHE.clear()
    skip_paths = doctor_skip_paths(root)
    code_files = gather_code_files(root, skip_paths)

    findings: list[Finding] = []
    findings.append(check_secrets(root, code_files))
    findings.extend(check_webhooks(root, code_files))
    findings.append(check_password_reset(root, code_files))
    findings.append(check_sql_strings(root, code_files))
    findings.append(check_unsafe_deserialization(root, code_files))
    findings.append(check_rate_limiting(root, code_files))
    findings.append(check_cors(root, code_files))
    findings.append(check_debug_mode(root, code_files))
    findings.append(check_error_monitoring(root, code_files))
    findings.append(check_client_bundle_secrets(root, code_files))
    findings.append(check_supabase_rls(root, code_files))
    findings.append(check_sourcemaps(root, code_files))
    findings.append(check_git_config_exec(root, code_files))
    return downgrade_test_only_findings(findings)


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
            if f.ref:
                lines.append(f"        ↳ why: {f.ref}")
    lines.append("")
    if fails:
        lines.append(f"Vibe check result: {len(fails)} launch-blocking issue(s), {len(warns)} warning(s)")
        return lines, 2
    if warns:
        lines.append(f"Vibe check result: no blockers, {len(warns)} warning(s)")
        return lines, 0
    lines.append("Vibe check result: clean ✨")
    return lines, 0
