"""`mmu hook` — the launch gate as an agent hook, for Claude Code, Codex CLI, Cursor and Gemini CLI.

Why hooks: agents skip optional MCP tools but cannot skip a hook. One command reads the
host's JSON payload on stdin, works out which host and event it is, and answers in that
host's dialect.

Events
  pre-shell  before a shell command. Gates only `git commit` / `git push`.
             commit → `--staged` (or `--changed` when the commit takes working-tree
             content: -a/--all, pathspecs, or a `git add` chained in the same command);
             push → `--since @{u}` when an upstream exists, else the whole project.
  stop       the agent is about to say "done". Scans `--changed`; blocking findings send
             the agent back to work. Loop guards: the host's own flag (stop_hook_active /
             loop_count) plus a per-session cap (MMU_STOP_MAX, default 3) kept in the git dir.
  post-edit  after a file edit (Claude Code / Codex). Non-blocking: P0 findings located in
             the edited file are returned as additional context.

Policy: fail OPEN. If the scanner cannot run or runs out of time the action is allowed and
one visible line says so. Every subprocess shares one deadline below the host timeout.

Scanner contract: `mmu vibecheck --format json` (schema mmu.vibecheck/v1), exit 0 clean,
1 blocking, 2 scanner error. See docs/vibecheck-json-schema.md.

Bypass: MMU_HOOK_DISABLE=1 in the environment (all events) or as a prefix on one command;
MMU_HOOK_ON_PUSH_ONLY=1 gates only pushes; MMU_STOP_DISABLE=1 turns off the stop gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HOSTS = ("claude", "codex", "cursor", "gemini")
EVENTS = ("pre-shell", "stop", "post-edit")

# Host hook timeouts written by `mmu install` / hooks.json are 60s (15s for post-edit).
DEADLINE_SECONDS = 45.0
POST_EDIT_DEADLINE_SECONDS = 10.0
STOP_MAX_DEFAULT = 3
REASON_MAX_CHARS = 6000

# `git` as a word (not part of a path or another word), then any global options
# (-C dir, -c k=v, --git-dir=…, --no-pager, …), then the subcommand as a whole word.
# Env-var prefixes, subshells, `&&` chains and line continuations all still match;
# the trailing lookahead keeps `git commit-tree` / `git pushx` out.
_GIT_OPTS = r"(?:\s+(?:-[cC]\s+\S+|--[a-z-]+(?:=\S+)?|-\w+))*"
_GIT_CMD = re.compile(
    r"(?<![\w./-])git(?P<opts>" + _GIT_OPTS + r")\s+(?P<verb>commit|push)(?![\w-])(?P<rest>[^;&|\n]*)"
)
_GIT_ADD = re.compile(r"(?<![\w./-])git" + _GIT_OPTS + r"\s+(?:add|stage|rm|mv)(?![\w-])")
_GIT_C_PATH = re.compile(r"-C\s+(?:'([^']+)'|\"([^\"]+)\"|(\S+))")
_PER_COMMAND_DISABLE = re.compile(r"(?<![\w-])MMU_HOOK_DISABLE=1(?=\s)")
_NOOP_FLAGS = re.compile(r"(?<!\S)(?:--dry-run|--help|-h)(?!\S)")

# commit options that consume the next token (so it is not a pathspec)
_COMMIT_ARG_OPTS = {"-m", "-F", "-C", "-c", "-t", "--message", "--file", "--reuse-message", "--reedit-message",
                    "--template", "--author", "--date", "--fixup", "--squash", "--cleanup", "--pathspec-from-file",
                    "--trailer"}

_CODE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".mts", ".cjs", ".go", ".rb", ".php", ".java", ".kt", ".rs",
    ".cs", ".swift", ".dart", ".vue", ".svelte", ".sql", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg",
    ".conf", ".sh", ".tf", ".html",
}
_PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update) File: (.+)$", re.MULTILINE)


# --- command analysis --------------------------------------------------------

def gated_match(command: str) -> re.Match[str] | None:
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


def should_gate(command: str) -> bool:
    return gated_match(command) is not None


def _commit_takes_worktree(command: str, match: re.Match[str]) -> bool:
    """True when the commit will include content that is not staged yet at hook time."""
    if _GIT_ADD.search(command[: match.start()]):
        return True  # `git add -A && git commit …`: the hook runs before the add
    try:
        tokens = shlex.split(match.group("rest"))
    except ValueError:
        return True
    skip = False
    for tok in tokens:
        if skip:
            skip = False
            continue
        if tok == "--":
            return True  # everything after is a pathspec
        if tok in ("--all", "--include", "--only", "--interactive", "--patch"):
            return True
        if tok.startswith("--"):
            skip = tok in _COMMIT_ARG_OPTS
            continue
        if tok.startswith("-") and len(tok) > 1:
            cluster = tok[1:]
            for i, ch in enumerate(cluster):
                if ch in "aiop":
                    return True
                if ch in "mFCct":
                    skip = i == len(cluster) - 1  # `-m msg` consumes the next token; `-mmsg` does not
                    break
            continue
        return True  # a bare token is a pathspec: git commits that file's working-tree content
    return False


def _git(args: list[str], cwd: Path, deadline: float) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True,
            timeout=max(1.0, min(3.0, deadline - time.monotonic())),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def repo_root(cwd: str, match: re.Match[str] | None, deadline: float) -> Path:
    """Git toplevel for the command: honours `git -C <path>`, falls back to cwd."""
    start = Path(cwd)
    if match is not None:
        c = _GIT_C_PATH.search(match.group("opts"))
        if c:
            start = (start / (c.group(1) or c.group(2) or c.group(3))).expanduser()
    top = _git(["rev-parse", "--show-toplevel"], start, deadline)
    return Path(top) if top else start


def scope_for(command: str, match: re.Match[str], root: Path, deadline: float) -> list[str]:
    """`mmu vibecheck` scope flags for a gated commit/push."""
    if match.group("verb") == "commit":
        return ["--changed"] if _commit_takes_worktree(command, match) else ["--staged"]
    if _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], root, deadline):
        return ["--since", "@{u}"]
    return []


# --- scanner -----------------------------------------------------------------

def _launcher() -> tuple[list[str], dict[str, str]]:
    """Run the scanner from the same source tree as this module (installed package or plugin bundle)."""
    env = dict(os.environ)
    src = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return [sys.executable, "-m", "mmu_cli", "vibecheck"], env


def _run(args: list[str], root: Path, deadline: float) -> subprocess.CompletedProcess[str] | str:
    cmd, env = _launcher()
    remaining = deadline - time.monotonic()
    if remaining < 2:
        return "no time left before the hook deadline"
    try:
        return subprocess.run(
            [*cmd, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=remaining, env=env, cwd=str(root),
        )
    except FileNotFoundError:
        return "python interpreter for the scanner was not found"
    except subprocess.TimeoutExpired:
        return f"scan exceeded {int(remaining)}s on {root} (large tree? add build dirs to `doctor.skip_paths`)"
    except OSError as exc:
        return f"scanner could not start: {exc}"


def run_scan(root: Path, scope: list[str], deadline: float) -> dict[str, Any] | str:
    """Return the parsed v1 document, or a short string saying why the scan could not run."""
    proc = _run(["--format", "json", *scope], root, deadline)
    if isinstance(proc, str):
        return proc
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["no output"]
        return f"scanner returned no JSON (exit {proc.returncode}): {tail[0][:120]}"
    if not isinstance(result, dict):
        return "scanner returned unexpected JSON"
    error = result.get("error")
    if isinstance(error, dict):
        return f"scanner error: {str(error.get('message') or error.get('code') or 'unknown')[:160]}"
    if proc.returncode not in (0, 1):
        return f"scanner exited {proc.returncode}"
    return result


def blocking(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in result.get("findings", []) if isinstance(f, dict) and f.get("status") == "fail"]


def _places(finding: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for loc in finding.get("locations") or []:
        if isinstance(loc, dict) and loc.get("path"):
            out.append(f"{loc['path']}:{loc['line']}" if loc.get("line") else str(loc["path"]))
    return out or [str(rel) for rel in finding.get("files") or []]


def _fallback_reason(fails: list[dict[str, Any]]) -> str:
    """Reason text built from the JSON document, used when the `--format agent` rendering is unavailable."""
    lines: list[str] = []
    for f in fails[:8]:
        rule = f.get("rule_id") or f.get("check")
        places = _places(f)
        where = f" {places[0]}" if places else ""
        more = f" (+{len(places) - 1}: {', '.join(places[1:4])})" if len(places) > 1 else ""
        lines.append(f"{f.get('severity')} {rule}{where}{more}")
        lines.append(f"  what: {f.get('message')}")
        fix = f.get("fix") or f.get("hint")
        if fix:
            lines.append("  fix: " + " ".join(part.strip() for part in str(fix).splitlines()))
        lines.append(f"  silence (only if false positive): add `mmu-ignore[{rule}]: <reason>` on the flagged line")
    if len(fails) > 8:
        lines.append(f"… and {len(fails) - 8} more; run `mmu vibecheck --format agent` for all of them.")
    return "\n".join(lines)


def build_reason(headline: str, fails: list[dict[str, Any]], root: Path, scope: list[str], deadline: float,
                 footer: str) -> str:
    """Headline + the scanner's own `--format agent` text (path:line, rule, fix, how to silence) + footer."""
    body = ""
    proc = _run(["--format", "agent", *scope], root, deadline)
    if not isinstance(proc, str) and proc.returncode == 1 and proc.stdout.strip():
        body = proc.stdout.strip()
    if not body:
        body = _fallback_reason(fails)
    if len(body) > REASON_MAX_CHARS:
        body = body[:REASON_MAX_CHARS].rsplit("\n", 1)[0] + "\n… (truncated; run `mmu vibecheck --format agent` for the rest)"
    return f"{headline}\n{body}\n{footer}"


# --- host dialects -----------------------------------------------------------

def detect_host(payload: dict[str, Any]) -> str:
    event = str(payload.get("hook_event_name") or "")
    if event in ("BeforeTool", "AfterTool", "AfterAgent", "BeforeAgent"):
        return "gemini"
    if (event[:1].islower() and event) or "conversation_id" in payload or "workspace_roots" in payload \
            or "cursor_version" in payload:
        return "cursor"
    if "turn_id" in payload or payload.get("tool_name") == "apply_patch" \
            or "/.codex/" in str(payload.get("transcript_path") or "").replace("\\", "/"):
        return "codex"
    return "claude"


_EVENT_BY_NAME = {
    "PreToolUse": "pre-shell", "BeforeTool": "pre-shell", "beforeShellExecution": "pre-shell",
    "Stop": "stop", "SubagentStop": "stop", "AfterAgent": "stop", "stop": "stop",
    "PostToolUse": "post-edit", "AfterTool": "post-edit", "afterFileEdit": "post-edit",
}


def detect_event(payload: dict[str, Any]) -> str | None:
    name = str(payload.get("hook_event_name") or "")
    if name in _EVENT_BY_NAME:
        return _EVENT_BY_NAME[name]
    if "stop_hook_active" in payload or "loop_count" in payload:
        return "stop"
    if "tool_response" in payload:
        return "post-edit"
    if "tool_input" in payload or "command" in payload:
        return "pre-shell"
    return None


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def shell_command(payload: dict[str, Any], host: str) -> str:
    """The shell command of a pre-shell payload, or "" when the tool is not a shell."""
    if host == "cursor":
        return str(payload.get("command") or "")
    tool = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    if host == "gemini":
        if tool and tool != "run_shell_command":
            return ""
        if isinstance(tool_input.get("command"), str):
            return tool_input["command"]
        # The field name is not documented; look at every string the tool was given.
        return "\n".join(_strings(tool_input))
    if tool not in ("Bash", "shell", "local_shell", "exec_command", ""):
        return ""
    command = tool_input.get("command")
    if isinstance(command, list):
        return " ".join(str(part) for part in command)
    return str(command or "")


def edited_files(payload: dict[str, Any]) -> list[str]:
    tool_input = payload.get("tool_input")
    out: list[str] = []
    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "notebook_path"):
            if isinstance(tool_input.get(key), str):
                out.append(tool_input[key])
        for text in _strings(tool_input):
            out.extend(m.strip() for m in _PATCH_FILE.findall(text))
    if isinstance(payload.get("file_path"), str):
        out.append(payload["file_path"])
    return list(dict.fromkeys(out))


def payload_cwd(payload: dict[str, Any]) -> str:
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        return cwd
    roots = payload.get("workspace_roots")
    if isinstance(roots, list) and roots and isinstance(roots[0], str):
        return roots[0]
    return os.getcwd()


class Reply:
    """What to print and which code to exit with, in the host's dialect."""

    def __init__(self, host: str, event: str) -> None:
        self.host, self.event = host, event

    def _emit(self, obj: dict[str, Any] | None, code: int = 0, stderr: str = "") -> int:
        if stderr:
            print(stderr, file=sys.stderr)
        if obj is not None:
            print(json.dumps(obj, ensure_ascii=True))
        return code

    def allow(self, note: str = "") -> int:
        """Let the action through. `note` is one visible line for the user (scanner could not run)."""
        if self.host == "cursor":
            if self.event == "pre-shell":
                out: dict[str, Any] = {"permission": "allow"}
                if note:
                    out["user_message"] = note
                return self._emit(out)
            return self._emit({}, stderr=note)
        if self.host == "gemini":
            return self._emit({"systemMessage": note} if note else {})
        return self._emit({"systemMessage": note} if note else None)

    def block(self, reason: str) -> int:
        if self.event == "pre-shell":
            if self.host == "cursor":
                first = reason.splitlines()[0]
                return self._emit({"permission": "deny", "user_message": first, "agent_message": reason})
            if self.host == "gemini":
                return self._emit({"decision": "deny", "reason": reason})
            # Claude Code and Codex: exit 2, stderr is handed to the model as the denial reason.
            return self._emit(None, code=2, stderr=reason)
        if self.event == "stop":
            if self.host == "cursor":
                return self._emit({"followup_message": reason})
            if self.host == "gemini":
                return self._emit({"decision": "deny", "reason": reason})
            return self._emit({"decision": "block", "reason": reason})
        return self.context(reason)

    def context(self, text: str) -> int:
        """Non-blocking feedback after an edit."""
        if self.host in ("claude", "codex"):
            return self._emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}})
        if self.host == "gemini":
            return self._emit({"hookSpecificOutput": {"hookEventName": "AfterTool", "additionalContext": text}})
        return self._emit({})  # Cursor's afterFileEdit has no documented output contract


# --- stop-gate loop guard ----------------------------------------------------

def stop_max() -> int:
    try:
        return max(0, int(os.environ.get("MMU_STOP_MAX", STOP_MAX_DEFAULT)))
    except ValueError:
        return STOP_MAX_DEFAULT


def _state_file(root: Path, session: str, deadline: float) -> Path | None:
    git_dir = _git(["rev-parse", "--absolute-git-dir"], root, deadline)
    if not git_dir:
        return None
    digest = hashlib.sha256(session.encode("utf-8", "replace")).hexdigest()[:16]
    return Path(git_dir) / "mmu" / f"stop-{digest}.json"


def _stop_count(state: Path | None) -> int:
    if state is None:
        return 0
    try:
        return int(json.loads(state.read_text(encoding="utf-8")).get("blocks", 0))
    except (OSError, ValueError, AttributeError):
        return 0


def _stop_record(state: Path | None, count: int) -> None:
    if state is None:
        return
    try:
        if count <= 0:
            state.unlink(missing_ok=True)
            return
        state.parent.mkdir(parents=True, exist_ok=True)
        cutoff = time.time() - 7 * 86400
        for old in state.parent.glob("stop-*.json"):
            if old != state and old.stat().st_mtime < cutoff:
                old.unlink(missing_ok=True)
        state.write_text(json.dumps({"blocks": count, "updated": int(time.time())}), encoding="utf-8")
    except OSError:
        pass


# --- event handlers ----------------------------------------------------------

_SILENCE = (
    "If a finding is a false positive, add a `mmu-ignore[<rule-id>]: <reason>` comment on the flagged line "
    "(a marker without a reason is ignored)."
)


def handle_pre_shell(payload: dict[str, Any], reply: Reply) -> int:
    deadline = time.monotonic() + DEADLINE_SECONDS
    command = shell_command(payload, reply.host)
    match = gated_match(command) if command else None
    if match is None:
        return reply.allow()
    root = repo_root(payload_cwd(payload), match, deadline)
    scope = scope_for(command, match, root, deadline)
    verb = match.group("verb")
    result = run_scan(root, scope, deadline)
    if isinstance(result, str):
        return reply.allow(f"mmu vibecheck gate did not run ({result}) — {verb} allowed unchecked.")
    fails = blocking(result)
    if not fails:
        return reply.allow()
    reason = build_reason(
        f"mmu vibecheck: {len(fails)} launch-blocking issue(s) in {root} — {verb} blocked.",
        fails, root, scope, deadline,
        f"Fix the P0 findings, then retry the {verb}. {_SILENCE} "
        "To skip the gate for one command, prefix it with MMU_HOOK_DISABLE=1.",
    )
    return reply.block(reason)


def handle_stop(payload: dict[str, Any], reply: Reply) -> int:
    if os.environ.get("MMU_HOOK_DISABLE") == "1" or os.environ.get("MMU_STOP_DISABLE") == "1":
        return reply.allow()
    limit = stop_max()
    if limit == 0 or payload.get("stop_hook_active") is True:
        return reply.allow()  # host loop guard: we already sent the agent back once in this chain
    try:
        if int(payload.get("loop_count") or 0) >= limit:
            return reply.allow()
    except (TypeError, ValueError):
        pass
    deadline = time.monotonic() + DEADLINE_SECONDS
    root = repo_root(payload_cwd(payload), None, deadline)
    session = str(payload.get("session_id") or payload.get("conversation_id") or "default")
    state = _state_file(root, session, deadline)
    if state is None:
        return reply.allow()  # not a git repository: nothing to scope the scan to, stay quiet
    result = run_scan(root, ["--changed"], deadline)
    if isinstance(result, str):
        return reply.allow(f"mmu vibecheck stop gate did not run ({result}).")
    fails = blocking(result)
    count = _stop_count(state)
    if not fails:
        _stop_record(state, 0)
        return reply.allow()
    if count >= limit:
        return reply.allow(
            f"mmu vibecheck: {len(fails)} launch-blocking issue(s) remain in changed files; the stop gate has "
            f"already sent the agent back {count} time(s) this session (MMU_STOP_MAX={limit}), so it is letting go. "
            "Run `mmu vibecheck --changed` to see them."
        )
    _stop_record(state, count + 1)
    reason = build_reason(
        f"mmu vibecheck: not done yet — {len(fails)} launch-blocking issue(s) in uncommitted changes ({root}).",
        fails, root, ["--changed"], deadline,
        "Fix the P0 findings and re-run `mmu vibecheck --changed --format agent` until it reports 0 blocking "
        f"before telling the user the work is done. {_SILENCE}",
    )
    return reply.block(reason)


def handle_post_edit(payload: dict[str, Any], reply: Reply) -> int:
    if os.environ.get("MMU_HOOK_DISABLE") == "1" or reply.host == "cursor":
        return reply.allow()
    files = [f for f in edited_files(payload) if Path(f).suffix.lower() in _CODE_SUFFIXES or Path(f).name.startswith(".env")]
    if not files:
        return reply.allow()
    deadline = time.monotonic() + POST_EDIT_DEADLINE_SECONDS
    cwd = Path(payload_cwd(payload))
    first = Path(files[0])
    start = first.parent if first.is_absolute() and first.parent.is_dir() else cwd
    top = _git(["rev-parse", "--show-toplevel"], start, deadline)
    if not top:
        return reply.allow()
    root = Path(top)
    wanted: set[str] = set()
    for name in files:
        p = Path(name) if Path(name).is_absolute() else cwd / name
        try:
            wanted.add(p.resolve().relative_to(root.resolve()).as_posix())
        except ValueError:
            continue
    result = run_scan(root, ["--changed"], deadline)
    if isinstance(result, str) or not wanted:
        return reply.allow()  # feedback only; the commit and stop gates report scanner trouble
    lines: list[str] = []
    for f in blocking(result):
        locs = [loc for loc in f.get("locations") or [] if isinstance(loc, dict) and loc.get("path") in wanted]
        if not locs:
            continue
        rule = f.get("rule_id") or f.get("check")
        where = ", ".join(f"{loc['path']}:{loc['line']}" if loc.get("line") else str(loc["path"]) for loc in locs[:4])
        lines.append(f"P0 {rule} {where}")
        lines.append(f"  what: {f.get('message')}")
        fix = f.get("fix") or f.get("hint")
        if fix:
            lines.append("  fix: " + " ".join(part.strip() for part in str(fix).splitlines()))
    if not lines:
        return reply.allow()
    text = (
        "mmu vibecheck: the file you just edited has launch-blocking issue(s). They will block the commit; "
        "fix them now.\n" + "\n".join(lines) + f"\n{_SILENCE}"
    )
    return reply.context(text[:REASON_MAX_CHARS])


HANDLERS = {"pre-shell": handle_pre_shell, "stop": handle_stop, "post-edit": handle_post_edit}


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", choices=HOSTS, default=None, help="Agent host (default: detect from the payload)")
    parser.add_argument("--event", choices=EVENTS, default=None, help="Hook event (default: detect from the payload)")


def run(host: str | None = None, event: str | None = None, stdin: Any = None) -> int:
    """Read one hook payload from stdin, answer in the host's dialect. Never raises."""
    try:
        raw = (stdin or sys.stdin).read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError, OSError):
        payload = None
    if not isinstance(payload, dict):
        return Reply(host or "claude", event or "pre-shell").allow()
    host = host or detect_host(payload)
    event = event or detect_event(payload)
    if event is None:
        return Reply(host, "pre-shell").allow() if host in ("cursor", "gemini") else 0
    reply = Reply(host, event)
    try:
        return HANDLERS[event](payload, reply)
    except Exception as exc:  # noqa: BLE001 — a broken gate must never brick the agent
        return reply.allow(f"mmu hook crashed ({type(exc).__name__}: {str(exc)[:120]}) — action allowed unchecked.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mmu hook", description="Agent hook entry point for mmu vibecheck")
    add_arguments(parser)
    args, _ = parser.parse_known_args(argv)
    return run(args.host, args.event)


if __name__ == "__main__":
    sys.exit(main())
