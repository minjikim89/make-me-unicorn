"""Production-configuration rules: CORS, debug mode, monitoring, source maps, TLS verification."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.analysis import (
    JS_SUFFIXES,
    code,
    framework_of,
    is_test_file,
    low,
    project_deps,
    server_frameworks,
    server_hints,
)
from mmu_cli.vibecheck.engine import (
    _ENV_SCAN_DEPTH,
    _REF_REEVE_AUG_2026,
    Finding,
    Location,
    Rule,
    _read,
    _rel,
    _walk_shallow,
    dedupe_locations,
    loc_at,
    register,
    server_anchor,
)

register(Rule(
    id="cors-wildcard",
    title="Wildcard CORS origin",
    severity="P1",
    summary="An allow-all CORS origin lets any website call the API from a visitor's browser, which is dangerous next to cookie or header auth.",
    fix=(
        "Replace the wildcard with an explicit allowlist of origins read from config.\n"
        "Never combine a wildcard or reflected origin with credentials."
    ),
    fix_variants=(
        ("express", (
            "Pass an allowlist: app.use(cors({origin: process.env.ALLOWED_ORIGINS.split(\",\"), credentials: true})). "
            "cors() with no options answers every origin with `Access-Control-Allow-Origin: *`."
        )),
        ("hono", (
            "Pass an allowlist: app.use(\"*\", cors({origin: [\"https://app.example.com\"], credentials: true})). "
            "cors() with no options answers every origin with `Access-Control-Allow-Origin: *`."
        )),
        ("fastapi", (
            "Set allow_origins to an explicit list read from settings, e.g. allow_origins=settings.cors_origins "
            "([\"https://app.example.com\"]). With allow_credentials=True a wildcard makes Starlette echo back any Origin, "
            "so every website can call the API with the visitor's cookies."
        )),
        ("nextjs", (
            "Set Access-Control-Allow-Origin to the one origin that needs it (or check the request Origin against an "
            "allowlist and echo it back); same-origin requests from the app itself need no CORS header at all."
        )),
    ),
    ref="https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS",
    tags=("config", "cors"),
    confidence="medium",
))

register(Rule(
    id="debug-mode",
    title="DEBUG hardcoded on",
    severity="P1",
    summary="Debug mode in production serves stack traces, settings and sometimes an interactive console to anyone who triggers an error.",
    fix="Read the flag from the environment and default to off: DEBUG = os.environ.get(\"DEBUG\", \"\").lower() in {\"1\", \"true\"}.",
    fix_variants=(
        ("flask", (
            "Remove debug=True from app.run(): the Werkzeug debugger executes arbitrary Python for anyone who reaches an error page.\n"
            "Use `flask run --debug` locally and a WSGI server (gunicorn) in production."
        )),
        ("fastapi", "Read the flag from the environment and default to off, e.g. FastAPI(debug=settings.debug) with `debug: bool = False` in settings."),
        ("docker", (
            "Run the production server in the image: drop --reload/--debug and dev scripts from CMD "
            "(e.g. CMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\"], `next start`, `node server.js`)."
        )),
    ),
    ref="https://docs.djangoproject.com/en/stable/ref/settings/#debug",
    tags=("config", "python"),
    confidence="high",
))

register(Rule(
    id="error-monitoring",
    title="No error monitoring",
    severity="P1",
    summary="Without an error tracker the first signal of a production bug is a user who already left.",
    fix="Install an error tracker (Sentry or similar) and initialise it at process start with the DSN from an env var.",
    fix_variants=(
        ("nextjs", "Run `npx @sentry/wizard@latest -i nextjs` (adds instrumentation.ts and the client/server configs) and set SENTRY_DSN in the deployment environment."),
        ("express", "Install @sentry/node, call Sentry.init({dsn: process.env.SENTRY_DSN}) before creating the app, and add Sentry.setupExpressErrorHandler(app) after the routes."),
        ("hono", "Install @sentry/cloudflare (Workers) or @sentry/node and wrap the app: export default Sentry.withSentry(env => ({dsn: env.SENTRY_DSN}), app)."),
        ("fastapi", "Install sentry-sdk[fastapi] and call sentry_sdk.init(dsn=os.environ[\"SENTRY_DSN\"]) before creating the FastAPI app."),
        ("flask", "Install sentry-sdk[flask] and call sentry_sdk.init(dsn=os.environ[\"SENTRY_DSN\"]) before creating the Flask app."),
        ("django", "Install sentry-sdk[django] and call sentry_sdk.init(dsn=os.environ[\"SENTRY_DSN\"]) in settings.py."),
    ),
    tags=("config", "observability"),
    confidence="low",
))

register(Rule(
    id="sourcemaps-exposed",
    title="Production source maps exposed",
    severity="P1",
    summary="Browser source maps published with the bundle let anyone read the original source, comments and internal URLs.",
    fix=(
        "Disable browser source maps for production builds (Vite: build.sourcemap false or \"hidden\"; Next.js: remove "
        "productionBrowserSourceMaps; webpack: devtool false or \"hidden-source-map\").\n"
        "If the error tracker needs them, upload the hidden maps at build time and do not deploy the .map files."
    ),
    ref=_REF_REEVE_AUG_2026,
    tags=("config", "frontend"),
    confidence="high",
))

register(Rule(
    id="disabled-ssl",
    title="TLS certificate verification disabled",
    severity="P1",
    summary="Turning off certificate verification lets anyone on the network path read and modify the connection (man-in-the-middle).",
    fix=(
        "Remove the override so certificates are verified (requests/httpx verify=True, Node rejectUnauthorized true, Go InsecureSkipVerify false).\n"
        "For a private CA pass its bundle instead: verify=\"/path/ca.pem\", `ca: fs.readFileSync(...)`, or tls.Config.RootCAs."
    ),
    ref="https://cwe.mitre.org/data/definitions/295.html",
    tags=("config", "transport"),
    confidence="high",
))

register(Rule(
    id="stack-trace-leak",
    title="Stack trace returned to the client",
    severity="P1",
    summary="Sending a stack trace in an HTTP response shows file paths, library versions and query fragments to whoever triggers an error.",
    fix=(
        "Log the exception on the server (with the error tracker) and return a generic message with a request id; "
        "never put traceback text or err.stack in the response body."
    ),
    fix_variants=(
        ("fastapi", "In the exception handler call logger.exception(exc) and return JSONResponse(status_code=500, content={\"error\": \"internal error\"})."),
        ("flask", "In the error handler call app.logger.exception(e) and return jsonify(error=\"internal error\"), 500."),
        ("express", "In the error middleware log err and respond res.status(500).json({error: \"internal error\"}); do not include err.stack."),
        ("nextjs", "Log the error on the server (console.error or the error tracker) and return NextResponse.json({error: \"internal error\"}, {status: 500})."),
    ),
    ref="https://cwe.mitre.org/data/definitions/209.html",
    tags=("config", "errors"),
    confidence="high",
))

_CORS_WILDCARD = re.compile(
    r"""access-control-allow-origin["']?\s*(?:[:,]|\]\s*=|=)\s*["']\*["']|access-control-allow-origin:\s*\*|"""
    r"""allow_origins\s*=\s*\[\s*["']\*["']\s*\]|\borigin\s*:\s*["']\*["']|cors_allow_all_origins\s*=\s*true|"""
    r"""cors_origin_allow_all\s*=\s*true|allowedorigins\(\s*["']\*["']""",
    re.IGNORECASE,
)
# Express/Hono/Fastify `cors()` with no options answers `Access-Control-Allow-Origin: *`.
_CORS_DEFAULT = re.compile(r"(?<![.\w$])cors\(\s*\)")
_CORS_IMPORT = re.compile(r"""["'](?:cors|hono/cors|@fastify/cors|@koa/cors|@elysiajs/cors)["']""")
_CORS_REFLECT = re.compile(r"\bcors\(\s*\{[^}]*\borigin\s*:\s*true\b[^}]*\bcredentials\s*:\s*true|\bcors\(\s*\{[^}]*\bcredentials\s*:\s*true\b[^}]*\borigin\s*:\s*true")
_ALLOW_CREDENTIALS = re.compile(r"allow_credentials\s*=\s*True|credentials\s*:\s*true|allow-credentials[\"']?\s*[:,]\s*[\"']true", re.IGNORECASE)

_MONITORING_DEPS = (
    "sentry", "rollbar", "bugsnag", "honeybadger", "datadog", "dd-trace", "ddtrace", "newrelic", "appsignal",
    "glitchtip", "highlight.run", "@highlight-run", "opentelemetry", "@vercel/otel", "logrocket", "airbrake",
    "raygun", "logtail", "@axiomhq", "next-axiom", "honeycomb", "logfire", "applicationinsights", "elastic-apm",
    "scout-apm", "posthog", "baselime", "@logtail",
)
_MONITORING_HINTS = (
    "sentry", "rollbar", "bugsnag", "honeybadger", "datadog", "dd-trace", "ddtrace", "newrelic", "appsignal", "glitchtip",
    "highlight-run", "opentelemetry", "otel", "logrocket", "airbrake", "raygun", "logtail", "axiom", "honeycomb", "logfire",
    "applicationinsights", "captureexception", "capture_exception", "elastic-apm",
)
_MONITORING_CODE = re.compile(
    r"\bsentry|rollbar|bugsnag|honeybadger|datadog|dd-trace|ddtrace|newrelic|appsignal|glitchtip|@highlight-run|"
    r"opentelemetry|@vercel/otel|logrocket|airbrake|raygun|logtail|next-axiom|honeycomb|logfire|applicationinsights|"
    r"captureException|capture_exception|elastic-apm",
    re.IGNORECASE,
)


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


def check_cors(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    offenders: list[str] = []
    locations: list[Location] = []
    with_credentials = False
    default_cors = False
    for path in code_files:
        suffix = path.suffix.lower()
        lowered = low(path)
        if "origin" not in lowered and "cors" not in lowered:
            continue
        text = code(path)
        hits = [m.start() for m in _CORS_WILDCARD.finditer(text)]
        if suffix in JS_SUFFIXES and "cors(" in text and _CORS_IMPORT.search(text):
            defaults = [m.start() for m in _CORS_DEFAULT.finditer(text)]
            default_cors = default_cors or bool(defaults)
            hits.extend(defaults)
            reflect = [m.start() for m in _CORS_REFLECT.finditer(text)]
            with_credentials = with_credentials or bool(reflect)
            hits.extend(reflect)
        if not hits:
            continue
        if _ALLOW_CREDENTIALS.search(text):
            with_credentials = True
        offenders.append(_rel(path, root))
        locations.extend(loc_at(path, root, text, pos) for pos in sorted(hits))
    if offenders:
        message = f"wildcard CORS origin in {len(offenders)} file(s)"
        if default_cors:
            message += "; cors() without options allows every origin"
        if with_credentials:
            message += "; combined with credentials, so any website can make authenticated requests for a visitor"
        locations = dedupe_locations(locations)
        return Finding(
            "cors-wildcard",
            "P1",
            "warn",
            message,
            files=offenders,
            locations=locations,
            framework=framework_of(root / locations[0].path, root),
        )
    return Finding("cors-wildcard", "P1", "ok", "no wildcard CORS origins detected")


_DEBUG_ASSIGN = re.compile(r"^[ \t]*DEBUG\s*(?::\s*bool\s*)?=\s*True\b", re.MULTILINE)
_DEBUG_CALL = re.compile(r"\b(?:\w+\.run|FastAPI|Flask|Starlette|Sanic|Quart|run_simple)\(")
_DEBUG_KWARG = re.compile(r"\b(?:debug|use_debugger)\s*=\s*True\b")
_DOCKER_CMD = re.compile(r"^[ \t]*(?:CMD|ENTRYPOINT)\b.*$", re.MULTILINE | re.IGNORECASE)
_DOCKER_DEV = re.compile(
    r"--reload\b|--debug\b|\bnext[\"',\s]+dev\b|\b(?:npm|pnpm|yarn|bun)[\"',\s]+(?:run[\"',\s]+)?dev\b|\bnodemon\b|"
    r"\bflask[\"',\s]+run\b|\brunserver\b|FLASK_DEBUG=1|\bvite[\"',\s]*(?:dev)?[\"'\]]*\s*$"
)


def _call_span(text: str, open_paren: int, limit: int = 600) -> str:
    depth = 0
    end = min(len(text), open_paren + limit)
    for i in range(open_paren, end):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren: i + 1]
    return text[open_paren:end]


def check_debug_mode(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """DEBUG = True, app.run(debug=True) / FastAPI(debug=True), and dev servers in a production Dockerfile."""
    offenders: list[str] = []
    locations: list[Location] = []
    details: set[str] = set()
    for path in code_files:
        if path.suffix.lower() != ".py" or is_test_file(path, root):
            continue
        text = code(path)
        hits = [loc_at(path, root, text, m.end() - 1) for m in _DEBUG_ASSIGN.finditer(text)]
        if hits:
            details.add("DEBUG = True")
        if "debug" in text:
            for m in _DEBUG_CALL.finditer(text):
                kw = _DEBUG_KWARG.search(_call_span(text, m.end() - 1))
                if kw:
                    hits.append(loc_at(path, root, text, m.end() - 1 + kw.start()))
                    details.add("debug=True passed to the app")
        if hits:
            offenders.append(_rel(path, root))
            locations.extend(hits)
    docker = False
    for path in config_files or []:
        name = path.name.lower()
        if not (name.startswith("dockerfile") or name.endswith(".dockerfile")) or re.search(r"dev|local|test", name):
            continue
        text = _read(path)
        cmds = list(_DOCKER_CMD.finditer(text))
        if cmds and _DOCKER_DEV.search(cmds[-1].group(0)):
            offenders.append(_rel(path, root))
            locations.append(loc_at(path, root, text, cmds[-1].start()))
            details.add("dev server in Dockerfile CMD")
            docker = True
    if offenders:
        locations = dedupe_locations(locations)
        first = root / locations[0].path
        return Finding(
            "debug-mode",
            "P1",
            "warn",
            f"debug mode hardcoded on in {len(offenders)} file(s): " + ", ".join(sorted(details)),
            files=offenders,
            locations=locations,
            framework="docker" if docker and first.suffix.lower() != ".py" else framework_of(first, root),
        )
    return Finding("debug-mode", "P1", "ok", "no hardcoded debug mode detected")


def check_error_monitoring(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    servers = server_frameworks(root, code_files)
    if not servers:
        return Finding("error-monitoring", "P1", "skip", "no server framework detected")
    deps = project_deps(root)
    if any(marker in dep for dep in deps for marker in _MONITORING_DEPS):
        return Finding("error-monitoring", "P1", "ok", "error monitoring dependency detected")
    for path in code_files:
        if is_test_file(path, root):
            continue
        lowered = low(path)
        if any(hint in lowered for hint in _MONITORING_HINTS) and _MONITORING_CODE.search(code(path)):
            return Finding("error-monitoring", "P1", "ok", "error monitoring found in code")
    anchor = server_anchor(root, [p for p in code_files if not is_test_file(p, root)], server_hints(servers))
    framework = framework_of(root / anchor.path, root) if anchor is not None else ""
    if not framework:
        framework = next((fw for fw in ("nextjs", "fastapi", "express", "hono", "flask", "django") if fw in servers), "")
    return Finding(
        "error-monitoring",
        "P1",
        "warn",
        "no error monitoring (Sentry etc.) detected",
        locations=[anchor] if anchor else [],
        framework=framework,
    )


_PY_TRACE = re.compile(r"traceback\.format_exc\(\)|traceback\.format_exception\(|\bformat_exc\(\)")
_PY_RESPONSE = re.compile(r"Response\(|jsonify\(|HTTPException\(|abort\(|make_response\(|\bcontent\s*=|\bdetail\s*=")
_PY_RETURN_BODY = re.compile(r"\breturn\b[^\n]*(?:\{|jsonify\(|Response\(|dict\()")
_JS_RESPONSE = re.compile(
    r"\bres(?:ponse)?\s*(?:\.status\([^)]*\))?\s*\.(?:json|send|end|write)\(|NextResponse\.json\(|Response\.json\(|"
    r"new\s+(?:Next)?Response\(|\bc\.(?:json|text|html)\(|\breply\s*(?:\.code\([^)]*\))?\s*\.send\(|ctx\.body\s*="
)
_JS_STACK = re.compile(r"\b(?:err|error|e|ex|exception)\.stack\b")
_ENV_GUARD = re.compile(r"NODE_ENV|development|production|isDev|isProd|\bdebug\b|\bDEBUG\b|\bdev\b", re.IGNORECASE)


def check_stack_trace_leak(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """traceback.format_exc() or err.stack placed in an HTTP response, with no environment guard around it."""
    locations: list[Location] = []
    for path in code_files:
        suffix = path.suffix.lower()
        if is_test_file(path, root):
            continue
        if suffix == ".py":
            text = code(path)
            if "format_exc" not in text:
                continue
            lines = text.splitlines()
            for m in _PY_TRACE.finditer(text):
                lineno = text.count("\n", 0, m.start()) + 1
                line = lines[lineno - 1]
                window = "\n".join(lines[max(0, lineno - 3): lineno])
                context = "\n".join(lines[max(0, lineno - 6): lineno + 1])
                if re.search(r"\braise\b|\blog\w*\.|print\(", line):
                    continue
                in_response = _PY_RETURN_BODY.search(line) or _PY_RESPONSE.search(window)
                if in_response and not re.search(r"\bif\b[^\n]*(?:debug|DEBUG|dev)", context):
                    locations.append(loc_at(path, root, text, m.start()))
        elif suffix in JS_SUFFIXES:
            text = code(path)
            if ".stack" not in text:
                continue
            for m in _JS_RESPONSE.finditer(text):
                span = _call_span(text, text.find("(", m.end() - 1) if text[m.end() - 1] != "(" else m.end() - 1, 300)
                stack = _JS_STACK.search(span)
                if stack is None:
                    continue
                before = text[max(0, m.start() - 300): m.start()]
                if _ENV_GUARD.search(span) or _ENV_GUARD.search(before):
                    continue
                locations.append(loc_at(path, root, text, m.start()))
    if locations:
        locations = dedupe_locations(locations)
        files = sorted({loc.path for loc in locations})
        return Finding(
            "stack-trace-leak",
            "P1",
            "warn",
            f"stack trace sent in an HTTP response in {len(files)} file(s)",
            files=files,
            locations=locations,
            framework=framework_of(root / locations[0].path, root),
        )
    return Finding("stack-trace-leak", "P1", "ok", "no stack traces in HTTP responses")


def check_sourcemaps(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Production source maps published alongside the bundle (Reeve Aug-2026: 13% of apps)."""
    offenders: list[str] = []
    details: set[str] = set()
    locations: list[Location] = []
    for d in _walk_shallow(root, _ENV_SCAN_DEPTH):
        for name in _BUILD_CONFIG_NAMES:
            cfg = d / name
            if not cfg.is_file():
                continue
            text = _read(cfg)
            for label, pat in _SOURCEMAP_SIGNALS:
                for m in pat.finditer(text):
                    offenders.append(_rel(cfg, root))
                    details.add(label)
                    locations.append(loc_at(cfg, root, text, m.start()))
    if offenders:
        return Finding(
            "sourcemaps-exposed",
            "P1",
            "warn",
            f"production source maps enabled in {len(set(offenders))} build config(s): " + ", ".join(sorted(details)),
            files=sorted(set(offenders)),
            locations=locations,
        )
    return Finding("sourcemaps-exposed", "P1", "ok", "no production source-map flags in build configs")


def check_disabled_ssl(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Discovers disabled SSL/TLS certificate verification (e.g. verify=False, rejectUnauthorized: false)."""
    patterns = [
        re.compile(r"\bverify\s*=\s*False\b", re.IGNORECASE),
        re.compile(r"\brejectUnauthorized\s*:\s*false\b", re.IGNORECASE),
        re.compile(r"\bNODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0['\"]?", re.IGNORECASE),
        re.compile(r"\bInsecureSkipVerify\s*:\s*true\b", re.IGNORECASE),
    ]
    offenders = []
    locations: list[Location] = []
    for path in code_files:
        if path.suffix.lower() not in JS_SUFFIXES | {".py", ".go"}:
            continue
        lowered = low(path)
        if "verify" not in lowered and "rejectunauthorized" not in lowered and "tls_reject" not in lowered:
            continue
        text = code(path)
        hits = sorted(m.start() for pat in patterns for m in pat.finditer(text))
        if hits:
            offenders.append(_rel(path, root))
            locations.extend(dedupe_locations([loc_at(path, root, text, pos) for pos in hits]))

    if offenders:
        return Finding(
            "disabled-ssl",
            "P1",
            "warn",
            f"disabled SSL/TLS verification detected in {len(offenders)} file(s)",
            files=offenders,
            locations=locations,
        )
    return Finding("disabled-ssl", "P1", "ok", "no disabled SSL/TLS verification detected")
