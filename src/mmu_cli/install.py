"""`mmu install` — wire the vibecheck gate into agent hosts, git, and AGENTS.md.

Targets
  --claude     .claude/settings.json   PreToolUse(Bash) + Stop + PostToolUse(Edit|Write|MultiEdit)
  --codex      .codex/hooks.json       PreToolUse(Bash) + Stop + PostToolUse(apply_patch|Edit|Write)
  --cursor     .cursor/hooks.json      beforeShellExecution + stop
  --gemini     .gemini/settings.json   BeforeTool(run_shell_command) + AfterAgent
  --git        <git hooks dir>/pre-commit, chaining any existing hook
  --agents-md  AGENTS.md               a marked instruction block
  --skill      .agents/skills/mmu-vibecheck/SKILL.md   the Agent Skill (Codex and other agentskills.io hosts)

Every write is idempotent: our entries are recognised by the `hook --host <host> --event <event>`
tail of the command (JSON configs) or by a marker line (git hook, AGENTS.md), removed, and
re-added. `--uninstall` only removes. Existing settings are merged, never replaced; a config
file that is not valid JSON is left untouched and reported.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

TARGETS = ("claude", "codex", "cursor", "gemini", "git", "agents-md", "skill")
SKILL_REL = "skills/mmu-vibecheck/SKILL.md"
UVX_COMMAND = 'uvx --from "make-me-unicorn>=0.9" mmu hook'
_OURS = re.compile(r"\bhook --host (?:claude|codex|cursor|gemini) --event (?:pre-shell|stop|post-edit)\b")

GIT_MARKER = "# mmu-vibecheck pre-commit hook"
CHAINED_SUFFIX = ".pre-mmu"
GIT_HOOK = f"""#!/bin/sh
{GIT_MARKER} (managed by `mmu install --git`; remove with `mmu install --git --uninstall`)
hook_dir=$(dirname "$0")
if [ -x "$hook_dir/pre-commit{CHAINED_SUFFIX}" ]; then
  "$hook_dir/pre-commit{CHAINED_SUFFIX}" "$@" || exit $?
fi
[ "${{MMU_HOOK_DISABLE:-}}" = "1" ] && exit 0
if command -v mmu >/dev/null 2>&1; then
  mmu vibecheck --staged --format agent
elif command -v uvx >/dev/null 2>&1; then
  uvx --from "make-me-unicorn>=0.9" mmu vibecheck --staged --format agent
else
  echo "mmu vibecheck: mmu is not installed (pip install make-me-unicorn); commit allowed unchecked." >&2
  exit 0
fi
status=$?
if [ "$status" -ge 2 ]; then
  echo "mmu vibecheck: the scanner could not run (exit $status); commit allowed unchecked." >&2
  exit 0
fi
exit "$status"
"""

MD_START = "<!-- mmu-vibecheck:start -->"
MD_END = "<!-- mmu-vibecheck:end -->"
MD_BLOCK = f"""{MD_START}
## Launch gate (mmu vibecheck)

Before committing, opening a PR, or telling the user the work is done, run:

```
mmu vibecheck --changed --format agent
```

(`uvx make-me-unicorn vibecheck --changed --format agent` when `mmu` is not installed.)

- Exit 1 means P0 (launch-blocking) findings: fix each one at the reported `path:line`, then re-run until it reports 0 blocking.
- P1 findings are warnings; fix them when they are in scope.
- Never silence a finding to get past the gate. Only for a real false positive, add `mmu-ignore[<rule-id>]: <reason>` on the flagged line; a marker without a reason is not applied.
{MD_END}"""


MIN_HOOK_VERSION = (0, 9)


def _is_ephemeral(path: str) -> bool:
    """True for executables in a uvx/pipx run cache: they vanish, so a hook must not point at them."""
    parts = [p.lower() for p in Path(path).resolve().parts]
    uvx_run = "uv" in parts and any(p.startswith("archive-v") for p in parts)
    pipx_run = "pipx" in parts and ".cache" in parts
    return uvx_run or pipx_run


def _supports_hook(executable: str) -> bool:
    """True when this mmu understands `mmu hook` (0.9+). An older mmu exits 2 on it, which a host reads as a block."""
    try:
        proc = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return False
    match = re.search(r"(\d+)\.(\d+)", proc.stdout) if proc.returncode == 0 else None
    if match is None:
        return False
    return (int(match.group(1)), int(match.group(2))) >= MIN_HOOK_VERSION


def default_command() -> str:
    """`mmu hook` only for a persistent mmu new enough to run it; otherwise the uvx form."""
    found = shutil.which("mmu")
    if found and not _is_ephemeral(found) and _supports_hook(found):
        return "mmu hook"
    return UVX_COMMAND


# --- JSON hook configs -------------------------------------------------------

def _cmd(base: str, host: str, event: str) -> str:
    return f"{base} --host {host} --event {event}"


def _is_ours(handler: Any) -> bool:
    return isinstance(handler, dict) and bool(_OURS.search(str(handler.get("command") or "")))


def _strip_nested(hooks: dict[str, Any]) -> None:
    """Remove our handlers from a Claude/Codex/Gemini-style {event: [{matcher, hooks: [handler]}]} map."""
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept = []
        for group in groups:
            if isinstance(group, dict) and isinstance(group.get("hooks"), list):
                handlers = [h for h in group["hooks"] if not _is_ours(h)]
                if not handlers and len(handlers) != len(group["hooks"]):
                    continue
                group = {**group, "hooks": handlers}
            kept.append(group)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]


def _strip_flat(hooks: dict[str, Any]) -> None:
    """Remove our handlers from a Cursor-style {event: [handler]} map."""
    for event in list(hooks):
        if not isinstance(hooks[event], list):
            continue
        kept = [h for h in hooks[event] if not _is_ours(h)]
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]


def _nested_entries(host: str, base: str) -> dict[str, list[dict[str, Any]]]:
    def handler(event: str, timeout: int) -> dict[str, Any]:
        return {"type": "command", "command": _cmd(base, host, event), "timeout": timeout}

    if host == "gemini":
        def g(event: str, name: str) -> dict[str, Any]:
            # Gemini CLI hook timeouts are in milliseconds.
            return {"name": name, "type": "command", "command": _cmd(base, host, event), "timeout": 60000}

        return {
            "BeforeTool": [{"matcher": "run_shell_command", "hooks": [g("pre-shell", "mmu-gate")]}],
            "AfterAgent": [{"hooks": [g("stop", "mmu-stop-gate")]}],
        }
    edit_matcher = "Edit|Write|MultiEdit" if host == "claude" else "apply_patch|Edit|Write"
    return {
        "PreToolUse": [{"matcher": "Bash", "hooks": [handler("pre-shell", 60)]}],
        "Stop": [{"hooks": [handler("stop", 60)]}],
        "PostToolUse": [{"matcher": edit_matcher, "hooks": [handler("post-edit", 15)]}],
    }


def _apply_json(host: str, data: dict[str, Any], base: str, uninstall: bool) -> dict[str, Any]:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
    if host == "cursor":
        _strip_flat(hooks)
        if not uninstall:
            data.setdefault("version", 1)
            hooks.setdefault("beforeShellExecution", []).append(
                {"command": _cmd(base, host, "pre-shell"), "timeout": 60, "matcher": "git"}
            )
            hooks.setdefault("stop", []).append({"command": _cmd(base, host, "stop"), "timeout": 60})
    else:
        _strip_nested(hooks)
        if not uninstall:
            for event, groups in _nested_entries(host, base).items():
                hooks.setdefault(event, []).extend(groups)
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    return data


_JSON_PATHS = {
    "claude": ".claude/settings.json",
    "codex": ".codex/hooks.json",
    "cursor": ".cursor/hooks.json",
    "gemini": ".gemini/settings.json",
}
_NOTES = {
    "claude": "restart Claude Code or open /hooks once to load the new hooks",
    "codex": "Codex loads project hooks only in trusted projects",
    "cursor": "check Cursor Settings > Hooks to confirm they loaded",
    "gemini": "Gemini CLI asks to trust project hooks on next start",
}


def _plan_json(host: str, root: Path, base: str, uninstall: bool) -> dict[str, Any]:
    path = root / _JSON_PATHS[host]
    before = path.read_text(encoding="utf-8") if path.is_file() else None
    data: Any = {}
    if before is not None and before.strip():
        try:
            data = json.loads(before)
        except json.JSONDecodeError as exc:
            return {"target": host, "path": str(path), "action": "error",
                    "detail": f"not valid JSON ({exc.msg} at line {exc.lineno}); left untouched"}
        if not isinstance(data, dict):
            return {"target": host, "path": str(path), "action": "error",
                    "detail": "top level is not a JSON object; left untouched"}
    had_ours = bool(before and _OURS.search(before))
    data = _apply_json(host, data, base, uninstall)
    after: str | None = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if uninstall and not had_ours:
        return {"target": host, "path": str(path), "action": "unchanged", "detail": "not installed"}
    if uninstall and data in ({}, {"version": 1}):
        after = None  # the file only ever held our hooks
    if before is not None and after is not None and json.loads(before.strip() or "{}") == data:
        return {"target": host, "path": str(path), "action": "unchanged", "detail": "already up to date"}
    action = "remove" if uninstall else ("update" if before is not None else "create")
    return {"target": host, "path": str(path), "action": action, "content": after,
            "detail": "" if uninstall else _NOTES[host]}


# --- git pre-commit ----------------------------------------------------------

def _git_hooks_dir(root: Path) -> Path | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=str(root),
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    path = Path(out.stdout.strip())
    return path if path.is_absolute() else (root / path)


def _plan_git(root: Path, uninstall: bool) -> dict[str, Any]:
    hooks_dir = _git_hooks_dir(root)
    if hooks_dir is None:
        return {"target": "git", "path": str(root / ".git/hooks/pre-commit"), "action": "error",
                "detail": "not a git repository (or git is unavailable)"}
    path = hooks_dir / "pre-commit"
    chained = hooks_dir / f"pre-commit{CHAINED_SUFFIX}"
    before = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None
    ours = before is not None and GIT_MARKER in before
    plan: dict[str, Any] = {"target": "git", "path": str(path), "executable": True}
    if uninstall:
        if not ours:
            return {**plan, "action": "unchanged", "detail": "not installed"}
        if chained.exists():
            return {**plan, "action": "remove", "content": None, "restore_from": str(chained),
                    "detail": f"restores the previous hook from {chained.name}"}
        return {**plan, "action": "remove", "content": None, "detail": ""}
    if ours and before == GIT_HOOK:
        return {**plan, "action": "unchanged", "detail": "already up to date"}
    if before is not None and not ours:
        if chained.exists():
            return {**plan, "action": "error",
                    "detail": f"{chained.name} already exists; move it away or merge it into pre-commit first"}
        return {**plan, "action": "update", "content": GIT_HOOK, "move_to": str(chained),
                "detail": f"existing hook kept as {chained.name} and run first"}
    return {**plan, "action": "update" if ours else "create", "content": GIT_HOOK, "detail": ""}


# --- AGENTS.md ---------------------------------------------------------------

_MD_RE = re.compile(r"\n*" + re.escape(MD_START) + r".*?" + re.escape(MD_END) + r"\n?", re.DOTALL)


def _plan_agents_md(root: Path, uninstall: bool) -> dict[str, Any]:
    path = root / "AGENTS.md"
    before = path.read_text(encoding="utf-8") if path.is_file() else None
    plan: dict[str, Any] = {"target": "agents-md", "path": str(path)}
    stripped = _MD_RE.sub("\n", before).rstrip("\n") if before is not None else ""
    if uninstall:
        if before is None or MD_START not in before:
            return {**plan, "action": "unchanged", "detail": "not installed"}
        return {**plan, "action": "remove", "content": (stripped + "\n") if stripped.strip() else None, "detail": ""}
    after = (stripped + "\n\n" if stripped.strip() else "") + MD_BLOCK + "\n"
    if before == after:
        return {**plan, "action": "unchanged", "detail": "already up to date"}
    return {**plan, "action": "update" if before is not None else "create", "content": after, "detail": ""}


# --- Agent Skill -------------------------------------------------------------

def _plan_skill(root: Path, uninstall: bool) -> dict[str, Any]:
    path = root / ".agents" / SKILL_REL
    plan: dict[str, Any] = {"target": "skill", "path": str(path)}
    before = path.read_text(encoding="utf-8") if path.is_file() else None
    if uninstall:
        if before is None or "name: mmu-vibecheck" not in before:
            return {**plan, "action": "unchanged", "detail": "not installed"}
        return {**plan, "action": "remove", "content": None, "prune_empty_parents": 3, "detail": ""}
    from mmu_cli._data import find_content_root

    content_root = find_content_root()
    source = content_root / SKILL_REL if content_root else None
    if source is None or not source.is_file():
        return {**plan, "action": "error", "detail": "the bundled skill file is missing; reinstall make-me-unicorn"}
    after = source.read_text(encoding="utf-8")
    if before == after:
        return {**plan, "action": "unchanged", "detail": "already up to date"}
    return {**plan, "action": "update" if before is not None else "create", "content": after, "detail": ""}


# --- driver ------------------------------------------------------------------

def plan(root: Path, targets: list[str], base: str, uninstall: bool = False) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for target in targets:
        if target in _JSON_PATHS:
            out.append(_plan_json(target, root, base, uninstall))
        elif target == "git":
            out.append(_plan_git(root, uninstall))
        elif target == "agents-md":
            out.append(_plan_agents_md(root, uninstall))
        elif target == "skill":
            out.append(_plan_skill(root, uninstall))
    return out


def apply(steps: list[dict[str, Any]]) -> None:
    for step in steps:
        if step["action"] in ("unchanged", "error"):
            continue
        path = Path(step["path"])
        try:
            if step.get("move_to"):
                path.rename(step["move_to"])
            if step.get("content") is None:
                path.unlink(missing_ok=True)
                if step.get("restore_from"):
                    Path(step["restore_from"]).rename(path)
                parent = path.parent
                for _ in range(int(step.get("prune_empty_parents", 0))):
                    if not parent.is_dir() or any(parent.iterdir()):
                        break
                    parent.rmdir()
                    parent = parent.parent
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(step["content"], encoding="utf-8", newline="\n")
            if step.get("executable"):
                path.chmod(path.stat().st_mode | 0o755)
        except OSError as exc:
            step["action"], step["detail"] = "error", f"write failed: {exc}"


def detect_targets(root: Path) -> list[str]:
    found = [host for host, rel in _JSON_PATHS.items() if (root / rel).parent.is_dir()]
    if (root / "AGENTS.md").is_file():
        found.append("agents-md")
    return found


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--claude", action="store_true", help="Claude Code: .claude/settings.json")
    parser.add_argument("--codex", action="store_true", help="Codex CLI: .codex/hooks.json")
    parser.add_argument("--cursor", action="store_true", help="Cursor: .cursor/hooks.json")
    parser.add_argument("--gemini", action="store_true", help="Gemini CLI: .gemini/settings.json")
    parser.add_argument("--git", action="store_true", help="git pre-commit hook (chains an existing one)")
    parser.add_argument("--agents-md", action="store_true", help="Append the gate instructions to AGENTS.md")
    parser.add_argument("--skill", action="store_true", help="Copy the mmu-vibecheck Agent Skill to .agents/skills/")
    parser.add_argument("--all", action="store_true", help="Every target above")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned changes without writing")
    parser.add_argument("--uninstall", action="store_true", help="Remove what `mmu install` added")
    parser.add_argument(
        "--command", dest="hook_command", metavar="CMD", default=None,
        help=f"Hook command to register (default: `mmu hook` when mmu is on PATH, else `{UVX_COMMAND}`)",
    )


def run(args: argparse.Namespace, root: Path) -> int:
    as_json = bool(getattr(args, "json", False))
    targets = list(TARGETS) if args.all else [t for t in TARGETS if getattr(args, t.replace("-", "_"))]
    if not targets:
        targets = detect_targets(root)
        if not targets:
            msg = ("nothing to install: pass --claude, --codex, --cursor, --gemini, --git, --agents-md, --skill or --all "
                   f"(no agent config directory found in {root})")
            print(json.dumps({"error": msg}) if as_json else f"mmu install: {msg}")
            return 2
    base = args.hook_command or default_command()
    try:
        shlex.split(base)
    except ValueError as exc:
        print(f"mmu install: --command is not a valid shell command: {exc}")
        return 2
    steps = plan(root, targets, base, uninstall=args.uninstall)
    if not args.dry_run:
        apply(steps)
    if as_json:
        public = [{k: v for k, v in s.items() if k not in ("content", "executable", "prune_empty_parents")} for s in steps]
        print(json.dumps({"dry_run": args.dry_run, "uninstall": args.uninstall, "command": base, "steps": public},
                         indent=2))
    else:
        verb = {"create": "create", "update": "update", "remove": "remove", "unchanged": "ok", "error": "ERROR"}
        prefix = "would " if args.dry_run else ""
        for s in steps:
            label = verb[s["action"]]
            head = f"{prefix}{label}" if s["action"] in ("create", "update", "remove") else label
            detail = f"  ({s['detail']})" if s.get("detail") else ""
            print(f"[{s['target']}] {head} {s['path']}{detail}")
            if args.dry_run and s.get("content") and s["action"] in ("create", "update"):
                for line in s["content"].rstrip("\n").splitlines():
                    print(f"    {line}")
        if not args.uninstall and any(s["target"] in _JSON_PATHS for s in steps):
            print(f"hook command: {base}")
    return 1 if any(s["action"] == "error" for s in steps) else 0
