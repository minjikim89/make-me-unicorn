import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli.validators import hn  # noqa: E402


SAMPLE_PAYLOAD = {
    "hits": [
        {
            "objectID": "12345",
            "title": "Show HN: a startup idea validator",
            "url": "https://example.com/post",
            "points": 42,
            "num_comments": 10,
            "story_text": "I built this because…",
            "created_at": "2026-04-01T00:00:00Z",
        },
        {
            "objectID": "67890",
            "story_title": "Ask HN: how do you validate ideas?",
            "url": None,
            "points": 7,
            "num_comments": 3,
            "comment_text": "Great question",
        },
    ]
}


class HNParseTests(unittest.TestCase):
    def test_parse_hits_extracts_titles_and_urls(self):
        hits = hn.parse_hits(SAMPLE_PAYLOAD)
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0]["title"], "Show HN: a startup idea validator")
        self.assertEqual(hits[0]["url"], "https://example.com/post")
        self.assertEqual(hits[0]["source"], "hn")
        self.assertEqual(hits[0]["points"], 42)

    def test_parse_hits_falls_back_to_story_title_and_hn_url(self):
        hits = hn.parse_hits(SAMPLE_PAYLOAD)
        self.assertEqual(hits[1]["title"], "Ask HN: how do you validate ideas?")
        self.assertEqual(hits[1]["url"], "https://news.ycombinator.com/item?id=67890")

    def test_search_hn_returns_empty_for_zero_limit(self):
        self.assertEqual(hn.search_hn("anything", limit=0), [])


if __name__ == "__main__":
    unittest.main()
