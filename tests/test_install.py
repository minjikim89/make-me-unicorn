"""Tests for `mmu install` (src/mmu_cli/install.py)."""

import argparse
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mmu_cli import install  # noqa: E402


def _run(root: Path, *flags: str, command: str | None = "mmu hook") -> tuple[int, str]:
    parser = argparse.ArgumentParser()
    install.add_arguments(parser)
    argv = list(flags) + (["--command", command] if command else [])
    out = io.StringIO()
    with redirect_stdout(out):
        code = install.run(parser.parse_args(argv), root)
    return code, out.getvalue()


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)


class JsonTargetTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _load(self, rel: str) -> dict:
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def test_claude_merge_preserves_existing_settings_and_is_idempotent(self):
        settings = self.root / ".claude" / "settings.json"
        settings.parent.mkdir()
        existing = {
            "permissions": {"allow": ["Bash(npm test)"]},
            "hooks": {
                "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "./guard.sh"}]}],
                "SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}],
            },
        }
        settings.write_text(json.dumps(existing), encoding="utf-8")
        self.assertEqual(_run(self.root, "--claude")[0], 0)
        data = self._load(".claude/settings.json")
        self.assertEqual(data["permissions"], existing["permissions"])
        self.assertEqual(data["hooks"]["SessionStart"], existing["hooks"]["SessionStart"])
        pre = data["hooks"]["PreToolUse"]
        self.assertEqual(pre[0], existing["hooks"]["PreToolUse"][0])
        self.assertEqual(pre[1], {"matcher": "Bash", "hooks": [
            {"type": "command", "command": "mmu hook --host claude --event pre-shell" + install.GUARD, "timeout": 60}]})
        self.assertEqual(data["hooks"]["Stop"][0]["hooks"][0]["command"], "mmu hook --host claude --event stop" + install.GUARD)
        self.assertEqual(data["hooks"]["PostToolUse"][0]["matcher"], "Edit|Write|MultiEdit")
        first = settings.read_text(encoding="utf-8")
        code, out = _run(self.root, "--claude")
        self.assertEqual(code, 0)
        self.assertIn("already up to date", out)
        self.assertEqual(settings.read_text(encoding="utf-8"), first)
        # changing the command replaces our entries instead of duplicating them
        _run(self.root, "--claude", command='uvx --from "make-me-unicorn>=0.9" mmu hook')
        data = self._load(".claude/settings.json")
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 2)
        self.assertIn('uvx --from "make-me-unicorn>=0.9" mmu hook --host claude', data["hooks"]["PreToolUse"][1]["hooks"][0]["command"])
        # uninstall leaves exactly what was there before
        self.assertEqual(_run(self.root, "--claude", "--uninstall")[0], 0)
        self.assertEqual(self._load(".claude/settings.json"), existing)

    def test_fresh_install_and_uninstall_remove_the_file(self):
        for flag, rel in [("--claude", ".claude/settings.json"), ("--codex", ".codex/hooks.json"),
                          ("--cursor", ".cursor/hooks.json"), ("--gemini", ".gemini/settings.json")]:
            with self.subTest(flag=flag):
                self.assertEqual(_run(self.root, flag)[0], 0)
                self.assertTrue((self.root / rel).is_file())
                self.assertEqual(_run(self.root, flag, "--uninstall")[0], 0)
                self.assertFalse((self.root / rel).exists())
                self.assertIn("not installed", _run(self.root, flag, "--uninstall")[1])

    def test_codex_shape(self):
        _run(self.root, "--codex")
        hooks = self._load(".codex/hooks.json")["hooks"]
        self.assertEqual(set(hooks), {"PreToolUse", "Stop", "PostToolUse"})
        self.assertEqual(hooks["PreToolUse"][0]["matcher"], "Bash")
        self.assertEqual(hooks["PostToolUse"][0]["matcher"], "apply_patch|Edit|Write")
        self.assertEqual(hooks["Stop"][0]["hooks"][0],
                         {"type": "command", "command": "mmu hook --host codex --event stop" + install.GUARD, "timeout": 60})

    def test_cursor_shape_and_merge(self):
        path = self.root / ".cursor" / "hooks.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"version": 1, "hooks": {"stop": [{"command": "./notify.sh"}]}}), encoding="utf-8")
        _run(self.root, "--cursor")
        _run(self.root, "--cursor")
        data = self._load(".cursor/hooks.json")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["hooks"]["stop"], [
            {"command": "./notify.sh"}, {"command": "mmu hook --host cursor --event stop" + install.GUARD, "timeout": 60}])
        shell = data["hooks"]["beforeShellExecution"]
        self.assertEqual(shell, [{"command": "mmu hook --host cursor --event pre-shell" + install.GUARD, "timeout": 60,
                                  "matcher": "git"}])
        self.assertNotIn("afterFileEdit", data["hooks"])
        _run(self.root, "--cursor", "--uninstall")
        self.assertEqual(self._load(".cursor/hooks.json"), {"version": 1, "hooks": {"stop": [{"command": "./notify.sh"}]}})

    def test_gemini_shape_uses_millisecond_timeouts_and_merges(self):
        path = self.root / ".gemini" / "settings.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
        _run(self.root, "--gemini")
        data = self._load(".gemini/settings.json")
        self.assertEqual(data["theme"], "dark")
        before = data["hooks"]["BeforeTool"][0]
        self.assertEqual(before["matcher"], "run_shell_command")
        self.assertEqual(before["hooks"][0], {"name": "mmu-gate", "type": "command",
                                               "command": "mmu hook --host gemini --event pre-shell" + install.GUARD,
                                               "timeout": 60000})
        self.assertEqual(data["hooks"]["AfterAgent"][0]["hooks"][0]["command"],
                         "mmu hook --host gemini --event stop" + install.GUARD)
        _run(self.root, "--gemini", "--uninstall")
        self.assertEqual(self._load(".gemini/settings.json"), {"theme": "dark"})

    @unittest.skipIf(os.name == "nt", "the guard is POSIX-only")
    def test_guard_turns_a_launcher_failure_into_allow(self):
        """`uvx` offline or an old `mmu` exits 2, which a host reads as a block: the registered command must not."""
        _run(self.root, "--claude", command="sh -c 'echo launcher failed >&2; exit 2' --")
        command = self._load(".claude/settings.json")["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertTrue(command.endswith(" || true"))
        self.assertEqual(subprocess.run(["sh", "-c", command], capture_output=True).returncode, 0)

    def test_uninstall_keeps_user_handlers_that_wrap_mmu(self):
        settings = self.root / ".claude" / "settings.json"
        settings.parent.mkdir()
        wrapper = {"type": "command",
                   "command": "./scripts/audit.sh && mmu hook --host claude --event pre-shell || notify-send blocked"}
        existing = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [wrapper]}], "Notification": []}}
        settings.write_text(json.dumps(existing), encoding="utf-8")
        _run(self.root, "--claude")
        self.assertEqual(self._load(".claude/settings.json")["hooks"]["PreToolUse"][0]["hooks"], [wrapper])
        _run(self.root, "--claude", "--uninstall")
        self.assertEqual(self._load(".claude/settings.json"), existing)

    def test_hooks_that_are_not_an_object_are_left_untouched(self):
        path = self.root / ".codex" / "hooks.json"
        path.parent.mkdir()
        text = json.dumps({"hooks": [{"command": "user.sh"}]})
        path.write_text(text, encoding="utf-8")
        code, out = _run(self.root, "--codex")
        self.assertEqual(code, 1)
        self.assertIn("`hooks` is not a JSON object; left untouched", out)
        self.assertEqual(path.read_text(encoding="utf-8"), text)

    def test_invalid_json_is_left_untouched(self):
        path = self.root / ".claude" / "settings.json"
        path.parent.mkdir()
        path.write_text('{"hooks": // comment\n', encoding="utf-8")
        code, out = _run(self.root, "--claude")
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", out)
        self.assertEqual(path.read_text(encoding="utf-8"), '{"hooks": // comment\n')

    def test_dry_run_writes_nothing(self):
        _git_init(self.root)
        code, out = _run(self.root, "--all", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would create", out)
        self.assertIn("mmu hook --host gemini --event stop", out)
        self.assertEqual([p.name for p in self.root.iterdir()], [".git"])
        self.assertFalse((self.root / ".git" / "hooks" / "pre-commit").exists())

    def test_default_command_and_target_detection(self):
        uvx = 'uvx --from "make-me-unicorn>=0.9" mmu hook'
        with mock.patch.object(install.shutil, "which", return_value="/usr/local/bin/mmu"), \
                mock.patch.object(install, "_supports_hook", return_value=True):
            self.assertEqual(install.default_command(), "mmu hook")
        with mock.patch.object(install.shutil, "which", return_value=None):
            self.assertEqual(install.default_command(), uvx)
        with mock.patch.object(install.shutil, "which", return_value="/usr/local/bin/mmu"), \
                mock.patch.object(install, "_supports_hook", return_value=False):
            self.assertEqual(install.default_command(), uvx, "an mmu older than 0.9 has no `hook` and exits 2")
        ephemeral = "/home/u/.cache/uv/archive-v0/AbC123/bin/mmu"
        with mock.patch.object(install.shutil, "which", return_value=ephemeral), \
                mock.patch.object(install, "_supports_hook", return_value=True):
            self.assertEqual(install.default_command(), uvx, "the mmu of a `uvx make-me-unicorn install` run is deleted later")
        self.assertTrue(install._is_ephemeral("/home/u/.local/pipx/.cache/0a1b/bin/mmu"))
        self.assertFalse(install._is_ephemeral("/home/u/.local/bin/mmu"))
        self.assertFalse(install._is_ephemeral("/home/u/.local/share/uv/tools/make-me-unicorn/bin/mmu"))
        # a custom UV_CACHE_DIR has no `uv` in its path (setup-uv, dev containers)
        self.assertTrue(install._is_ephemeral("/home/runner/work/_temp/setup-uv-cache/archive-v0/x/bin/mmu"))
        with mock.patch.dict(os.environ, {"UV_CACHE_DIR": "/tmp/ci-cache"}):
            self.assertTrue(install._is_ephemeral("/tmp/ci-cache/builds-v0/x/bin/mmu"))
            self.assertFalse(install._is_ephemeral("/usr/local/bin/mmu"))
        code, out = _run(self.root)
        self.assertEqual(code, 2)
        self.assertIn("nothing to install", out)
        (self.root / ".cursor").mkdir()
        self.assertEqual(_run(self.root)[0], 0)
        self.assertTrue((self.root / ".cursor" / "hooks.json").is_file())
        self.assertFalse((self.root / ".claude").exists())


class GitHookTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)
        _git_init(self.root)
        self.hook = self.root / ".git" / "hooks" / "pre-commit"

    def test_install_is_executable_and_idempotent(self):
        self.assertEqual(_run(self.root, "--git")[0], 0)
        self.assertTrue(self.hook.stat().st_mode & stat.S_IXUSR)
        self.assertIn(install.GIT_MARKER, self.hook.read_text(encoding="utf-8"))
        self.assertIn("mmu vibecheck --staged", self.hook.read_text(encoding="utf-8"))
        self.assertIn("already up to date", _run(self.root, "--git")[1])
        self.assertFalse((self.hook.parent / "pre-commit.pre-mmu").exists())
        _run(self.root, "--git", "--uninstall")
        self.assertFalse(self.hook.exists())

    def test_chains_existing_hook_and_restores_it(self):
        self.hook.parent.mkdir(parents=True, exist_ok=True)
        original = "#!/bin/sh\necho existing-hook-ran\nexit 7\n"
        self.hook.write_text(original, encoding="utf-8")
        self.hook.chmod(0o755)
        code, out = _run(self.root, "--git")
        self.assertEqual(code, 0)
        self.assertIn("run first", out)
        chained = self.hook.parent / "pre-commit.pre-mmu"
        self.assertEqual(chained.read_text(encoding="utf-8"), original)
        # the existing hook runs first and its failure wins
        proc = subprocess.run([str(self.hook)], capture_output=True, text=True, cwd=str(self.root))
        self.assertEqual(proc.returncode, 7)
        self.assertIn("existing-hook-ran", proc.stdout)
        _run(self.root, "--git")  # second install must not chain our own hook onto itself
        self.assertEqual(chained.read_text(encoding="utf-8"), original)
        self.assertEqual(_run(self.root, "--git", "--uninstall")[0], 0)
        self.assertEqual(self.hook.read_text(encoding="utf-8"), original)
        self.assertFalse(chained.exists())

    def test_hook_blocks_a_real_commit_and_fails_open_on_scanner_error(self):
        _run(self.root, "--git")
        bin_dir = self.root / "fakebin"
        bin_dir.mkdir()
        shim = bin_dir / "mmu"
        shim.write_text(f'#!/bin/sh\nPYTHONPATH="{REPO_ROOT / "src"}" exec "{sys.executable}" -m mmu_cli "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
        env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        env.pop("MMU_HOOK_DISABLE", None)
        (self.root / ".gitignore").write_text("fakebin/\n", encoding="utf-8")
        (self.root / "pay.py").write_text('KEY = "sk_live_' + "a1b2c3d4e5" * 3 + '"\n', encoding="utf-8")
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.test", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "add", "-A"], cwd=str(self.root), check=True, env=env)
        proc = subprocess.run([*git, "commit", "-m", "x"], cwd=str(self.root), capture_output=True, text=True, env=env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("P0 secrets pay.py:1", proc.stdout + proc.stderr)
        proc = subprocess.run([*git, "commit", "-m", "x"], cwd=str(self.root), capture_output=True, text=True,
                              env={**env, "MMU_HOOK_DISABLE": "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # scanner error (exit 2) must not block the commit
        shim.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
        (self.root / "b.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run([*git, "add", "-A"], cwd=str(self.root), check=True, env=env)
        proc = subprocess.run([*git, "commit", "-m", "y"], cwd=str(self.root), capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("could not run", proc.stderr)

    def test_hook_manager_directory_is_left_untouched(self):
        """husky dispatches on the hook's file name: moving its pre-commit aside silently stops the user's hook."""
        husky = self.root / ".husky" / "_"
        husky.mkdir(parents=True)
        stub = husky / "pre-commit"
        stub.write_text('#!/usr/bin/env sh\n. "$(dirname "$0")/h"\n', encoding="utf-8")
        subprocess.run(["git", "config", "core.hooksPath", ".husky/_"], cwd=str(self.root), check=True)
        code, out = _run(self.root, "--git")
        self.assertEqual(code, 1)
        self.assertIn("core.hooksPath is .husky/_", out)
        self.assertIn("mmu vibecheck --staged --format agent", out)
        self.assertEqual(sorted(p.name for p in husky.iterdir()), ["pre-commit"])
        self.assertNotIn(install.GIT_MARKER, stub.read_text(encoding="utf-8"))

    def test_not_a_repo_is_an_error(self):
        with tempfile.TemporaryDirectory() as plain:
            code, out = _run(Path(plain), "--git")
        self.assertEqual(code, 1)
        self.assertIn("not a git repository", out)


class AgentsMdTests(unittest.TestCase):
    def test_append_idempotent_and_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "AGENTS.md"
            path.write_text("# Agents\n\nUse pnpm.\n", encoding="utf-8")
            _run(root, "--agents-md")
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Agents\n\nUse pnpm.\n\n" + install.MD_START))
            self.assertIn("mmu vibecheck --changed --format agent", text)
            self.assertIn("mmu-ignore[<rule-id>]: <reason>", text)
            _run(root, "--agents-md")
            self.assertEqual(path.read_text(encoding="utf-8"), text)
            self.assertEqual(text.count(install.MD_START), 1)
            _run(root, "--agents-md", "--uninstall")
            self.assertEqual(path.read_text(encoding="utf-8"), "# Agents\n\nUse pnpm.\n")

    def test_created_file_is_removed_on_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _run(root, "--agents-md")
            self.assertTrue((root / "AGENTS.md").is_file())
            _run(root, "--agents-md", "--uninstall")
            self.assertFalse((root / "AGENTS.md").exists())


class AllTargetsTests(unittest.TestCase):
    def test_all_then_uninstall_all_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _git_init(root)
            self.assertEqual(_run(root, "--all")[0], 0)
            for rel in (".claude/settings.json", ".codex/hooks.json", ".cursor/hooks.json", ".gemini/settings.json",
                        ".git/hooks/pre-commit", "AGENTS.md", ".agents/skills/mmu-vibecheck/SKILL.md"):
                self.assertTrue((root / rel).is_file(), rel)
            code, out = _run(root, "--all")
            self.assertEqual(code, 0)
            self.assertEqual(out.count("already up to date"), 7)
            self.assertEqual(_run(root, "--all", "--uninstall")[0], 0)
            left = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git/" not in p.as_posix())
            self.assertEqual(left, [])
            self.assertFalse((root / ".agents").exists())
            self.assertFalse((root / ".git" / "hooks" / "pre-commit").exists())

    def test_skill_copy_matches_the_canonical_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(_run(root, "--skill")[0], 0)
            canonical = (REPO_ROOT / "skills" / "mmu-vibecheck" / "SKILL.md").read_text(encoding="utf-8")
            self.assertEqual((root / ".agents/skills/mmu-vibecheck/SKILL.md").read_text(encoding="utf-8"), canonical)
            self.assertEqual((REPO_ROOT / ".agents/skills/mmu-vibecheck/SKILL.md").read_text(encoding="utf-8"), canonical)
            self.assertEqual((REPO_ROOT / "src/mmu_cli/data/skills/mmu-vibecheck/SKILL.md").read_text(encoding="utf-8"), canonical)

    def test_skill_frontmatter_follows_the_agent_skills_spec(self):
        for name in ("mmu-vibecheck", "mmu-startup"):
            text = (REPO_ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            front = text.split("---")[1]
            fields = dict(line.split(": ", 1) for line in front.strip().splitlines() if ": " in line and not line.startswith(" "))
            with self.subTest(skill=name):
                self.assertEqual(fields["name"], name)
                self.assertRegex(fields["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
                self.assertLessEqual(len(fields["description"]), 1024)
                self.assertLess(len(text.splitlines()), 500)
        vibecheck = (REPO_ROOT / "skills/mmu-vibecheck/SKILL.md").read_text(encoding="utf-8")
        for trigger in ("webhook", "auth", "Stripe", "Supabase", "CORS", "env vars", "before committing", "done"):
            self.assertIn(trigger, vibecheck.split("---")[1])

    def test_pre_commit_framework_manifest(self):
        text = (REPO_ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
        self.assertIn("id: mmu-vibecheck", text)
        self.assertIn("entry: mmu vibecheck --staged", text)
        self.assertIn("pass_filenames: false", text)


if __name__ == "__main__":
    unittest.main()
