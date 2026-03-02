"""Tests for feature flag config and conditional blueprint scanning."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mmu_cli.cli import FEATURE_FLAG_DEFAULTS, load_feature_flags, _generate_stack_config  # noqa: E402
from mmu_cli.display import scan_blueprint, scan_all_blueprints  # noqa: E402


class FeatureFlagLoadingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_defaults_all_true(self):
        """Without config file, all flags should default to True."""
        flags = load_feature_flags(self.root)
        self.assertEqual(flags, FEATURE_FLAG_DEFAULTS)
        for v in flags.values():
            self.assertTrue(v)

    def test_load_config_overrides(self):
        """Config file should override specific flags."""
        self.write(".mmu/config.toml", """
[features]
billing = false
i18n = false

[architecture]
containerized = false

[market]
targets_eu = false
""")
        flags = load_feature_flags(self.root)
        self.assertFalse(flags["has_billing"])
        self.assertFalse(flags["has_i18n"])
        self.assertFalse(flags["uses_containers"])
        self.assertFalse(flags["targets_eu"])
        # Unset flags remain True
        self.assertTrue(flags["has_mfa"])
        self.assertTrue(flags["has_file_upload"])

    def test_invalid_config_returns_defaults(self):
        """Malformed TOML should fall back to defaults."""
        self.write(".mmu/config.toml", "this is not valid toml {{{}}")
        flags = load_feature_flags(self.root)
        self.assertEqual(flags, FEATURE_FLAG_DEFAULTS)


class ConditionalScanningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_no_flags_counts_all(self):
        """Without flags, all items should be counted."""
        self.write("test.md", """
<!-- if:has_billing -->
## Billing
- [ ] Item A
- [ ] Item B
<!-- endif -->
## Always
- [ ] Item C
""")
        done, total, skipped = scan_blueprint(self.root / "test.md", None)
        self.assertEqual(total, 3)
        self.assertEqual(skipped, 0)

    def test_flag_false_skips_section(self):
        """Items in a false-flag section should be skipped."""
        self.write("test.md", """
<!-- if:has_billing -->
## Billing
- [ ] Item A
- [x] Item B
<!-- endif -->
## Always
- [ ] Item C
""")
        flags = {"has_billing": False}
        done, total, skipped = scan_blueprint(self.root / "test.md", flags)
        self.assertEqual(total, 1)  # Only Item C
        self.assertEqual(done, 0)
        self.assertEqual(skipped, 2)  # Item A and B

    def test_flag_true_counts_section(self):
        """Items in a true-flag section should be counted normally."""
        self.write("test.md", """
<!-- if:has_billing -->
## Billing
- [ ] Item A
- [x] Item B
<!-- endif -->
## Always
- [ ] Item C
""")
        flags = {"has_billing": True}
        done, total, skipped = scan_blueprint(self.root / "test.md", flags)
        self.assertEqual(total, 3)
        self.assertEqual(done, 1)
        self.assertEqual(skipped, 0)

    def test_multiple_conditions(self):
        """Multiple conditional sections should work independently."""
        self.write("test.md", """
<!-- if:has_billing -->
- [ ] Billing item
<!-- endif -->
<!-- if:has_i18n -->
- [ ] i18n item
<!-- endif -->
- [ ] Always item
""")
        flags = {"has_billing": False, "has_i18n": True}
        done, total, skipped = scan_blueprint(self.root / "test.md", flags)
        self.assertEqual(total, 2)  # i18n + always
        self.assertEqual(skipped, 1)  # billing

    def test_unknown_flag_defaults_true(self):
        """Unknown flag names in markers should default to True."""
        self.write("test.md", """
<!-- if:unknown_future_flag -->
- [ ] Future item
<!-- endif -->
""")
        flags = {}
        done, total, skipped = scan_blueprint(self.root / "test.md", flags)
        self.assertEqual(total, 1)
        self.assertEqual(skipped, 0)


class ConfigGenerationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_generates_valid_toml(self):
        """Generated config should be parseable by our simple parser."""
        from mmu_cli.cli import _parse_simple_toml
        content = _generate_stack_config(self.root)
        data = _parse_simple_toml(content)
        self.assertIn("features", data)
        self.assertIn("architecture", data)
        self.assertIn("market", data)

    def test_detects_dockerfile(self):
        """Should detect Docker when Dockerfile exists."""
        (self.root / "Dockerfile").write_text("FROM node:20\n")
        content = _generate_stack_config(self.root)
        self.assertIn("containerized = true", content)

    def test_no_dockerfile_defaults_false(self):
        """Without Dockerfile, containerized should be false."""
        content = _generate_stack_config(self.root)
        self.assertIn("containerized = false", content)


class RealBlueprintScanTest(unittest.TestCase):
    """Test against actual blueprint files in the repo."""

    def test_billing_blueprint_skippable(self):
        """04-billing.md should be fully skippable."""
        bp = ROOT / "docs" / "blueprints" / "04-billing.md"
        if not bp.exists():
            self.skipTest("Blueprint not in working directory")

        _, total_on, _ = scan_blueprint(bp, {"has_billing": True})
        _, total_off, skipped = scan_blueprint(bp, {"has_billing": False})

        self.assertGreater(total_on, 0)
        self.assertEqual(total_off, 0)
        self.assertEqual(skipped, total_on)

    def test_full_scan_skip_count(self):
        """Minimal config should skip significant items from full scan."""
        bp_dir = ROOT / "docs" / "blueprints"
        if not bp_dir.exists():
            self.skipTest("Blueprints not in working directory")

        all_on = scan_all_blueprints(ROOT, None)
        total_on = sum(t for _, _, t, _ in all_on)

        conservative = {k: False for k in FEATURE_FLAG_DEFAULTS}
        all_off = scan_all_blueprints(ROOT, conservative)
        total_off = sum(t for _, _, t, _ in all_off)
        skipped_off = sum(s for _, _, _, s in all_off)

        self.assertGreater(skipped_off, 50, "Should skip at least 50 items with all flags off")
        self.assertLess(total_off, total_on, "Filtered total should be less than full total")


if __name__ == "__main__":
    unittest.main()
