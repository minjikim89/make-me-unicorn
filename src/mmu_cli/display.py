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
_CONDITION_IF = re.compile(r"^<!--\s*if:(\w+)\s*-->")
_CONDITION_ENDIF = re.compile(r"^<!--\s*endif\s*-->")

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

# Aliases for `mmu show <name>` fuzzy matching
BLUEPRINT_ALIASES: dict[str, str] = {}
for _fname, _label in BLUEPRINT_NAMES.items():
    _key = _label.lower().replace(" & ", "-").replace(" ", "-")
    BLUEPRINT_ALIASES[_key] = _fname
# Extra shortcuts
BLUEPRINT_ALIASES.update({
    "front": "01-frontend.md",
    "back": "02-backend.md",
    "devops": "05-devops.md",
    "ops": "05-devops.md",
    "sec": "06-security.md",
    "mon": "07-monitoring.md",
    "seo": "08-seo-marketing.md",
    "marketing": "08-seo-marketing.md",
    "legal": "09-legal-compliance.md",
    "compliance": "09-legal-compliance.md",
    "perf": "10-performance.md",
    "test": "11-testing.md",
    "ci": "12-cicd.md",
    "cd": "12-cicd.md",
    "email": "13-email-notifications.md",
    "notif": "13-email-notifications.md",
    "notification": "13-email-notifications.md",
    "a11y": "15-accessibility.md",
})


def resolve_blueprint(name: str) -> str | None:
    """Resolve a user-provided name to a blueprint filename, or None."""
    key = name.lower().strip()
    if key in BLUEPRINT_ALIASES:
        return BLUEPRINT_ALIASES[key]
    # Try partial match
    for alias, fname in BLUEPRINT_ALIASES.items():
        if key in alias or alias in key:
            return fname
    # Try matching against BLUEPRINT_NAMES values
    for fname, label in BLUEPRINT_NAMES.items():
        if key in label.lower():
            return fname
    return None


_PRIORITY_RE = re.compile(r"^\[P([012])\]\s*", re.IGNORECASE)

PRIORITY_LABELS = {
    0: ("🔴", "critical"),
    1: ("🟡", "important"),
    2: ("", ""),  # default, no marker
}


def _parse_priority(text: str) -> tuple[int, str]:
    """Extract priority tag from item text. Returns (priority, clean_text)."""
    m = _PRIORITY_RE.match(text)
    if m:
        return int(m.group(1)), text[m.end():].strip()
    return 2, text  # default priority


def render_blueprint_detail(
    path: Path,
    label: str,
    flags: dict[str, bool] | None = None,
) -> str:
    """Build a colorful detailed view of a single blueprint file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return red(f"  Cannot read {path}")

    lines: list[str] = []
    section_heading = re.compile(r"^##\s+(.+)$")
    _item_done = re.compile(r"^\s*-\s*\[x\]\s+(.+)$", re.IGNORECASE)
    _item_todo = re.compile(r"^\s*-\s*\[\s\]\s+(.+)$")

    # First pass: gather section stats
    # items: (is_done, priority, clean_text)
    sections: list[tuple[str, list[tuple[bool, int, str]]]] = []
    skipped_sections: list[str] = []
    current_section = ""
    current_items: list[tuple[bool, int, str]] = []
    condition_stack: list[bool] = []

    for line in text.splitlines():
        stripped = line.strip()

        m_if = _CONDITION_IF.match(stripped)
        if m_if:
            flag_name = m_if.group(1)
            if flags is not None:
                condition_stack.append(flags.get(flag_name, True))
            else:
                condition_stack.append(True)
            continue
        if _CONDITION_ENDIF.match(stripped):
            if condition_stack:
                condition_stack.pop()
            continue

        active = _is_active(condition_stack)

        hm = section_heading.match(line)
        if hm:
            if current_section and current_items:
                sections.append((current_section, current_items))
            elif current_section and not current_items and not active:
                skipped_sections.append(current_section)
            current_section = hm.group(1).strip()
            current_items = []
            continue

        if not active:
            # Track section name for skipped display but skip item
            continue

        dm = _item_done.match(line)
        if dm:
            pri, clean = _parse_priority(dm.group(1).strip())
            current_items.append((True, pri, clean))
            continue
        tm = _item_todo.match(line)
        if tm:
            pri, clean = _parse_priority(tm.group(1).strip())
            current_items.append((False, pri, clean))

    if current_section and current_items:
        sections.append((current_section, current_items))
    elif current_section and not current_items and not _is_active(condition_stack):
        skipped_sections.append(current_section)

    # Overall stats
    all_done = sum(1 for _, items in sections for done, _, _ in items if done)
    all_total = sum(len(items) for _, items in sections)
    all_pct = all_done / all_total if all_total else 0.0

    # Priority stats
    p0_total = sum(1 for _, items in sections for _, p, _ in items if p == 0)
    p0_done = sum(1 for _, items in sections for d, p, _ in items if p == 0 and d)
    p1_total = sum(1 for _, items in sections for _, p, _ in items if p == 1)
    p1_done = sum(1 for _, items in sections for d, p, _ in items if p == 1 and d)

    # Header
    lines.append("")
    lines.append(bold(f"  🗺️  {label.upper()}") + dim(f"  ({all_done}/{all_total})  {all_pct*100:.0f}%"))
    lines.append(f"  {progress_bar(all_done, all_total, 40)}")

    # Priority summary (if any priorities exist)
    if p0_total > 0 or p1_total > 0:
        parts = []
        if p0_total > 0:
            p0_color = green if p0_done == p0_total else red
            parts.append(p0_color(f"🔴 P0: {p0_done}/{p0_total}"))
        if p1_total > 0:
            p1_color = green if p1_done == p1_total else yellow
            parts.append(p1_color(f"🟡 P1: {p1_done}/{p1_total}"))
        lines.append(f"  {' · '.join(parts)}")

    lines.append("")
    lines.append(dim("  ─" * 28))

    # Sections with global item numbering
    item_num = 0
    for section_name, items in sections:
        s_done = sum(1 for d, _, _ in items if d)
        s_total = len(items)
        s_has_p0 = any(p == 0 and not d for d, p, _ in items)

        if s_done == s_total and s_total > 0:
            section_status = green(" ✓")
        elif s_has_p0:
            section_status = red(f" {s_done}/{s_total} 🔴")
        elif s_done > 0:
            section_status = yellow(f" {s_done}/{s_total}")
        else:
            section_status = red(f" 0/{s_total}")

        lines.append("")
        lines.append(f"  {bold(section_name)}{section_status}")
        lines.append(f"  {mini_bar(s_done, s_total)}")

        for is_done, priority, item_text in items:
            item_num += 1
            num_str = dim(f"{item_num:>3}")
            pri_icon, _ = PRIORITY_LABELS.get(priority, ("", ""))
            pri_str = f"{pri_icon} " if pri_icon else "  "

            if is_done:
                lines.append(f"  {num_str} {pri_str}{green('✓')} {dim(item_text)}")
            else:
                if priority == 0:
                    lines.append(f"  {num_str} {pri_str}{red('✗')} {red(bold(item_text))}")
                elif priority == 1:
                    lines.append(f"  {num_str} {pri_str}{yellow('✗')} {bold(item_text)}")
                else:
                    lines.append(f"  {num_str} {pri_str}{dim('✗')} {item_text}")

    lines.append("")
    lines.append(dim("  ─" * 28))

    # Tip — priority aware
    if all_pct >= 1.0:
        lines.append(f"  {green('✨')} {bold(label)} is complete!")
    elif p0_total > p0_done:
        lines.append(f"  🔴 {bold(str(p0_total - p0_done))} critical items remain — fix these first")
    elif p1_total > p1_done:
        lines.append(f"  🟡 {bold(str(p1_total - p1_done))} important items remain")
    elif all_pct >= 0.7:
        remaining = all_total - all_done
        lines.append(f"  💡 Almost there — {bold(str(remaining))} items remaining")
    else:
        lines.append(f"  💡 {all_total - all_done} items to go")

    # Skipped sections (not applicable per config)
    if skipped_sections:
        lines.append("")
        lines.append(f"  {dim('Skipped (not applicable):')}")
        for sec in skipped_sections:
            lines.append(f"    {dim('⊘ ' + sec)}")

    bp_key = label.lower().replace(" & ", "-").replace(" ", "-")
    lines.append(f"  {dim('Tip:')} {cyan(f'mmu check {bp_key} <#>')} · {cyan(f'mmu uncheck {bp_key} <#>')}")
    lines.append("")
    return "\n".join(lines)


def _is_active(condition_stack: list[bool]) -> bool:
    """Return True if all conditions in the stack are met (no false parent)."""
    return all(condition_stack)


def scan_blueprint(
    path: Path,
    flags: dict[str, bool] | None = None,
) -> tuple[int, int, int]:
    """Return (done, total, skipped) checkbox counts for a blueprint file.

    When *flags* is provided, sections wrapped in ``<!-- if:flag_name -->``
    markers are skipped if the flag is False.  Skipped items are excluded
    from both *done* and *total* and counted separately in *skipped*.
    """
    done = 0
    total = 0
    skipped = 0
    condition_stack: list[bool] = []

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0, 0, 0

    for line in text.splitlines():
        stripped = line.strip()

        # Handle condition markers
        m_if = _CONDITION_IF.match(stripped)
        if m_if:
            flag_name = m_if.group(1)
            if flags is not None:
                condition_stack.append(flags.get(flag_name, True))
            else:
                condition_stack.append(True)
            continue

        if _CONDITION_ENDIF.match(stripped):
            if condition_stack:
                condition_stack.pop()
            continue

        active = _is_active(condition_stack)

        if _CHECK_DONE.match(line):
            if active:
                done += 1
                total += 1
            else:
                skipped += 1
        elif _CHECK_TODO.match(line):
            if active:
                total += 1
            else:
                skipped += 1

    return done, total, skipped


def scan_all_blueprints(
    root: Path,
    flags: dict[str, bool] | None = None,
) -> list[tuple[str, int, int, int]]:
    """Scan all blueprint files. Returns [(name, done, total, skipped), ...]."""
    bp_dir = root / "docs" / "blueprints"
    results = []
    for filename, label in BLUEPRINT_NAMES.items():
        path = bp_dir / filename
        if path.is_file():
            done, total, skipped = scan_blueprint(path, flags)
            results.append((label, done, total, skipped))
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


def render_status(root: Path, flags: dict[str, bool] | None = None) -> str:
    """Build the full visual status dashboard string."""
    lines: list[str] = []

    # --- Blueprint scan ---
    blueprints = scan_all_blueprints(root, flags)
    bp_done = sum(d for _, d, _, _ in blueprints)
    bp_total = sum(t for _, _, t, _ in blueprints)
    bp_skipped = sum(s for _, _, _, s in blueprints)

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
    bp_header = bold("  🗺️  BLUEPRINTS") + dim(f"  ({bp_done}/{bp_total})")
    if bp_skipped > 0:
        bp_header += dim(f"  [{bp_skipped} skipped]")
    lines.append(bp_header)
    lines.append("")
    for label, d, t, s in blueprints:
        pct_text = f"{d/t*100:.0f}%" if t > 0 else "--"
        skip_text = dim(f" -{s}") if s > 0 else ""
        lines.append(f"    {label:<18} {mini_bar(d, t)}  {dim(pct_text)}{skip_text}")
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
