import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli import cli  # noqa: E402


class ValidateCommandTests(unittest.TestCase):
    def test_zero_limit_runs_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cli.command_validate(
                    "AI tutor for kids",
                    Path(tmp),
                    limit=0,
                    use_llm=False,
                    output_format="text",
                    save=True,
                )
            self.assertEqual(exit_code, 0)
            output = buf.getvalue()
            self.assertIn("AI tutor for kids", output)
            self.assertIn("Threads found: 0", output)
            reports = list((Path(tmp) / "reports" / "validate").glob("ai-tutor-for-kids-*.md"))
            self.assertEqual(len(reports), 1)

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.command_validate(
                    "test idea",
                    Path(tmp),
                    limit=0,
                    output_format="json",
                    save=False,
                )
            output = buf.getvalue()
            self.assertIn('"idea": "test idea"', output)
            self.assertIn('"hits": []', output)


if __name__ == "__main__":
    unittest.main()
