"""Vibecheck output formatters: text (humans), json (`mmu.vibecheck/v1`), agent (LLM context), sarif."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mmu_cli.vibecheck.engine import (
    INFORMATION_URI,
    SCHEMA,
    Finding,
    Location,
    Rule,
    ScanResult,
    all_rules,
    fingerprint,
    tool_version,
)

FORMATS = ("text", "json", "sarif", "agent")
_REPORTED = {"fail", "warn", "suppressed", "baselined"}
_ICONS = {
    "fail": "[fail]", "warn": "[warn]", "ok": "[ok]", "skip": "[skip]", "suppressed": "[suppressed]",
    "baselined": "[baselined]",
}

_HASH_COMMENT = {".py", ".rb", ".sh", ".bash", ".zsh", ".yml", ".yaml", ".toml", ".tf", ".r", ".pl", ".ex", ".exs"}
_SLASH_COMMENT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".mts", ".cjs", ".cts", ".go", ".java", ".cs", ".kt", ".swift", ".rs",
    ".c", ".cc", ".cpp", ".h", ".php", ".dart", ".scala",
}


# --- text ------------------------------------------------------------------

def _indented(prefix: str, text: str, indent: str) -> list[str]:
    first, *rest = text.splitlines() or [""]
    return [f"{indent}{prefix}{first}", *[f"{indent}  {line}" for line in rest]]


def format_findings(findings: list[Finding]) -> tuple[list[str], int]:
    """Render findings as human-readable lines; return (lines, exit_code) with 1 = blocking findings."""
    lines = ["Vibe check — what AI-generated code usually misses", ""]
    fails = [f for f in findings if f.status == "fail"]
    warns = [f for f in findings if f.status == "warn"]
    suppressed = [f for f in findings if f.status == "suppressed"]
    baselined = [f for f in findings if f.status == "baselined"]
    for f in findings:
        lines.append(f"  {_ICONS.get(f.status, f'[{f.status}]')} ({f.severity}) {f.check}: {f.message}")
        if f.status not in _REPORTED:
            continue
        places = [loc.label() for loc in f.locations] or list(f.files)
        for place in places[:5]:
            lines.append(f"        - {place}")
        if len(places) > 5:
            lines.append(f"        - … and {len(places) - 5} more")
        if f.status == "suppressed":
            lines.append(f"        ↳ suppressed: {f.suppress_reason}")
            continue
        if f.status == "baselined":
            lines.append("        ↳ in the baseline: not blocking, fix when you touch this code")
            continue
        for note in f.notes:
            lines.append(f"        ↳ note: {note}")
        if f.hint:
            lines.extend(_indented("↳ fix: ", f.hint, "        "))
        if f.ref:
            lines.append(f"        ↳ why: {f.ref}")
    lines.append("")
    tail = f", {len(suppressed)} suppressed" if suppressed else ""
    if baselined:
        tail += f", {len(baselined)} baselined"
    if fails:
        lines.append(f"Vibe check result: {len(fails)} launch-blocking issue(s), {len(warns)} warning(s){tail}")
        return lines, 1
    if warns:
        lines.append(f"Vibe check result: no blockers, {len(warns)} warning(s){tail}")
        return lines, 0
    lines.append(f"Vibe check result: clean ✨{tail}")
    return lines, 0


def _scope_label(scope: dict[str, Any]) -> str:
    mode = scope.get("mode", "all")
    if mode == "all":
        return "all files"
    label = f"since {scope.get('since')}" if mode == "since" else mode
    return f"{label} ({scope.get('files', 0)} file(s))"


def render_text(result: ScanResult) -> str:
    lines, _ = format_findings(result.findings)
    if result.scope.get("mode", "all") != "all":
        lines.insert(1, f"Scope: {_scope_label(result.scope)}")
    return "\n".join(lines)


# --- json ------------------------------------------------------------------

def to_json(result: ScanResult, include_all: bool = False) -> dict[str, Any]:
    """The `mmu.vibecheck/v1` document. ok/skip findings are included only with `include_all`."""
    findings = [f for f in result.findings if include_all or f.status in _REPORTED]
    return {
        "schema": SCHEMA,
        "tool": {"name": "mmu", "version": tool_version()},
        "root": str(result.root),
        "scope": dict(result.scope),
        "summary": result.summary(),
        "findings": [f.to_dict() for f in findings],
    }


def error_json(code: str, message: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "error": {"code": code, "message": message}}


# --- agent -----------------------------------------------------------------

def _silence_hint(finding: Finding) -> str:
    """How to suppress this finding, in the comment syntax of the file it points at."""
    loc = finding.locations[0] if finding.locations else None
    rule = finding.check
    if loc is None:
        return f'add "{rule}" to [vibecheck] ignore in .mmu/config.toml'
    name = Path(loc.path).name.lower()
    suffix = Path(name).suffix
    marker = ""
    if loc.line and not Path(loc.path).is_absolute() and not loc.path.startswith(".git/"):
        if suffix in _HASH_COMMENT or name.startswith(".env") or name in {"dockerfile", "requirements.txt", ".gitignore"}:
            marker = "#"
        elif suffix in _SLASH_COMMENT:
            marker = "//"
        elif suffix == ".sql":
            marker = "--"
    if not marker:
        return f'add "{loc.path}:{rule}" to [vibecheck] ignore in .mmu/config.toml'
    return f"{marker} mmu-ignore[{rule}]: <reason>"


def _rerun_command(scope: dict[str, Any]) -> str:
    mode = scope.get("mode", "all")
    flag = {"changed": " --changed", "staged": " --staged"}.get(mode, "")
    if mode == "since":
        flag = f" --since {scope.get('since')}"
    return f"mmu vibecheck --format agent{flag}"


def render_agent(result: ScanResult) -> str:
    """Compact plain text for an LLM's context: no ANSI, a few lines per finding, ok/skip omitted."""
    s = result.summary()
    lines = [
        f"mmu vibecheck: {s['blocking']} blocking (P0), {s['warnings']} warning(s) (P1), "
        f"{s['suppressed']} suppressed"
        + (f", {s['baselined']} baselined" if s.get("baselined") else "")
        + f" | scope: {_scope_label(result.scope)}"
    ]
    active = [f for f in result.findings if f.status in {"fail", "warn"}]
    active.sort(key=lambda f: 0 if f.status == "fail" else 1)
    for f in active:
        first = f.locations[0].label() if f.locations else "(project)"
        more = ""
        if len(f.locations) > 1:
            extra = ", ".join(loc.label() for loc in f.locations[1:4])
            rest = len(f.locations) - 4
            more = f" (+{len(f.locations) - 1}: {extra}{', …' if rest > 0 else ''})"
        lines.append(f"{f.severity} {f.check} {first}{more}")
        lines.append(f"  what: {f.message}")
        for note in f.notes:
            lines.append(f"  note: {note}")
        if f.hint:
            lines.append("  fix: " + " ".join(part.strip() for part in f.hint.splitlines()))
        lines.append(f"  silence (only if false positive): {_silence_hint(f)}")
    rerun = _rerun_command(result.scope)
    if s["blocking"]:
        lines.append(f"Fix every P0 above, then re-run `{rerun}` until it reports 0 blocking.")
    elif s["warnings"]:
        lines.append(f"No blocking findings. P1 warnings do not block; fix them when in scope and re-run `{rerun}`.")
    else:
        lines.append("No findings. Nothing to fix.")
    return "\n".join(lines)


# --- sarif -----------------------------------------------------------------

def _sarif_rule(rule: Rule) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": rule.id,
        "name": "".join(part.capitalize() for part in rule.id.split("-")),
        "shortDescription": {"text": rule.title},
        "fullDescription": {"text": rule.summary},
        "help": {"text": rule.fix},
        "defaultConfiguration": {"level": "error" if rule.severity == "P0" else "warning"},
        "properties": {
            "tags": [*rule.tags, "security"],
            "security-severity": "8.0" if rule.severity == "P0" else "5.0",  # GitHub: high / medium
            "severity": rule.severity,
            "confidence": rule.confidence,
        },
    }
    if rule.ref:
        out["helpUri"] = rule.ref
    return out


def _sarif_location(loc: Location) -> dict[str, Any]:
    path = Path(loc.path)
    uri = path.as_uri() if path.is_absolute() else loc.path.replace("\\", "/")
    region: dict[str, Any] = {"startLine": max(1, loc.line or 1)}
    if loc.end_line and loc.end_line >= region["startLine"]:
        region["endLine"] = loc.end_line
    if loc.snippet:
        region["snippet"] = {"text": loc.snippet}
    physical: dict[str, Any] = {"artifactLocation": {"uri": uri}, "region": region}
    if not path.is_absolute():
        physical["artifactLocation"]["uriBaseId"] = "%SRCROOT%"
    return {"physicalLocation": physical}


def to_sarif(result: ScanResult) -> dict[str, Any]:
    """SARIF 2.1.0 log. One result per location, so code-scanning UIs annotate every line."""
    rules = all_rules()
    index = {rule.id: i for i, rule in enumerate(rules)}
    results: list[dict[str, Any]] = []
    for f in result.findings:
        if f.status not in _REPORTED:
            continue
        base: dict[str, Any] = {
            "ruleId": f.check,
            "level": "error" if f.severity == "P0" else "warning",
            "message": {"text": f.message},
        }
        if f.check in index:
            base["ruleIndex"] = index[f.check]
        if f.status == "suppressed":
            kind = "inSource" if f.suppress_source == "inline" else "external"
            base["suppressions"] = [{"kind": kind, "justification": f.suppress_reason}]
        if f.status == "baselined":
            base["baselineState"] = "unchanged"
            base["level"] = "note"
        if not f.locations:
            results.append({**base, "partialFingerprints": {"primaryLocationLineHash": f"{fingerprint(f.check, None)}:1"}})
        for loc in f.locations:
            results.append({
                **base,
                "locations": [_sarif_location(loc)],
                "partialFingerprints": {"primaryLocationLineHash": f"{fingerprint(f.check, loc)}:1"},
            })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "mmu-vibecheck",
                        "version": tool_version(),
                        "informationUri": INFORMATION_URI,
                        "rules": [_sarif_rule(rule) for rule in rules],
                    }
                },
                "originalUriBaseIds": {"%SRCROOT%": {"uri": result.root.resolve().as_uri() + "/"}},
                "results": results,
            }
        ],
    }


# --- rules -----------------------------------------------------------------

def render_rule_list(rules: list[Rule]) -> str:
    width = max((len(rule.id) for rule in rules), default=0)
    lines = [f"{rule.id.ljust(width)}  {rule.severity}  {rule.title}" for rule in rules]
    lines.append("")
    lines.append("Details: mmu vibecheck --explain <rule-id>")
    return "\n".join(lines)


def render_rule(rule: Rule) -> str:
    lines = [
        f"{rule.id} ({rule.severity}, confidence: {rule.confidence})",
        rule.title,
        "",
        f"What & why: {rule.summary}",
        "",
        "Fix:",
        *[f"  {line}" for line in rule.fix.splitlines()],
        "",
    ]
    for name, fix in rule.fix_variants:
        lines += [f"Fix ({name}):", *[f"  {line}" for line in fix.splitlines()], ""]
    if rule.ref:
        lines.append(f"Reference: {rule.ref}")
    if rule.tags:
        lines.append(f"Tags: {', '.join(rule.tags)}")
    lines.append(f"Suppress one line: mmu-ignore[{rule.id}]: <reason>  (same line or the line above)")
    lines.append(f'Suppress by path: [vibecheck] ignore = ["path/glob/**:{rule.id}"] in .mmu/config.toml')
    return "\n".join(lines)
