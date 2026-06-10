"""Reddit search via the public JSON endpoint (no auth)."""

from __future__ import annotations

from typing import Any

REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"
USER_AGENT = "make-me-unicorn-validator/0.7 (+https://github.com/minjikim89/make-me-unicorn)"


def parse_listing(payload: dict[str, Any]) -> list[dict[str, Any]]:
    children = payload.get("data", {}).get("children", [])
    threads: list[dict[str, Any]] = []
    for child in children:
        data = child.get("data", {})
        threads.append(
            {
                "source": "reddit",
                "title": (data.get("title") or "").strip(),
                "url": "https://www.reddit.com" + data.get("permalink", ""),
                "text": data.get("selftext") or "",
                "subreddit": data.get("subreddit"),
                "score": data.get("score") or 0,
                "comments": data.get("num_comments") or 0,
                "created_at": data.get("created_utc"),
            }
        )
    return threads


def search_reddit(query: str, limit: int = 30) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    import requests  # type: ignore[import-untyped]

    response = requests.get(
        REDDIT_SEARCH_URL,
        params={"q": query, "limit": min(limit, 100), "sort": "relevance", "t": "year"},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()
    return parse_listing(response.json())[:limit]
