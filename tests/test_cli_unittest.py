import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mmu_cli import cli


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


if __name__ == "__main__":
    unittest.main()
