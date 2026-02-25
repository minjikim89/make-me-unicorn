from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

MODES = {
    "problem": ["docs/core/strategy.md", "docs/research/competitors.md", "docs/research/user_feedback.md"],
    "product": ["docs/core/product.md", "docs/ops/roadmap.md"],
    "design": ["docs/core/ux.md", "docs/core/product.md"],
    "frontend": ["docs/core/architecture.md", "current_sprint.md"],
    "backend": ["docs/core/architecture.md", "current_sprint.md", "docs/adr/001_decision_template.md"],
    "auth": ["docs/checklists/auth_security.md", "docs/core/architecture.md"],
    "billing": ["docs/core/pricing.md", "docs/checklists/billing_tax.md", "docs/ops/compliance.md"],
    "growth": ["docs/checklists/seo_distribution.md", "docs/ops/metrics.md"],
    "compliance": ["docs/ops/compliance.md", "docs/core/pricing.md"],
    "reliability": ["docs/ops/reliability.md", "docs/checklists/release_readiness.md"],
    "analytics": ["docs/ops/metrics.md", "docs/core/product.md"],
    "launch": ["docs/checklists/release_readiness.md", "docs/ops/roadmap.md"],
}

REQUIRED_FILES = [
    "README.md",
    "Unicorn.md",
    "current_sprint.md",
    "docs/core/strategy.md",
    "docs/core/product.md",
    "docs/core/pricing.md",
    "docs/core/architecture.md",
    "docs/core/ux.md",
    "docs/ops/roadmap.md",
    "docs/ops/metrics.md",
    "docs/ops/compliance.md",
    "docs/ops/reliability.md",
    "docs/checklists/from_scratch.md",
    "docs/checklists/auth_security.md",
    "docs/checklists/billing_tax.md",
    "docs/checklists/seo_distribution.md",
    "docs/checklists/release_readiness.md",
    "prompts/start.md",
    "prompts/close.md",
    "prompts/adr.md",
]

DEFAULT_SKIP_PATHS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "docs",
    ".mmu",
    ".github",
    "src/mmu_cli",
    "scripts",
    "examples",
    "cli",
    "tests",
}

CODE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rb", ".java", ".cs"}
HEADING_PATTERN = re.compile(r"^##\s*(M\d+)\s+(.+?)\s*$")
UNCHECKED_PATTERN = re.compile(r"^\s*-\s*\[\s\]\s+(.+)$")

INIT_TEMPLATES: dict[str, str] = {
    "README.md": dedent(
        """\
        # Make Me Unicorn Workspace

        This workspace uses Make Me Unicorn operating docs.

        ## Quick Start
        1. Update `docs/core/*` with your project context.
        2. Set this week's priorities in `current_sprint.md`.
        3. Start each working session with `prompts/start.md`.
        4. Close each session with `prompts/close.md`.
        """
    ),
    "Unicorn.md": dedent(
        """\
        # Unicorn Hub

        Primary operating hub for this project.

        ## Current Mode
        - mode: product
        - goal: reduce execution drift
        """
    ),
    "current_sprint.md": dedent(
        """\
        # Current Sprint

        ## Goal 1
        -

        ## Goal 2
        -

        ## Goal 3
        -
        """
    ),
    "docs/core/strategy.md": "# Strategy\n\n- ICP:\n- Core problem:\n- Success metric:\n",
    "docs/core/product.md": "# Product\n\n- Core flow:\n- Scope (this sprint):\n- Out of scope:\n",
    "docs/core/pricing.md": "# Pricing\n\n- Free:\n- Pro:\n- Refund policy:\n",
    "docs/core/architecture.md": "# Architecture\n\n- System map:\n- Data flow:\n- dev/staging/prod separation:\n",
    "docs/core/ux.md": "# UX\n\n- Main journey:\n- Empty/error states:\n",
    "docs/ops/roadmap.md": "# Roadmap\n\n- This month:\n- Next month:\n",
    "docs/ops/metrics.md": "# Metrics\n\n- North star:\n- Activation:\n- Retention:\n",
    "docs/ops/compliance.md": "# Compliance\n\n- Privacy policy:\n- Terms:\n- Data deletion flow:\n",
    "docs/ops/reliability.md": "# Reliability\n\n- Monitoring:\n- Incident handling:\n- Backup/recovery:\n",
    "docs/checklists/from_scratch.md": dedent(
        """\
        # SaaS From Scratch Checklist

        Purpose: move from idea to paid product with fewer blind spots.

        ## M0 Problem Fit
        - [ ] One ICP is clearly defined.
        - [ ] Problem statement is written in one sentence.
        - [ ] Existing alternatives are mapped.
        - [ ] One or two success metrics are defined.

        ## M1 Build Fit
        - [ ] Core value action is achievable within 1 minute.
        - [ ] Signup/login/logout are stable.
        - [ ] Error, empty, and loading states are implemented.
        - [ ] Basic event instrumentation exists.
        - [ ] `dev` and `staging` environments are separated.

        ## M2 Revenue Fit
        - [ ] Pricing page and plan comparison exist.
        - [ ] Payment success/failure/cancellation paths are tested.
        - [ ] Refund and cancellation policy is documented.
        - [ ] Access control matches subscription state.

        ## M3 Trust Fit
        - [ ] Privacy policy and terms are published.
        - [ ] Support contact path and response policy exist.
        - [ ] Admin/operator access controls exist.
        - [ ] Logging and monitoring are configured.

        ## M4 Growth Fit
        - [ ] OG thumbnail is configured.
        - [ ] Title/description/canonical are configured per page.
        - [ ] `sitemap.xml` and `robots.txt` are valid.
        - [ ] Core funnel events are tracked.

        ## M5 Scale Fit
        - [ ] Backup and recovery playbook is documented.
        - [ ] Alert routing for critical failures is active.
        - [ ] Incident communication template exists.
        - [ ] Monthly risk review ritual exists.
        - [ ] `prod` deployments run through a controlled pipeline.
        """
    ),
    "docs/checklists/auth_security.md": dedent(
        """\
        # Auth & Security Checklist

        - [ ] Login/signup path exists
        - [ ] password reset flow exists
        - [ ] Session management and logout covered
        """
    ),
    "docs/checklists/billing_tax.md": dedent(
        """\
        # Billing & Tax Checklist

        - [ ] Pricing and plan limits defined
        - [ ] webhook signature verification implemented
        - [ ] idempotent webhook processing implemented
        - [ ] Refund/cancel policy documented
        """
    ),
    "docs/checklists/seo_distribution.md": dedent(
        """\
        # SEO & Distribution Checklist

        - [ ] sitemap and robots configured
        - [ ] OG thumbnail/open graph metadata configured
        - [ ] Basic analytics events defined
        """
    ),
    "docs/checklists/release_readiness.md": dedent(
        """\
        # Release Readiness Checklist

        - [ ] Rollback plan exists
        - [ ] Monitoring and alerts active
        - [ ] Support path and status page defined
        """
    ),
    "prompts/start.md": "# Session Start Prompt\n\n- Mode:\n- Context files:\n- Today's objective:\n",
    "prompts/close.md": "# Session Close Prompt\n\n- What changed:\n- Decisions made:\n- Next actions:\n",
    "prompts/adr.md": "# ADR Prompt\n\n- Decision:\n- Context:\n- Options considered:\n- Trade-offs:\n",
}


class Result(dict):
    @property
    def exit_code(self) -> int:
        return int(self.get("exit_code", 1))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mmu", description="Make Me Unicorn CLI")
    parser.add_argument("--root", default=".", help="Project root path")
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    sub = parser.add_subparsers(dest="command", required=False)

    p_init = sub.add_parser("init", help="Initialize baseline docs and checklists")
    p_init.add_argument("--json", action="store_true", help="Output structured JSON")
    p_init.add_argument("--root", default=".", help="Project root path")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing files")

    p_start = sub.add_parser("start", help="Start a focused mode session")
    p_start.add_argument("--json", action="store_true", help="Output structured JSON")
    p_start.add_argument("--mode", required=True, choices=sorted(MODES.keys()))
    p_start.add_argument("--root", default=".", help="Project root path")
    p_start.add_argument("--emit", choices=["list", "bundle"], default="list", help="Output format")
    p_start.add_argument("--output", help="Write bundle output to a file")
    p_start.add_argument("--clipboard", action="store_true", help="Copy bundle output to clipboard")

    p_close = sub.add_parser("close", help="Close current session")
    p_close.add_argument("--json", action="store_true", help="Output structured JSON")
    p_close.add_argument("--root", default=".", help="Project root path")

    p_doctor = sub.add_parser("doctor", help="Run guardrail checks")
    p_doctor.add_argument("--json", action="store_true", help="Output structured JSON")
    p_doctor.add_argument("--root", default=".", help="Project root path")

    p_gate = sub.add_parser("gate", help="Check stage gate readiness")
    p_gate.add_argument("--json", action="store_true", help="Output structured JSON")
    p_gate.add_argument("--stage", required=True, help="Stage key (for example: M0, M1, M6)")
    p_gate.add_argument("--root", default=".", help="Project root path")

    p_status = sub.add_parser("status", help="Visual dashboard of launch progress")
    p_status.add_argument("--json", action="store_true", help="Output structured JSON")
    p_status.add_argument("--root", default=".", help="Project root path")

    p_snapshot = sub.add_parser("snapshot", help="Run snapshot diagnostic from mmu CLI")
    p_snapshot.add_argument("--json", action="store_true", help="Output structured JSON")
    p_snapshot.add_argument("--root", default=".", help="MMU root path where snapshot script exists")
    p_snapshot.add_argument("--target", default=".", help="Target project path to scan")
    p_snapshot.add_argument("--output", default="SNAPSHOT.md", help="Output report path")
    p_snapshot.add_argument("--no-md", action="store_true", help="Do not persist markdown report")

    return parser.parse_args()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def root_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def exists(root: Path, rel: str) -> bool:
    return (root / rel).is_file()


def read_text(path: Path, errors: list[str] | None = None) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        if errors is not None:
            errors.append(f"cannot read {path}: {exc}")
        return None


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def normalize_rel(path: str) -> str:
    return path.strip().strip("/")


def should_skip_rel(rel_path: str, skip_paths: set[str]) -> bool:
    rel_path = normalize_rel(rel_path)
    for skip in skip_paths:
        s = normalize_rel(skip)
        if not s:
            continue
        if rel_path == s or rel_path.startswith(f"{s}/"):
            return True
    return False


def load_config(root: Path) -> dict[str, Any]:
    cfg_path = root / ".mmu/config.toml"
    if not cfg_path.is_file() or tomllib is None:
        return {}
    content = read_text(cfg_path)
    if content is None:
        return {}
    try:
        data = tomllib.loads(content)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def doctor_skip_paths(root: Path) -> set[str]:
    cfg = load_config(root)
    merged = set(DEFAULT_SKIP_PATHS)
    doctor_cfg = cfg.get("doctor") if isinstance(cfg, dict) else None
    if isinstance(doctor_cfg, dict):
        extra = doctor_cfg.get("skip_paths")
        if isinstance(extra, list):
            for item in extra:
                if isinstance(item, str) and item.strip():
                    merged.add(item.strip())
    return merged


def gather_code_files(root: Path, skip_paths: set[str]) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir

        kept_dirs: list[str] = []
        for dirname in dirnames:
            child = f"{rel_dir}/{dirname}" if rel_dir else dirname
            if not should_skip_rel(child, skip_paths):
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            rel_file = f"{rel_dir}/{filename}" if rel_dir else filename
            if should_skip_rel(rel_file, skip_paths):
                continue
            path = root / rel_file
            if path.suffix.lower() in CODE_EXTENSIONS and path.is_file():
                files.append(path)
    return files


def file_contains_any(path: Path, patterns: list[str], errors: list[str], max_bytes: int = 2_000_000) -> bool:
    try:
        with path.open("rb") as f:
            raw = f.read(max_bytes)
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
        return False
    text = raw.decode("utf-8", errors="ignore")
    return any(p in text for p in patterns)


def detect_nextjs(root: Path) -> bool:
    next_configs = ["next.config.js", "next.config.mjs", "next.config.ts"]
    if any((root / name).exists() for name in next_configs):
        return True
    pkg = root / "package.json"
    pkg_text = read_text(pkg) if pkg.is_file() else None
    if pkg_text and '"next"' in pkg_text:
        return True
    return (root / "app").is_dir() or (root / "src/app").is_dir()


def has_metadata_markers(root: Path, code_files: list[Path], errors: list[str]) -> bool:
    candidate_layouts = [
        root / "app/layout.tsx",
        root / "app/layout.jsx",
        root / "src/app/layout.tsx",
        root / "src/app/layout.jsx",
    ]
    patterns = ["export const metadata", "generateMetadata(", "openGraph", "twitter:", "og:"]
    for layout in candidate_layouts:
        if layout.is_file() and file_contains_any(layout, patterns, errors):
            return True

    for file in code_files[:300]:
        if file_contains_any(file, patterns, errors):
            return True
    return False


def detect_webhook_files(root: Path, code_files: list[Path]) -> list[Path]:
    out: list[Path] = []
    for file in code_files:
        rel = file.relative_to(root).as_posix().lower()
        name = file.name.lower()
        if "webhook" in name or "/webhook" in rel or "webhooks" in rel:
            out.append(file)
    return out


def check_webhook_safety(webhook_files: list[Path], errors: list[str]) -> tuple[bool, bool]:
    signature_markers = [
        "stripe-signature",
        "constructevent",
        "webhook secret",
        "verify_signature",
        "x-signature",
        "svix",
    ]
    idempotency_markers = [
        "idempotent",
        "idempotency",
        "event_id",
        "processed_event",
        "dedupe",
        "on conflict",
        "upsert",
    ]
    has_signature = False
    has_idempotency = False
    for file in webhook_files:
        content = read_text(file, errors)
        if content is None:
            continue
        text = content.lower()
        if any(m in text for m in signature_markers):
            has_signature = True
        if any(m in text for m in idempotency_markers):
            has_idempotency = True
    return has_signature, has_idempotency


def has_environment_split(root: Path) -> bool:
    dev = [".env.development", ".env.dev", ".env.local"]
    staging = [".env.staging", ".env.stage"]
    prod = [".env.production", ".env.prod"]
    return (
        any((root / p).is_file() for p in dev)
        and any((root / p).is_file() for p in staging)
        and any((root / p).is_file() for p in prod)
    )


def build_bundle(root: Path, files: list[str], read_errors: list[str]) -> tuple[str, list[str]]:
    sections: list[str] = []
    missing: list[str] = []
    for rel in files:
        path = root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        content = read_text(path, read_errors)
        if content is None:
            missing.append(rel)
            continue
        sections.append(f"### {rel}\n\n```md\n{content}\n```")
    bundle = "\n\n".join(sections)
    return bundle, missing


def try_copy_clipboard(content: str) -> tuple[bool, str]:
    if sys.platform != "darwin":
        return False, "clipboard copy is only supported on macOS for now"
    try:
        proc = subprocess.run(["pbcopy"], input=content.encode("utf-8"), check=False)
    except OSError as exc:
        return False, f"failed to run pbcopy: {exc}"
    if proc.returncode != 0:
        return False, "pbcopy returned non-zero exit status"
    return True, "bundle copied to clipboard"


def command_start(mode: str, root: Path, emit: str, output: str | None, clipboard: bool) -> Result:
    mode_files = MODES[mode]
    write_text(root / ".mmu/last_mode", f"{mode}\n")
    write_text(root / ".mmu/last_started_at", f"{utc_now()}\n")

    messages = [f"Mode: {mode}", "Inject these files:"]
    present: list[str] = []
    missing: list[str] = []
    for rel in mode_files:
        if exists(root, rel):
            messages.append(f"  [ok] {rel}")
            present.append(rel)
        else:
            messages.append(f"  [missing] {rel}")
            missing.append(rel)

    if exists(root, "prompts/start.md"):
        messages.append("Prompt: prompts/start.md")

    bundle = ""
    read_errors: list[str] = []
    if emit == "bundle" or output or clipboard:
        bundle, bundle_missing = build_bundle(root, mode_files, read_errors)
        for rel in bundle_missing:
            if rel not in missing:
                missing.append(rel)

    if output:
        out_path = (root / output).resolve() if not Path(output).is_absolute() else Path(output)
        write_text(out_path, bundle)
        messages.append(f"Bundle written: {out_path}")

    if clipboard:
        ok, note = try_copy_clipboard(bundle)
        messages.append(("  [ok] " if ok else "  [warn] ") + note)

    if emit == "bundle":
        messages.append("--- BUNDLE START ---")
        messages.append(bundle if bundle else "(empty bundle)")
        messages.append("--- BUNDLE END ---")

    for err in read_errors:
        messages.append(f"  [warn] {err}")

    return Result(
        exit_code=0,
        mode=mode,
        injected_files=mode_files,
        present_files=present,
        missing_files=missing,
        output_file=output,
        messages=messages,
    )


def command_close(root: Path) -> Result:
    append_text(root / ".mmu/session_close.log", f"{utc_now()}\n")

    messages = ["Session close checklist"]
    sprint = root / "current_sprint.md"
    placeholder_found = False
    if sprint.is_file():
        messages.append("  [ok] current_sprint.md exists")
        text = read_text(sprint)
        if text and re.search(r"Goal 1|Goal 2|Goal 3", text):
            placeholder_found = True
            messages.append("  [warn] current_sprint.md still has placeholder goals")
    else:
        messages.append("  [missing] current_sprint.md")

    if exists(root, "prompts/close.md"):
        messages.append("  [next] Run prompt from prompts/close.md")
    if exists(root, "prompts/adr.md"):
        messages.append("  [next] If decisions changed, run prompts/adr.md")

    return Result(exit_code=0, placeholder_goals=placeholder_found, messages=messages)


def _find_mmu_root() -> Path | None:
    """Find the MMU package root (where docs/blueprints/ lives)."""
    # Walk up from this file: src/mmu_cli/cli.py -> repo root
    pkg_root = Path(__file__).resolve().parents[2]
    if (pkg_root / "docs" / "blueprints").is_dir():
        return pkg_root
    return None


def command_init(root: Path, force: bool) -> Result:
    created: list[str] = []
    skipped: list[str] = []
    overwritten: list[str] = []
    messages = [f"Init workspace: {root}"]

    for rel, content in INIT_TEMPLATES.items():
        path = root / rel
        existed_before = path.exists()
        if existed_before and not force:
            skipped.append(rel)
            messages.append(f"  [skip] {rel} (already exists)")
            continue
        write_text(path, content)
        if existed_before and force:
            overwritten.append(rel)
            messages.append(f"  [overwrite] {rel}")
        else:
            created.append(rel)
            messages.append(f"  [create] {rel}")

    # Copy blueprint files from MMU package
    mmu_root = _find_mmu_root()
    if mmu_root:
        bp_src = mmu_root / "docs" / "blueprints"
        bp_dst = root / "docs" / "blueprints"
        for bp_file in sorted(bp_src.glob("*.md")):
            rel = f"docs/blueprints/{bp_file.name}"
            dst = bp_dst / bp_file.name
            existed_before = dst.exists()
            if existed_before and not force:
                skipped.append(rel)
                messages.append(f"  [skip] {rel} (already exists)")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(bp_file.read_text(encoding="utf-8"), encoding="utf-8")
            if existed_before and force:
                overwritten.append(rel)
                messages.append(f"  [overwrite] {rel}")
            else:
                created.append(rel)
                messages.append(f"  [create] {rel}")
    else:
        messages.append("  [warn] Blueprint source not found — run from MMU repo or install from PyPI")

    if created or overwritten:
        messages.append("Init result: workspace scaffold ready")
        messages.append("")
        messages.append("Next steps:")
        messages.append("  1. mmu status          — see your launch dashboard")
        messages.append("  2. mmu doctor          — check what's missing")
        messages.append("  3. Edit docs/checklists/from_scratch.md — check off completed items")
        messages.append("  4. mmu gate --stage M0 — verify M0 Problem Fit")
        return Result(
            exit_code=0,
            created=created,
            overwritten=overwritten,
            skipped=skipped,
            messages=messages,
        )

    messages.append("Init result: nothing changed")
    return Result(exit_code=0, created=[], overwritten=[], skipped=skipped, messages=messages)


def parse_stage_headings(checklist_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in checklist_text.splitlines():
        m = HEADING_PATTERN.match(line)
        if m:
            stage = m.group(1).upper()
            title = m.group(2).strip()
            out[stage] = f"{stage} {title}"
    return out


def command_doctor(root: Path) -> Result:
    messages = ["Doctor checks"]
    failures = 0
    read_errors: list[str] = []

    for rel in REQUIRED_FILES:
        if exists(root, rel):
            messages.append(f"  [ok] {rel}")
        else:
            messages.append(f"  [fail] missing {rel}")
            failures += 1

    auth_checklist = root / "docs/checklists/auth_security.md"
    auth_text = read_text(auth_checklist, read_errors) if auth_checklist.is_file() else None
    if auth_text and re.search(r"password reset", auth_text, re.IGNORECASE):
        messages.append("  [ok] auth includes password reset")
    else:
        messages.append("  [fail] auth checklist missing password reset coverage")
        failures += 1

    billing_checklist = root / "docs/checklists/billing_tax.md"
    billing_text = read_text(billing_checklist, read_errors) if billing_checklist.is_file() else None
    if billing_text and ("webhook" in billing_text.lower() and "idempotent" in billing_text.lower()):
        messages.append("  [ok] billing includes webhook safety")
    else:
        messages.append("  [fail] billing checklist missing webhook safety")
        failures += 1

    seo_checklist = root / "docs/checklists/seo_distribution.md"
    seo_text = read_text(seo_checklist, read_errors) if seo_checklist.is_file() else None
    if seo_text and ("og thumbnail" in seo_text.lower() or "open graph" in seo_text.lower()):
        messages.append("  [ok] SEO includes OG thumbnail")
    else:
        messages.append("  [fail] SEO checklist missing OG thumbnail")
        failures += 1

    arch_file = root / "docs/core/architecture.md"
    arch_text = read_text(arch_file, read_errors) if arch_file.is_file() else None
    if arch_text and "dev/staging/prod" in arch_text:
        messages.append("  [ok] architecture includes environment split")
    else:
        messages.append("  [fail] architecture missing dev/staging/prod split")
        failures += 1

    skip_paths = doctor_skip_paths(root)
    code_files = gather_code_files(root, skip_paths)
    if not code_files:
        messages.append("  [skip] codebase checks (no source files detected)")
    else:
        nextjs = detect_nextjs(root)
        if nextjs:
            if has_metadata_markers(root, code_files, read_errors):
                messages.append("  [ok] Next.js metadata/OG markers detected")
            else:
                messages.append("  [fail] Next.js detected but metadata/OG markers are missing")
                failures += 1
        else:
            messages.append("  [skip] Next.js metadata check (Next.js not detected)")

        webhook_files = detect_webhook_files(root, code_files)
        if webhook_files:
            has_sig, has_idem = check_webhook_safety(webhook_files, read_errors)
            if has_sig:
                messages.append("  [ok] webhook signature verification markers detected")
            else:
                messages.append("  [fail] webhook handlers found but signature verification markers missing")
                failures += 1
            if has_idem:
                messages.append("  [ok] webhook idempotency markers detected")
            else:
                messages.append("  [fail] webhook handlers found but idempotency markers missing")
                failures += 1
        else:
            messages.append("  [skip] webhook safety check (no webhook handlers detected)")

        env_example = root / ".env.example"
        if env_example.is_file():
            messages.append("  [ok] .env.example exists")
        else:
            messages.append("  [fail] missing .env.example for environment documentation")
            failures += 1

        if has_environment_split(root):
            messages.append("  [ok] environment split files detected (dev/staging/prod)")
        else:
            messages.append("  [fail] missing environment split files for dev/staging/prod")
            failures += 1

    for err in read_errors:
        messages.append(f"  [warn] {err}")

    if failures > 0:
        messages.append(f"Doctor result: {failures} issue(s) found")
        return Result(exit_code=2, failures=failures, messages=messages)

    messages.append("Doctor result: clean")
    return Result(exit_code=0, failures=0, messages=messages)


def command_gate(stage: str, root: Path) -> Result:
    stage = stage.upper().strip()
    if not re.fullmatch(r"M\d+", stage):
        return Result(exit_code=1, messages=[f"Invalid stage: {stage} (expected format M<number>)"])

    checklist = root / "docs/checklists/from_scratch.md"
    text = read_text(checklist)
    if text is None:
        return Result(exit_code=1, messages=["Missing or unreadable checklist: docs/checklists/from_scratch.md"])

    headings = parse_stage_headings(text)
    heading = headings.get(stage)
    if not heading:
        available = ", ".join(sorted(headings.keys())) if headings else "none"
        return Result(exit_code=1, messages=[f"Stage not found: {stage}", f"Available stages: {available}"])

    lines = text.splitlines()
    in_section = False
    pending: list[str] = []

    for line in lines:
        m = HEADING_PATTERN.match(line)
        if m:
            current = m.group(1).upper()
            if current == stage:
                in_section = True
                continue
            if in_section:
                break

        if in_section:
            unchecked = UNCHECKED_PATTERN.match(line)
            if unchecked:
                pending.append(line.strip())

    messages = [f"Gate report: {stage} ({heading})"]
    if pending:
        for line in pending:
            messages.append(f"  {line}")
        messages.append("Gate result: NOT PASS")
        return Result(exit_code=3, stage=stage, heading=heading, pending=pending, messages=messages)

    messages.append("Gate result: PASS")
    return Result(exit_code=0, stage=stage, heading=heading, pending=[], messages=messages)


def command_snapshot(root: Path, target: str, output: str, no_md: bool) -> Result:
    candidates = [
        root / "snapshot",
        root / "scripts/snapshot.sh",
        Path(__file__).resolve().parents[2] / "snapshot",
        Path(__file__).resolve().parents[2] / "scripts/snapshot.sh",
    ]

    script = next((p for p in candidates if p.is_file()), None)
    if script is None:
        return Result(
            exit_code=1,
            messages=[
                "Snapshot script not found.",
                "Expected one of: snapshot or scripts/snapshot.sh",
            ],
        )

    cmd = [str(script), target]
    if no_md:
        cmd.append("--no-md")
    else:
        cmd.append(output)

    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except OSError as exc:
        return Result(exit_code=1, messages=[f"failed to run snapshot: {exc}"])

    out_lines = proc.stdout.splitlines() if proc.stdout else []
    err_lines = proc.stderr.splitlines() if proc.stderr else []
    messages = out_lines + [f"[stderr] {line}" for line in err_lines]
    return Result(exit_code=proc.returncode, command=cmd, messages=messages)


def command_status(root: Path) -> Result:
    from mmu_cli.display import render_status, scan_all_blueprints, scan_gates

    dashboard = render_status(root)

    blueprints = scan_all_blueprints(root)
    gates = scan_gates(root)
    bp_done = sum(d for _, d, _ in blueprints)
    bp_total = sum(t for _, _, t in blueprints)
    gate_done = sum(d for _, d, _ in gates)
    gate_total = sum(t for _, _, t in gates)

    return Result(
        exit_code=0,
        dashboard=dashboard,
        blueprint_progress={"done": bp_done, "total": bp_total},
        gate_progress={"done": gate_done, "total": gate_total},
        messages=[dashboard],
    )


def render_result(result: Result, as_json: bool) -> int:
    if as_json:
        clean = {k: v for k, v in result.items() if k != "dashboard"}
        print(json.dumps(clean, ensure_ascii=False, indent=2))
    else:
        from mmu_cli.display import colorize_message

        for line in result.get("messages", []):
            print(colorize_message(line))
    return result.exit_code


def main() -> int:
    args = parse_args()
    root = root_path(getattr(args, "root", "."))

    # Default: `mmu` with no subcommand shows status dashboard
    if not args.command:
        result = command_status(root)
        return render_result(result, False)

    if args.command == "init":
        result = command_init(root, args.force)
        return render_result(result, args.json)
    if args.command == "start":
        result = command_start(args.mode, root, args.emit, args.output, args.clipboard)
        return render_result(result, args.json)
    if args.command == "close":
        result = command_close(root)
        return render_result(result, args.json)
    if args.command == "doctor":
        result = command_doctor(root)
        return render_result(result, args.json)
    if args.command == "gate":
        result = command_gate(args.stage, root)
        return render_result(result, args.json)
    if args.command == "status":
        result = command_status(root)
        return render_result(result, args.json)
    if args.command == "snapshot":
        result = command_snapshot(root, args.target, args.output, args.no_md)
        return render_result(result, args.json)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
