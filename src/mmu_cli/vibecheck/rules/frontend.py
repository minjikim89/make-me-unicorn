"""Frontend rules: tokens kept in browser storage."""

from __future__ import annotations

import re
from pathlib import Path

from mmu_cli.vibecheck.analysis import JS_SUFFIXES, code, is_test_file
from mmu_cli.vibecheck.engine import Finding, Location, Rule, _rel, dedupe_locations, loc_at, register

register(Rule(
    id="jwt-localstorage",
    title="Auth token in browser storage",
    severity="P1",
    summary="A token kept in localStorage/sessionStorage is readable by any script on the page, so one XSS bug becomes account takeover.",
    fix=(
        "Have the server set the session token in a cookie with HttpOnly, Secure and SameSite=Lax (or Strict), stop "
        "writing it to localStorage/sessionStorage, and send requests with credentials: \"include\".\n"
        "Add CSRF protection for state-changing requests once auth is cookie-based."
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#local-storage",
    tags=("frontend", "auth"),
    confidence="high",
))

_JWT_LOCALSTORAGE_PATTERN = re.compile(
    r"""(?:localStorage|sessionStorage)(?:\.setItem\(\s*['"`](?:jwt|token|access_token|id_token|auth_token|authToken)['"`]|\[\s*['"`](?:jwt|token|access_token|id_token|auth_token|authToken)['"`]\s*\]\s*=|\.(?:jwt|token|access_token|id_token|auth_token|authToken)\s*=)""",
    re.IGNORECASE
)


def check_jwt_localstorage(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    js_files = [p for p in code_files if p.suffix.lower() in JS_SUFFIXES]
    if not js_files:
        return Finding("jwt-localstorage", "P1", "skip", "no JS/TS frontend files detected")
    offenders: list[str] = []
    locations: list[Location] = []
    for path in js_files:
        if is_test_file(path, root):
            continue
        text = code(path)
        if "Storage" not in text:
            continue
        hits = [loc_at(path, root, text, m.start()) for m in _JWT_LOCALSTORAGE_PATTERN.finditer(text)]
        if hits:
            offenders.append(_rel(path, root))
            locations.extend(hits)
    if offenders:
        return Finding(
            check="jwt-localstorage",
            severity="P1",
            status="warn",
            message=f"JWT or access token stored in localStorage/sessionStorage in {len(offenders)} file(s)",
            files=sorted(set(offenders)),
            locations=locations,
        )
    return Finding("jwt-localstorage", "P1", "ok", "no JWT localStorage storage detected")


register(Rule(
    id="dangerous-html",
    title="Unsanitized HTML injected into the page",
    severity="P1",
    summary="Rendering a non-literal string as HTML (dangerouslySetInnerHTML, v-html, innerHTML) runs any script it contains in the visitor's session (XSS).",
    fix=(
        "Render the value as text, or sanitize it first: dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(html)}} "
        "(isomorphic-dompurify on the server). For Markdown use a renderer that escapes raw HTML (react-markdown without rehype-raw)."
    ),
    fix_variants=(
        ("vue", "Use {{ value }} interpolation instead of v-html, or sanitize first: v-html=\"DOMPurify.sanitize(value)\"."),
    ),
    ref="https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html",
    tags=("frontend", "xss"),
    confidence="medium",
))

_DANGEROUS_REACT = re.compile(r"dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*([^}]*)\}")
_DANGEROUS_VUE = re.compile(r"""\bv-html\s*=\s*["']([^"']+)["']""")
_DANGEROUS_SVELTE = re.compile(r"\{@html\s+([^}]+)\}")
_INNER_HTML = re.compile(r"\.(?:innerHTML|outerHTML)\s*=\s*([^;\n]+)")
_SANITIZER = re.compile(r"dompurify|sanitize|sanitise|\bxss\(|escape_?html|\bhe\.encode|striptags|\bpurify\b", re.IGNORECASE)
# Values that are not page content: serialized data, literals, and generated markup such as syntax highlighting.
_INERT_HTML = re.compile(
    r"""^\s*(?:JSON\.stringify\(|["'][^"'$]*["']\s*$|`[^`$]*`\s*$|["']{2}|null\b|undefined\b)|"""
    r"""highlight|shiki|katex|prism|\bsvg\b|icon|jsonld|json_ld|schema|structured|\bt\(|\bcss\b|styles?\b|theme|script""",
    re.IGNORECASE,
)
_HEAD_TAG = re.compile(r"<(?:script|style)\b[^<>]*$", re.IGNORECASE)


def check_dangerous_html(root: Path, code_files: list[Path], config_files: list[Path] | None = None) -> Finding:
    """Non-literal values rendered as HTML in a file with no sanitizer."""
    locations: list[Location] = []
    for path in code_files:
        suffix = path.suffix.lower()
        if suffix not in JS_SUFFIXES or is_test_file(path, root):
            continue
        text = code(path)
        if "HTML" not in text and "html" not in text:
            continue
        patterns = [_DANGEROUS_REACT]
        if suffix == ".vue":
            patterns.append(_DANGEROUS_VUE)
        elif suffix == ".svelte":
            patterns.append(_DANGEROUS_SVELTE)
        elif "innerHTML" in text or "outerHTML" in text:
            patterns.append(_INNER_HTML)
        hits = [m for pattern in patterns for m in pattern.finditer(text)]
        if not hits or _SANITIZER.search(text):
            continue
        for m in hits:
            if _INERT_HTML.search(m.group(1)) or _HEAD_TAG.search(text[max(0, m.start() - 200): m.start()]):
                continue
            locations.append(loc_at(path, root, text, m.start()))
    if locations:
        locations = dedupe_locations(sorted(locations, key=lambda loc: (loc.path, loc.line or 0)))
        files = sorted({loc.path for loc in locations})
        return Finding(
            "dangerous-html",
            "P1",
            "warn",
            f"non-literal HTML rendered without a sanitizer in {len(files)} file(s)",
            files=files,
            locations=locations,
            framework="vue" if files[0].endswith(".vue") else "",
        )
    return Finding("dangerous-html", "P1", "ok", "no unsanitized HTML injection detected")
