"""HN search via the public Algolia API (no auth)."""

from __future__ import annotations

from typing import Any

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
USER_AGENT = "make-me-unicorn-validator/0.6"


def parse_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for raw in payload.get("hits", []):
        title = raw.get("title") or raw.get("story_title") or ""
        url = raw.get("url") or (
            f"https://news.ycombinator.com/item?id={raw['objectID']}" if raw.get("objectID") else ""
        )
        text = raw.get("comment_text") or raw.get("story_text") or ""
        hits.append(
            {
                "source": "hn",
                "title": title.strip(),
                "url": url,
                "text": text,
                "points": raw.get("points") or 0,
                "comments": raw.get("num_comments") or 0,
                "created_at": raw.get("created_at"),
            }
        )
    return hits


def search_hn(query: str, limit: int = 30) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    import requests  # type: ignore[import-untyped]

    response = requests.get(
        ALGOLIA_URL,
        params={"query": query, "tags": "story", "hitsPerPage": min(limit, 100)},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()
    return parse_hits(response.json())[:limit]
