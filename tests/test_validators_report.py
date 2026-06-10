import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli.validators import report  # noqa: E402


SENTIMENT = {"compound": 0.34, "count": 4, "pos": 0.4, "neg": 0.1, "neu": 0.5}
HITS = [
    {"source": "hn", "title": "Show HN: AI tutor", "url": "https://hn.example/1", "text": "nice"},
    {"source": "reddit", "title": "AI tutors any good?", "url": "https://r.example/2", "text": ""},
]
COMPETITORS = [("Khanmigo", 5), ("Duolingo", 3)]


class VerdictTests(unittest.TestCase):
    def test_no_signal_when_count_zero(self):
        self.assertEqual(report.verdict(0.9, 0), "NO SIGNAL")

    def test_threshold_boundaries(self):
        t = report.VERDICT_THRESHOLD
        self.assertEqual(report.verdict(t, 5), "POSITIVE LEAN")
        self.assertEqual(report.verdict(t - 0.01, 5), "MIXED")
        self.assertEqual(report.verdict(-t, 5), "NEGATIVE LEAN")
        self.assertEqual(report.verdict(-t + 0.01, 5), "MIXED")
        self.assertEqual(report.verdict(0.0, 5), "MIXED")


class SlugTests(unittest.TestCase):
    def test_slugify_basic(self):
        self.assertEqual(report.slugify("AI tutor for kids!"), "ai-tutor-for-kids")

    def test_slugify_empty_falls_back(self):
        self.assertEqual(report.slugify("!!!"), "idea")

    def test_report_filename_distinguishes_truncation_collisions(self):
        prefix = "AI tutor for kids that works fully offline in rural mountain areas"
        self.assertGreaterEqual(len(report.slugify(prefix)), 60)  # truncation kicks in
        a = f"{prefix} of California"
        b = f"{prefix} of Texas"
        self.assertEqual(report.slugify(a), report.slugify(b))  # slug collides
        self.assertNotEqual(report.report_filename(a), report.report_filename(b))

    def test_report_filename_stable_for_same_idea(self):
        self.assertEqual(report.report_filename("AI tutor"), report.report_filename("AI tutor"))
        self.assertTrue(report.report_filename("AI tutor").endswith(".md"))


class FormatTextTests(unittest.TestCase):
    def test_includes_idea_counts_and_threads(self):
        out = report.format_text("AI tutor", HITS, SENTIMENT, COMPETITORS)
        self.assertIn("MMU Validate — AI tutor", out)
        self.assertIn("Threads found: 2", out)
        self.assertIn("POSITIVE LEAN", out)
        self.assertIn("Khanmigo (5)", out)
        self.assertIn("[HN] Show HN: AI tutor", out)
        self.assertIn("https://hn.example/1", out)

    def test_llm_section_only_when_present(self):
        without = report.format_text("x", HITS, SENTIMENT, [])
        self.assertNotIn("LLM Synthesis", without)
        with_llm = report.format_text("x", HITS, SENTIMENT, [], llm_report="Verdict: go")
        self.assertIn("LLM Synthesis", with_llm)
        self.assertIn("Verdict: go", with_llm)

    def test_handles_empty_results(self):
        empty = {"compound": 0.0, "count": 0, "pos": 0.0, "neg": 0.0, "neu": 0.0}
        out = report.format_text("x", [], empty, [])
        self.assertIn("Threads found: 0", out)
        self.assertIn("NO SIGNAL", out)


class FormatMarkdownTests(unittest.TestCase):
    def test_structure(self):
        out = report.format_markdown("AI tutor", HITS, SENTIMENT, COMPETITORS, llm_report="Go.")
        self.assertIn("# Validation Report: AI tutor", out)
        self.assertIn("## Competitors / named entities", out)
        self.assertIn("- Khanmigo (5)", out)
        self.assertIn("## Top threads", out)
        self.assertIn("[Show HN: AI tutor](https://hn.example/1)", out)
        self.assertIn("## LLM Synthesis", out)

    def test_omits_empty_sections(self):
        empty = {"compound": 0.0, "count": 0, "pos": 0.0, "neg": 0.0, "neu": 0.0}
        out = report.format_markdown("x", [], empty, [])
        self.assertNotIn("## Competitors", out)
        self.assertNotIn("## Top threads", out)
        self.assertNotIn("## LLM Synthesis", out)


if __name__ == "__main__":
    unittest.main()
