"""Shared source analysis for rules: comment stripping, local imports, frameworks, route and auth markers.

Everything here is cached per scan (see `engine.run_cache`) and works on text, not on a
real parser, so it stays fast and dependency-free. Offsets in comment-stripped text equal
offsets in the original, so matches map straight to line numbers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from mmu_cli.vibecheck.engine import _ENV_SCAN_DEPTH, _is_test_path, _read, _rel, _walk_shallow, run_cache

JS_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".mts", ".cjs", ".cts", ".vue", ".svelte"}
_SLASH_COMMENT_SUFFIXES = JS_SUFFIXES | {".go", ".java", ".cs", ".php", ".rs", ".kt", ".swift", ".dart"}
_HASH_COMMENT_SUFFIXES = {".py", ".rb", ".sh", ".yml", ".yaml", ".toml"}

# Strings are matched so that comment markers inside them are left alone.
_SLASH_TOKEN = re.compile(
    r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`|(?<![:\\])//[^\n]*|/\*[\s\S]*?\*/'
)
_HASH_TOKEN = re.compile(
    r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|#[^\n]*'
)

_CODE_CACHE: dict[Path, tuple[str, str]] = run_cache()  # path -> (raw text it was derived from, stripped text)
_LOW_CACHE: dict[Path, tuple[str, str]] = run_cache()
_TEST_CACHE: dict[tuple[Path, Path], bool] = run_cache()
_FACTS: dict[tuple[str, Path], object] = run_cache()


def _blank(text: str) -> str:
    return re.sub(r"[^\n]", " ", text)


def strip_comments(text: str, suffix: str) -> str:
    """`text` with comments replaced by spaces (same length, same line breaks)."""
    suffix = suffix.lower()
    if suffix in _SLASH_COMMENT_SUFFIXES:
        return _SLASH_TOKEN.sub(lambda m: _blank(m.group(0)) if m.group(0)[0] == "/" else m.group(0), text)
    if suffix in _HASH_COMMENT_SUFFIXES:
        if suffix == ".py":
            return _HASH_TOKEN.sub(lambda m: _blank_python_token(m, text), text)
        return _HASH_TOKEN.sub(lambda m: _blank(m.group(0)) if m.group(0)[0] == "#" else m.group(0), text)
    return text


def _blank_python_token(m: re.Match[str], text: str) -> str:
    """Blank `#` comments and docstrings (a triple-quoted string that starts its own statement)."""
    token = m.group(0)
    if token[0] == "#":
        return _blank(token)
    if token[:3] in {'"""', "'''"}:
        line_start = text.rfind("\n", 0, m.start()) + 1
        if not text[line_start: m.start()].strip():
            return _blank(token)
    return token


def code(path: Path) -> str:
    """Content of `path` with comments blanked: what counts as evidence of a safeguard."""
    raw = _read(path)
    cached = _CODE_CACHE.get(path)
    if cached is None or cached[0] is not raw:
        cached = (raw, strip_comments(raw, path.suffix))
        _CODE_CACHE[path] = cached
    return cached[1]


def low(path: Path) -> str:
    """Lower-cased `code(path)`, for cheap substring pre-checks before a regex runs."""
    stripped = code(path)
    cached = _LOW_CACHE.get(path)
    if cached is None or cached[0] is not stripped:
        cached = (stripped, stripped.lower())
        _LOW_CACHE[path] = cached
    return cached[1]


def is_test_file(path: Path, root: Path) -> bool:
    key = (path, root)
    if key not in _TEST_CACHE:
        _TEST_CACHE[key] = _is_test_path(_rel(path, root))
    return _TEST_CACHE[key]


# --- Manifests and frameworks ------------------------------------------------

_REQ_NAME = re.compile(r"^[ \t]*([A-Za-z0-9][A-Za-z0-9._-]*)", re.MULTILINE)
_PYPROJECT_DEP = re.compile(r"""["']([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?:[<>=!~;].*?)?["']""")
_POETRY_DEP = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*=", re.MULTILINE)


def project_deps(root: Path) -> set[str]:
    """Lower-cased dependency names declared in manifests at the root and in nested app packages."""
    key = ("deps", root)
    if key in _FACTS:
        return _FACTS[key]  # type: ignore[return-value]
    deps: set[str] = set()
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        pkg = _read(d / "package.json")
        if pkg:
            try:
                data = json.loads(pkg)
            except ValueError:
                data = {}
            if isinstance(data, dict):
                for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    block = data.get(section)
                    if isinstance(block, dict):
                        deps.update(str(name).lower() for name in block)
        for name in ("requirements.txt", "requirements-prod.txt", "requirements/base.txt", "requirements/prod.txt"):
            deps.update(m.lower() for m in _REQ_NAME.findall(_read(d / name)))
        pyproject = _read(d / "pyproject.toml")
        if pyproject:
            deps.update(m.lower() for m in _PYPROJECT_DEP.findall(pyproject))
            deps.update(m.lower() for m in _POETRY_DEP.findall(pyproject))
        deps.update(m.lower() for m in _POETRY_DEP.findall(_read(d / "Pipfile")))
    deps = {d.replace("_", "-") for d in deps}
    _FACTS[key] = deps
    return deps


_SERVER_DEPS = {
    "express": "express", "fastify": "fastify", "koa": "koa", "hono": "hono", "@nestjs/core": "nestjs",
    "next": "nextjs", "@remix-run/node": "remix", "@sveltejs/kit": "sveltekit", "nuxt": "nuxt", "elysia": "elysia",
    "fastapi": "fastapi", "flask": "flask", "django": "django", "starlette": "starlette", "sanic": "sanic",
    "quart": "quart", "litestar": "litestar", "aiohttp": "aiohttp", "tornado": "tornado", "@hapi/hapi": "hapi",
    "restify": "restify", "@trpc/server": "trpc", "astro": "astro",
}
_PY_FRAMEWORK = re.compile(r"^[ \t]*(?:from|import)\s+(fastapi|flask|django|starlette|sanic|quart|litestar|aiohttp)\b", re.MULTILINE)
_JS_FRAMEWORK = re.compile(
    r"""(?:from\s+|require\(\s*)["'](express|fastify|koa|hono|@nestjs/core|elysia|next)(?:/[^"']*)?["']"""
)
_GO_RB_SERVER = re.compile(r"gin-gonic/gin|gofiber/fiber|labstack/echo|go-chi/chi|\bnet/http\b|Sinatra::|Rails\.application")


def server_frameworks(root: Path, code_files: list[Path]) -> set[str]:
    """Server frameworks this project runs: from manifests first, then from imports in non-test code."""
    key = ("servers", root)
    if key in _FACTS:
        return _FACTS[key]  # type: ignore[return-value]
    found = {fw for dep, fw in _SERVER_DEPS.items() if dep in project_deps(root)}
    if any((root / name).is_file() for name in ("next.config.js", "next.config.mjs", "next.config.ts")):
        found.add("nextjs")
    if not found:
        for path in code_files:
            if is_test_file(path, root):
                continue
            suffix = path.suffix.lower()
            text = code(path)
            if suffix == ".py":
                found.update(m for m in _PY_FRAMEWORK.findall(text))
            elif suffix in JS_SUFFIXES:
                found.update(_SERVER_DEPS.get(m, m) for m in _JS_FRAMEWORK.findall(text))
            elif suffix in {".go", ".rb"} and _GO_RB_SERVER.search(text):
                found.add("go" if suffix == ".go" else "ruby")
    _FACTS[key] = found
    return found


def server_hints(servers: set[str]) -> list[str]:
    """Manifest spellings of the detected frameworks (`next` for nextjs), for anchoring to the dependency line."""
    return sorted({f'"{dep}"' for dep, fw in _SERVER_DEPS.items() if fw in servers} | set(servers))


_NEXT_ROUTE = re.compile(r"(?:^|/)(?:app|pages)/(?:.*/)?(?:route|page|layout|middleware|actions?)\.[cm]?[jt]sx?$|(?:^|/)pages/api/")


def framework_of(path: Path, root: Path) -> str:
    """The framework a file belongs to; picks the fix variant shown for a finding in it."""
    rel = _rel(path, root)
    suffix = path.suffix.lower()
    text = code(path) if path.is_file() else ""
    deps = project_deps(root)
    if suffix == ".sql":
        return "supabase" if "supabase" in rel.lower() else ""
    if suffix == ".py":
        m = _PY_FRAMEWORK.search(text)
        if m:
            return "fastapi" if m.group(1) == "starlette" else m.group(1)
        for name in ("fastapi", "flask", "django"):
            if name in deps:
                return name
        return ""
    if suffix in JS_SUFFIXES:
        m = _JS_FRAMEWORK.search(text)
        if m and m.group(1) != "next":
            return _SERVER_DEPS.get(m.group(1), m.group(1))
        if _NEXT_ROUTE.search(rel) or (m and m.group(1) == "next") or "next/" in text:
            return "nextjs"
        for dep, name in (("next", "nextjs"), ("hono", "hono"), ("express", "express"), ("fastify", "fastify")):
            if dep in deps:
                return name
    return ""


# --- Local imports -----------------------------------------------------------

_JS_IMPORT = re.compile(r"""(?:\bfrom\s+|\brequire\(\s*|\bimport\(\s*|\bimport\s+)["']([^"'\n]+)["']""")
_PY_FROM = re.compile(r"^[ \t]*from\s+(\.*[\w.]*)\s+import\s+([^\n#]+)", re.MULTILINE)
_PY_IMPORT = re.compile(r"^[ \t]*import\s+([\w.]+)", re.MULTILINE)
_JS_TRY = ("", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", "/index.ts", "/index.tsx", "/index.js", "/index.mjs")
_ALIAS_PREFIXES = ("@/", "~/", "#/", "$lib/", "src/")


def _package_roots(path: Path, root: Path) -> list[Path]:
    """Directories an aliased import may be relative to: every ancestor up to the root, each with `src/`."""
    out: list[Path] = []
    current = path.parent
    while True:
        out.extend([current, current / "src", current / "app"])
        if current == root or root not in current.parents:
            break
        current = current.parent
    return out


def _first_file(candidates: list[Path]) -> Path | None:
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def local_imports(path: Path, root: Path) -> list[Path]:
    """First-party files that `path` imports (relative and aliased JS/TS imports, Python module imports)."""
    key = ("imports", path)
    if key in _FACTS:
        return _FACTS[key]  # type: ignore[return-value]
    out: list[Path] = []
    text = code(path)
    suffix = path.suffix.lower()
    if suffix in JS_SUFFIXES:
        for spec in _JS_IMPORT.findall(text):
            bases: list[Path] = []
            if spec.startswith("."):
                bases = [path.parent / spec]
            else:
                for prefix in _ALIAS_PREFIXES:
                    if spec.startswith(prefix):
                        rest = spec[len(prefix):]
                        bases = [base / rest for base in _package_roots(path, root)]
                        break
            hit = _first_file([Path(str(base) + ext) for base in bases for ext in _JS_TRY])
            if hit is not None:
                out.append(hit)
    elif suffix == ".py":
        modules: list[tuple[str, list[str]]] = [(m, []) for m in _PY_IMPORT.findall(text)]
        for module, names in _PY_FROM.findall(text):
            modules.append((module, [n.strip().split(" ")[0] for n in names.strip("() ").split(",") if n.strip()]))
        for module, names in modules:
            dots = len(module) - len(module.lstrip("."))
            parts = [part for part in module.lstrip(".").split(".") if part]
            if dots:
                base = path.parent
                for _ in range(dots - 1):
                    base = base.parent
                bases = [base]
            else:
                bases = _package_roots(path, root)
            for base in bases:
                target = base.joinpath(*parts) if parts else base
                cands = [target.with_suffix(".py"), target / "__init__.py"] if parts else []
                cands += [target / f"{name}.py" for name in names]
                hits = [c for c in cands if c.is_file()]
                if hits:
                    out.extend(hits)
                    break
    resolved = [p for p in dict.fromkeys(out) if p != path]
    _FACTS[key] = resolved
    return resolved


def related_files(path: Path, root: Path, depth: int = 2, limit: int = 30) -> list[Path]:
    """`path` plus the first-party files it imports, `depth` levels deep."""
    seen: dict[Path, None] = {path: None}
    frontier = [path]
    for _ in range(depth):
        nxt: list[Path] = []
        for current in frontier:
            for imported in local_imports(current, root):
                if imported not in seen and len(seen) < limit:
                    seen[imported] = None
                    nxt.append(imported)
        frontier = nxt
    return list(seen)


def related_code(path: Path, root: Path, depth: int = 2) -> str:
    return "\n".join(code(p) for p in related_files(path, root, depth))


# --- Routes ------------------------------------------------------------------

_NEXT_HANDLER = re.compile(
    r"export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|PATCH|DELETE)\b|export\s+const\s+(?:GET|POST|PUT|PATCH|DELETE)\b|"
    r"export\s*\{[^}]*\b(?:GET|POST|PUT|PATCH|DELETE)\b"
)
_PAGES_API = re.compile(r"(?:^|/)pages/api/")
_DEFAULT_EXPORT = re.compile(r"export\s+default\b|module\.exports\s*=")
JS_ROUTE = re.compile(
    r"""\b[\w$.]+\.(get|post|put|patch|delete|all|on)\(\s*(?:\[\s*)?(["'`])(/[^"'`\n]*|\*)\2"""
)
PY_ROUTE = re.compile(
    r"""@[\w.]+\.(get|post|put|patch|delete|route|api_route)\(\s*(?:path\s*=\s*)?(["'])([^"'\n]*)\2"""
)
_DJANGO_VIEW = re.compile(r"^[ \t]*(?:async\s+)?def\s+\w+\(\s*(?:self\s*,\s*)?request\b", re.MULTILINE)


def route_paths(path: Path, root: Path) -> list[tuple[int, str]]:
    """(offset, route path) of the HTTP routes a file declares. Next.js route files yield their URL path."""
    text = code(path)
    suffix = path.suffix.lower()
    rel = _rel(path, root)
    out: list[tuple[int, str]] = []
    if suffix == ".py":
        out.extend((m.start(), m.group(3)) for m in PY_ROUTE.finditer(text))
        if not out:
            m = _DJANGO_VIEW.search(text)
            if m and re.search(r"(?:^|/)views?(?:/|\.py$)|(?:^|/)api/", rel):
                out.append((m.start(), ""))
    elif suffix in JS_SUFFIXES:
        name = path.name.lower()
        handler = _NEXT_HANDLER.search(text)
        if handler and re.match(r"route\.[cm]?[jt]sx?$", name):
            url = "/" + rel.rsplit("/", 1)[0] if "/" in rel else "/"
            out.append((handler.start(), re.sub(r"^/(?:src/)?app", "", url) or "/"))
        elif _PAGES_API.search(rel):
            m = _DEFAULT_EXPORT.search(text)
            if m:
                out.append((m.start(), "/" + re.sub(r"\.[cm]?[jt]sx?$", "", rel[rel.index("pages/api/") + 6:])))
        out.extend((m.start(), m.group(3)) for m in JS_ROUTE.finditer(text))
    return out


# --- Auth and rate-limit evidence --------------------------------------------

AUTH_CHECK = re.compile(
    r"\bauth\(|\bauth\s*[,)]|\.auth\.(?:getUser|getSession|getClaims)|getUser\b|getSession|getServerSession|"
    r"[cC]urrent_?[uU]ser|get_current_|[rR]equire_?(?:[aA]uth|[uU]ser|[aA]dmin|[lL]ogin|[rR]ole|[sS]ession)|"
    r"is_?[aA]uthenticated|is_?[aA]dmin|is_superuser|is_staff|login_required|[pP]ermission|[aA]uthoriz|[aA]uthoris|"
    r"[aA]uthenticat|verify_?[tT]oken|verify_?[jJ]wt|jwt\.(?:verify|decode)|jwtVerify|getToken\(|\bsession\b|"
    r"cookies\(\)|[cC]lerk|withAuth|ensureAuth|ensureLoggedIn|protect\(|[gG]uard\b|"
    r"Depends\(\s*[\w.]*(?:user|auth|token|admin|key|perm|login|verify|require|session)|Security\(|passport\.|"
    r"[bB]earer|x-api-key|api_key_header|[cC]heck_?[rR]ole|has_?[rR]ole|\.role\b|\brole\s*[!=]=|\buserId\b|req\.user\b|request\.user\b|"
    r"basic_?[aA]uth|verifyKey|validateRequest|getAuth\(|useSession|requireSession|\.protect\b|adminOnly|admin_only|"
    r"admin_required|assertAdmin|ensureAdmin|checkAdmin|verifyAdmin|isOwner|workos|kinde|unkey"
)

RATE_LIMIT = re.compile(
    r"rate[_\-\s]?limit|slowapi|\bLimiter\(|@limiter\.|flask_limiter|throttle_classes|DEFAULT_THROTTLE|"
    r"Throttler(?:Module|Guard)|@Throttle\(|@nestjs/throttler|rate-limiter-flexible|RateLimiter|rack[-_:]*attack|"
    r"tollbooth|golang\.org/x/time/rate|\barcjet\b|@arcjet/|limiter\.(?:check|limit|consume)\(|"
    r"\.limit\(\s*\{\s*key\b|status(?:_code|Code)?\s*[:=(,]\s*429\b|\.status\(\s*429\s*\)|"
    r"TooManyRequests|Too Many Requests|HTTP_429",
    re.IGNORECASE,
)
_WRANGLER_RATELIMIT = re.compile(r"""type\s*=\s*["']ratelimit["']|\[\[(?:unsafe\.bindings\.)?ratelimits?\]\]|"ratelimits"\s*:""")
_MIDDLEWARE_NAMES = ("middleware.ts", "middleware.js", "proxy.ts", "proxy.js", "src/middleware.ts", "src/middleware.js", "src/proxy.ts")
_GLOBAL_USE = re.compile(r"\b\w+\.use\([\s\S]{0,200}")


def wrangler_rate_limit(root: Path) -> bool:
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        for name in ("wrangler.toml", "wrangler.json", "wrangler.jsonc"):
            if _WRANGLER_RATELIMIT.search(_read(d / name)):
                return True
    return False


def middleware_code(root: Path, code_files: list[Path]) -> str:
    """Code that runs in front of every route: Next.js middleware files and global `app.use(...)` lines."""
    key = ("middleware", root)
    if key in _FACTS:
        return _FACTS[key]  # type: ignore[return-value]
    chunks: list[str] = []
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        for name in _MIDDLEWARE_NAMES:
            mw = d / name
            if mw.is_file():
                chunks.append(related_code(mw, root, 1))
    for path in code_files:
        suffix = path.suffix.lower()
        if suffix in JS_SUFFIXES and not is_test_file(path, root):
            text = code(path)
            if ".use(" in text:
                chunks.extend(m.group(0) for m in _GLOBAL_USE.finditer(text))
        elif suffix == ".py" and not is_test_file(path, root):
            text = code(path)
            if "add_middleware(" in text or "dependencies=" in text or "MIDDLEWARE" in text:
                chunks.extend(
                    line for line in text.splitlines()
                    if "add_middleware(" in line or "dependencies=" in line or "Middleware" in line
                )
    joined = "\n".join(chunks)
    _FACTS[key] = joined
    return joined
