"""Free local NLP for the default validate mode.

Sentiment via VADER. Competitor extraction via a naive capitalized-token
heuristic — good enough for v1; LLM mode produces the polished version.
"""

from __future__ import annotations

import re
from collections import Counter

_STOPWORDS = {
    "I", "Im", "The", "This", "That", "It", "We", "You", "They", "He", "She",
    "There", "What", "Why", "How", "When", "Where", "Which", "Who", "If",
    "But", "And", "Or", "Not", "Now", "Here", "Then", "Also", "So", "Yet",
    "Would", "Could", "Should", "Will", "Can", "May", "Might", "Must",
    "Even", "While", "Since", "Before", "After", "Because", "Although",
    "Show", "Ask", "OP", "TL", "DR", "FYI", "OK",
    "HN", "AI", "API", "URL", "USA", "EU", "UK", "SaaS", "Reddit",
}

_CAP_TOKEN = re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)\b")


def analyze_sentiment(texts: list[str]) -> dict[str, float]:
    """Return aggregate VADER scores: pos, neg, neu, compound (mean)."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    except ImportError as exc:
        raise ImportError(
            "Sentiment analysis requires the [validate] extra. "
            "Install with `pip install make-me-unicorn[validate]`."
        ) from exc

    analyzer = SentimentIntensityAnalyzer()
    scores = [analyzer.polarity_scores(t) for t in texts if t]
    if not scores:
        return {"pos": 0.0, "neg": 0.0, "neu": 0.0, "compound": 0.0, "count": 0}
    return {
        "pos": sum(s["pos"] for s in scores) / len(scores),
        "neg": sum(s["neg"] for s in scores) / len(scores),
        "neu": sum(s["neu"] for s in scores) / len(scores),
        "compound": sum(s["compound"] for s in scores) / len(scores),
        "count": len(scores),
    }


def extract_competitors(texts: list[str], top_n: int = 10) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for text in texts:
        if not text:
            continue
        for match in _CAP_TOKEN.findall(text):
            if match in _STOPWORDS:
                continue
            if len(match) < 3:
                continue
            counter[match] += 1
    return counter.most_common(top_n)
