"""The benchmark is a release gate: no P0 false positives, and recall does not regress."""

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

try:
    import tomllib  # noqa: F401
    HAVE_TOML = True
except ModuleNotFoundError:  # Python 3.10 without tomli
    HAVE_TOML = importlib.util.find_spec("tomli") is not None

from bench.materialize import FIXTURES, fixture_names, materialize, synthetic_secret  # noqa: E402
from mmu_cli.vibecheck import all_rules  # noqa: E402
from mmu_cli.vibecheck.rules.secrets import secret_hits  # noqa: E402

# Locked-in results. Raise them when the rules improve; a drop is a regression.
MIN_P0_RECALL = 1.0
MIN_P1_RECALL = 1.0
MIN_PLANTED_RECALL = 0.94  # 52 of 55 planted issues; the 3 misses have no rule (see [[uncovered]])
MAX_P1_FALSE_POSITIVES = 1  # pickle.load of a self-written cache file in fastapi-good


def load_bench():
    spec = importlib.util.spec_from_file_location("mmu_bench", ROOT / "scripts" / "bench.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mmu_bench"] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAVE_TOML, "needs tomllib (Python 3.11+) or tomli")
class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bench = load_bench()
        cls.results = cls.bench.run_all()
        cls.summary = cls.bench.summarize(cls.results)

    def test_no_p0_false_positives_on_any_fixture(self):
        offenders = [(r.name, key) for r in self.results for key in r.fp if key[2] == "P0"]
        self.assertEqual(offenders, [])
        self.assertEqual(self.summary["P0"]["precision"], 1.0)

    def test_correct_code_is_never_reported(self):
        self.assertEqual([(r.name, v) for r in self.results for v in r.violations], [])

    def test_recall_does_not_regress(self):
        self.assertGreaterEqual(self.summary["P0"]["recall"], MIN_P0_RECALL, [(r.name, r.fn) for r in self.results if r.fn])
        self.assertGreaterEqual(self.summary["P1"]["recall"], MIN_P1_RECALL, [(r.name, r.fn) for r in self.results if r.fn])
        self.assertGreaterEqual(self.summary["planted"]["recall"], MIN_PLANTED_RECALL)

    def test_p1_false_positives_stay_bounded(self):
        self.assertLessEqual(self.summary["P1"]["fp"], MAX_P1_FALSE_POSITIVES, [(r.name, r.fp) for r in self.results if r.fp])

    def test_clean_fixtures_scan_clean(self):
        by_name = {r.name: r for r in self.results}
        for name in ("next-supabase-good", "express-good", "py-venv"):
            self.assertEqual((by_name[name].tp, by_name[name].fp), ([], []), name)

    def test_every_rule_has_a_positive_and_every_fixture_a_ground_truth(self):
        covered = set(self.summary["rules"])
        self.assertEqual({rule.id for rule in all_rules()} - covered, set())
        for name in fixture_names():
            self.assertTrue((ROOT / "bench" / "expected" / f"{name}.toml").is_file(), name)

    def test_published_numbers_match_the_code(self):
        section = self.bench.doc_section()
        self.assertIsNotNone(section, "docs/benchmark.md has no generated fixture section")
        self.assertEqual(section, self.bench.render_markdown(self.results, self.summary).strip(),
                         "run `python scripts/bench.py --markdown`")


class FixtureHygieneTests(unittest.TestCase):
    def test_committed_fixtures_hold_no_key_shaped_strings(self):
        jwt = re.compile(r"eyJ[0-9A-Za-z_-]{10,}\.eyJ")
        for path in sorted(FIXTURES.rglob("*")):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            self.assertEqual(secret_hits(text), [], path)
            self.assertIsNone(jwt.search(text), path)

    def test_materialize_fills_placeholders_and_restores_dotfiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = materialize("next-supabase-stripe", Path(tmp) / "app")
            env = (root / ".env").read_text(encoding="utf-8")
            self.assertNotIn("{{SECRET", env)
            self.assertEqual({label for _, label in secret_hits(env)},
                             {"Stripe live secret key", "Stripe webhook signing secret", "OpenAI API key", "Supabase service_role JWT"})
            self.assertTrue((root / ".gitignore").is_file())
            self.assertFalse(list(root.rglob("_dot_*")))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue((materialize("agent-trap", Path(tmp) / "repo") / ".git" / "config").is_file())

    def test_synthetic_secrets_are_deterministic(self):
        self.assertEqual(synthetic_secret("stripe_live"), synthetic_secret("stripe_live"))
        self.assertNotEqual(synthetic_secret("github", "a"), synthetic_secret("github", "b"))
        with self.assertRaises(ValueError):
            synthetic_secret("nope")


if __name__ == "__main__":
    unittest.main()
