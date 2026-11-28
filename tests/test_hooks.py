"""Tests for `mmu hook` (src/mmu_cli/hooks.py) and the plugin wrapper hooks/vibecheck_gate.py."""

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli import hooks  # noqa: E402

FAKE_KEY = "sk_live_" + "a1b2c3d4e5" * 3  # assembled at runtime; not a real credential

FAIL_DOC = {
    "schema": "mmu.vibecheck/v1",
    "summary": {"blocking": 1},
    "findings": [{
        "rule_id": "secrets", "severity": "P0", "status": "fail", "message": "possible hardcoded secrets",
        "locations": [{"path": "app/pay.py", "line": 7}, {"path": "app/other.py", "line": 2}],
        "fix": "Replace the literal\nwith an env lookup", "ref": "https://example.test/why",
    }],
}
CLEAN_DOC = {"schema": "mmu.vibecheck/v1", "summary": {"blocking": 0}, "findings": []}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.test", "-c", "commit.gpgsign=false",
         "-c", "core.hooksPath=/dev/null", *args],
        cwd=str(root), check=True, capture_output=True,
    )


def _repo(tmp: str) -> Path:
    root = Path(tmp).resolve()
    _git(root, "init", "-q", "-b", "main")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _call(payload, host=None, event=None, env=None):
    """Run hooks.run on a payload; return (exit code, parsed stdout or None, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    stdin = io.StringIO(payload if isinstance(payload, str) else json.dumps(payload))
    with mock.patch.dict(os.environ, env or {}, clear=False), redirect_stdout(out), redirect_stderr(err):
        code = hooks.run(host, event, stdin=stdin)
    text = out.getvalue().strip()
    return code, (json.loads(text) if text else None), err.getvalue()


def _deny_reason(out) -> str:
    """The reason of a Claude Code / Codex PreToolUse deny, or "" when the output is not a deny."""
    hso = (out or {}).get("hookSpecificOutput") or {}
    return hso.get("permissionDecisionReason", "") if hso.get("permissionDecision") == "deny" else ""


class ShouldGateTests(unittest.TestCase):
    def test_gates_commit_and_push_variants(self):
        for cmd in [
            "git commit -m x", "git add -A && git commit -m 'y'", "cd app; git push origin main",
            "git -C /tmp/x commit -am z", "LANG=C git push", "cd app\ngit commit -m newline-separated",
            "git -c user.name=x commit -m y", "git --git-dir=/r/.git --work-tree=/r commit -m y",
            "git --no-pager push --force-with-lease", "(git commit -m x)", "echo $(git push)",
            "git add . &&\n  git commit -m 'multi'", "git commit -n -m x", "git commit --no-verify -m x",
            # other spellings of the same call
            "/usr/bin/git commit -m x", "./git commit -m x", '"git" commit -m x', "git.exe commit -m x",
            'git -c "user.name=A B" commit -m x', "git --git-dir .git commit -m x", "git --work-tree . commit -m x",
            "git \\\ncommit -m x", "sudo -u dev git commit -m x", "env LANG=C git push", "time git push",
            "bash -lc 'git commit -m x'", "sh -o pipefail -c \"git push\"", "eval git commit -m x",
            "if git commit -m x; then echo ok; fi", "git commit -m x 2>&1 | tail -3", "{ git push; }",
            "git commit -F- <<'EOF'\nmessage\nEOF", 'git commit -m "docs: mention --help flag"',
            'git commit -m "add -h option"', 'git commit -m "fix --dry-run handling"', "git push origin feat",
            "git push --tags", "git push origin tag v1",
        ]:
            with self.subTest(cmd=cmd):
                self.assertTrue(hooks.should_gate(cmd))

    def test_ignores_other_git_and_non_git(self):
        for cmd in [
            "git status", "git log --oneline", "ls -la", "gitk", "git commit-tree HEAD^{tree}", "git pushx",
            "legit commit", "git commit --dry-run", "git push --dry-run origin main", "git push -n",
            "git commit --help", "git help commit", "git --help commit", "git commit --porcelain",
            "git push origin --delete old", "git push -d origin old", "git push origin :old",
            # git commit / git push as text, not as a command
            'echo "run git commit when done"', 'grep -rn "git commit" docs/', "# git commit later",
            "ls # then git push", "cat <<EOF\ngit commit -m x\nEOF", "cat <<'EOF' > notes.md\ndon't git push\nEOF",
            'git log --grep="git commit"', 'gh pr create --title "fix git push bug"', "man git commit",
            "which git commit", "git submodule foreach git commit -m x",
        ]:
            with self.subTest(cmd=cmd):
                self.assertFalse(hooks.should_gate(cmd))

    def test_per_command_disable_is_honoured_only_where_the_shell_sees_it(self):
        for cmd in ["MMU_HOOK_DISABLE=1 git commit -m x", "cd app && MMU_HOOK_DISABLE=1 git push",
                    "export MMU_HOOK_DISABLE=1; git commit -m x", "env MMU_HOOK_DISABLE=true git push",
                    "MMU_HOOK_DISABLE=1 bash -c 'git commit -m x'"]:
            with self.subTest(cmd=cmd):
                self.assertFalse(hooks.should_gate(cmd))
        for cmd in ["MMU_HOOK_DISABLE=0 git commit -m x", "OTHER_MMU_HOOK_DISABLE=1 git commit -m x",
                    'git commit -m "MMU_HOOK_DISABLE=1 is the bypass"', "echo MMU_HOOK_DISABLE=1 && git commit -m x",
                    "git commit -m x # MMU_HOOK_DISABLE=1", "(export MMU_HOOK_DISABLE=1); git push"]:
            with self.subTest(cmd=cmd):
                self.assertTrue(hooks.should_gate(cmd))

    def test_env_switches(self):
        for value in ("1", "true", "YES"):
            with mock.patch.dict(os.environ, {"MMU_HOOK_DISABLE": value}):
                self.assertFalse(hooks.should_gate("git push"))
        with mock.patch.dict(os.environ, {"MMU_HOOK_ON_PUSH_ONLY": "1"}):
            self.assertFalse(hooks.should_gate("git commit -m x"))
            self.assertTrue(hooks.should_gate("git push"))
            self.assertTrue(hooks.should_gate("git commit -m x && git push"))

    def test_target_repository_follows_cd_and_git_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for name in ("proj", "other"):
                (root / name).mkdir()
                _git(root / name, "init", "-q")
            deadline = time.monotonic() + 30
            cases = {
                "git -C proj commit -m x": "proj", "git -C 'proj' push": "proj", "cd proj && git commit -m x": "proj",
                "(cd proj; git commit -m x)": "proj", "pushd proj && git commit -m x": "proj",
                "git --git-dir=proj/.git --work-tree=proj commit -m x": "proj", "git --work-tree other push": "other",
                "cd proj && cd ../other && git commit -m x": "other",
                "(cd proj); git -C other commit -m x": "other",
            }
            for cmd, expected in cases.items():
                with self.subTest(cmd=cmd):
                    call = hooks.gated_call(cmd, root)
                    self.assertEqual(hooks.repo_root(call, deadline).resolve(), root / expected)


class ScopeTests(unittest.TestCase):
    """Real git repositories: the scope must be exactly what the commit records or the push sends."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _repo(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        for rel in ("tracked.py", "sub/inner.py"):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text("x = 1\n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "files")

    def _scope(self, command: str, cwd: Path | None = None):
        call = hooks.gated_call(command, cwd or self.root)
        self.assertIsNotNone(call, command)
        scope = hooks.scope_for(call, self.root, time.monotonic() + 30)
        return None if scope is None else (scope.flags, scope.files)

    def test_plain_commit_scans_staged(self):
        for cmd in ["git commit -m x", "git commit -m 'fix -a flag handling'", "git commit -m -a",
                    "git commit --amend --no-edit", "git commit -q -m x", "git commit -mfoo",
                    "git commit --message 'a b' -S", "git commit -F msg.txt", "git commit -S -m x 2>&1"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self._scope(cmd), (["--staged"], None))

    def test_commit_lists_exactly_the_files_it_records(self):
        (self.root / "staged.py").write_text("s = 1\n", encoding="utf-8")
        _git(self.root, "add", "staged.py")
        (self.root / "tracked.py").write_text("x = 2\n", encoding="utf-8")       # modified, not staged
        (self.root / "scratch.py").write_text("u = 1\n", encoding="utf-8")       # untracked
        (self.root / "sub" / "new.py").write_text("n = 1\n", encoding="utf-8")   # untracked, in sub/
        listed = ["--files-from", "-"]
        cases = {
            "git commit -am x": ["staged.py", "tracked.py"],
            "git commit --all -m x": ["staged.py", "tracked.py"],
            "git commit -m x tracked.py": ["tracked.py"],
            "git commit -m x -- tracked.py": ["tracked.py"],
            "git commit --include tracked.py -m x": ["staged.py", "tracked.py"],
            "git add scratch.py && git commit -m x": ["scratch.py", "staged.py"],
            "git add -A && git commit -m x": ["scratch.py", "staged.py", "sub/new.py", "tracked.py"],
            "cd sub && git add . && git commit -m x": ["staged.py", "sub/new.py"],
            "git add no-such-file && git commit -m x": ["staged.py"],  # the add fails: what is staged
        }
        for cmd, files in cases.items():
            with self.subTest(cmd=cmd):
                self.assertEqual(self._scope(cmd), (listed, files))
        for cmd in ["git add -p && git commit -m x", "git commit -p -m x", "git commit -m 'unterminated"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self._scope(cmd), (["--changed"], None))

    def test_push_scans_only_commits_no_remote_has(self):
        self.assertEqual(self._scope("git push -u origin main"), ([], None), "no remote-tracking refs: everything")
        bare = Path(self._tmp.name) / "remote.git"
        _git(self.root, "init", "-q", "--bare", str(bare))
        _git(self.root, "remote", "add", "origin", str(bare))
        _git(self.root, "push", "-q", "-u", "origin", "main")
        self.assertIsNone(self._scope("git push"), "up to date: nothing to scan")
        _git(self.root, "checkout", "-q", "-b", "feat")
        self.assertIsNone(self._scope("git push -u origin feat"), "new branch without new commits")
        (self.root / "feature.py").write_text("f = 1\n", encoding="utf-8")
        (self.root / "untracked.py").write_text("u = 1\n", encoding="utf-8")
        _git(self.root, "add", "feature.py")
        _git(self.root, "commit", "-q", "-m", "feature")
        listed = (["--files-from", "-"], ["feature.py"])
        for cmd in ("git push -u origin feat", "git push origin HEAD:refs/heads/x", "git push origin feat",
                    "git push --all"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self._scope(cmd), listed)
        self.assertIsNone(self._scope("git push origin main"), "main has nothing new")
        self.assertEqual(self._scope("git push origin no-such-branch"), ([], None), "unknown revision: everything")


class DetectionTests(unittest.TestCase):
    def test_detect_host(self):
        cases = [
            ({"hook_event_name": "PreToolUse", "tool_name": "Bash", "permission_mode": "default"}, "claude"),
            ({"hook_event_name": "Stop", "stop_hook_active": False, "last_assistant_message": "done"}, "claude"),
            ({"hook_event_name": "PreToolUse", "tool_name": "Bash", "turn_id": "t1"}, "codex"),
            ({"hook_event_name": "PostToolUse", "tool_name": "apply_patch"}, "codex"),
            ({"hook_event_name": "Stop", "transcript_path": "/home/u/.codex/sessions/x.jsonl"}, "codex"),
            ({"hook_event_name": "beforeShellExecution", "command": "ls", "conversation_id": "c"}, "cursor"),
            ({"hook_event_name": "stop", "status": "completed", "loop_count": 0}, "cursor"),
            ({"command": "ls", "workspace_roots": ["/w"]}, "cursor"),
            ({"hook_event_name": "BeforeTool", "tool_name": "run_shell_command"}, "gemini"),
            ({"hook_event_name": "AfterAgent"}, "gemini"),
        ]
        for payload, host in cases:
            with self.subTest(payload=payload):
                self.assertEqual(hooks.detect_host(payload), host)

    def test_detect_event(self):
        cases = [
            ({"hook_event_name": "PreToolUse"}, "pre-shell"), ({"hook_event_name": "BeforeTool"}, "pre-shell"),
            ({"hook_event_name": "beforeShellExecution"}, "pre-shell"), ({"hook_event_name": "Stop"}, "stop"),
            ({"hook_event_name": "stop"}, "stop"), ({"hook_event_name": "AfterAgent"}, "stop"),
            ({"hook_event_name": "PostToolUse"}, "post-edit"), ({"stop_hook_active": False}, "stop"),
            ({"tool_input": {"command": "ls"}}, "pre-shell"), ({"unrelated": 1}, None),
        ]
        for payload, event in cases:
            with self.subTest(payload=payload):
                self.assertEqual(hooks.detect_event(payload), event)

    def test_shell_command_per_host(self):
        self.assertEqual(hooks.shell_command({"tool_name": "Bash", "tool_input": {"command": "git push"}}, "claude"), "git push")
        self.assertEqual(hooks.shell_command({"tool_name": "Edit", "tool_input": {"command": "git push"}}, "claude"), "")
        self.assertEqual(hooks.shell_command({"tool_name": "Bash", "tool_input": None}, "codex"), "")
        self.assertEqual(hooks.shell_command({"command": "git push", "cwd": "/w"}, "cursor"), "git push")
        self.assertEqual(
            hooks.shell_command({"tool_name": "run_shell_command", "tool_input": {"command": "git push"}}, "gemini"),
            "git push",
        )
        # Gemini's field name is not documented: fall back to every string in tool_input.
        fallback = hooks.shell_command(
            {"tool_name": "run_shell_command", "tool_input": {"cmd": "git commit -m x", "dir": "."}}, "gemini")
        self.assertTrue(hooks.should_gate(fallback))
        self.assertEqual(hooks.shell_command({"tool_name": "write_file", "tool_input": {"command": "git push"}}, "gemini"), "")

    def test_edited_files(self):
        self.assertEqual(hooks.edited_files({"tool_input": {"file_path": "/w/a.ts"}}), ["/w/a.ts"])
        patch = "*** Begin Patch\n*** Update File: app/a.py\n@@\n-x\n+y\n*** Add File: app/b.py\n+z\n*** End Patch"
        self.assertEqual(hooks.edited_files({"tool_input": {"command": patch}}), ["app/a.py", "app/b.py"])


class PreShellOutputTests(unittest.TestCase):
    """Each host's block / allow / fail-open shape, with the scanner mocked."""

    def _run(self, payload, host, doc, env=None):
        with mock.patch.object(hooks, "run_scan", return_value=doc), \
                mock.patch.object(hooks, "_run", return_value="skip agent rendering"):
            return _call(payload, host=host, env=env)

    def test_claude_block_is_a_json_deny_with_exit_0(self):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": "."}
        code, out, err = self._run(payload, None, FAIL_DOC)
        self.assertEqual((code, err), (0, ""), "exit 2 is reserved: a launcher failure must never look like a block")
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        reason = _deny_reason(out)
        self.assertIn("commit blocked", reason)
        self.assertIn("P0 secrets app/pay.py:7", reason)
        self.assertIn("app/other.py:2", reason)
        self.assertIn("fix: Replace the literal with an env lookup", reason)
        self.assertIn("mmu-ignore[secrets]: <reason>", reason)
        self.assertIn("MMU_HOOK_DISABLE=1", reason)

    def test_codex_block_matches_claude_contract(self):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "turn_id": "t", "tool_input": {"command": "git push"}, "cwd": "."}
        with mock.patch.object(hooks, "scope_for", return_value=hooks.Scope([])):
            code, out, err = self._run(payload, None, FAIL_DOC)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("push blocked", _deny_reason(out))

    def test_cursor_block_is_permission_deny_json(self):
        payload = {"hook_event_name": "beforeShellExecution", "command": "git commit -m x", "cwd": ".", "conversation_id": "c"}
        code, out, err = self._run(payload, None, FAIL_DOC)
        self.assertEqual(code, 0)
        self.assertEqual(out["permission"], "deny")
        self.assertIn("P0 secrets app/pay.py:7", out["agent_message"])
        self.assertNotIn("\n", out["user_message"])
        self.assertEqual(err, "")

    def test_gemini_block_is_decision_deny_json(self):
        payload = {"hook_event_name": "BeforeTool", "tool_name": "run_shell_command", "tool_input": {"command": "git commit -m x"}, "cwd": "."}
        code, out, err = self._run(payload, None, FAIL_DOC)
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "deny")
        self.assertIn("P0 secrets app/pay.py:7", out["reason"])
        self.assertEqual(err, "")

    def test_allow_shapes(self):
        for host, payload, expected in [
            ("claude", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, None),
            ("codex", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, None),
            ("cursor", {"command": "git commit -m x"}, {"permission": "allow"}),
            ("gemini", {"tool_name": "run_shell_command", "tool_input": {"command": "git commit -m x"}}, {}),
        ]:
            with self.subTest(host=host):
                code, out, err = self._run(payload, host, CLEAN_DOC)
                self.assertEqual((code, out, err), (0, expected, ""))

    def test_non_gated_commands_never_scan(self):
        with mock.patch.object(hooks, "run_scan", side_effect=AssertionError("must not scan")):
            self.assertEqual(_call({"tool_name": "Bash", "tool_input": {"command": "ls"}}, host="claude")[:2], (0, None))
            self.assertEqual(_call({"tool_name": "Write", "tool_input": {"command": "git push"}}, host="claude")[0], 0)
            self.assertEqual(_call({"command": "npm test"}, host="cursor")[1], {"permission": "allow"})
            self.assertEqual(_call({"tool_name": "Bash", "tool_input": None}, host="claude")[0], 0)
            code, out, _ = _call({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, host="claude",
                                 env={"MMU_HOOK_DISABLE": "1"})
            self.assertEqual((code, out), (0, None))

    def test_scanner_failure_fails_open_with_one_visible_line(self):
        for host, payload, key in [
            ("claude", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, "systemMessage"),
            ("codex", {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, "systemMessage"),
            ("cursor", {"command": "git commit -m x"}, "user_message"),
            ("gemini", {"tool_name": "run_shell_command", "tool_input": {"command": "git commit -m x"}}, "systemMessage"),
        ]:
            with self.subTest(host=host):
                code, out, _ = self._run(payload, host, "scan exceeded 45s")
                self.assertEqual(code, 0)
                self.assertIn("did not run (scan exceeded 45s)", out[key])
                self.assertIn("allowed unchecked", out[key])
                if host == "cursor":
                    self.assertEqual(out["permission"], "allow")

    def test_malformed_stdin_and_crashes_allow(self):
        self.assertEqual(_call("not json")[0], 0)
        self.assertEqual(_call("[1, 2]")[0], 0)
        self.assertEqual(_call("not json", host="cursor", event="pre-shell")[1], {"permission": "allow"})
        with mock.patch.object(hooks, "run_scan", side_effect=RuntimeError("boom")):
            code, out, _ = _call({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}, host="claude")
        self.assertEqual(code, 0)
        self.assertIn("mmu hook crashed (RuntimeError: boom)", out["systemMessage"])

    def test_scope_reaches_the_scanner(self):
        seen = []

        def fake(root, scope, deadline):
            seen.append((scope.flags, scope.stdin()))
            return CLEAN_DOC

        with tempfile.TemporaryDirectory() as tmp:
            root = _repo(tmp)
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            with mock.patch.object(hooks, "run_scan", side_effect=fake):
                _call({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": str(root)}, host="claude")
                _call({"tool_name": "Bash", "tool_input": {"command": "git commit -am x"}, "cwd": str(root)}, host="claude")
                _call({"command": "git add -A && git commit -m x", "cwd": str(root)}, host="cursor")
        listed = (["--files-from", "-"], "README.md\n")
        self.assertEqual(seen, [(["--staged"], ""), listed, listed])

    def test_hook_entry_point_never_exits_2(self):
        """Exit 2 means "block" to Claude Code, Codex and Gemini: no argument or launcher mistake may produce it."""
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}})
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
        for args in (["--host", "claude", "--event", "pre-shell", "||", "true"], ["--host", "nope"], ["--bogus"]):
            proc = subprocess.run([sys.executable, "-m", "mmu_cli", "hook", *args], input=payload,
                                  capture_output=True, text=True, env=env, timeout=60)
            with self.subTest(args=args):
                self.assertEqual(proc.returncode, 0, proc.stderr)


class RunScanTests(unittest.TestCase):
    def test_error_object_and_bad_output_become_reasons(self):
        def proc(stdout, code):
            return subprocess.CompletedProcess([], code, stdout=stdout, stderr="")

        deadline = time.monotonic() + 30
        err = json.dumps({"schema": "mmu.vibecheck/v1", "error": {"code": "not-a-git-repo", "message": "x is not a git repository"}})
        with mock.patch.object(hooks.subprocess, "run", return_value=proc(err, 2)):
            self.assertIn("scanner error: x is not a git repository", hooks.run_scan(Path("."), hooks.Scope([]), deadline))
        with mock.patch.object(hooks.subprocess, "run", return_value=proc("Traceback…", 1)):
            self.assertIn("no JSON", hooks.run_scan(Path("."), hooks.Scope([]), deadline))
        with mock.patch.object(hooks.subprocess, "run", side_effect=subprocess.TimeoutExpired("mmu", 1)):
            self.assertIn("scan exceeded", hooks.run_scan(Path("."), hooks.Scope([]), deadline))
        self.assertIn("no time left", hooks.run_scan(Path("."), hooks.Scope([]), time.monotonic()))
        self.assertIn("not a directory", hooks.run_scan(Path("/no/such/dir"), hooks.Scope([]), deadline))


class RealRepoTests(unittest.TestCase):
    """Real scanner, real git repo, no mocks."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _repo(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write_secret(self, rel="app/pay.py"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'KEY = "{FAKE_KEY}"\n', encoding="utf-8")
        return path

    def _edit(self, session: str, path: Path, **extra):
        """Tell the gate the agent edited `path` (what Claude Code sends after Edit/Write)."""
        return _call({"hook_event_name": "PostToolUse", "tool_name": "Write", "session_id": session,
                      "cwd": str(self.root), "tool_input": {"file_path": str(path)}, "tool_response": {}, **extra})

    def _state(self) -> list[dict]:
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((self.root / ".git" / "mmu").glob("stop-*.json"))]

    def test_modules_in_the_scanned_repo_are_never_imported(self):
        (self.root / "fnmatch.py").write_text('open("PLANTED", "w").write("x")\n', encoding="utf-8")
        (self.root / "json.py").write_text('open("PLANTED", "w").write("x")\n', encoding="utf-8")
        self._write_secret()
        _git(self.root, "add", "app/pay.py")
        code, out, _ = _call({"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(self.root),
                              "tool_input": {"command": "git commit -m x"}})
        self.assertIn("P0 secrets app/pay.py:1", _deny_reason(out))
        self.assertFalse((self.root / "PLANTED").exists())

    def test_a_pass_narrowed_by_repo_config_says_so(self):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(self.root),
                   "tool_input": {"command": "git add -A && git commit -m x"}}
        config = self.root / ".mmu" / "config.toml"
        config.parent.mkdir()
        config.write_text('[vibecheck]\nskip_paths = ["app"]\n', encoding="utf-8")
        self._write_secret()
        code, out, _ = _call(payload)
        self.assertEqual(_deny_reason(out), "")
        self.assertIn(".mmu/config.toml narrowed the check: 1 file(s) not scanned (skip_paths: app)",
                      out["systemMessage"])
        config.write_text('[vibecheck]\nignore = ["secrets"]\n', encoding="utf-8")
        code, out, _ = _call(payload)
        self.assertEqual(_deny_reason(out), "")
        self.assertIn("P0 rule(s) ignored: secrets", out["systemMessage"])
        config.write_text('[vibecheck]\nskip_paths = ["docs"]\n', encoding="utf-8")
        self.assertTrue(_deny_reason(_call(payload)[1]), "a skip path outside the change neither hides nor notes it")

    def test_commit_gate_blocks_staged_secret_and_ignores_unstaged(self):
        self._write_secret()
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(self.root),
                   "tool_input": {"command": "git commit -m x"}}
        self.assertEqual(_call(payload)[:2], (0, None), "nothing staged: plain commit is not blocked by untracked files")
        self.assertEqual(_call({**payload, "tool_input": {"command": "git add README.md && git commit -m x"}})[:2],
                         (0, None), "an unrelated untracked file does not block a commit that leaves it out")
        code, out, err = _call({**payload, "tool_input": {"command": "git add -A && git commit -m x"}})
        reason = _deny_reason(out)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("P0 secrets app/pay.py:1", reason)
        self.assertIn("scope: listed (1 file(s))", reason)
        self.assertNotIn(FAKE_KEY, reason)
        _git(self.root, "add", "-A")
        code, out, _ = _call(payload)
        self.assertEqual(code, 0)
        self.assertIn("scope: staged", _deny_reason(out))
        self.assertEqual(_call({**payload, "tool_input": {"command": 'echo "git commit -m x"'}})[:2], (0, None))

    def test_stop_gate_blocks_then_respects_guards(self):
        bad = self._write_secret()
        for session in ("s1", "s2", "s3"):
            self._edit(session, bad)
        payload = {"hook_event_name": "Stop", "session_id": "s1", "cwd": str(self.root), "stop_hook_active": False}
        code, out, _ = _call(payload)
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "block")
        self.assertIn("not done yet", out["reason"])
        self.assertIn("P0 secrets app/pay.py:1", out["reason"])
        # host loop guard
        self.assertEqual(_call({**payload, "stop_hook_active": True})[1], None)
        # our own cap: default 3 blocks per session, state under the git dir
        self.assertEqual(_call(payload)[1]["decision"], "block")
        self.assertEqual(_call(payload)[1]["decision"], "block")
        code, out, _ = _call(payload)
        self.assertEqual(code, 0)
        self.assertNotIn("decision", out)
        self.assertIn("letting go", out["systemMessage"])
        self.assertEqual(len(list((self.root / ".git" / "mmu").glob("stop-*.json"))), 3)
        self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=str(self.root), capture_output=True,
                                        text=True).stdout.strip(), "?? app/")
        # another session has its own budget; MMU_STOP_MAX / disable switches are honoured
        self.assertEqual(_call({**payload, "session_id": "s2"})[1]["decision"], "block")
        self.assertIsNone(_call({**payload, "session_id": "s3"}, env={"MMU_STOP_MAX": "0"})[1])
        self.assertIsNone(_call({**payload, "session_id": "s3"}, env={"MMU_STOP_DISABLE": "1"})[1])
        # a clean scan resets the counter
        (self.root / "app" / "pay.py").write_text('import os\nKEY = os.environ["STRIPE_KEY"]\n', encoding="utf-8")
        self.assertIsNone(_call(payload)[1])
        self.assertEqual(len(self._state()), 2)  # s1 cleared; s2 and s3 remain

    def test_stop_gate_cap_restarts_for_a_new_finding(self):
        bad = self._write_secret()
        self._edit("s1", bad)
        payload = {"hook_event_name": "Stop", "session_id": "s1", "cwd": str(self.root), "stop_hook_active": False}
        for _ in range(3):
            self.assertEqual(_call(payload)[1]["decision"], "block")
        self.assertIn("letting go", _call(payload)[1]["systemMessage"])
        other = self._write_secret("app/second.py")
        self._edit("s1", other)
        code, out, _ = _call(payload)
        self.assertEqual(out["decision"], "block", "a P0 the agent has not been sent back for yet counts afresh")
        self.assertIn("app/second.py:1", out["reason"])
        self.assertEqual(self._state()[0]["blocks"], 1)

    def test_stop_gate_ignores_preexisting_files_the_agent_never_touched(self):
        self._write_secret("app/legacy.py")  # uncommitted before the session, never edited by the agent
        payload = {"hook_event_name": "Stop", "session_id": "s1", "cwd": str(self.root), "stop_hook_active": False}
        with mock.patch.object(hooks, "run_scan", side_effect=AssertionError("no recorded edits: must not scan")):
            self.assertEqual(_call(payload), (0, None, ""))
        # the agent edits an unrelated, clean file: still allowed, and the state is cleared
        (self.root / "README.md").write_text("x\nmore\n", encoding="utf-8")
        self._edit("s1", self.root / "README.md")
        self.assertEqual(self._state()[0]["edited"], ["README.md"])
        self.assertEqual(_call(payload), (0, None, ""))
        self.assertEqual(self._state(), [])
        # Codex follows the same rule
        self.assertEqual(_call({**payload, "session_id": "c1", "turn_id": "t"}), (0, None, ""))

    def test_stop_gate_blocks_only_on_edited_files_and_clears_when_fixed(self):
        self._write_secret("app/legacy.py")
        bad = self._write_secret("app/pay.py")
        self._edit("s1", bad)
        self.assertEqual(self._state()[0]["edited"], ["app/pay.py"])
        payload = {"hook_event_name": "Stop", "session_id": "s1", "cwd": str(self.root), "stop_hook_active": False}
        code, out, _ = _call(payload)
        self.assertEqual((code, out["decision"]), (0, "block"))
        self.assertIn("1 launch-blocking issue(s) in files edited in this session", out["reason"])
        self.assertIn("P0 secrets app/pay.py:1", out["reason"])
        self.assertNotIn("legacy.py", out["reason"])
        self.assertIn("mmu-ignore[secrets]: <reason>", out["reason"])
        self.assertIn("explicitly asked to defer", out["reason"])
        self.assertIn("list these P0s in your final message and stop", out["reason"])
        self.assertNotIn(FAKE_KEY, out["reason"])
        self.assertEqual(self._state()[0]["blocks"], 1)
        # fixed: allowed, state cleared, and the untouched legacy file never blocks
        bad.write_text('import os\nKEY = os.environ["STRIPE_KEY"]\n', encoding="utf-8")
        self._edit("s1", bad)
        self.assertEqual(self._state()[0]["blocks"], 1, "recording an edit keeps the block counter")
        self.assertEqual(_call(payload), (0, None, ""))
        self.assertEqual(self._state(), [])
        self.assertEqual(_call(payload), (0, None, ""))

    def test_edits_are_recorded_for_non_code_files_and_apply_patch(self):
        (self.root / "notes.md").write_text("n\n", encoding="utf-8")
        with mock.patch.object(hooks, "run_scan", side_effect=AssertionError("must not scan")):
            self._edit("s1", self.root / "notes.md")
        patch = "*** Begin Patch\n*** Add File: app/new.py\n+x = 1\n*** End Patch"
        _call({"hook_event_name": "PostToolUse", "tool_name": "apply_patch", "session_id": "s1", "cwd": str(self.root),
               "tool_input": {"command": patch}})
        self.assertEqual(self._state()[0]["edited"], ["app/new.py", "notes.md"])
        outside = Path(tempfile.gettempdir()) / "mmu-outside.py"
        self._edit("s2", outside)
        self.assertEqual(len(self._state()), 1)

    def test_stop_gate_dialects(self):
        self._write_secret()
        code, out, _ = _call({"hook_event_name": "stop", "status": "completed", "loop_count": 0,
                              "conversation_id": "c1", "workspace_roots": [str(self.root)]})
        self.assertEqual(code, 0)
        self.assertEqual(list(out), ["followup_message"])
        self.assertIn("P0 secrets app/pay.py:1", out["followup_message"])
        self.assertEqual(_call({"hook_event_name": "stop", "status": "completed", "loop_count": 3,
                                "conversation_id": "c2", "workspace_roots": [str(self.root)]})[1], {})
        code, out, _ = _call({"hook_event_name": "AfterAgent", "session_id": "g1", "cwd": str(self.root),
                              "stop_hook_active": False})
        self.assertEqual((code, out["decision"]), (0, "deny"))
        # Cursor and Gemini have no edit tracking: every uncommitted change counts
        self.assertIn("in uncommitted changes", out["reason"])
        self._edit("x1", self.root / "app" / "pay.py", turn_id="t")
        code, out, _ = _call({"hook_event_name": "Stop", "session_id": "x1", "turn_id": "t", "cwd": str(self.root)})
        self.assertEqual(out["decision"], "block")

    def test_stop_gate_is_silent_outside_git_and_when_clean(self):
        self.assertIsNone(_call({"hook_event_name": "Stop", "session_id": "s", "cwd": str(self.root)})[1])
        with tempfile.TemporaryDirectory() as plain:
            (Path(plain) / "pay.py").write_text(f'KEY = "{FAKE_KEY}"\n', encoding="utf-8")
            self.assertEqual(_call({"hook_event_name": "Stop", "session_id": "s", "cwd": plain}), (0, None, ""))

    def test_post_edit_feedback_only_for_the_edited_file(self):
        bad = self._write_secret()
        self._write_secret("app/other.py")
        payload = {"hook_event_name": "PostToolUse", "tool_name": "Write", "cwd": str(self.root),
                   "tool_input": {"file_path": str(bad)}, "tool_response": {}}
        code, out, _ = _call(payload)
        self.assertEqual(code, 0)
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PostToolUse")
        self.assertIn("P0 secrets app/pay.py:1", hso["additionalContext"])
        self.assertNotIn("other.py", hso["additionalContext"])
        # Codex apply_patch payload, relative path
        patch = "*** Begin Patch\n*** Update File: app/pay.py\n@@\n*** End Patch"
        code, out, _ = _call({"hook_event_name": "PostToolUse", "tool_name": "apply_patch", "cwd": str(self.root),
                              "tool_input": {"command": patch}})
        self.assertIn("app/pay.py:1", out["hookSpecificOutput"]["additionalContext"])
        # clean file, non-code file: nothing, and no scan for the latter
        (self.root / "ok.py").write_text("x = 1\n", encoding="utf-8")
        self.assertIsNone(_call({**payload, "tool_input": {"file_path": str(self.root / "ok.py")}})[1])
        with mock.patch.object(hooks, "run_scan", side_effect=AssertionError("must not scan")):
            self.assertIsNone(_call({**payload, "tool_input": {"file_path": str(self.root / "notes.md")}})[1])


class WrapperTests(unittest.TestCase):
    """hooks/vibecheck_gate.py runs the bundled source without `mmu` on PATH."""

    def test_plugin_wrapper_blocks_real_secret_from_bundled_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _repo(tmp)
            (root / "pay.py").write_text(f'KEY = "{FAKE_KEY}"\n', encoding="utf-8")
            _git(root, "add", "pay.py")
            payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(root),
                       "tool_input": {"command": "git commit -m x"}}
            git_dir = str(Path(subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()).parent)
            for var in ("CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT"):
                env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT")}
                env.update({var: str(REPO_ROOT), "PATH": git_dir})
                proc = subprocess.run(
                    [sys.executable, str(REPO_ROOT / "hooks" / "vibecheck_gate.py"), "--event", "pre-shell"],
                    input=json.dumps(payload), capture_output=True, text=True, env=env, cwd=tmp, timeout=60,
                )
                with self.subTest(var=var):
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    reason = _deny_reason(json.loads(proc.stdout))
                    self.assertIn("P0 secrets pay.py:1", reason)
                    self.assertNotIn(FAKE_KEY, proc.stdout)

    @unittest.skipIf(os.name == "nt", "POSIX shell shim")
    def test_plugin_wrapper_never_hands_an_old_mmu_the_hook(self):
        """mmu < 0.9 has no `hook` and exits 2 (argparse): that would block every Bash call and every stop."""
        with tempfile.TemporaryDirectory() as tmp:
            plugin, bin_dir = Path(tmp) / "plugin", Path(tmp) / "bin"
            (plugin / "hooks").mkdir(parents=True)
            bin_dir.mkdir()
            (plugin / "hooks" / "vibecheck_gate.py").write_text(
                (REPO_ROOT / "hooks" / "vibecheck_gate.py").read_text(encoding="utf-8"), encoding="utf-8")
            old = bin_dir / "mmu"
            old.write_text('#!/bin/sh\n[ "$1" = "--version" ] && { echo "mmu 0.6.3"; exit 0; }\n'
                           'echo "mmu: error: invalid choice: hook" >&2\nexit 2\n', encoding="utf-8")
            old.chmod(0o755)
            env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT")}
            env["PATH"] = f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin"
            for event in ("pre-shell", "stop"):
                proc = subprocess.run([sys.executable, str(plugin / "hooks" / "vibecheck_gate.py"), "--event", event],
                                      input='{"tool_name": "Bash", "tool_input": {"command": "ls"}}',
                                      capture_output=True, text=True, env=env, timeout=60)
                with self.subTest(event=event):
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertIn("did not run", json.loads(proc.stdout)["systemMessage"])

    def test_hooks_json_shape(self):
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data["hooks"]), {"PreToolUse", "Stop", "PostToolUse"})
        self.assertEqual(data["hooks"]["PreToolUse"][0]["matcher"], "Bash")
        self.assertEqual(data["hooks"]["PostToolUse"][0]["matcher"], "Edit|Write|MultiEdit")
        for event, groups in data["hooks"].items():
            handler = groups[0]["hooks"][0]
            self.assertEqual(handler["type"], "command")
            self.assertIn("${CLAUDE_PLUGIN_ROOT}/hooks/vibecheck_gate.py", handler["command"])
            self.assertLessEqual(handler["timeout"], 60)
            self.assertGreater(handler["timeout"], hooks.POST_EDIT_DEADLINE_SECONDS if event == "PostToolUse" else hooks.DEADLINE_SECONDS)


if __name__ == "__main__":
    unittest.main()
