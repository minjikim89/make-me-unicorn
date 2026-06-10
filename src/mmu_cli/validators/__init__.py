"""Idea validation toolkit for MMU.

Default mode (free): scrape Reddit + HN, run free NLP locally.
`--llm` opt-in: synthesize a 1-page validation report via Anthropic API.
"""

from mmu_cli.validators.hn import search_hn
from mmu_cli.validators.nlp import analyze_sentiment, extract_competitors
from mmu_cli.validators.reddit import search_reddit
from mmu_cli.validators.report import format_markdown, format_text, report_filename, slugify

__all__ = [
    "analyze_sentiment",
    "extract_competitors",
    "format_markdown",
    "format_text",
    "report_filename",
    "search_hn",
    "search_reddit",
    "slugify",
]
