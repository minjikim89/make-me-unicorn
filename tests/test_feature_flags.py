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


class AutoCheckConditionTest(unittest.TestCase):
    """Test that run_scan respects condition markers (false-pass prevention)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_scan_skips_disabled_block_items(self):
        """Auto-check should NOT mark items inside disabled condition blocks."""
        from mmu_cli.scan import run_scan

        # Create a blueprint with a conditional billing section
        self.write("docs/blueprints/14-analytics.md", """
## Analytics Strategy
- [ ] Choose analytics platform (PostHog, Mixpanel, or Amplitude).
<!-- if:has_billing -->
## Business Metrics
- [ ] Track Monthly Recurring Revenue (MRR).
<!-- endif -->
""")
        # Create package.json with posthog to trigger scan rule
        self.write("package.json", '{"dependencies": {"posthog-js": "^1.0.0"}}')

        flags = {"has_billing": False}
        result = run_scan(self.root, flags)

        # Read the blueprint back
        text = (self.root / "docs" / "blueprints" / "14-analytics.md").read_text()
        # The "analytics platform" item should be auto-checked (active section)
        self.assertIn("[x]", text.split("Analytics Strategy")[1].split("if:has_billing")[0])
        # The "MRR" item should NOT be auto-checked (disabled section)
        self.assertIn("[ ] Track Monthly Recurring Revenue", text)

    def test_scan_checks_enabled_block_items(self):
        """Auto-check SHOULD mark items inside enabled condition blocks."""
        from mmu_cli.scan import run_scan

        self.write("docs/blueprints/14-analytics.md", """
<!-- if:has_billing -->
## Business Metrics
- [ ] Track Monthly Recurring Revenue (MRR).
<!-- endif -->
## Analytics Strategy
- [ ] Choose analytics platform (PostHog, Mixpanel, or Amplitude).
""")
        self.write("package.json", '{"dependencies": {"posthog-js": "^1.0.0"}}')

        flags = {"has_billing": True}
        result = run_scan(self.root, flags)

        text = (self.root / "docs" / "blueprints" / "14-analytics.md").read_text()
        # Both items should be eligible for auto-check
        self.assertIn("[x]", text)

    def test_scan_without_flags_checks_all(self):
        """Without flags, all items should be eligible for auto-check."""
        from mmu_cli.scan import run_scan

        self.write("docs/blueprints/14-analytics.md", """
<!-- if:has_billing -->
## Business Metrics
- [ ] Track Monthly Recurring Revenue (MRR).
<!-- endif -->
## Analytics Strategy
- [ ] Choose analytics platform (PostHog, Mixpanel, or Amplitude).
""")
        self.write("package.json", '{"dependencies": {"posthog-js": "^1.0.0"}}')

        result = run_scan(self.root, None)

        text = (self.root / "docs" / "blueprints" / "14-analytics.md").read_text()
        # Without flags, all items should be checkable
        self.assertIn("[x]", text)


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


class ScoreBreakdownTest(unittest.TestCase):
    """Test mmu status --why score decomposition."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_breakdown_shows_composition(self):
        """Score breakdown should show applicable, checked, skipped counts."""
        from mmu_cli.display import render_score_breakdown

        self.write("docs/blueprints/01-frontend.md", """
## Frontend
- [x] Item A
- [ ] Item B
<!-- if:has_billing -->
- [ ] Billing item
<!-- endif -->
""")
        flags = {"has_billing": False}
        output = render_score_breakdown(self.root, flags)
        self.assertIn("SCORE BREAKDOWN", output)
        self.assertIn("Skipped", output)
        self.assertIn("has_billing", output)

    def test_breakdown_all_enabled(self):
        """With all flags enabled, no disabled flags should appear."""
        from mmu_cli.display import render_score_breakdown

        self.write("docs/blueprints/01-frontend.md", """
## Frontend
- [x] Item A
- [ ] Item B
""")
        output = render_score_breakdown(self.root, None)
        self.assertIn("All feature flags enabled", output)


class NextActionsTest(unittest.TestCase):
    """Test mmu next command."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_recommends_unchecked_items(self):
        """Should recommend unchecked items sorted by priority."""
        from mmu_cli.display import render_next_actions

        self.write("docs/blueprints/01-frontend.md", """
## Frontend
- [ ] [P0] Critical item
- [ ] [P1] Important item
- [ ] Regular item
- [x] Done item
""")
        output = render_next_actions(self.root, None, count=3)
        self.assertIn("NEXT ACTIONS", output)
        self.assertIn("Critical item", output)
        self.assertIn("Important item", output)
        # Should not include done items
        self.assertNotIn("Done item", output)

    def test_respects_flags(self):
        """Should not recommend items in disabled sections."""
        from mmu_cli.display import render_next_actions

        self.write("docs/blueprints/01-frontend.md", """
<!-- if:has_billing -->
- [ ] Billing item
<!-- endif -->
- [ ] Always item
""")
        flags = {"has_billing": False}
        output = render_next_actions(self.root, flags, count=3)
        self.assertNotIn("Billing item", output)
        self.assertIn("Always item", output)

    def test_empty_when_all_done(self):
        """Should show done message when all items are checked."""
        from mmu_cli.display import render_next_actions

        self.write("docs/blueprints/01-frontend.md", """
## Frontend
- [x] Done item
""")
        output = render_next_actions(self.root, None, count=3)
        self.assertIn("done", output.lower())

    def test_priority_parsing_preserves_brackets(self):
        """[P0]/[P1] tags should be parsed correctly, not mangled by lstrip."""
        from mmu_cli.display import render_next_actions

        self.write("docs/blueprints/01-frontend.md", """
## Frontend
- [ ] [P0] Critical security fix
- [ ] [P1] Important performance item
- [ ] Regular item
""")
        output = render_next_actions(self.root, None, count=3)
        # P0 should render with red/bold, not show "P0]" or "P1]"
        self.assertNotIn("P0]", output)
        self.assertNotIn("P1]", output)
        self.assertIn("Critical security fix", output)
        self.assertIn("Important performance item", output)

    def test_negative_count_defaults_to_3(self):
        """next -n 0 or negative should default to 3, not show done."""
        from mmu_cli.display import render_next_actions

        self.write("docs/blueprints/01-frontend.md", """
## Frontend
- [ ] Item A
- [ ] Item B
""")
        output = render_next_actions(self.root, None, count=0)
        self.assertIn("Item A", output)
        self.assertNotIn("done", output.lower())

    def test_diversity_cap(self):
        """Recommendations should not all come from one blueprint."""
        from mmu_cli.display import render_next_actions

        self.write("docs/blueprints/01-frontend.md", """
## Frontend
- [ ] Frontend item 1
- [ ] Frontend item 2
- [ ] Frontend item 3
- [ ] Frontend item 4
""")
        self.write("docs/blueprints/02-backend.md", """
## Backend
- [ ] Backend item 1
- [ ] Backend item 2
""")
        output = render_next_actions(self.root, None, count=4)
        # Should include backend items (not just 4 frontend)
        self.assertIn("Backend item", output)
        # Frontend should be capped at 2
        self.assertNotIn("Frontend item 3", output)


class CheckConditionAwareTest(unittest.TestCase):
    """Test that mmu check uses condition-aware item numbering."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_check_skips_hidden_items(self):
        """check #1 should target first visible item, not hidden one."""
        from mmu_cli.cli import command_check

        self.write("docs/blueprints/01-frontend.md", """
<!-- if:has_billing -->
- [ ] Hidden billing item
<!-- endif -->
- [ ] Visible item A
- [ ] Visible item B
""")
        self.write(".mmu/config.toml", """
[features]
billing = false
""")
        result = command_check("frontend", 1, self.root, force_state="check")
        self.assertEqual(result.exit_code, 0)

        text = (self.root / "docs" / "blueprints" / "01-frontend.md").read_text()
        # Hidden item should NOT be checked
        self.assertIn("[ ] Hidden billing item", text)
        # Visible item A (#1) should be checked
        self.assertIn("[x] Visible item A", text)


class BreakdownWarningTest(unittest.TestCase):
    """Test --why warning when flags are set but no markers exist."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_warns_when_flags_disabled_but_no_skips(self):
        """Should warn if flags are disabled but no items were skipped."""
        from mmu_cli.display import render_score_breakdown

        # Blueprint WITHOUT condition markers
        self.write("docs/blueprints/01-frontend.md", """
## Frontend
- [ ] Item A
- [ ] Item B
""")
        flags = {"has_billing": False, "has_mfa": False}
        output = render_score_breakdown(self.root, flags)
        self.assertIn("no items were skipped", output)
        self.assertIn("mmu init --force", output)


if __name__ == "__main__":
    unittest.main()
