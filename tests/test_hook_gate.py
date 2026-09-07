"""Tests for the Claude Code PreToolUse commit gate shipped in hooks/vibecheck_gate.py."""

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("vibecheck_gate", REPO_ROOT / "hooks" / "vibecheck_gate.py")
gate = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(gate)


def _payload(command: str, cwd: str = ".") -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})


class ShouldGateTests(unittest.TestCase):
    def test_gates_commit_and_push_variants(self):
        for cmd in ["git commit -m x", "git add -A && git commit -m 'y'", "cd app; git push origin main", "git -C /tmp/x commit -am z"]:
            with self.subTest(cmd=cmd):
                self.assertTrue(gate._should_gate(cmd))

    def test_ignores_other_git_and_non_git(self):
        for cmd in ["git status", "git log --oneline", "ls -la", "echo 'git commit' > notes.txt", "gitk"]:
            with self.subTest(cmd=cmd):
                self.assertFalse(gate._should_gate(cmd))

    def test_env_switches(self):
        with mock.patch.dict(os.environ, {"MMU_HOOK_DISABLE": "1"}):
            self.assertFalse(gate._should_gate("git push"))
        with mock.patch.dict(os.environ, {"MMU_HOOK_ON_PUSH_ONLY": "1"}, clear=False):
            os.environ.pop("MMU_HOOK_DISABLE", None)
            self.assertFalse(gate._should_gate("git commit -m x"))
            self.assertTrue(gate._should_gate("git push"))


class MainTests(unittest.TestCase):
    def _run(self, payload: str, result):
        err = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(payload)), \
             mock.patch.object(gate, "_run_vibecheck", return_value=result), \
             redirect_stderr(err):
            code = gate.main()
        return code, err.getvalue()

    def test_allows_non_bash_tool(self):
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x"}, "cwd": "."})
        code, _ = self._run(payload, {"findings": [{"status": "fail"}]})
        self.assertEqual(code, 0)

    def test_allows_when_no_fail(self):
        code, err = self._run(_payload("git commit -m x"), {"findings": [{"status": "ok"}, {"status": "warn"}]})
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_blocks_on_fail_with_reason(self):
        result = {"findings": [{
            "check": "secrets", "severity": "P0", "status": "fail",
            "message": "possible hardcoded secrets in 1 file(s)", "hint": "rotate it",
            "files": ["src/pay.py"], "ref": "https://example.com/why",
        }]}
        code, err = self._run(_payload("git commit -m x"), result)
        self.assertEqual(code, 2)
        self.assertIn("commit blocked", err)
        self.assertIn("secrets", err)
        self.assertIn("src/pay.py", err)
        self.assertIn("why: https://example.com/why", err)
        self.assertIn("MMU_HOOK_DISABLE=1", err)

    def test_allows_when_scanner_unavailable(self):
        code, err = self._run(_payload("git push"), None)
        self.assertEqual(code, 0)
        self.assertIn("allowing", err)

    def test_allows_on_malformed_stdin(self):
        with mock.patch.object(sys, "stdin", io.StringIO("not json")):
            self.assertEqual(gate.main(), 0)


class EndToEndTests(unittest.TestCase):
    def test_bundled_source_fallback_blocks_real_secret(self):
        """No `mmu` on PATH → the hook imports mmu_cli from CLAUDE_PLUGIN_ROOT/src and still blocks."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "pay.py").write_text('KEY = "sk_live_' + "a1b2c3d4e5" * 3 + '"\n', encoding="utf-8")
            env = {"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT), "PATH": "/nonexistent"}
            with mock.patch.dict(os.environ, env, clear=False):
                result = gate._run_vibecheck(root)
        self.assertIsNotNone(result)
        checks = {f["check"]: f for f in result["findings"]}
        self.assertEqual(checks["secrets"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
