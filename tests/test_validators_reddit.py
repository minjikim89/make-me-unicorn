import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli.validators import reddit  # noqa: E402


SAMPLE_LISTING = {
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "title": "  Anyone using an AI tutor for kids?  ",
                    "permalink": "/r/edtech/comments/abc/ai_tutor/",
                    "selftext": "Looking for recommendations.",
                    "subreddit": "edtech",
                    "score": 55,
                    "num_comments": 12,
                    "created_utc": 1743500000.0,
                },
            },
            {
                # Deleted / sparse post: most fields missing or null
                "kind": "t3",
                "data": {
                    "title": None,
                    "permalink": "/r/startups/comments/xyz/deleted/",
                    "selftext": None,
                    "score": None,
                    "num_comments": None,
                },
            },
        ]
    }
}


class RedditParseTests(unittest.TestCase):
    def test_parse_listing_extracts_fields(self):
        threads = reddit.parse_listing(SAMPLE_LISTING)
        self.assertEqual(len(threads), 2)
        first = threads[0]
        self.assertEqual(first["source"], "reddit")
        self.assertEqual(first["title"], "Anyone using an AI tutor for kids?")
        self.assertEqual(first["url"], "https://www.reddit.com/r/edtech/comments/abc/ai_tutor/")
        self.assertEqual(first["subreddit"], "edtech")
        self.assertEqual(first["score"], 55)
        self.assertEqual(first["comments"], 12)

    def test_parse_listing_handles_sparse_posts(self):
        threads = reddit.parse_listing(SAMPLE_LISTING)
        sparse = threads[1]
        self.assertEqual(sparse["title"], "")
        self.assertEqual(sparse["text"], "")
        self.assertEqual(sparse["score"], 0)
        self.assertEqual(sparse["comments"], 0)

    def test_parse_listing_empty_payload(self):
        self.assertEqual(reddit.parse_listing({}), [])
        self.assertEqual(reddit.parse_listing({"data": {}}), [])
        self.assertEqual(reddit.parse_listing({"data": {"children": []}}), [])

    def test_parse_listing_child_without_data(self):
        threads = reddit.parse_listing({"data": {"children": [{"kind": "t3"}]}})
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["title"], "")

    def test_search_reddit_returns_empty_for_zero_limit(self):
        self.assertEqual(reddit.search_reddit("anything", limit=0), [])


if __name__ == "__main__":
    unittest.main()
