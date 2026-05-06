import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli.validators import nlp  # noqa: E402

try:
    import vaderSentiment  # noqa: F401
    _HAS_VADER = True
except ImportError:
    _HAS_VADER = False


@unittest.skipUnless(_HAS_VADER, "vaderSentiment not installed (install via [validate] extra)")
class SentimentTests(unittest.TestCase):
    def test_positive_text_has_positive_compound(self):
        result = nlp.analyze_sentiment(["I love this idea, it's brilliant and helpful!"])
        self.assertGreater(result["compound"], 0.5)
        self.assertEqual(result["count"], 1)

    def test_negative_text_has_negative_compound(self):
        result = nlp.analyze_sentiment(["This is terrible. I hate it. Absolute waste of time."])
        self.assertLess(result["compound"], -0.3)

    def test_empty_input_returns_zero_count(self):
        result = nlp.analyze_sentiment([])
        self.assertEqual(result["count"], 0)


class CompetitorExtractionTests(unittest.TestCase):
    def test_extracts_capitalized_names_and_drops_stopwords(self):
        texts = [
            "We compared Notion and Obsidian. Notion won on collaboration.",
            "I switched from Notion to Roam.",
        ]
        comps = dict(nlp.extract_competitors(texts))
        self.assertIn("Notion", comps)
        self.assertEqual(comps["Notion"], 3)
        self.assertIn("Obsidian", comps)
        self.assertNotIn("The", comps)
        self.assertNotIn("HN", comps)

    def test_short_tokens_are_dropped(self):
        comps = dict(nlp.extract_competitors(["AI is a thing. UX matters."]))
        self.assertNotIn("AI", comps)
        self.assertNotIn("UX", comps)


if __name__ == "__main__":
    unittest.main()
