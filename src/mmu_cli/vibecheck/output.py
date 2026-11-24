"""Vibecheck output formatters."""

from __future__ import annotations

from mmu_cli.vibecheck.engine import Finding

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
