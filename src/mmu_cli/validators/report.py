"""Format validation results for terminal + markdown output."""

from __future__ import annotations

import hashlib
import re
from typing import Any

# Verdict cutoffs on the mean VADER compound score. VADER's own convention
# treats |compound| >= 0.05 as non-neutral for a single sentence; we average
# over whole threads, so we require a stronger ±0.2 lean before calling a
# direction. Anything in between reads as MIXED rather than a false signal.
VERDICT_THRESHOLD = 0.2


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "idea"


def report_filename(idea: str) -> str:
    """Stable per-idea filename: slug + short content hash.

    The hash suffix keeps repeat runs of the *same* idea writing to the same
    file, while ideas that collide after slug truncation ("AI tutor for kids
    in California" vs "... in Texas") get distinct reports.
    """
    digest = hashlib.sha256(idea.encode("utf-8")).hexdigest()[:8]
    return f"{slugify(idea)}-{digest}.md"


def verdict(compound: float, count: int) -> str:
    """Map a mean compound score to a verdict label (see VERDICT_THRESHOLD)."""
    if count == 0:
        return "NO SIGNAL"
    if compound >= VERDICT_THRESHOLD:
        return "POSITIVE LEAN"
    if compound <= -VERDICT_THRESHOLD:
        return "NEGATIVE LEAN"
    return "MIXED"


# Backward-compat alias for the pre-0.7 private name.
_verdict = verdict


def format_text(
    idea: str,
    hits: list[dict[str, Any]],
    sentiment: dict[str, float],
    competitors: list[tuple[str, int]],
    llm_report: str | None = None,
) -> str:
    lines: list[str] = []
    lines.append(f"MMU Validate — {idea}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Threads found: {len(hits)} (HN + Reddit)")
    lines.append(
        f"Sentiment: {_verdict(sentiment.get('compound', 0.0), int(sentiment.get('count', 0)))}  "
        f"(compound={sentiment.get('compound', 0.0):+.2f}, n={int(sentiment.get('count', 0))})"
    )
    lines.append("")
    if competitors:
        lines.append("Competitors / named entities (top mentions):")
        for name, count in competitors:
            lines.append(f"  - {name} ({count})")
        lines.append("")
    if hits:
        lines.append("Top threads:")
        for hit in hits[:10]:
            src = hit.get("source", "?").upper()
            title = hit.get("title", "")[:90]
            url = hit.get("url", "")
            lines.append(f"  [{src}] {title}")
            if url:
                lines.append(f"        {url}")
        lines.append("")
    if llm_report:
        lines.append("LLM Synthesis")
        lines.append("-" * 60)
        lines.append(llm_report.strip())
        lines.append("")
    return "\n".join(lines)


def format_markdown(
    idea: str,
    hits: list[dict[str, Any]],
    sentiment: dict[str, float],
    competitors: list[tuple[str, int]],
    llm_report: str | None = None,
) -> str:
    lines: list[str] = []
    lines.append(f"# Validation Report: {idea}")
    lines.append("")
    lines.append(
        f"- **Threads**: {len(hits)}  "
        f"- **Sentiment**: {_verdict(sentiment.get('compound', 0.0), int(sentiment.get('count', 0)))} "
        f"(compound `{sentiment.get('compound', 0.0):+.2f}`, n={int(sentiment.get('count', 0))})"
    )
    lines.append("")
    if competitors:
        lines.append("## Competitors / named entities")
        lines.append("")
        for name, count in competitors:
            lines.append(f"- {name} ({count})")
        lines.append("")
    if hits:
        lines.append("## Top threads")
        lines.append("")
        for hit in hits[:20]:
            src = hit.get("source", "?").upper()
            title = hit.get("title", "")
            url = hit.get("url", "")
            lines.append(f"- **[{src}]** [{title}]({url})")
        lines.append("")
    if llm_report:
        lines.append("## LLM Synthesis")
        lines.append("")
        lines.append(llm_report.strip())
        lines.append("")
    return "\n".join(lines)
