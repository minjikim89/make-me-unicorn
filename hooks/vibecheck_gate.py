#!/usr/bin/env python3
"""Claude Code PreToolUse hook: run `mmu vibecheck` before `git commit` / `git push`.

Why a hook and not an MCP tool: agents reliably skip optional tools but cannot skip
a hook. With auto mode on by default, this is the last point where a human-visible
gate exists between "the agent wrote it" and "it is in the repo".

Contract (Claude Code hooks):
  stdin  — JSON with tool_name, tool_input.command, cwd
  exit 0 — allow (stdout is ignored for PreToolUse unless JSON)
  exit 2 — block; stderr is shown to the agent as the reason

Zero dependencies: uses the bundled mmu_cli from the plugin root when the CLI is
not installed. Set MMU_HOOK_DISABLE=1 to bypass, MMU_HOOK_ON_PUSH_ONLY=1 to gate
only pushes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# `git` as a word, then any number of global options (-C dir, -c k=v, --git-dir=…,
# --no-pager, …), then the subcommand as a whole word. Env-var prefixes
# (`FOO=1 git commit`), subshells, and chained commands all still match; a word
# boundary that is not a hyphen keeps `git commit-tree` / `git push-x` out.
_GIT_OPTS = r"(?:\s+(?:-[cC]\s+\S+|--[a-z-]+(?:=\S+)?|-\w+))*"
_GIT_COMMIT = re.compile(r"(?<![\w./-])git" + _GIT_OPTS + r"\s+commit(?![\w-])")
_GIT_PUSH = re.compile(r"(?<![\w./-])git" + _GIT_OPTS + r"\s+push(?![\w-])")


def _should_gate(command: str) -> bool:
    if os.environ.get("MMU_HOOK_DISABLE") == "1":
        return False
    if _GIT_PUSH.search(command):
        return True
    if os.environ.get("MMU_HOOK_ON_PUSH_ONLY") == "1":
        return False
    return bool(_GIT_COMMIT.search(command))


def _repo_root(cwd: str) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return Path(cwd)


def _run_vibecheck(root: Path) -> dict | None:
    """Prefer an installed `mmu`; fall back to the plugin's bundled source."""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    candidates: list[list[str]] = [["mmu", "vibecheck", "--json", "--root", str(root)]]
    if plugin_root:
        candidates.append([sys.executable, "-m", "mmu_cli", "vibecheck", "--json", "--root", str(root)])
    env = dict(os.environ)
    if plugin_root:
        env["PYTHONPATH"] = str(Path(plugin_root) / "src") + os.pathsep + env.get("PYTHONPATH", "")
    for cmd in candidates:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=50, env=env, cwd=str(root))
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return None
        if proc.stdout.strip().startswith("{"):
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                continue
    return None


def _format_block(result: dict, root: Path) -> str:
    fails = [f for f in result.get("findings", []) if f.get("status") == "fail"]
    lines = [f"mmu vibecheck: {len(fails)} launch-blocking issue(s) in {root} — commit blocked."]
    for f in fails[:6]:
        lines.append(f"  ✗ ({f.get('severity')}) {f.get('check')}: {f.get('message')}")
        for rel in f.get("files", [])[:3]:
            lines.append(f"      - {rel}")
        if f.get("hint"):
            lines.append(f"      ↳ {f['hint']}")
        if f.get("ref"):
            lines.append(f"      ↳ why: {f['ref']}")
    lines.append("Fix the P0 findings, or run `mmu vibecheck` for the full report. "
                 "Bypass once with MMU_HOOK_DISABLE=1 if a finding is a false positive (and open an issue).")
    return "\n".join(lines)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    command = str(tool_input.get("command") or "")
    if not _should_gate(command):
        return 0
    root = _repo_root(payload.get("cwd") or os.getcwd())
    result = _run_vibecheck(root)
    if result is None:
        # Never block on our own failure; say so quietly on stderr (exit 0 = allow).
        print("mmu vibecheck hook: could not run the scanner (mmu not installed?) — allowing.", file=sys.stderr)
        return 0
    if any(f.get("status") == "fail" for f in result.get("findings", [])):
        print(_format_block(result, root), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
