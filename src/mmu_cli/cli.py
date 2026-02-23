from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

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

STAGE_HEADINGS = {
    "M0": "M0 Problem Fit",
    "M1": "M1 Build Fit",
    "M2": "M2 Revenue Fit",
    "M3": "M3 Trust Fit",
    "M4": "M4 Growth Fit",
    "M5": "M5 Scale Fit",
}

CODE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rb", ".java", ".cs"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mmu", description="Make Me Unicorn CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Start a focused mode session")
    p_start.add_argument("--mode", required=True, choices=sorted(MODES.keys()))
    p_start.add_argument("--root", default=".", help="Project root path")

    p_close = sub.add_parser("close", help="Close current session")
    p_close.add_argument("--root", default=".", help="Project root path")

    p_doctor = sub.add_parser("doctor", help="Run guardrail checks")
    p_doctor.add_argument("--root", default=".", help="Project root path")

    p_gate = sub.add_parser("gate", help="Check stage gate readiness")
    p_gate.add_argument("--stage", required=True, choices=sorted(STAGE_HEADINGS.keys()))
    p_gate.add_argument("--root", default=".", help="Project root path")

    return parser.parse_args()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def root_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def exists(root: Path, rel: str) -> bool:
    return (root / rel).is_file()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def command_start(mode: str, root: Path) -> int:
    mode_files = MODES[mode]
    write_text(root / ".mmu/last_mode", f"{mode}\n")
    write_text(root / ".mmu/last_started_at", f"{utc_now()}\n")

    print(f"Mode: {mode}")
    print("Inject these files:")
    for rel in mode_files:
        status = "ok" if exists(root, rel) else "missing"
        print(f"  [{status}] {rel}")

    if exists(root, "prompts/start.md"):
        print("Prompt: prompts/start.md")
    return 0


def command_close(root: Path) -> int:
    append_text(root / ".mmu/session_close.log", f"{utc_now()}\n")

    print("Session close checklist")
    sprint = root / "current_sprint.md"
    if sprint.is_file():
        print("  [ok] current_sprint.md exists")
        text = read_text(sprint)
        if re.search(r"Goal 1|Goal 2|Goal 3", text):
            print("  [warn] current_sprint.md still has placeholder goals")
    else:
        print("  [missing] current_sprint.md")

    if exists(root, "prompts/close.md"):
        print("  [next] Run prompt from prompts/close.md")
    if exists(root, "prompts/adr.md"):
        print("  [next] If decisions changed, run prompts/adr.md")
    return 0


def gather_code_files(root: Path) -> list[Path]:
    files: list[Path] = []
    skip = {
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
    }
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel == item or rel.startswith(f"{item}/") for item in skip):
            continue
        if path.suffix.lower() in CODE_EXTENSIONS:
            files.append(path)
    return files


def detect_nextjs(root: Path, code_files: list[Path]) -> bool:
    next_configs = ["next.config.js", "next.config.mjs", "next.config.ts"]
    if any((root / name).exists() for name in next_configs):
        return True
    pkg = root / "package.json"
    if pkg.is_file() and '"next"' in read_text(pkg):
        return True
    app_dir_markers = [root / "app", root / "src/app"]
    if any(p.is_dir() for p in app_dir_markers):
        return True
    return False


def has_metadata_markers(root: Path, code_files: list[Path]) -> bool:
    candidate_layouts = [
        root / "app/layout.tsx",
        root / "app/layout.jsx",
        root / "src/app/layout.tsx",
        root / "src/app/layout.jsx",
    ]
    patterns = ["export const metadata", "generateMetadata(", "openGraph", "twitter:", "og:"]
    for layout in candidate_layouts:
        if layout.is_file():
            text = read_text(layout)
            if any(p in text for p in patterns):
                return True
    for file in code_files:
        text = read_text(file)
        if any(p in text for p in patterns):
            return True
    return False


def detect_webhook_files(code_files: list[Path]) -> list[Path]:
    out: list[Path] = []
    for file in code_files:
        name = file.name.lower()
        rel = str(file).lower()
        if "webhook" in name or "/webhook" in rel or "webhooks" in rel:
            out.append(file)
    return out


def check_webhook_safety(webhook_files: list[Path]) -> tuple[bool, bool]:
    signature_markers = [
        "stripe-signature",
        "constructEvent",
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
        text = read_text(file).lower()
        if any(m.lower() in text for m in signature_markers):
            has_signature = True
        if any(m.lower() in text for m in idempotency_markers):
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


def command_doctor(root: Path) -> int:
    failures = 0

    print("Doctor checks")
    for rel in REQUIRED_FILES:
        if exists(root, rel):
            print(f"  [ok] {rel}")
        else:
            print(f"  [fail] missing {rel}")
            failures += 1

    auth_checklist = root / "docs/checklists/auth_security.md"
    if auth_checklist.is_file() and re.search(r"password reset", read_text(auth_checklist), re.IGNORECASE):
        print("  [ok] auth includes password reset")
    else:
        print("  [fail] auth checklist missing password reset coverage")
        failures += 1

    billing_checklist = root / "docs/checklists/billing_tax.md"
    billing_text = read_text(billing_checklist).lower()
    if billing_checklist.is_file() and ("webhook" in billing_text and "idempotent" in billing_text):
        print("  [ok] billing includes webhook safety")
    else:
        print("  [fail] billing checklist missing webhook safety")
        failures += 1

    seo_checklist = root / "docs/checklists/seo_distribution.md"
    seo_text = read_text(seo_checklist).lower()
    if seo_checklist.is_file() and ("og thumbnail" in seo_text or "open graph" in seo_text):
        print("  [ok] SEO includes OG thumbnail")
    else:
        print("  [fail] SEO checklist missing OG thumbnail")
        failures += 1

    arch_file = root / "docs/core/architecture.md"
    if arch_file.is_file() and "dev/staging/prod" in read_text(arch_file):
        print("  [ok] architecture includes environment split")
    else:
        print("  [fail] architecture missing dev/staging/prod split")
        failures += 1

    # Codebase checks are only enforced when source files exist.
    code_files = gather_code_files(root)
    if not code_files:
        print("  [skip] codebase checks (no source files detected)")
    else:
        nextjs = detect_nextjs(root, code_files)
        if nextjs:
            if has_metadata_markers(root, code_files):
                print("  [ok] Next.js metadata/OG markers detected")
            else:
                print("  [fail] Next.js detected but metadata/OG markers are missing")
                failures += 1
        else:
            print("  [skip] Next.js metadata check (Next.js not detected)")

        webhook_files = detect_webhook_files(code_files)
        if webhook_files:
            has_sig, has_idem = check_webhook_safety(webhook_files)
            if has_sig:
                print("  [ok] webhook signature verification markers detected")
            else:
                print("  [fail] webhook handlers found but signature verification markers missing")
                failures += 1
            if has_idem:
                print("  [ok] webhook idempotency markers detected")
            else:
                print("  [fail] webhook handlers found but idempotency markers missing")
                failures += 1
        else:
            print("  [skip] webhook safety check (no webhook handlers detected)")

        env_example = root / ".env.example"
        if env_example.is_file():
            print("  [ok] .env.example exists")
        else:
            print("  [fail] missing .env.example for environment documentation")
            failures += 1

        if has_environment_split(root):
            print("  [ok] environment split files detected (dev/staging/prod)")
        else:
            print("  [fail] missing environment split files for dev/staging/prod")
            failures += 1

    if failures > 0:
        print(f"Doctor result: {failures} issue(s) found")
        return 2

    print("Doctor result: clean")
    return 0


def command_gate(stage: str, root: Path) -> int:
    heading = STAGE_HEADINGS[stage]
    checklist = root / "docs/checklists/from_scratch.md"
    if not checklist.is_file():
        print("Missing checklist: docs/checklists/from_scratch.md")
        return 1

    lines = read_text(checklist).splitlines()
    in_section = False
    pending: list[str] = []
    for line in lines:
        if line.strip() == f"## {heading}":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("- [ ]"):
            pending.append(line)

    print(f"Gate report: {stage} ({heading})")
    if pending:
        for line in pending:
            print(f"  {line}")
        print("Gate result: NOT PASS")
        return 3

    print("Gate result: PASS")
    return 0


def main() -> int:
    args = parse_args()
    root = root_path(getattr(args, "root", "."))

    if args.command == "start":
        return command_start(args.mode, root)
    if args.command == "close":
        return command_close(root)
    if args.command == "doctor":
        return command_doctor(root)
    if args.command == "gate":
        return command_gate(args.stage, root)

    return 1
