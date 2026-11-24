"""Production-configuration rules: CORS, debug mode, monitoring, source maps, TLS verification."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.engine import _ENV_SCAN_DEPTH, _REF_REEVE_AUG_2026, Finding, _read, _rel, _walk_shallow

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


def check_disabled_ssl(root: Path, code_files: list[Path]) -> Finding:
    """Discovers disabled SSL/TLS certificate verification (e.g. verify=False, rejectUnauthorized: false)."""
    patterns = [
        re.compile(r"\bverify\s*=\s*False\b", re.IGNORECASE),
        re.compile(r"\brejectUnauthorized\s*:\s*false\b", re.IGNORECASE),
        re.compile(r"\bNODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0['\"]?", re.IGNORECASE),
        re.compile(r"\bInsecureSkipVerify\s*:\s*true\b", re.IGNORECASE),
    ]
    offenders = []
    for path in code_files:
        if path.suffix.lower() not in {".py", ".js", ".ts", ".jsx", ".tsx", ".go"}:
            continue
        text = _read(path)
        if any(pat.search(text) for pat in patterns):
            offenders.append(_rel(path, root))

    if offenders:
        return Finding(
            "disabled-ssl",
            "P1",
            "warn",
            f"disabled SSL/TLS verification detected in {len(offenders)} file(s)",
            hint="Disabling SSL/TLS verification exposes your application to Man-in-the-Middle (MitM) attacks. Enable certificate validation in production.",
            files=offenders,
        )
    return Finding("disabled-ssl", "P1", "ok", "no disabled SSL/TLS verification detected")
