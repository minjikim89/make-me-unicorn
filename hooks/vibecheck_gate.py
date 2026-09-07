#!/usr/bin/env python3
"""Claude Code PreToolUse hook: run `mmu vibecheck` before `git commit` / `git push`.

Why a hook and not an MCP tool: agents reliably skip optional tools but cannot skip
a hook. With auto mode on by default, this is the last point where a human-visible
gate exists between "the agent wrote it" and "it is in the repo".

Contract (Claude Code hooks):
  stdin  — JSON with tool_name, tool_input.command, cwd
  exit 0 — allow. A JSON object on stdout with "systemMessage" shows a warning
           to the user (used when the scanner itself could not run).
  exit 2 — block; stderr is shown to the agent as the reason.
  A hook that exceeds its timeout is treated as "allow", so every subprocess
  here shares one deadline well under the 60s configured in hooks.json.

Zero dependencies. Uses the plugin's bundled `mmu_cli` (CLAUDE_PLUGIN_ROOT/src)
when set, otherwise an installed `mmu`.

Bypass:
  MMU_HOOK_DISABLE=1 in the hook's environment (Claude Code's env) — disables
  the gate for the session. The same assignment as a prefix on the command
  itself (`MMU_HOOK_DISABLE=1 git commit …`) — skips the gate for that one
  command; the hook recognises the prefix explicitly.
  MMU_HOOK_ON_PUSH_ONLY=1 — gate only pushes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

DEADLINE_SECONDS = 45  # hooks.json timeout is 60; leave headroom so we fail closed-loudly, not by timeout

# `git` as a word (not part of a path or another word), then any global options
# (-C dir, -c k=v, --git-dir=…, --no-pager, …), then the subcommand as a whole word.
# Env-var prefixes, subshells, `&&` chains and line continuations all still match;
# the trailing lookahead keeps `git commit-tree` / `git pushx` out.
_GIT_OPTS = r"(?:\s+(?:-[cC]\s+\S+|--[a-z-]+(?:=\S+)?|-\w+))*"
_GIT_CMD = re.compile(
    r"(?<![\w./-])git(?P<opts>" + _GIT_OPTS + r")\s+(?P<verb>commit|push)(?![\w-])(?P<rest>[^;&|\n]*)"
)
_GIT_C_PATH = re.compile(r"-C\s+(?:'([^']+)'|\"([^\"]+)\"|(\S+))")
_PER_COMMAND_DISABLE = re.compile(r"(?<![\w-])MMU_HOOK_DISABLE=1(?=\s)")
_NOOP_FLAGS = re.compile(r"(?<!\S)(?:--dry-run|--help|-h)(?!\S)")


def _gated_match(command: str) -> re.Match[str] | None:
    """Return the first commit/push match that should be gated, or None."""
    if os.environ.get("MMU_HOOK_DISABLE") == "1" or _PER_COMMAND_DISABLE.search(command):
        return None
    push_only = os.environ.get("MMU_HOOK_ON_PUSH_ONLY") == "1"
    for m in _GIT_CMD.finditer(command):
        if _NOOP_FLAGS.search(m.group("rest")):
            continue
        if m.group("verb") == "push" or not push_only:
            return m
    return None


def _should_gate(command: str) -> bool:
    return _gated_match(command) is not None


def _repo_root(cwd: str, match: re.Match[str] | None, deadline: float) -> Path:
    """Git toplevel for the command: honours `git -C <path>`, falls back to cwd."""
    start = Path(cwd)
    if match is not None:
        c = _GIT_C_PATH.search(match.group("opts"))
        if c:
            start = (start / (c.group(1) or c.group(2) or c.group(3))).expanduser()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start), capture_output=True, text=True, timeout=max(1.0, min(3.0, deadline - time.monotonic())),
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return start


def _launcher() -> tuple[list[str], dict[str, str]]:
    """One launcher, chosen up front: bundled source when the plugin root is known, else installed `mmu`."""
    env = dict(os.environ)
    plugin_root = env.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root and (Path(plugin_root) / "src" / "mmu_cli").is_dir():
        env["PYTHONPATH"] = str(Path(plugin_root) / "src") + os.pathsep + env.get("PYTHONPATH", "")
        return [sys.executable, "-m", "mmu_cli", "vibecheck", "--json"], env
    return ["mmu", "vibecheck", "--json"], env


def _run_vibecheck(root: Path, deadline: float) -> dict | str:
    """Return the parsed JSON result, or a short string saying why it could not run."""
    cmd, env = _launcher()
    remaining = deadline - time.monotonic()
    if remaining < 2:
        return "no time left before the hook deadline"
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=remaining, env=env, cwd=str(root))
    except FileNotFoundError:
        return "`mmu` is not installed and CLAUDE_PLUGIN_ROOT is not set"
    except subprocess.TimeoutExpired:
        return f"scan exceeded {int(remaining)}s on {root} (large tree? add build dirs to `doctor.skip_paths`)"
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["no output"]
        return f"scanner returned no JSON (exit {proc.returncode}): {tail[0][:120]}"
    return result if isinstance(result, dict) else "scanner returned unexpected JSON"


def _format_block(fails: list[dict], root: Path) -> str:
    lines = [f"mmu vibecheck: {len(fails)} launch-blocking issue(s) in {root} — commit blocked."]
    for f in fails[:6]:
        lines.append(f"  ✗ ({f.get('severity')}) {f.get('check')}: {f.get('message')}")
        for rel in f.get("files", [])[:3]:
            lines.append(f"      - {rel}")
        if f.get("hint"):
            lines.append(f"      ↳ {f['hint']}")
        if f.get("ref"):
            lines.append(f"      ↳ why: {f['ref']}")
    lines.append(
        "Fix the P0 findings, or run `mmu vibecheck` for the full report. If a finding is a false positive, "
        "prefix this one command with MMU_HOOK_DISABLE=1 and open an issue."
    )
    return "\n".join(lines)


def main() -> int:
    deadline = time.monotonic() + DEADLINE_SECONDS
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
    match = _gated_match(command)
    if match is None:
        return 0
    root = _repo_root(payload.get("cwd") or os.getcwd(), match, deadline)
    result = _run_vibecheck(root, deadline)
    if isinstance(result, str):
        # Fail open, but visibly: a systemMessage on stdout is shown to the user with exit 0.
        print(json.dumps({"systemMessage": f"mmu vibecheck gate did not run ({result}) — commit allowed unchecked."}))
        return 0
    fails = [f for f in result.get("findings", []) if f.get("status") == "fail"]
    if fails:
        print(_format_block(fails, root), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
