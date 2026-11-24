"""Production-configuration rules: CORS, debug mode, monitoring, source maps, TLS verification."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.engine import (
    _ENV_SCAN_DEPTH,
    _REF_REEVE_AUG_2026,
    _SERVER_HINTS,
    Finding,
    Location,
    Rule,
    _read,
    _rel,
    _walk_shallow,
    clean_snippet,
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
        "Replace `*` with an explicit allowlist read from config, e.g. FastAPI allow_origins=[\"https://app.example.com\"] "
        "or Express cors({origin: [\"https://app.example.com\"]}).\n"
        "Never combine a wildcard or reflected origin with credentials."
    ),
    ref="https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS",
    tags=("config", "cors"),
    confidence="medium",
))

register(Rule(
    id="debug-mode",
    title="DEBUG hardcoded on",
    severity="P1",
    summary="Debug mode in production serves stack traces, settings and sometimes secrets to anyone who triggers an error.",
    fix="Read the flag from the environment and default to off: DEBUG = os.environ.get(\"DEBUG\", \"\").lower() in {\"1\", \"true\"}.",
    ref="https://docs.djangoproject.com/en/stable/ref/settings/#debug",
    tags=("config", "python"),
    confidence="high",
))

register(Rule(
    id="error-monitoring",
    title="No error monitoring",
    severity="P1",
    summary="Without an error tracker the first signal of a production bug is a user who already left.",
    fix=(
        "Install an error tracker and initialise it at process start with the DSN from an env var.\n"
        "Python: sentry_sdk.init(dsn=os.environ[\"SENTRY_DSN\"]). Node/Next.js: Sentry.init({dsn: process.env.SENTRY_DSN})."
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


def check_cors(root: Path, code_files: list[Path]) -> Finding:
    offenders = []
    locations: list[Location] = []
    for path in code_files[:400]:
        text = _read(path)
        if not any(m in text.lower() for m in _CORS_WILDCARD_MARKERS):
            continue
        offenders.append(_rel(path, root))
        for i, line in enumerate(text.splitlines(), 1):
            if any(m in line.lower() for m in _CORS_WILDCARD_MARKERS):
                locations.append(Location(_rel(path, root), i, snippet=clean_snippet(line)))
    if offenders:
        return Finding(
            "cors-wildcard",
            "P1",
            "warn",
            f"wildcard CORS origin in {len(offenders)} file(s)",
            files=offenders,
            locations=locations,
        )
    return Finding("cors-wildcard", "P1", "ok", "no wildcard CORS origins detected")


def check_debug_mode(root: Path, code_files: list[Path]) -> Finding:
    pattern = re.compile(r"^\s*DEBUG\s*=\s*True\b", re.MULTILINE)
    offenders = []
    locations: list[Location] = []
    for path in code_files:
        if path.suffix.lower() != ".py":
            continue
        text = _read(path)
        hits = [loc_at(path, root, text, m.end() - 1) for m in pattern.finditer(text)]
        if hits:
            offenders.append(_rel(path, root))
            locations.extend(hits)
    if offenders:
        return Finding(
            "debug-mode",
            "P1",
            "warn",
            f"DEBUG = True in {len(offenders)} file(s)",
            files=offenders,
            locations=locations,
        )
    return Finding("debug-mode", "P1", "ok", "no hardcoded DEBUG = True detected")


def check_error_monitoring(root: Path, code_files: list[Path]) -> Finding:
    pkg = (_read(root / "package.json") + _read(root / "requirements.txt") + _read(root / "pyproject.toml")).lower()
    if any(m in pkg for m in _MONITORING_MARKERS):
        return Finding("error-monitoring", "P1", "ok", "error monitoring dependency detected")
    for path in code_files[:400]:
        if any(m in _read(path).lower() for m in _MONITORING_MARKERS):
            return Finding("error-monitoring", "P1", "ok", "error monitoring markers found in code")
    anchor = server_anchor(root, code_files, _SERVER_HINTS)
    return Finding(
        "error-monitoring",
        "P1",
        "warn",
        "no error monitoring (Sentry etc.) detected",
        locations=[anchor] if anchor else [],
    )


def check_sourcemaps(root: Path, code_files: list[Path]) -> Finding:
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


def check_disabled_ssl(root: Path, code_files: list[Path]) -> Finding:
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
        if path.suffix.lower() not in {".py", ".js", ".ts", ".jsx", ".tsx", ".go"}:
            continue
        text = _read(path)
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
