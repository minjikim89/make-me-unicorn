"""CLI entry behaviour: console scripts, --version, global flags, default command, output encoding."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _mmu(*args: str, cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src"), **(env or {})}
    return subprocess.run([sys.executable, "-m", "mmu_cli", *args], capture_output=True, cwd=cwd, env=full_env, timeout=60)


class CliEntryTests(unittest.TestCase):
    def test_both_console_scripts_are_declared(self):
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('mmu = "mmu_cli.cli:main"', text)
        self.assertIn('make-me-unicorn = "mmu_cli.cli:main"', text)

    def test_version_flag(self):
        proc = _mmu("--version")
        self.assertEqual(proc.returncode, 0)
        self.assertRegex(proc.stdout.decode(), r"^mmu \d+\.\d+\.\d+")

    def test_no_subcommand_runs_vibecheck(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "db.py").write_text('q = f"SELECT * FROM t WHERE id = {i}"\n', encoding="utf-8")
            proc = _mmu(cwd=tmp)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn("sql-fstring", proc.stdout.decode("utf-8"))
            as_json = _mmu("--json", "--root", tmp)
            self.assertEqual(json.loads(as_json.stdout)["schema"], "mmu.vibecheck/v1")
            (Path(tmp) / "db.py").unlink()
            self.assertEqual(_mmu(cwd=tmp).returncode, 0)

    def test_global_flags_before_the_subcommand(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as elsewhere:
            (Path(tmp) / "db.py").write_text('q = f"SELECT * FROM t WHERE id = {i}"\n', encoding="utf-8")
            before = _mmu("--json", "--root", tmp, "vibecheck", cwd=elsewhere)
            after = _mmu("vibecheck", "--json", "--root", tmp, cwd=elsewhere)
            self.assertEqual(json.loads(before.stdout)["summary"], json.loads(after.stdout)["summary"])
            self.assertEqual(json.loads(before.stdout)["summary"]["blocking"], 1)
            for argv in (["--json", "--root", tmp, "doctor"], ["doctor", "--json", "--root", tmp],
                         ["--root", tmp, "doctor", "--json"]):
                proc = _mmu(*argv, cwd=elsewhere)
                with self.subTest(argv=argv):
                    self.assertIsInstance(json.loads(proc.stdout), dict)

    def test_output_survives_a_cp1252_console(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "db.py").write_text('q = f"SELECT * FROM t WHERE id = {i}"\n', encoding="utf-8")
            proc = _mmu("vibecheck", cwd=tmp, env={"PYTHONIOENCODING": "cp1252"})
            self.assertEqual(proc.returncode, 1, proc.stderr.decode("utf-8", "replace"))
            self.assertIn("✗", proc.stdout.decode("utf-8"))
            self.assertNotIn(b"UnicodeEncodeError", proc.stderr)


if __name__ == "__main__":
    unittest.main()
