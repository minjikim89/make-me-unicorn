"""LLM synthesis for `mmu validate --llm`.

Imported only when --llm is passed, so the default validate flow never
triggers Anthropic SDK loading.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SYSTEM_PROMPT = """You are an experienced startup advisor reviewing real online discussions about a startup idea. Produce a concise validation report (max 400 words) with:

1. Verdict: STRONG / MIXED / WEAK / RED FLAG
2. Key pain points the discussions actually surface (3-5 bullets)
3. Existing solutions / competitors mentioned
4. Risks or red flags
5. Suggested next 1-2 validation experiments

Be honest. If signal is thin, say so. Do not invent data."""


def synthesize_report(idea: str, hits: list[dict[str, Any]], root: Path | None = None) -> str:
    from mmu_cli.llm import LLMClient

    client = LLMClient(root)
    snippets = []
    for hit in hits[:40]:
        title = hit.get("title", "")[:200]
        text = (hit.get("text") or "")[:400]
        source = hit.get("source", "?")
        snippets.append(f"[{source}] {title}\n{text}".strip())

    user_prompt = (
        f"Startup idea: {idea}\n\n"
        f"Real discussions ({len(snippets)} threads):\n\n"
        + "\n\n---\n\n".join(snippets)
    )

    return client.complete(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=1500, temperature=0.4)
