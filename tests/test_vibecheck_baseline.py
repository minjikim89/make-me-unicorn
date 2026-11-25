"""Baselines: `--write-baseline` records current findings, `--baseline` reports only new ones."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mmu_cli import cli, vibecheck  # noqa: E402
from mmu_cli.vibecheck import engine  # noqa: E402

def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "argv", ["mmu", *argv]), redirect_stdout(out), redirect_stderr(err):
        try:
            code = cli.main()
        except SystemExit as exc:
            code = int(exc.code or 0)
    return code, out.getvalue(), err.getvalue()


class Project(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)
        self.files: list[Path] = []

    def write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        engine.reset_caches()
        if path not in self.files:
            self.files.append(path)
        return path

    def scan(self) -> dict[str, list]:
        out: dict[str, list] = {}
        for f in vibecheck.scan(self.root).findings:
            out.setdefault(f.check, []).append(f)
        return out

    def status(self, rule: str) -> str:
        return self.scan()[rule][0].status

    def lines(self, finding) -> list[tuple[str, int | None]]:
        return [(loc.path, loc.line) for loc in finding.locations]


class BaselineTests(Project):
    def setUp(self):
        super().setUp()
        self.write("db.py", 'q = f"SELECT * FROM t WHERE id = {c}"\n')
        self.write("settings.py", "DEBUG = True\n")

    def test_write_then_apply(self):
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--write-baseline")
        self.assertEqual(code, 0)
        path = self.root / ".mmu/vibecheck-baseline.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["schema"], "mmu.vibecheck-baseline/v1")
        self.assertEqual([(e["rule_id"], e["path"]) for e in doc["entries"]], [("sql-fstring", "db.py"), ("debug-mode", "settings.py")])
        for entry in doc["entries"]:
            self.assertRegex(entry["fingerprint"], r"^[0-9a-f]{16}$")

        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--baseline", "--format", "json")
        self.assertEqual(code, 0)
        doc = json.loads(out)
        self.assertEqual((doc["summary"]["blocking"], doc["summary"]["warnings"], doc["summary"]["baselined"]), (0, 0, 2))
        self.assertEqual({f["status"] for f in doc["findings"]}, {"baselined"})

    def test_new_findings_still_block_and_line_shifts_do_not(self):
        run_cli("vibecheck", "--root", str(self.root), "--write-baseline", "base.json")
        self.write("db.py", '# moved down\n\nq = f"SELECT * FROM t WHERE id = {c}"\nr = f"DELETE FROM t WHERE id = {c}"\n')
        result = vibecheck.scan(self.root, baseline=self.root / "base.json")
        by = {(f.check, f.status): f for f in result.findings}
        self.assertEqual(self.lines(by[("sql-fstring", "fail")]), [("db.py", 4)])
        self.assertEqual(self.lines(by[("sql-fstring", "baselined")]), [("db.py", 3)])
        self.assertEqual(result.exit_code(), 1)
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--baseline", "base.json", "--format", "agent")
        self.assertEqual(code, 1)
        self.assertIn("baselined", out.splitlines()[0])
        self.assertIn("db.py:4", out)
        self.assertNotIn("db.py:3", out)
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--baseline", "base.json")
        self.assertIn("[baselined]", out)

    def test_missing_or_invalid_baseline_is_exit_2(self):
        code, out, err = run_cli("vibecheck", "--root", str(self.root), "--baseline", "nope.json")
        self.assertEqual(code, 2)
        self.assertIn("baseline", err)
        self.write("bad.json", "{}")
        code, out, _ = run_cli("vibecheck", "--root", str(self.root), "--baseline", "bad.json", "--format", "json")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["error"]["code"], "bad-baseline")


if __name__ == "__main__":
    unittest.main()
