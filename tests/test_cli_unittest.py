import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mmu_cli import cli  # noqa: E402


class CLITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def make_required_docs(self) -> None:
        for rel in cli.REQUIRED_FILES:
            self.write(rel, "ok\n")

    def test_start_bundle_writes_output_file(self) -> None:
        self.write("docs/core/product.md", "# Product\nhello\n")
        self.write("docs/ops/roadmap.md", "# Roadmap\nworld\n")
        self.write("prompts/start.md", "start prompt")

        result = cli.command_start(
            mode="product",
            root=self.root,
            emit="bundle",
            output=".mmu/context_bundle.md",
            clipboard=False,
        )

        self.assertEqual(result.exit_code, 0)
        bundle_path = self.root / ".mmu/context_bundle.md"
        self.assertTrue(bundle_path.is_file())
        bundle = bundle_path.read_text(encoding="utf-8")
        self.assertIn("docs/core/product.md", bundle)
        self.assertIn("docs/ops/roadmap.md", bundle)

    def test_init_creates_scaffold_and_doctor_passes(self) -> None:
        result = cli.command_init(self.root, force=False)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((self.root / "README.md").is_file())
        self.assertTrue((self.root / "docs/checklists/auth_security.md").is_file())

        doctor = cli.command_doctor(self.root)
        self.assertEqual(doctor.exit_code, 0)

    def test_init_respects_existing_files_without_force(self) -> None:
        self.write("README.md", "custom-readme\n")
        result = cli.command_init(self.root, force=False)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("README.md", result.get("skipped", []))
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "custom-readme\n")

    def _check_some_items(self) -> tuple[Path, Path]:
        cli.command_init(self.root, force=False)
        for num in (1, 2, 3):
            self.assertEqual(cli.command_check("frontend", num, self.root, force_state="check").exit_code, 0)
        gates = self.root / "docs/checklists/from_scratch.md"
        gates.write_text(gates.read_text(encoding="utf-8").replace("- [ ]", "- [x]", 1), encoding="utf-8")
        config = self.root / ".mmu/config.toml"
        config.write_text(config.read_text(encoding="utf-8").replace("i18n = false", "i18n = true"), encoding="utf-8")
        return self.root / "docs/blueprints/01-frontend.md", config

    def test_init_force_keeps_checked_items_and_config(self) -> None:
        blueprint, config = self._check_some_items()
        config_before = config.read_text(encoding="utf-8")

        result = cli.command_init(self.root, force=True)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(blueprint.read_text(encoding="utf-8").count("[x]"), 3)
        self.assertEqual((self.root / "docs/checklists/from_scratch.md").read_text(encoding="utf-8").count("[x]"), 1)
        self.assertEqual(config.read_text(encoding="utf-8"), config_before)
        self.assertIn(".mmu/config.toml", result.get("skipped", []))

    def test_init_force_keeps_edited_docs(self) -> None:
        cli.command_init(self.root, force=False)
        self.write("README.md", "my project\n")
        self.write("docs/core/product.md", "# Product\nreal notes\n")

        cli.command_init(self.root, force=True)

        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), "my project\n")
        self.assertEqual((self.root / "docs/core/product.md").read_text(encoding="utf-8"), "# Product\nreal notes\n")

    def test_init_force_keeps_file_with_checked_custom_item(self) -> None:
        blueprint, _ = self._check_some_items()
        custom = blueprint.read_text(encoding="utf-8") + "- [x] My own launch item\n"
        blueprint.write_text(custom, encoding="utf-8")

        result = cli.command_init(self.root, force=True)

        self.assertEqual(blueprint.read_text(encoding="utf-8"), custom)
        self.assertIn("docs/blueprints/01-frontend.md", result.get("skipped", []))

    def test_init_reset_wipes_progress_and_config(self) -> None:
        blueprint, config = self._check_some_items()

        result = cli.command_init(self.root, force=False, reset=True)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(blueprint.read_text(encoding="utf-8").count("[x]"), 0)
        self.assertIn("i18n = false", config.read_text(encoding="utf-8"))

    def test_check_requires_exact_blueprint_name(self) -> None:
        cli.command_init(self.root, force=False)
        blueprints = self.root / "docs/blueprints"
        before = {p.name: p.read_text(encoding="utf-8") for p in blueprints.glob("*.md")}

        for name in ("e", "latest", "fron", ""):
            for state in ("check", "uncheck"):
                result = cli.command_check(name, 1, self.root, force_state=state)
                self.assertEqual(result.exit_code, 1, name)
                self.assertIn("Unknown blueprint", result["messages"][0])
        self.assertIn("frontend", cli.command_check("fron", 1, self.root, force_state="check")["messages"][1])
        self.assertEqual(before, {p.name: p.read_text(encoding="utf-8") for p in blueprints.glob("*.md")})

        for name in ("frontend", "Front", "seo-marketing", "SEO & Marketing", "a11y", "01-frontend"):
            self.assertEqual(cli.command_check(name, 1, self.root, force_state="check").exit_code, 0, name)

    def test_show_reports_ambiguous_blueprint_name(self) -> None:
        cli.command_init(self.root, force=False)

        ambiguous = cli.command_show("e", self.root)
        self.assertEqual(ambiguous.exit_code, 1)
        self.assertIn("Ambiguous blueprint", ambiguous["messages"][0])
        self.assertIn("frontend", ambiguous["messages"][1])

        self.assertEqual(cli.command_show("fron", self.root).get("blueprint"), "01-frontend.md")
        self.assertEqual(cli.command_show("billing", self.root).get("blueprint"), "04-billing.md")
        self.assertEqual(cli.command_show("zzz", self.root).exit_code, 1)

    def test_badge_color_defined_for_every_stage(self) -> None:
        from mmu_cli import display

        for _threshold, stage, _art in display.UNICORN_STAGES:
            self.assertIn(stage, display.STAGE_COLORS)
        stage, _ = display.unicorn_art(0.65)
        self.assertEqual(stage, "young")
        self.assertIn("9c27b0", display.render_badge_markdown(65, stage))
        self.assertIn("#9c27b0", display.render_badge_svg(65, stage))

    def test_next_in_uninitialized_directory_points_to_init(self) -> None:
        result = cli.command_next(self.root)
        text = "\n".join(result["messages"])
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result["initialized"])
        self.assertNotIn("you're done", text)
        self.assertIn("mmu init", text)
        self.assertIn("mmu vibecheck", text)

        cli.command_init(self.root, force=False)
        after = cli.command_next(self.root)
        self.assertTrue(after["initialized"])
        self.assertNotIn("isn't initialized", "\n".join(after["messages"]))

    @unittest.skipIf(sys.platform == "win32", "bash script execution is not supported on Windows")
    def test_snapshot_command_runs_local_script(self) -> None:
        script = self.root / "snapshot"
        script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "echo 'snapshot-ok'\n",
            encoding="utf-8",
        )
        os.chmod(script, 0o755)

        result = cli.command_snapshot(self.root, target=".", output="SNAPSHOT.md", no_md=True)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("snapshot-ok", "\n".join(result.get("messages", [])))

    def test_snapshot_without_script_explains_repo_checkout_requirement(self) -> None:
        from unittest import mock

        elsewhere = self.root / "site-packages" / "mmu_cli" / "cli.py"
        with mock.patch.object(cli, "__file__", str(elsewhere)):
            result = cli.command_snapshot(self.root, target=".", output="SNAPSHOT.md", no_md=True)
        self.assertEqual(result.exit_code, 2)
        text = "\n".join(result["messages"])
        self.assertIn("repo checkout", text)
        self.assertIn("./snapshot", text)

    def test_gate_parses_flexible_heading_and_indented_checklist(self) -> None:
        self.write(
            "docs/checklists/from_scratch.md",
            """
##   M7   Future Fit
  - [ ] Keep founder context durable

## M8 Another Gate
- [ ] next
""".strip()
            + "\n",
        )

        result = cli.command_gate("M7", self.root)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result["stage"], "M7")
        self.assertTrue(result["pending"])

    def test_gate_passes_when_no_pending_items(self) -> None:
        self.write(
            "docs/checklists/from_scratch.md",
            """
## M0 Problem Fit
- [x] done
""".strip()
            + "\n",
        )
        result = cli.command_gate("M0", self.root)
        self.assertEqual(result.exit_code, 0)

    def test_doctor_reports_missing_required_files(self) -> None:
        result = cli.command_doctor(self.root)
        self.assertEqual(result.exit_code, 2)
        self.assertGreater(result["failures"], 0)

    def test_doctor_passes_with_required_files(self) -> None:
        self.make_required_docs()
        self.write("docs/core/architecture.md", "dev/staging/prod")
        self.write("docs/checklists/auth_security.md", "password reset")
        self.write("docs/checklists/billing_tax.md", "webhook idempotent")
        self.write("docs/checklists/seo_distribution.md", "OG thumbnail")

        result = cli.command_doctor(self.root)
        self.assertEqual(result.exit_code, 0)

    def test_read_text_reports_errors(self) -> None:
        errors = []
        bad = self.root / "missing.txt"
        text = cli.read_text(bad, errors)
        self.assertIsNone(text)
        self.assertTrue(errors)

    def test_render_result_json(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.render_result(cli.Result(exit_code=0, messages=["ok"]), as_json=True)
        self.assertEqual(code, 0)
        self.assertIn('"exit_code": 0', out.getvalue())

    def test_root_path_handles_none(self) -> None:
        # `serve-mcp` lets `--root` default to None; main() must not crash.
        resolved = cli.root_path(None)
        self.assertEqual(resolved, Path.cwd())

    def test_root_path_handles_string(self) -> None:
        resolved = cli.root_path(str(self.root))
        self.assertEqual(resolved, self.root.resolve())


class NestedSkipDirTests(unittest.TestCase):
    """Vendor and build output is skipped wherever it sits, not only at the root."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skip = set(cli.DEFAULT_SKIP_PATHS)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, rel: str, text: str = "const x = 1;\n") -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_nested_node_modules_is_skipped(self) -> None:
        self.assertTrue(cli.should_skip_rel("website/node_modules/next/index.js", self.skip))
        self.assertTrue(cli.should_skip_rel("apps/web/node_modules", self.skip))

    def test_root_node_modules_still_skipped(self) -> None:
        self.assertTrue(cli.should_skip_rel("node_modules/next/index.js", self.skip))

    def test_other_nested_vendor_dirs_are_skipped(self) -> None:
        for rel in ("packages/ui/dist/bundle.js", "services/api/build/out.js", "sub/.venv/lib/x.py"):
            self.assertTrue(cli.should_skip_rel(rel, self.skip), rel)

    def test_source_dirs_are_scanned_by_default(self) -> None:
        # `scripts`, `tests`, `docs`, `examples` are the user's code, not vendor output.
        for rel in ("apps/api/scripts/deploy.py", "apps/api/tests/test_x.py", "scripts/deploy.py", "tests/test_x.py",
                    "docs/conf.py", "examples/app.py", "cli/main.py"):
            self.assertFalse(cli.should_skip_rel(rel, self.skip), rel)

    def test_configured_skip_paths_are_root_anchored(self) -> None:
        skip = self.skip | {"scripts"}
        self.assertTrue(cli.should_skip_rel("scripts/deploy.py", skip))
        self.assertFalse(cli.should_skip_rel("apps/api/scripts/deploy.py", skip))

    def test_build_output_dirs_are_skipped_at_any_depth(self) -> None:
        for rel in ("vendor/lib/x.rb", "apps/web/.vercel/output/x.js", "svc/target/debug/x.js", "web/.output/server/x.mjs"):
            self.assertTrue(cli.should_skip_rel(rel, self.skip), rel)

    def test_a_name_containing_a_vendor_dir_is_not_skipped(self) -> None:
        self.assertFalse(cli.should_skip_rel("src/node_modules_helper.py", self.skip))
        self.assertFalse(cli.should_skip_rel("src/my-build/app.js", self.skip))

    def test_gather_code_files_prunes_nested_vendor_dirs(self) -> None:
        self._write("web/node_modules/next/index.js")
        self._write("web/src/app.js")
        self._write("packages/ui/dist/bundle.js")
        self._write("apps/api/scripts/deploy.py", "x = 1\n")
        found = {
            p.relative_to(self.root).as_posix()
            for p in cli.gather_code_files(self.root, self.skip)
        }
        self.assertIn("web/src/app.js", found)
        self.assertIn("apps/api/scripts/deploy.py", found)
        self.assertNotIn("web/node_modules/next/index.js", found)
        self.assertNotIn("packages/ui/dist/bundle.js", found)


if __name__ == "__main__":
    unittest.main()
