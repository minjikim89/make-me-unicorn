"""LLM integration for MMU CLI — optional, requires ``pip install make-me-unicorn[llm]``."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Lazy import gate
# ---------------------------------------------------------------------------

_HAS_ANTHROPIC = False
try:
    import anthropic  # type: ignore[import-untyped]

    _HAS_ANTHROPIC = True
except ImportError:
    anthropic = None  # type: ignore[assignment]


def require_llm() -> None:
    """Raise a clear error if LLM dependencies are missing."""
    if not _HAS_ANTHROPIC:
        print(
            "\n  LLM features require the anthropic SDK.\n"
            "  Install with:  pip install make-me-unicorn[llm]\n",
            file=sys.stderr,
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------

def get_api_key(root: Path | None = None) -> str:
    """Resolve API key: env var → .mmu/config.toml → error."""
    key = os.environ.get("MMU_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    # Try config file
    if root:
        cfg_path = root / ".mmu" / "config.toml"
        if cfg_path.is_file():
            try:
                import tomllib

                data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
                llm_cfg = data.get("llm", {})
                if isinstance(llm_cfg, dict) and llm_cfg.get("api_key"):
                    return str(llm_cfg["api_key"])
            except Exception:
                pass

    print(
        "\n  No API key found.\n"
        "  Set MMU_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY environment variable,\n"
        "  or add [llm] api_key to .mmu/config.toml\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "claude-sonnet-4-20250514"


class LLMClient:
    """Thin wrapper around Anthropic API for MMU use cases."""

    def __init__(self, root: Path | None = None) -> None:
        require_llm()
        api_key = get_api_key(root)
        self.client = anthropic.Anthropic(api_key=api_key)  # type: ignore[union-attr]
        self.model = os.environ.get("MMU_MODEL", _DEFAULT_MODEL)
        self.usage_log: list[dict[str, Any]] = []

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Send a completion request and return the text response."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=temperature,
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "model": self.model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.usage_log.append(usage)
        return response.content[0].text

    def log_usage(self, root: Path) -> None:
        """Append usage stats to .mmu/llm_usage.log."""
        if not self.usage_log:
            return
        log_path = root / ".mmu" / "llm_usage.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            for entry in self.usage_log:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.usage_log.clear()


# ---------------------------------------------------------------------------
# Document generation helpers
# ---------------------------------------------------------------------------

_CORE_DOCS = ["strategy.md", "product.md", "pricing.md", "architecture.md", "ux.md"]

_SYSTEM_PROMPT = (
    "You are a SaaS strategy assistant helping a solo founder set up their project. "
    "Generate filled project documentation based on the founder's answers. "
    "Follow the exact structure and style of the reference example. "
    "Be specific and actionable — avoid generic placeholders. "
    "Output ONLY the markdown content, no surrounding explanation."
)

_QUESTIONS = [
    ("Product", "What is your product? (one sentence)"),
    ("Customer", "Who is your ideal customer?"),
    ("Problem", "What problem does it solve?"),
    ("Stack", "What tech stack are you using? (e.g., Next.js + Supabase)"),
    ("Revenue", "What is your monetization plan? (free, freemium, paid-only)"),
]


def interactive_questions() -> dict[str, str]:
    """Ask the founder 5 setup questions via stdin."""
    answers: dict[str, str] = {}
    print("\n  🦄 MMU Interactive Setup\n")
    for key, question in _QUESTIONS:
        print(f"  {question}")
        answer = input("  > ").strip()
        if answer:
            answers[key] = answer
    return answers


def generate_core_docs(
    client: LLMClient,
    answers: dict[str, str],
    examples_dir: Path,
    output_dir: Path,
) -> list[str]:
    """Generate core docs using LLM with few-shot examples. Returns list of generated files."""
    context = "\n".join(f"{k}: {v}" for k, v in answers.items())
    generated: list[str] = []

    for doc_name in _CORE_DOCS:
        example_path = examples_dir / doc_name
        example = ""
        if example_path.is_file():
            example = example_path.read_text(encoding="utf-8")

        user_prompt = (
            f"Generate docs/core/{doc_name} for this project:\n\n"
            f"{context}\n\n"
        )
        if example:
            user_prompt += f"Follow this format exactly:\n\n{example}\n"

        print(f"  Generating docs/core/{doc_name}...")
        content = client.complete(_SYSTEM_PROMPT, user_prompt)

        out_path = output_dir / doc_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        generated.append(f"docs/core/{doc_name}")

    return generated


def format_agent_context(mode: str, bundle: str, root: Path) -> str:
    """Format context for direct LLM injection (--agent flag)."""
    sections: list[str] = []
    sections.append(f"# MMU Session Context — Mode: {mode}\n")

    # Start prompt
    start_path = root / "prompts" / "start.md"
    if start_path.is_file():
        sections.append(f"## Session Protocol\n\n{start_path.read_text(encoding='utf-8')}\n")

    # Sprint
    sprint_path = root / "current_sprint.md"
    if sprint_path.is_file():
        sections.append(f"## Current Sprint\n\n{sprint_path.read_text(encoding='utf-8')}\n")

    # Known issues
    issues_path = root / "docs" / "ops" / "known_issues.md"
    if issues_path.is_file():
        sections.append(f"## Known Issues\n\n{issues_path.read_text(encoding='utf-8')}\n")

    # Context bundle
    if bundle:
        sections.append(f"## Context Documents\n\n{bundle}\n")

    return "\n---\n\n".join(sections)
