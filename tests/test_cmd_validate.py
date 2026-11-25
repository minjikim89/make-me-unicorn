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

    def test_missing_validate_extra_names_the_install_command(self):
        import importlib.util
        from contextlib import redirect_stderr
        from unittest import mock

        real_find_spec = importlib.util.find_spec

        def fake_find_spec(name, *args, **kwargs):
            if name in {"requests", "vaderSentiment"}:
                return None
            return real_find_spec(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch("importlib.util.find_spec", fake_find_spec), \
                    mock.patch("mmu_cli.validators.fetch_threads") as fetch, \
                    redirect_stdout(out), redirect_stderr(err):
                exit_code = cli.command_validate("test idea", Path(tmp), limit=5, save=False)
            self.assertEqual(exit_code, 2)
            fetch.assert_not_called()
            self.assertIn("pip install 'make-me-unicorn[validate]'", err.getvalue())
            self.assertIn("requests", err.getvalue())
            self.assertNotIn("internet connection", err.getvalue())

    def test_partial_source_failure_is_visible_in_output(self):
        from contextlib import redirect_stderr
        from unittest import mock

        hits = [{"source": "hn", "title": "A great tool", "url": "https://example.com", "text": ""}]
        errors = ["Reddit fetch failed: HTTPError: 429"]
        for fmt, marker in (("text", "Partial results"), ("markdown", "Partial results"), ("json", '"errors"')):
            with tempfile.TemporaryDirectory() as tmp:
                out = io.StringIO()
                with mock.patch("mmu_cli.validators.fetch_threads", return_value=(hits, errors)), \
                        redirect_stdout(out), redirect_stderr(io.StringIO()):
                    exit_code = cli.command_validate("test idea", Path(tmp), limit=5, output_format=fmt, save=True)
                self.assertEqual(exit_code, 0, fmt)
                self.assertIn(marker, out.getvalue(), fmt)
                self.assertIn("Reddit fetch failed: HTTPError: 429", out.getvalue(), fmt)
                report = next((Path(tmp) / "reports" / "validate").glob("*.md")).read_text(encoding="utf-8")
                self.assertIn("Reddit fetch failed", report)


if __name__ == "__main__":
    unittest.main()
