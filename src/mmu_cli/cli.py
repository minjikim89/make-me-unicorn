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
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
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
    p_init.add_argument("--interactive", action="store_true", help="LLM-guided project setup (requires anthropic SDK)")

    p_start = sub.add_parser("start", help="Start a focused mode session")
    p_start.add_argument("--json", action="store_true", help="Output structured JSON")
    p_start.add_argument("--mode", required=True, choices=sorted(MODES.keys()))
    p_start.add_argument("--root", default=".", help="Project root path")
    p_start.add_argument("--emit", choices=["list", "bundle"], default="list", help="Output format")
    p_start.add_argument("--output", help="Write bundle output to a file")
    p_start.add_argument("--clipboard", action="store_true", help="Copy bundle output to clipboard")
    p_start.add_argument("--agent", action="store_true", help="Format context for LLM agent injection")

    p_close = sub.add_parser("close", help="Close current session")
    p_close.add_argument("--json", action="store_true", help="Output structured JSON")
    p_close.add_argument("--root", default=".", help="Project root path")

    p_doctor = sub.add_parser("doctor", help="Run guardrail checks")
    p_doctor.add_argument("--json", action="store_true", help="Output structured JSON")
    p_doctor.add_argument("--root", default=".", help="Project root path")
    p_doctor.add_argument("--deep", action="store_true", help="LLM-powered semantic analysis (requires anthropic SDK)")

    p_gate = sub.add_parser("gate", help="Check stage gate readiness")
    p_gate.add_argument("--json", action="store_true", help="Output structured JSON")
    p_gate.add_argument("--stage", required=True, help="Stage key (for example: M0, M1, M6)")
    p_gate.add_argument("--root", default=".", help="Project root path")

    p_status = sub.add_parser("status", help="Visual dashboard of launch progress")
    p_status.add_argument("--json", action="store_true", help="Output structured JSON")
    p_status.add_argument("--root", default=".", help="Project root path")
    p_status.add_argument("--why", action="store_true", help="Show score breakdown (applicable/auto/manual/skipped)")

    p_next = sub.add_parser("next", help="Recommend highest-impact items to tackle next")
    p_next.add_argument("--json", action="store_true", help="Output structured JSON")
    p_next.add_argument("--root", default=".", help="Project root path")
    p_next.add_argument("-n", type=int, default=3, help="Number of recommendations (default: 3)")

    p_show = sub.add_parser("show", help="Show detailed blueprint checklist")
    p_show.add_argument("blueprint", help="Blueprint name (e.g. frontend, auth, billing, seo)")
    p_show.add_argument("--json", action="store_true", help="Output structured JSON")
    p_show.add_argument("--root", default=".", help="Project root path")

    p_check = sub.add_parser("check", help="Mark a checklist item as done")
    p_check.add_argument("blueprint", help="Blueprint name (e.g. frontend, auth)")
    p_check.add_argument("item", type=int, help="Item number (shown in `mmu show`)")
    p_check.add_argument("--json", action="store_true", help="Output structured JSON")
    p_check.add_argument("--root", default=".", help="Project root path")

    p_uncheck = sub.add_parser("uncheck", help="Mark a checklist item as not done")
    p_uncheck.add_argument("blueprint", help="Blueprint name (e.g. frontend, auth)")
    p_uncheck.add_argument("item", type=int, help="Item number (shown in `mmu show`)")
    p_uncheck.add_argument("--json", action="store_true", help="Output structured JSON")
    p_uncheck.add_argument("--root", default=".", help="Project root path")

    p_scan = sub.add_parser("scan", help="Auto-detect tech stack and pre-check blueprint items")
    p_scan.add_argument("--json", action="store_true", help="Output structured JSON")
    p_scan.add_argument("--root", default=".", help="Project root path")

    p_generate = sub.add_parser("generate", help="Generate or update a doc using LLM")
    p_generate.add_argument("doc", help="Doc to generate (strategy, product, pricing, architecture, ux)")
    p_generate.add_argument("--json", action="store_true", help="Output structured JSON")
    p_generate.add_argument("--root", default=".", help="Project root path")

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


def _parse_simple_toml(text: str) -> dict[str, Any]:
    """Minimal TOML parser for flat section/key=value configs.

    Only handles ``[section]`` headers and ``key = value`` lines where
    values are booleans, quoted strings, or numbers.  This covers the
    .mmu/config.toml format without requiring tomllib (Python 3.11+).
    """
    data: dict[str, Any] = {}
    section: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1].strip()
            section = {}
            data[name] = section
            continue
        if "=" in line and section is not None:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.split("#", 1)[0].strip()  # strip inline comments
            if val.lower() == "true":
                section[key] = True
            elif val.lower() == "false":
                section[key] = False
            elif val.startswith('"') and val.endswith('"'):
                section[key] = val[1:-1]
            else:
                try:
                    section[key] = int(val)
                except ValueError:
                    section[key] = val
    return data


def load_config(root: Path) -> dict[str, Any]:
    cfg_path = root / ".mmu/config.toml"
    if not cfg_path.is_file():
        return {}
    content = read_text(cfg_path)
    if content is None:
        return {}
    if tomllib is not None:
        try:
            data = tomllib.loads(content)
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}
    # Fallback for Python < 3.11 without tomli
    try:
        return _parse_simple_toml(content)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Feature flags — used by blueprint scanner to skip non-applicable items
# ---------------------------------------------------------------------------

# All flags default to True so that projects without config get the full
# checklist (backward compatible).  Only explicitly set False flags cause
# items to be skipped.

FEATURE_FLAG_DEFAULTS: dict[str, bool] = {
    # [features]
    "has_billing": True,
    "has_email_transactional": True,
    "has_email_marketing": True,
    "has_i18n": True,
    "has_file_upload": True,
    "has_mfa": True,
    "has_push_notifications": True,
    "has_in_app_notifications": True,
    "has_ab_testing": True,
    "has_webhooks_outgoing": True,
    # [architecture]
    "uses_containers": True,
    "uses_iac": True,
    "uses_ssr": True,
    "uses_serverless": True,
    # [market]
    "targets_eu": True,
    "targets_california": True,
    "targets_korea": True,
}


def load_feature_flags(root: Path) -> dict[str, bool]:
    """Load feature flags from .mmu/config.toml, merged with defaults.

    Config format::

        [features]
        billing = false
        i18n = false

        [architecture]
        containerized = false

        [market]
        targets_eu = false

    Short config keys are mapped to canonical flag names (e.g.
    ``billing`` -> ``has_billing``, ``containerized`` -> ``uses_containers``).
    """
    cfg = load_config(root)
    flags = dict(FEATURE_FLAG_DEFAULTS)

    # Mapping from short config key -> canonical flag name
    key_map: dict[str, str] = {
        "billing": "has_billing",
        "email_transactional": "has_email_transactional",
        "email_marketing": "has_email_marketing",
        "i18n": "has_i18n",
        "file_upload": "has_file_upload",
        "mfa": "has_mfa",
        "push_notifications": "has_push_notifications",
        "in_app_notifications": "has_in_app_notifications",
        "ab_testing": "has_ab_testing",
        "webhooks_outgoing": "has_webhooks_outgoing",
        "containerized": "uses_containers",
        "iac": "uses_iac",
        "ssr": "uses_ssr",
        "serverless": "uses_serverless",
        "targets_eu": "targets_eu",
        "targets_california": "targets_california",
        "targets_korea": "targets_korea",
    }

    for section in ("features", "architecture", "market"):
        section_data = cfg.get(section)
        if not isinstance(section_data, dict):
            continue
        for key, value in section_data.items():
            canonical = key_map.get(key)
            if canonical and isinstance(value, bool):
                flags[canonical] = value

    return flags


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


def command_init_interactive(root: Path) -> Result:
    """LLM-guided interactive project initialization."""
    from mmu_cli.llm import LLMClient, generate_core_docs, interactive_questions

    client = LLMClient(root)
    answers = interactive_questions()

    if not answers:
        return Result(exit_code=1, messages=["No answers provided. Aborting interactive setup."])

    # Find examples directory for few-shot prompts
    mmu_root = _find_mmu_root()
    examples_dir = (mmu_root / "examples" / "filled" / "tasknote" / "docs" / "core") if mmu_root else Path()

    output_dir = root / "docs" / "core"
    generated = generate_core_docs(client, answers, examples_dir, output_dir)

    # Run normal init for remaining files (blueprints, checklists, etc.)
    init_result = command_init(root, force=False)

    messages = ["\n  🦄 Interactive setup complete!\n"]
    messages.append("  LLM-generated docs:")
    for g in generated:
        messages.append(f"    [create] {g}")
    messages.append("")
    messages.extend(init_result.get("messages", []))

    client.log_usage(root)

    return Result(
        exit_code=0,
        generated=generated,
        created=init_result.get("created", []),
        messages=messages,
    )


def command_doctor_deep(root: Path) -> Result:
    """LLM-powered semantic code analysis on top of regular doctor."""
    from mmu_cli.llm import LLMClient

    base_result = command_doctor(root)
    client = LLMClient(root)

    # Collect docs for analysis
    docs_content: dict[str, str] = {}
    for name in ["strategy.md", "product.md", "architecture.md", "pricing.md"]:
        path = root / f"docs/core/{name}"
        content = read_text(path)
        if content and content.strip():
            docs_content[name] = content

    # Collect code files (limited)
    skip_paths = doctor_skip_paths(root)
    code_files = gather_code_files(root, skip_paths)[:15]
    code_content: dict[str, str] = {}
    for f in code_files:
        content = read_text(f)
        if content and len(content) < 8000:
            code_content[f.relative_to(root).as_posix()] = content

    if not docs_content and not code_content:
        messages = base_result.get("messages", [])
        messages.append("\n  [skip] Deep analysis: no docs or code to analyze")
        return Result(exit_code=base_result.exit_code, messages=messages)

    system = (
        "You are a SaaS code reviewer. Analyze the project documentation and source code. "
        "Report concisely:\n"
        "1. Doc-code mismatches (docs say one thing, code does another)\n"
        "2. Missing error handling or security concerns\n"
        "3. Incomplete implementations (stubs, TODOs)\n"
        "4. Blind spots the founder might miss\n"
        "Be specific with file references. Format as a concise checklist."
    )

    user_parts: list[str] = []
    if docs_content:
        user_parts.append("## Documentation\n")
        for name, content in docs_content.items():
            user_parts.append(f"### {name}\n{content}\n")
    if code_content:
        user_parts.append("## Code\n")
        for name, content in code_content.items():
            user_parts.append(f"### {name}\n```\n{content}\n```\n")

    analysis = client.complete(system, "\n".join(user_parts), max_tokens=2000)
    client.log_usage(root)

    messages = base_result.get("messages", [])
    messages.append("")
    messages.append("  === Deep Analysis (Claude) ===")
    messages.append(analysis)

    return Result(exit_code=base_result.exit_code, messages=messages)


def command_generate(doc_name: str, root: Path) -> Result:
    """Generate or update a core doc using LLM."""
    from mmu_cli.llm import LLMClient

    valid_docs = {"strategy", "product", "pricing", "architecture", "ux"}
    if doc_name not in valid_docs:
        return Result(exit_code=1, messages=[f"Unknown doc: {doc_name}. Choose from: {', '.join(sorted(valid_docs))}"])

    filename = f"{doc_name}.md"
    target = root / "docs" / "core" / filename
    existing = read_text(target) if target.is_file() else None

    # Gather project context
    context_parts: list[str] = []
    for name in ["strategy.md", "product.md", "architecture.md"]:
        path = root / f"docs/core/{name}"
        content = read_text(path)
        if content and content.strip() and name != filename:
            context_parts.append(f"### {name}\n{content}")

    sprint = read_text(root / "current_sprint.md")
    if sprint:
        context_parts.append(f"### current_sprint.md\n{sprint}")

    # Load example
    mmu_root = _find_mmu_root()
    example = ""
    if mmu_root:
        example_path = mmu_root / "examples" / "filled" / "tasknote" / "docs" / "core" / filename
        if example_path.is_file():
            example = example_path.read_text(encoding="utf-8")

    client = LLMClient(root)

    system = (
        "You are a SaaS strategy assistant. Generate or update the requested document "
        "based on the project's current state. Follow the reference format exactly. "
        "Be specific and actionable. Output ONLY the markdown content."
    )
    user_prompt = f"Generate docs/core/{filename}.\n\n"
    if existing and existing.strip():
        user_prompt += f"Current content (update and improve):\n{existing}\n\n"
    if context_parts:
        user_prompt += f"Project context:\n\n{''.join(context_parts)}\n\n"
    if example:
        user_prompt += f"Reference format:\n{example}\n"

    print(f"\n  Generating docs/core/{filename}...")
    content = client.complete(system, user_prompt)
    write_text(target, content)
    client.log_usage(root)

    return Result(exit_code=0, messages=[f"  [create] docs/core/{filename} generated"])


def command_start(mode: str, root: Path, emit: str, output: str | None, clipboard: bool, agent: bool = False) -> Result:
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
    if emit == "bundle" or output or clipboard or agent:
        bundle, bundle_missing = build_bundle(root, mode_files, read_errors)
        for rel in bundle_missing:
            if rel not in missing:
                missing.append(rel)

    # --agent: format context for LLM injection
    if agent:
        from mmu_cli.llm import format_agent_context

        agent_ctx = format_agent_context(mode, bundle, root)
        if clipboard:
            ok, note = try_copy_clipboard(agent_ctx)
            messages.append(("  [ok] " if ok else "  [warn] ") + note)
        if output:
            out_path = (root / output).resolve() if not Path(output).is_absolute() else Path(output)
            write_text(out_path, agent_ctx)
            messages.append(f"Agent context written: {out_path}")
        messages.append("--- AGENT CONTEXT ---")
        messages.append(agent_ctx)
        messages.append("--- END ---")

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


def _generate_stack_config(root: Path) -> str:
    """Generate a .mmu/config.toml with feature flags.

    Auto-detects what it can from the project, defaults the rest to true
    so that users can opt-out of sections that don't apply.
    """
    # Basic auto-detection
    has_docker = (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists()
    has_package_json = (root / "package.json").exists()

    # Try to detect billing/email from package.json or requirements
    billing_hint = False
    email_hint = False
    i18n_hint = False
    if has_package_json:
        try:
            pkg = (root / "package.json").read_text(encoding="utf-8").lower()
            billing_hint = any(k in pkg for k in ("stripe", "lemonsqueezy", "paddle", "@paypal"))
            email_hint = any(k in pkg for k in ("resend", "postmark", "sendgrid", "nodemailer", "@react-email"))
            i18n_hint = any(k in pkg for k in ("next-intl", "i18next", "react-i18next", "next-i18n"))
        except OSError:
            pass

    req_path = root / "requirements.txt"
    if req_path.exists():
        try:
            reqs = req_path.read_text(encoding="utf-8").lower()
            billing_hint = billing_hint or any(k in reqs for k in ("stripe", "paddle"))
            email_hint = email_hint or any(k in reqs for k in ("resend", "sendgrid", "postmark"))
        except OSError:
            pass

    lines = [
        "# MMU Feature Config — controls which checklist sections apply to your project.",
        "# Set to false to skip sections that don't apply. This makes your score accurate.",
        "# Regenerate with: mmu init --force",
        "",
        "[features]",
        f"billing = true{_hint(billing_hint, 'detected')}",
        "email_transactional = true",
        f"email_marketing = true{_hint(email_hint, 'email detected')}",
        "i18n = true" if i18n_hint else "i18n = false  # set true if your app supports multiple languages",
        "file_upload = true",
        "mfa = false  # set true if your app has multi-factor auth",
        "push_notifications = false  # set true if your app sends push notifications",
        "in_app_notifications = false  # set true if your app has a notification bell/inbox",
        "ab_testing = false  # set true if you plan to run A/B tests",
        "webhooks_outgoing = false  # set true if your app dispatches webhooks to external services",
        "",
        "[architecture]",
        f"containerized = {'true' if has_docker else 'false'}  # Dockerfile detected" if has_docker else "containerized = false  # set true if using Docker",
        "iac = false  # set true if using Terraform/Pulumi/SST",
        "ssr = true",
        "serverless = false  # set true if using Lambda/Cloudflare Workers",
        "",
        "[market]",
        "targets_eu = false  # set true if you serve EU users (enables GDPR section)",
        "targets_california = false  # set true if you serve CA users (enables CCPA section)",
        "targets_korea = false  # set true if you target Korean market (enables Naver registration)",
        "",
    ]
    return "\n".join(lines) + "\n"


def _hint(detected: bool, label: str) -> str:
    return f"  # {label}" if detected else ""


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

    # Generate feature config if it doesn't exist (or force)
    config_path = root / ".mmu" / "config.toml"
    if not config_path.exists() or force:
        config_content = _generate_stack_config(root)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content, encoding="utf-8")
        rel = ".mmu/config.toml"
        if config_path.exists() and not force:
            pass  # already counted
        else:
            created.append(rel)
            messages.append(f"  [create] {rel}")

    if created or overwritten:
        messages.append("Init result: workspace scaffold ready")
        messages.append("")
        messages.append("Next steps:")
        messages.append("  1. mmu status          — see your launch dashboard")
        messages.append("  2. mmu doctor          — check what's missing")
        messages.append("  3. Edit .mmu/config.toml — customize your stack profile")
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


def command_show(blueprint_name: str, root: Path) -> Result:
    from mmu_cli.display import (
        BLUEPRINT_NAMES,
        render_blueprint_detail,
        resolve_blueprint,
    )

    filename = resolve_blueprint(blueprint_name)
    if not filename:
        available = ", ".join(
            label.lower() for label in BLUEPRINT_NAMES.values()
        )
        return Result(
            exit_code=1,
            messages=[
                f"Unknown blueprint: {blueprint_name}",
                f"Available: {available}",
            ],
        )

    label = BLUEPRINT_NAMES[filename]
    bp_path = root / "docs" / "blueprints" / filename
    if not bp_path.is_file():
        return Result(
            exit_code=1,
            messages=[
                f"Blueprint file not found: {bp_path}",
                "Run `mmu init` first to create blueprint files.",
            ],
        )

    flags = load_feature_flags(root)
    detail = render_blueprint_detail(bp_path, label, flags)
    return Result(exit_code=0, blueprint=filename, messages=[detail])


def command_check(blueprint_name: str, item_num: int, root: Path, *, force_state: str | None = None) -> Result:
    """Check/uncheck a blueprint item.

    force_state: "check" = always mark [x], "uncheck" = always mark [ ], None = toggle.
    """
    from mmu_cli.display import BLUEPRINT_NAMES, resolve_blueprint

    filename = resolve_blueprint(blueprint_name)
    if not filename:
        return Result(exit_code=1, messages=[f"Unknown blueprint: {blueprint_name}"])

    label = BLUEPRINT_NAMES[filename]
    bp_path = root / "docs" / "blueprints" / filename
    if not bp_path.is_file():
        return Result(exit_code=1, messages=[f"Blueprint file not found: {bp_path}"])

    text = read_text(bp_path)
    if text is None:
        return Result(exit_code=1, messages=[f"Cannot read {bp_path}"])

    # Find all checklist items and their line indices
    lines = text.splitlines()
    check_done = re.compile(r"^(\s*-\s*)\[x\](\s+.+)$", re.IGNORECASE)
    check_todo = re.compile(r"^(\s*-\s*)\[\s\](\s+.+)$")
    items: list[tuple[int, bool, str]] = []  # (line_idx, is_done, item_text)

    for i, line in enumerate(lines):
        dm = check_done.match(line)
        if dm:
            items.append((i, True, dm.group(2).strip()))
            continue
        tm = check_todo.match(line)
        if tm:
            items.append((i, False, tm.group(2).strip()))

    if item_num < 1 or item_num > len(items):
        return Result(
            exit_code=1,
            messages=[f"Item #{item_num} out of range (1-{len(items)}). Use `mmu show {blueprint_name}` to see items."],
        )

    idx, was_done, item_text = items[item_num - 1]
    line = lines[idx]

    # Determine action
    if force_state == "check":
        if was_done:
            from mmu_cli.display import dim
            return Result(exit_code=0, action="already_checked", item=item_text,
                          messages=[f"  {dim('already ✓')} {label} #{item_num}: {item_text}"])
        lines[idx] = re.sub(r"\[\s\]", "[x]", line, count=1)
        action = "checked"
    elif force_state == "uncheck":
        if not was_done:
            from mmu_cli.display import dim
            return Result(exit_code=0, action="already_unchecked", item=item_text,
                          messages=[f"  {dim('already ✗')} {label} #{item_num}: {item_text}"])
        lines[idx] = re.sub(r"\[x\]", "[ ]", line, count=1, flags=re.IGNORECASE)
        action = "unchecked"
    else:
        # Toggle
        if was_done:
            lines[idx] = re.sub(r"\[x\]", "[ ]", line, count=1, flags=re.IGNORECASE)
            action = "unchecked"
        else:
            lines[idx] = re.sub(r"\[\s\]", "[x]", line, count=1)
            action = "checked"

    write_text(bp_path, "\n".join(lines) + "\n" if text.endswith("\n") else "\n".join(lines))

    from mmu_cli.display import green, red, bold

    if action == "checked":
        msg = f"  {green('✓')} {bold(label)} #{item_num}: {item_text}"
    else:
        msg = f"  {red('✗')} {bold(label)} #{item_num}: {item_text} (unchecked)"

    return Result(exit_code=0, action=action, item=item_text, messages=[msg])


def command_scan(root: Path) -> Result:
    from mmu_cli.display import (
        BLUEPRINT_NAMES,
        bold,
        cyan,
        dim,
        green,
        magenta,
        mini_bar,
        progress_bar,
        scan_all_blueprints,
        yellow,
    )
    from mmu_cli.scan import run_scan

    flags = load_feature_flags(root)
    result = run_scan(root, flags)
    tech = result["tech_stack"]
    checked = result["checked_count"]
    total_new = result["total_newly_checked"]

    lines: list[str] = []
    lines.append("")
    lines.append(bold("  🔍  CODEBASE SCAN RESULTS"))
    lines.append(dim("  ─" * 28))
    lines.append("")

    # Detected tech stack
    lines.append(bold("  Detected Stack:"))
    for category, items in tech.items():
        items_str = ", ".join(bold(i) for i in items)
        lines.append(f"    {cyan(category + ':')}  {items_str}")
    lines.append("")

    if not tech:
        lines.append(f"    {yellow('No technologies detected.')}")
        lines.append("    Make sure package.json or requirements.txt exists.")
        lines.append("")

    # Blueprint updates
    lines.append(dim("  ─" * 28))
    if checked:
        lines.append(bold(f"  📝  Auto-checked {total_new} items across {len(checked)} blueprints:"))
        lines.append("")
        for bp_file, count in sorted(checked.items()):
            label = BLUEPRINT_NAMES.get(bp_file, bp_file)
            lines.append(f"    {green('+')} {label}: {bold(str(count))} items newly checked")
    else:
        lines.append(f"  {dim('No new items to auto-check (already up to date or no blueprints found).')}")

    # Show updated totals (reuse flags loaded above)
    blueprints = scan_all_blueprints(root, flags)
    if blueprints:
        bp_done = sum(d for _, d, _, _ in blueprints)
        bp_total = sum(t for _, _, t, _ in blueprints)
        bp_skipped = sum(s for _, _, _, s in blueprints)
        lines.append("")
        lines.append(dim("  ─" * 28))
        skip_note = dim(f"  [{bp_skipped} skipped]") if bp_skipped > 0 else ""
        lines.append(f"  {bold('Updated totals:')}  {progress_bar(bp_done, bp_total)}{skip_note}")
        lines.append("")
        for label, d, t, _s in blueprints:
            lines.append(f"    {label:<18} {mini_bar(d, t)}")
        lines.append("")

    lines.append(dim("  ─" * 28))
    if total_new > 0:
        lines.append(f"  {magenta('✨')} Scan complete! {bold(str(total_new))} items auto-checked")
        lines.append(f"  {dim('Review with:')} {cyan('mmu show <blueprint>')} {dim('— edit with:')} {cyan('mmu check/uncheck <blueprint> <#>')}")
    else:
        lines.append(f"  💡 Run {cyan('mmu init')} first if blueprints don't exist yet")
    lines.append("")

    dashboard = "\n".join(lines)
    return Result(
        exit_code=0,
        tech_stack=tech,
        newly_checked=total_new,
        checked_by_blueprint=checked,
        messages=[dashboard],
    )


def command_status(root: Path, why: bool = False) -> Result:
    from mmu_cli.display import render_status, render_score_breakdown, scan_all_blueprints, scan_gates

    flags = load_feature_flags(root)
    dashboard = render_status(root, flags)

    if why:
        breakdown = render_score_breakdown(root, flags)
        dashboard = dashboard + "\n" + breakdown

    blueprints = scan_all_blueprints(root, flags)
    gates = scan_gates(root)
    bp_done = sum(d for _, d, _, _ in blueprints)
    bp_total = sum(t for _, _, t, _ in blueprints)
    bp_skipped = sum(s for _, _, _, s in blueprints)
    gate_done = sum(d for _, d, _ in gates)
    gate_total = sum(t for _, _, t in gates)

    return Result(
        exit_code=0,
        dashboard=dashboard,
        blueprint_progress={"done": bp_done, "total": bp_total, "skipped": bp_skipped},
        gate_progress={"done": gate_done, "total": gate_total},
        messages=[dashboard],
    )


def command_next(root: Path, count: int = 3) -> Result:
    from mmu_cli.display import render_next_actions

    flags = load_feature_flags(root)
    output = render_next_actions(root, flags, count)

    return Result(
        exit_code=0,
        messages=[output],
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
        if getattr(args, "interactive", False):
            result = command_init_interactive(root)
        else:
            result = command_init(root, args.force)
        return render_result(result, args.json)
    if args.command == "start":
        result = command_start(args.mode, root, args.emit, args.output, args.clipboard, agent=getattr(args, "agent", False))
        return render_result(result, args.json)
    if args.command == "close":
        result = command_close(root)
        return render_result(result, args.json)
    if args.command == "doctor":
        if getattr(args, "deep", False):
            result = command_doctor_deep(root)
        else:
            result = command_doctor(root)
        return render_result(result, args.json)
    if args.command == "generate":
        result = command_generate(args.doc, root)
        return render_result(result, args.json)
    if args.command == "gate":
        result = command_gate(args.stage, root)
        return render_result(result, args.json)
    if args.command == "status":
        result = command_status(root, why=getattr(args, "why", False))
        return render_result(result, args.json)
    if args.command == "next":
        result = command_next(root, count=getattr(args, "n", 3))
        return render_result(result, args.json)
    if args.command == "show":
        result = command_show(args.blueprint, root)
        return render_result(result, args.json)
    if args.command == "check":
        result = command_check(args.blueprint, args.item, root, force_state="check")
        return render_result(result, args.json)
    if args.command == "uncheck":
        result = command_check(args.blueprint, args.item, root, force_state="uncheck")
        return render_result(result, args.json)
    if args.command == "scan":
        result = command_scan(root)
        return render_result(result, args.json)
    if args.command == "snapshot":
        result = command_snapshot(root, args.target, args.output, args.no_md)
        return render_result(result, args.json)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
