"""Idea validation toolkit for MMU.

Default mode (free): scrape Reddit + HN, run free NLP locally.
`--llm` opt-in: synthesize a 1-page validation report via Anthropic API.
"""

from typing import Any

from mmu_cli.validators.hn import search_hn
from mmu_cli.validators.nlp import analyze_sentiment, extract_competitors
from mmu_cli.validators.reddit import search_reddit
from mmu_cli.validators.report import format_markdown, format_text, report_filename, slugify

__all__ = [
    "analyze_sentiment",
    "extract_competitors",
    "fetch_threads",
    "format_markdown",
    "format_text",
    "report_filename",
    "search_hn",
    "search_reddit",
    "slugify",
]


def fetch_threads(idea: str, limit: int = 30) -> tuple[list[dict[str, Any]], list[str]]:
    """Search HN + Reddit in parallel; return (hits, per-source error strings).

    Shared by `mmu validate` and the MCP `mmu_validate_idea` tool. Hits keep
    HN-before-Reddit ordering regardless of which fetch finishes first.
    """
    if limit <= 0:
        return [], []
    from concurrent.futures import ThreadPoolExecutor

    hits: list[dict[str, Any]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [("HN", pool.submit(search_hn, idea, limit=limit)),
                   ("Reddit", pool.submit(search_reddit, idea, limit=limit))]
        for source, future in futures:
            try:
                hits.extend(future.result())
            except Exception as exc:
                errors.append(f"{source} fetch failed: {type(exc).__name__}: {exc}")
    return hits, errors
