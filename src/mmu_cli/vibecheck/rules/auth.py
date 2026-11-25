"""Auth-surface rules: password reset, rate limiting, unthrottled LLM routes, unprotected admin routes."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.analysis import (
    AUTH_CHECK,
    JS_SUFFIXES,
    RATE_LIMIT,
    code,
    framework_of,
    low,
    is_test_file,
    middleware_code,
    project_deps,
    route_paths,
    server_frameworks,
    server_hints,
    wrangler_rate_limit,
)
from mmu_cli.vibecheck.engine import (
    Finding,
    Location,
    Rule,
    _rel,
    loc_at,
    register,
    server_anchor,
)

register(Rule(
    id="password-reset",
    title="Password login without a reset flow",
    severity="P0",
    summary="Users sign in with a password but nothing lets them recover a forgotten one, which locks real users out from day one.",
    fix=(
        "Add a forgot-password flow next to the login code: a request endpoint that emails a single-use, expiring "
        "token (store only its hash) and a confirm endpoint that sets the new password and revokes the token and existing sessions.\n"
        "Return the same response for unknown emails."
    ),
    fix_variants=(
        ("supabase", (
            "Add a forgot-password page that calls supabase.auth.resetPasswordForEmail(email, {redirectTo: `${origin}/auth/update-password`}) "
            "and an update-password page that calls supabase.auth.updateUser({password}).\n"
            "Link the forgot-password page from the login form."
        )),
        ("nextjs", (
            "Add a forgot-password route that emails a single-use, expiring token (store only its hash) and a reset "
            "route (e.g. app/reset-password/[token]/page.tsx plus a server action) that sets the new password hash and revokes the token and existing sessions.\n"
            "Return the same response for unknown emails and link the page from the login form."
        )),
        ("express", (
            "Add POST /auth/forgot-password (emails a single-use token valid for about 15 minutes; store only its hash) "
            "and POST /auth/reset-password (checks the token, sets the new bcrypt/argon2 hash, deletes the token and existing sessions).\n"
            "Return the same response for unknown emails and rate limit both routes."
        )),
        ("fastapi", (
            "Add POST /auth/password-reset/request (emails a single-use token valid for about 15 minutes; store only its hash) "
            "and POST /auth/password-reset/confirm (checks the token, stores the new password hash, revokes the token and existing sessions).\n"
            "Return the same response for unknown emails and rate limit both routes."
        )),
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html",
    tags=("auth",),
    confidence="medium",
))

register(Rule(
    id="rate-limiting",
    title="Server without rate limiting",
    severity="P1",
    summary="Login, signup and AI endpoints without a rate limit allow credential stuffing and turn paid APIs into a free compute faucet.",
    fix=(
        "Add a limiter to login, signup, password-reset and any LLM/paid-API endpoint, keyed by IP and by user, "
        "and return 429 when it trips. Use the framework's limiter or one at the edge (CDN/WAF rule)."
    ),
    fix_variants=(
        ("nextjs", (
            "Rate limit login, signup, password-reset and LLM/paid-API routes with @upstash/ratelimit: create "
            "`new Ratelimit({redis: Redis.fromEnv(), limiter: Ratelimit.slidingWindow(5, \"1 m\")})` and call "
            "`const {success} = await ratelimit.limit(ip)` at the top of the route handler or in middleware.ts; return 429 when !success."
        )),
        ("express", (
            "Add express-rate-limit: `const limiter = rateLimit({windowMs: 60_000, limit: 5})` and mount it on login, "
            "signup, password-reset and LLM/paid-API routes, e.g. app.post(\"/login\", limiter, handler). Set app.set(\"trust proxy\", 1) behind a proxy."
        )),
        ("hono", (
            "Cloudflare Workers: add a rate limit binding in wrangler.toml and call `const {success} = await c.env.RL.limit({key: ip})` "
            "in middleware; return c.text(\"slow down\", 429) when !success. Elsewhere use hono-rate-limiter's rateLimiter({windowMs, limit, keyGenerator})."
        )),
        ("fastapi", (
            "Add slowapi: `limiter = Limiter(key_func=get_remote_address)`, set app.state.limiter and the RateLimitExceeded handler, "
            "then decorate login, signup, password-reset and LLM routes with @limiter.limit(\"5/minute\") (the route needs a `request: Request` parameter)."
        )),
        ("flask", (
            "Add Flask-Limiter: `limiter = Limiter(get_remote_address, app=app)` and decorate login, signup, password-reset "
            "and LLM routes with @limiter.limit(\"5 per minute\")."
        )),
        ("django", (
            "Add django-ratelimit: decorate login, signup and password-reset views with @ratelimit(key=\"ip\", rate=\"5/m\", block=True); "
            "for DRF set DEFAULT_THROTTLE_CLASSES and DEFAULT_THROTTLE_RATES."
        )),
    ),
    ref="https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/",
    tags=("auth", "abuse"),
    confidence="low",
))

register(Rule(
    id="llm-route-unthrottled",
    title="Paid LLM route open to anyone",
    severity="P1",
    summary="A route that calls a paid LLM API with no authentication and no rate limit lets anyone run up the bill with a loop.",
    fix=(
        "Require a signed-in user on the route and add a per-user and per-IP rate limit before the model call; "
        "also cap max tokens and input length."
    ),
    fix_variants=(
        ("nextjs", (
            "At the top of the handler require a session (e.g. `const {data: {user}} = await supabase.auth.getUser()` or "
            "`await auth()`; return 401 without one) and rate limit per user with @upstash/ratelimit (return 429 when !success).\n"
            "Cap max_tokens and reject oversized input before calling the model."
        )),
        ("express", (
            "Put an auth middleware and an express-rate-limit limiter in front of the route: "
            "app.post(\"/api/ai\", requireAuth, rateLimit({windowMs: 60_000, limit: 10}), handler).\n"
            "Cap max_tokens and reject oversized input before calling the model."
        )),
        ("hono", (
            "Put an auth middleware and a rate limiter in front of the route (Cloudflare rate limit binding or hono-rate-limiter) "
            "and return 401/429 before the model call.\nCap max_tokens and reject oversized input."
        )),
        ("fastapi", (
            "Add `user: User = Depends(current_user)` to the route and a slowapi limit (@limiter.limit(\"10/minute\")).\n"
            "Cap max_tokens and reject oversized input before calling the model."
        )),
    ),
    ref="https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/",
    tags=("abuse", "llm"),
    confidence="medium",
))

register(Rule(
    id="admin-route-no-auth",
    title="Admin route without an auth check",
    severity="P1",
    summary="A route under /admin with no session, role or token check in its file or in middleware is reachable by anyone who guesses the URL.",
    fix=(
        "Check the caller before doing anything: load the session, return 401 without one and 403 unless the user "
        "has the admin role. Do the check on the server in the handler or in middleware that covers the path."
    ),
    fix_variants=(
        ("nextjs", (
            "At the top of the handler load the session (e.g. `const {data: {user}} = await supabase.auth.getUser()` or `await auth()`), "
            "return 401 without one and 403 unless the user has the admin role.\n"
            "A middleware.ts matcher for /admin and /api/admin is a second layer, not a replacement for the check in the handler."
        )),
        ("express", "Mount an auth and role middleware before the admin routes: app.use(\"/admin\", requireAuth, requireRole(\"admin\"))."),
        ("hono", "Mount an auth and role middleware before the admin routes: app.use(\"/admin/*\", requireAdmin)."),
        ("fastapi", (
            "Add an admin dependency to the router or route: APIRouter(prefix=\"/admin\", dependencies=[Depends(require_admin)]), "
            "where require_admin loads the current user and raises HTTPException(403) unless user.is_admin."
        )),
    ),
    ref="https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
    tags=("auth", "authz"),
    confidence="medium",
))

# --- password-reset ----------------------------------------------------------

# Certain password login: the app itself checks a password.
_PASSWORD_LOGIN = re.compile(
    r"signInWithPassword|sign_in_with_password|signInWithEmailAndPassword|"
    r"bcrypt(?:js)?\.compare(?:Sync)?\(|\bcompare(?:Sync)?\(\s*\w*[pP]assword|argon2\.verify\(|\bverify_password\(|"
    r"\bcheck_password(?:_hash)?\(|pwd_context\.verify\(|\bcheckpw\(|\.verify\(\s*\w*password|\bcomparePasswords?\(|"
    r"\bverifyPassword\(|\bisPasswordMatch\(|\bvalidatePassword\(|OAuth2PasswordRequestForm|passport-local|"
    r"CredentialsProvider\(|\bCredentials\(\s*\{|password_verify\(|\bcheckPassword\(|\bmatchPassword\(|"
    r"scrypt(?:Sync)?\([^)\n]*password|timingSafeEqual\([^)\n]*[pP]assword"
)
_RESET_FLOW = re.compile(
    r"(?:forgot|forgotten|reset|recover|lost)[\s_\-]*(?:your[\s_\-]*)?(?:password|pass|pw)\b|"
    r"password[\s_\-]*(?:reset|recovery|recover|forgot)|resetPasswordForEmail|sendPasswordResetEmail|"
    r"reset[_\-]?token|recovery[_\-]?token|PasswordResetForm|PasswordResetView|password_reset|requestPasswordReset",
    re.IGNORECASE,
)
# Auth products that ship their own password recovery: the app has nothing to add.
_MANAGED_AUTH_DEPS = (
    "@clerk/", "@auth0/", "auth0", "@supabase/auth-ui-react", "@stytch/", "stytch", "@workos-inc/", "workos",
    "@kinde-oss/", "@descope/", "firebaseui", "react-firebaseui", "@aws-amplify/ui-react", "django-allauth",
    "fastapi-users", "flask-security", "flask-security-too", "devise", "@logto/", "@propelauth/", "supertokens",
    "@nhost/", "keycloak-js", "@okta/",
)

def _managed_auth(root: Path) -> str:
    for dep in sorted(project_deps(root)):
        if any(dep == m or (m.endswith("/") and dep.startswith(m)) for m in _MANAGED_AUTH_DEPS):
            return dep
    return ""


def check_password_reset(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Password login is certain (the app verifies a password itself) and no reset flow exists anywhere."""
    evidence: list[tuple[Path, int]] = []
    has_reset = False
    for path in code_files:
        if is_test_file(path, root):
            continue
        lowered = low(path)
        if "passw" not in lowered and "passport" not in lowered and "credentials" not in lowered and "checkpw" not in lowered:
            if not has_reset and _RESET_FLOW.search(_rel(path, root)):
                has_reset = True
            continue
        text = code(path)
        if not has_reset and (_RESET_FLOW.search(_rel(path, root)) or _RESET_FLOW.search(text)):
            has_reset = True
        m = _PASSWORD_LOGIN.search(text)
        if m:
            evidence.append((path, m.start()))
    if not evidence:
        return Finding("password-reset", "P0", "skip", "no password-based login detected")
    if has_reset:
        return Finding("password-reset", "P0", "ok", "password login and a reset flow were both found")
    managed = _managed_auth(root)
    if managed:
        return Finding("password-reset", "P0", "skip", f"auth is handled by {managed}, which provides password recovery")
    locations: list[Location] = []
    for path, pos in evidence[:5]:
        locations.append(loc_at(path, root, code(path), pos))
    first = evidence[0][0]
    framework = framework_of(first, root)
    if any(dep.startswith("@supabase/") or dep == "supabase" for dep in project_deps(root)):
        framework = "supabase"
    return Finding(
        "password-reset",
        "P0",
        "fail",
        f"password login in {len(evidence)} file(s) but no forgot/reset-password flow anywhere in the project",
        locations=locations,
        framework=framework,
    )


# --- rate-limiting -----------------------------------------------------------

_RATE_LIMIT_HINTS = ("limit", "throttl", "429", "too many", "toomany", "arcjet", "slowapi", "attack", "tollbooth", "x/time/rate")


def _has_rate_limit(root: Path, code_files: list[Path]) -> bool:
    if wrangler_rate_limit(root):
        return True
    for path in code_files:
        if is_test_file(path, root):
            continue
        lowered = low(path)
        if not any(hint in lowered for hint in _RATE_LIMIT_HINTS):
            continue
        if RATE_LIMIT.search(code(path)):
            return True
    return False


def check_rate_limiting(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    servers = server_frameworks(root, code_files)
    if not servers:
        return Finding("rate-limiting", "P1", "skip", "no server framework detected")
    if _has_rate_limit(root, code_files):
        return Finding("rate-limiting", "P1", "ok", "rate limiting found in code")
    anchor = server_anchor(root, [p for p in code_files if not is_test_file(p, root)], server_hints(servers))
    framework = ""
    if anchor is not None:
        framework = framework_of(root / anchor.path, root)
    if not framework:
        framework = next((fw for fw in ("nextjs", "fastapi", "express", "hono", "flask", "django") if fw in servers), "")
    return Finding(
        "rate-limiting",
        "P1",
        "warn",
        f"{', '.join(sorted(servers))} server detected but no rate limiting in code",
        locations=[anchor] if anchor else [],
        framework=framework,
    )


# --- llm-route-unthrottled ---------------------------------------------------

_LLM_IMPORT = re.compile(
    r"""(?:from\s+|require\(\s*|import\s+)["'](?:openai|@anthropic-ai/sdk|ai|@ai-sdk/[\w-]+|@google/generative-ai|"""
    r"""@google/genai|replicate|groq-sdk|@mistralai/[\w-]+|cohere-ai|@langchain/[\w-]+|langchain(?:/[\w/-]+)?|together-ai)["']|"""
    r"""^\s*(?:from|import)\s+(?:openai|anthropic|google\.generativeai|google\.genai|litellm|groq|mistralai|cohere|replicate|"""
    r"""langchain\w*|together)\b""",
    re.MULTILINE,
)
_LLM_HINTS = (
    "openai", "anthropic", "ai-sdk", "generative", "genai", "replicate", "groq", "mistral", "cohere", "langchain",
    "litellm", "together", "\"ai\"", "'ai'",
)
_LLM_CALL = re.compile(
    r"\.chat\.completions\.create\(|\.completions\.create\(|\.messages\.(?:create|stream)\(|\.responses\.create\(|"
    r"\b(?:streamText|generateText|generateObject|streamObject|embedMany)\(|\.generateContent(?:Stream)?\(|"
    r"\.generate_content\(|\.images\.generate\(|\.embeddings\.create\(|\breplicate\.run\(|\blitellm\.a?completion\(|"
    r"\.audio\.(?:speech|transcriptions)\.create\(|\.invoke\(|\.astream\("
)


def check_llm_routes(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Route files that call a paid LLM SDK with no auth and no limiter in the file or in middleware."""
    candidates: list[tuple[Path, int]] = []
    for path in code_files:
        suffix = path.suffix.lower()
        if (suffix not in JS_SUFFIXES and suffix != ".py") or is_test_file(path, root):
            continue
        lowered = low(path)
        if not any(hint in lowered for hint in _LLM_HINTS):
            continue
        text = code(path)
        if not _LLM_IMPORT.search(text):
            continue
        call = _LLM_CALL.search(text)
        if call is None or not route_paths(path, root):
            continue
        candidates.append((path, call.start()))
    if not candidates:
        return Finding("llm-route-unthrottled", "P1", "skip", "no route calls an LLM SDK directly")
    middleware = middleware_code(root, code_files)
    if AUTH_CHECK.search(middleware) or RATE_LIMIT.search(middleware):
        return Finding("llm-route-unthrottled", "P1", "ok", "LLM routes sit behind auth or rate-limit middleware")
    open_routes: list[Location] = []
    for path, pos in candidates:
        text = code(path)
        if AUTH_CHECK.search(text) or RATE_LIMIT.search(text):
            continue
        open_routes.append(loc_at(path, root, text, pos))
    if not open_routes:
        return Finding("llm-route-unthrottled", "P1", "ok", f"{len(candidates)} LLM route file(s) check auth or rate limits")
    return Finding(
        "llm-route-unthrottled",
        "P1",
        "warn",
        f"{len(open_routes)} route file(s) call a paid LLM API with no auth and no rate limit",
        locations=open_routes,
        framework=framework_of(root / open_routes[0].path, root),
    )


# --- admin-route-no-auth -----------------------------------------------------

_ADMIN_PATH = re.compile(r"(?:^|/)admin(?:/|$)", re.IGNORECASE)
_ADMIN_PREFIX_MOUNT = re.compile(r"""\.(?:use|route|group|basePath)\(\s*["'`][^"'`\n]*/admin\b[^"'`\n]*["'`]\s*,""")
_ADMIN_ROUTER_PREFIX = re.compile(r"""prefix\s*=\s*["'][^"'\n]*/admin\b""")


def check_admin_routes(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Routes whose path contains /admin, with no auth, session or role check in the file or in middleware."""
    candidates: list[tuple[Path, int]] = []
    guarded_elsewhere = False
    for path in code_files:
        suffix = path.suffix.lower()
        if (suffix not in JS_SUFFIXES and suffix != ".py") or is_test_file(path, root):
            continue
        if "admin" not in low(path) and "admin" not in _rel(path, root).lower():
            continue
        text = code(path)
        mount = _ADMIN_PREFIX_MOUNT.search(text)
        if mount and AUTH_CHECK.search(text[mount.start(): mount.start() + 300]):
            guarded_elsewhere = True
        for pos, route in route_paths(path, root):
            if _ADMIN_PATH.search(route.strip("/")):
                candidates.append((path, pos))
                break
        else:
            prefix = _ADMIN_ROUTER_PREFIX.search(text) if suffix == ".py" else None
            if prefix and route_paths(path, root):
                candidates.append((path, prefix.start()))
    if not candidates:
        return Finding("admin-route-no-auth", "P1", "skip", "no /admin routes detected")
    if guarded_elsewhere or AUTH_CHECK.search(middleware_code(root, code_files)):
        return Finding("admin-route-no-auth", "P1", "ok", "admin routes sit behind auth middleware")
    open_routes = [
        loc_at(path, root, code(path), pos) for path, pos in candidates if not AUTH_CHECK.search(code(path))
    ]
    if not open_routes:
        return Finding("admin-route-no-auth", "P1", "ok", f"{len(candidates)} admin route file(s) check auth")
    return Finding(
        "admin-route-no-auth",
        "P1",
        "warn",
        f"{len(open_routes)} admin route file(s) have no auth, session or role check",
        locations=open_routes,
        framework=framework_of(root / open_routes[0].path, root),
    )
