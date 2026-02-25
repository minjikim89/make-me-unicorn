"""Visual display components for MMU CLI — colors, progress bars, unicorn art."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Color support
# ---------------------------------------------------------------------------

_NO_COLOR = os.environ.get("NO_COLOR") or not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if _NO_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(t: str) -> str:
    return _c("92", t)


def red(t: str) -> str:
    return _c("91", t)


def yellow(t: str) -> str:
    return _c("93", t)


def blue(t: str) -> str:
    return _c("94", t)


def cyan(t: str) -> str:
    return _c("96", t)


def magenta(t: str) -> str:
    return _c("95", t)


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def progress_bar(done: int, total: int, width: int = 30) -> str:
    if total == 0:
        pct = 0.0
    else:
        pct = done / total
    filled = int(width * pct)
    empty = width - filled
    bar = green("█" * filled) + dim("░" * empty)
    pct_str = f"{pct * 100:.0f}%"
    return f"{bar}  {bold(pct_str)}  ({done}/{total})"


# ---------------------------------------------------------------------------
# Unicorn evolution ASCII art
# ---------------------------------------------------------------------------

UNICORN_STAGES = [
    # 0-15%: egg
    (0.15, "egg", [
        dim("        .-\"\"\"-. "),
        dim("       /       \\"),
        dim("      |    ?    |"),
        dim("       \\       /"),
        dim("        '-----' "),
    ]),
    # 15-35%: hatching
    (0.35, "hatching", [
        yellow("        .--") + dim("*") + yellow("--."),
        yellow("       / ") + bold("°v°") + yellow("  \\"),
        yellow("      |       |"),
        yellow("       \\ ___ /"),
        yellow("        '---' "),
    ]),
    # 35-55%: baby unicorn
    (0.55, "foal", [
        cyan("          /"),
        cyan("    ,") + bold("~~") + cyan("/"),
        "    " + bold("(o.o)"),
        "    " + bold("/|  |\\"),
        "    " + dim("_/ \\_ "),
    ]),
    # 55-75%: young unicorn
    (0.75, "young", [
        magenta("         //"),
        magenta("   ,") + bold("~~~") + magenta("//"),
        "   " + bold("(o_o)") + magenta("  *"),
        "   " + bold("/|  |\\"),
        "   " + bold("_/  \\_"),
    ]),
    # 75-95%: unicorn
    (0.95, "unicorn", [
        magenta("        ///"),
        magenta("  ,") + bold("~~~~") + magenta("///"),
        "  " + bold("(^_^)") + magenta("  **"),
        "  " + bold("/|  |\\") + magenta(" ~"),
        "  " + bold("_/  \\_"),
    ]),
    # 95-100%: FULL UNICORN
    (1.01, "legendary", [
        magenta(" *") + bold("      ///") + magenta("   *"),
        magenta("  *,") + bold("~~~~") + magenta("///") + magenta("  *"),
        magenta("  ") + bold("(^o^)") + magenta(" ** !!"),
        "  " + bold("/|  |\\") + magenta(" ~*~"),
        "  " + bold("_/  \\_") + magenta("  *"),
    ]),
]


def unicorn_art(pct: float) -> tuple[str, list[str]]:
    """Return (stage_name, art_lines) for the given completion percentage."""
    for threshold, name, art in UNICORN_STAGES:
        if pct <= threshold:
            return name, art
    return UNICORN_STAGES[-1][1], UNICORN_STAGES[-1][2]


# ---------------------------------------------------------------------------
# Blueprint scanner
# ---------------------------------------------------------------------------

_CHECK_DONE = re.compile(r"^\s*-\s*\[x\]\s+", re.IGNORECASE)
_CHECK_TODO = re.compile(r"^\s*-\s*\[\s\]\s+")

BLUEPRINT_NAMES = {
    "01-frontend.md": "Frontend",
    "02-backend.md": "Backend",
    "03-auth.md": "Auth",
    "04-billing.md": "Billing",
    "05-devops.md": "DevOps",
    "06-security.md": "Security",
    "07-monitoring.md": "Monitoring",
    "08-seo-marketing.md": "SEO & Marketing",
    "09-legal-compliance.md": "Legal",
    "10-performance.md": "Performance",
    "11-testing.md": "Testing",
    "12-cicd.md": "CI/CD",
    "13-email-notifications.md": "Email & Notif",
    "14-analytics.md": "Analytics",
    "15-accessibility.md": "Accessibility",
}


def scan_blueprint(path: Path) -> tuple[int, int]:
    """Return (done, total) checkbox counts for a blueprint file."""
    done = 0
    total = 0
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0, 0
    for line in text.splitlines():
        if _CHECK_DONE.match(line):
            done += 1
            total += 1
        elif _CHECK_TODO.match(line):
            total += 1
    return done, total


def scan_all_blueprints(root: Path) -> list[tuple[str, int, int]]:
    """Scan all blueprint files. Returns [(name, done, total), ...]."""
    bp_dir = root / "docs" / "blueprints"
    results = []
    for filename, label in BLUEPRINT_NAMES.items():
        path = bp_dir / filename
        if path.is_file():
            done, total = scan_blueprint(path)
            results.append((label, done, total))
    return results


def scan_gates(root: Path) -> list[tuple[str, int, int]]:
    """Scan gate stages from from_scratch.md. Returns [(stage_label, done, total), ...]."""
    checklist = root / "docs" / "checklists" / "from_scratch.md"
    try:
        text = checklist.read_text(encoding="utf-8")
    except OSError:
        return []

    heading_re = re.compile(r"^##\s*(M\d+)\s+(.+?)\s*$")
    results = []
    current_label = ""
    done = 0
    total = 0

    for line in text.splitlines():
        m = heading_re.match(line)
        if m:
            if current_label:
                results.append((current_label, done, total))
            current_label = f"{m.group(1)} {m.group(2)}"
            done = 0
            total = 0
            continue
        if current_label:
            if _CHECK_DONE.match(line):
                done += 1
                total += 1
            elif _CHECK_TODO.match(line):
                total += 1

    if current_label:
        results.append((current_label, done, total))
    return results


# ---------------------------------------------------------------------------
# Render full status dashboard
# ---------------------------------------------------------------------------

def mini_bar(done: int, total: int, width: int = 16) -> str:
    if total == 0:
        return dim("░" * width) + "  --"
    pct = done / total
    filled = int(width * pct)
    empty = width - filled
    if pct >= 1.0:
        bar = green("█" * width)
    elif pct >= 0.5:
        bar = cyan("█" * filled) + dim("░" * empty)
    elif pct > 0:
        bar = yellow("█" * filled) + dim("░" * empty)
    else:
        bar = dim("░" * width)
    return f"{bar} {done:>3}/{total:<3}"


def render_status(root: Path) -> str:
    """Build the full visual status dashboard string."""
    lines: list[str] = []

    # --- Blueprint scan ---
    blueprints = scan_all_blueprints(root)
    bp_done = sum(d for _, d, _ in blueprints)
    bp_total = sum(t for _, _, t in blueprints)

    # --- Gate scan ---
    gates = scan_gates(root)
    gate_done = sum(d for _, d, _ in gates)
    gate_total = sum(t for _, _, t in gates)

    # --- Overall ---
    all_done = bp_done + gate_done
    all_total = bp_total + gate_total
    all_pct = all_done / all_total if all_total else 0.0

    # --- Unicorn art ---
    stage_name, art = unicorn_art(all_pct)

    lines.append("")
    lines.append(bold("  🦄  MAKE ME UNICORN — STATUS DASHBOARD"))
    lines.append(dim("  ─" * 28))
    lines.append("")

    # Art + overall progress side by side
    for art_line in art:
        lines.append(f"  {art_line}")
    lines.append("")
    lines.append(f"  Stage: {bold(stage_name.upper())}    {progress_bar(all_done, all_total)}")
    lines.append("")

    # --- Gate progress ---
    lines.append(dim("  ─" * 28))
    lines.append(bold("  📋  LAUNCH GATES") + dim(f"  ({gate_done}/{gate_total})"))
    lines.append("")
    for label, d, t in gates:
        status = green(" ✓ PASS") if d == t and t > 0 else red(" ✗ OPEN")
        lines.append(f"    {label:<22} {mini_bar(d, t)}{status}")
    lines.append("")

    # --- Blueprint progress ---
    lines.append(dim("  ─" * 28))
    lines.append(bold("  🗺️  BLUEPRINTS") + dim(f"  ({bp_done}/{bp_total})"))
    lines.append("")
    for label, d, t in blueprints:
        pct_text = f"{d/t*100:.0f}%" if t > 0 else "--"
        lines.append(f"    {label:<18} {mini_bar(d, t)}  {dim(pct_text)}")
    lines.append("")

    lines.append(dim("  ─" * 28))

    # --- Tip (context-aware) ---
    open_gates = [label for label, d, t in gates if t > 0 and d < t]
    gate_pct = gate_done / gate_total if gate_total else 0.0

    if all_pct == 0:
        tip = "Start by checking items in " + cyan("docs/checklists/from_scratch.md")
    elif all_pct >= 1.0:
        tip = magenta("✨ LEGENDARY! ") + "You're ready to launch"
    elif not open_gates and all_pct < 1.0:
        tip = green("All gates PASS! ") + "Now tackle blueprint items for full coverage"
    elif gate_pct >= 0.8 and open_gates:
        tip = "Gates almost done! Remaining: " + bold(", ".join(open_gates))
    elif all_pct < 0.25:
        first_open = open_gates[0] if open_gates else "open gates"
        tip = "Focus on " + bold(first_open) + " gate next"
    elif all_pct < 0.5:
        tip = "Moving along! Tackle blueprint items for deeper coverage"
    elif all_pct < 0.75:
        tip = "Strong progress — start thinking about " + bold("launch readiness")
    else:
        tip = magenta("Almost there! ") + "Review remaining items and ship it"

    lines.append(f"  💡 {tip}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Colorize existing command outputs
# ---------------------------------------------------------------------------

def colorize_message(msg: str) -> str:
    """Add colors to existing [ok]/[fail]/[warn]/[skip] prefixed messages."""
    if "[ok]" in msg:
        return msg.replace("[ok]", green("✓"))
    if "[fail]" in msg:
        return msg.replace("[fail]", red("✗"))
    if "[warn]" in msg:
        return msg.replace("[warn]", yellow("⚠"))
    if "[skip]" in msg:
        return msg.replace("[skip]", dim("⊘"))
    if "[missing]" in msg:
        return msg.replace("[missing]", red("✗"))
    if "[next]" in msg:
        return msg.replace("[next]", cyan("→"))
    if "[create]" in msg:
        return msg.replace("[create]", green("+"))
    if "[overwrite]" in msg:
        return msg.replace("[overwrite]", yellow("~"))
    if "Doctor result: clean" in msg:
        return green(bold("  ✓ Doctor result: clean"))
    if "Doctor result:" in msg:
        return red(bold(f"  {msg.strip()}"))
    if "Gate result: PASS" in msg:
        return green(bold("  ✓ Gate result: PASS"))
    if "Gate result: NOT PASS" in msg:
        return red(bold("  ✗ Gate result: NOT PASS"))
    if msg.startswith("Mode:"):
        return bold(f"  🎯 {msg}")
    if msg.startswith("Session close"):
        return bold(f"  📋 {msg}")
    return msg
