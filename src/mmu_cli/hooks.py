"""`mmu hook` — the launch gate as an agent hook, for Claude Code, Codex CLI, Cursor and Gemini CLI.

Why hooks: agents skip optional MCP tools but cannot skip a hook. One command reads the
host's JSON payload on stdin, works out which host and event it is, and answers in that
host's dialect.

Events
  pre-shell  before a shell command. Gates only `git commit` / `git push` in command position.
             commit → `--staged`, or exactly the files it records when that differs
             (-a/--all, pathspecs, a `git add` earlier in the same command);
             push → the files touched by commits no remote-tracking ref has yet (the whole
             project when the repository has no remote-tracking refs at all).
  stop       the agent is about to say "done". Scans `--changed`; blocking findings send
             the agent back to work. On Claude Code and Codex only findings in files the
             agent edited in this session count (recorded by post-edit); no recorded edits,
             no block. Cursor and Gemini count every uncommitted change. Loop guards: the
             host's own flag (stop_hook_active / loop_count) plus a per-session cap
             (MMU_STOP_MAX, default 3) kept in the git dir.
  post-edit  after a file edit (Claude Code / Codex). Non-blocking: P0 findings located in
             the edited file are returned as additional context.

Policy: fail OPEN. If the scanner cannot run or runs out of time the action is allowed and
one visible line says so. Every subprocess shares one deadline below the host timeout.
Every decision, blocks included, is JSON on stdout with exit 0: a host reads exit 2 as a block,
and a launcher failure (an old `mmu`, `uvx` offline) must never look like one.

Scanner contract: `mmu vibecheck --format json` (schema mmu.vibecheck/v1), exit 0 clean,
1 blocking, 2 scanner error. See docs/vibecheck-json-schema.md.

Bypass: MMU_HOOK_DISABLE=1 in the environment (all events) or as a prefix on one command
(`MMU_HOOK_DISABLE=1 git commit ...`, or exported earlier in the same command);
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HOSTS = ("claude", "codex", "cursor", "gemini")
EVENTS = ("pre-shell", "stop", "post-edit")

# Host hook timeouts written by `mmu install` / hooks.json are 60s (15s for post-edit).
DEADLINE_SECONDS = 45.0
POST_EDIT_DEADLINE_SECONDS = 10.0
STOP_MAX_DEFAULT = 3
REASON_MAX_CHARS = 6000

# Fallback for a command the parser below cannot split (unbalanced quotes): the old text search.
_GIT_FALLBACK = re.compile(r"(?<![\w./-])git(?:\s+-\S+(?:\s+\S+)?)*?\s+(?P<verb>commit|push)(?![\w-])")

# commit options that consume the next token (so it is not a pathspec)
_COMMIT_ARG_OPTS = {"-m", "-F", "-C", "-c", "-t", "--message", "--file", "--reuse-message", "--reedit-message",
                    "--template", "--author", "--date", "--fixup", "--squash", "--cleanup", "--pathspec-from-file",
                    "--trailer"}
_COMMIT_NOOP = {"--dry-run", "-h", "--help", "--short", "--porcelain", "--long"}
_PUSH_ARG_OPTS = {"--repo", "--receive-pack", "--exec", "-o", "--push-option"}
_PUSH_NOOP = {"--dry-run", "-n", "-h", "--help", "--delete", "-d"}

_CODE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".mts", ".cjs", ".go", ".rb", ".php", ".java", ".kt", ".rs",
    ".cs", ".swift", ".dart", ".vue", ".svelte", ".sql", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg",
    ".conf", ".sh", ".tf", ".html",
}
_PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update) File: (.+)$", re.MULTILINE)
_TRUTHY = {"1", "true", "yes", "on"}


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUTHY


def env_on(name: str) -> bool:
    return _truthy(os.environ.get(name))


# --- command analysis --------------------------------------------------------
#
# The command is split the way a POSIX shell splits it, not searched as text: only a `git commit`
# or `git push` in command position is gated, so `echo "git commit"`, a comment, a heredoc body or a
# commit message that mentions `--help` decides nothing. `cd`/`pushd`, `git -C`, `--git-dir` and
# `--work-tree` move the target repository; `bash -c '...'` and `eval` are followed; env prefixes,
# wrappers (`env`, `sudo`, `command`, `time`, ...) and redirections are skipped.
# Not followed: a variable in command position (`$GIT commit`) and git aliases.

_PUNCT = ";&|()<>\n"
_OPERATORS = ("<<<", "&&", "||", ";;", ">>", "<<", ">&", "<&", "&>", ">|", ";", "&", "|", "(", ")", "<", ">", "\n")
_SEPARATORS = {"&&", "||", ";;", ";", "&", "|", "\n"}
_REDIRECTS = {"<<<", ">>", "<<", ">&", "<&", "&>", ">|", "<", ">"}
_RESERVED = {"if", "then", "else", "elif", "do", "while", "until", "!", "{", "}", "fi", "done", "esac"}
_WRAPPER_ARGS: dict[str, set[str]] = {
    "sudo": {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U"}, "doas": {"-u", "-C"},
    "env": {"-u", "-C", "-S"}, "nice": {"-n"}, "timeout": {"-s", "-k"}, "exec": {"-a"}, "time": {"-f", "-o"},
    "command": set(), "builtin": set(), "nohup": set(),
}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "ash"}
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_GIT_ARG_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix",
                 "--list-cmds"}
_ADD_VERBS = {"add", "stage"}
_ADD_INTERACTIVE = {"-p", "--patch", "-i", "--interactive", "-e", "--edit"}


@dataclass
class GitCall:
    """One `git` invocation found in a shell command."""

    verb: str
    args: list[str]
    cwd: Path                 # where git runs (after `cd` and `-C`)
    start: Path               # where to look for the repository (`--work-tree` / `--git-dir` win)
    disabled: bool = False    # MMU_HOOK_DISABLE=1 set for this command
    adds: list[tuple[Path, list[str]]] = field(default_factory=list)  # `git add` calls earlier in the command
    unparsed: bool = False    # found by the text fallback: scope is a superset


def _strip_shell_noise(command: str) -> str:
    """Drop what a shell never runs as words: line continuations, comments and heredoc bodies."""
    out: list[str] = []
    i, n = 0, len(command)
    quote = ""
    heredocs: list[str] = []
    word_start = True
    while i < n:
        ch = command[i]
        if quote == "'":
            out.append(ch)
            quote = "" if ch == "'" else quote
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            if command[i + 1] == "\n":
                i += 2
                continue
            out.append(command[i:i + 2])
            i += 2
            word_start = False
            continue
        if quote == '"':
            out.append(ch)
            quote = "" if ch == '"' else quote
            i += 1
            continue
        if ch in "'\"":
            quote = ch
        elif ch == "#" and word_start:
            end = command.find("\n", i)
            i = n if end < 0 else end
            continue
        elif command.startswith("<<", i) and not command.startswith("<<<", i):
            j = i + (3 if command.startswith("<<-", i) else 2)
            while j < n and command[j] in " \t":
                j += 1
            k = j
            while k < n and command[k] not in " \t\n;&|()<>":
                k += 1
            delim = re.sub(r"[\"'\\]", "", command[j:k])
            if delim:
                heredocs.append(delim)
            out.append(command[i:k])
            i, word_start = k, False
            continue
        elif ch == "\n" and heredocs:
            out.append(ch)
            i += 1
            for delim in heredocs:
                while i < n:
                    end = command.find("\n", i)
                    line = command[i:n if end < 0 else end]
                    i = n if end < 0 else end + 1
                    if line.strip() == delim:
                        break
            heredocs, word_start = [], True
            continue
        out.append(ch)
        i += 1
        word_start = ch in " \t\n;&|()<>"
    return "".join(out)


def _tokens(command: str) -> list[str]:
    """Shell words and operators. Raises ValueError on unbalanced quotes."""
    lex = shlex.shlex(_strip_shell_noise(command), posix=True, punctuation_chars=_PUNCT)
    lex.whitespace, lex.whitespace_split, lex.commenters = " \t\r", True, ""
    out: list[str] = []
    for tok in lex:
        if tok and all(c in _PUNCT for c in tok):
            while tok:
                op = next(o for o in _OPERATORS if tok.startswith(o))
                out.append(op)
                tok = tok[len(op):]
        else:
            out.append(tok)
    return out


def _command_words(words: list[str]) -> tuple[dict[str, str], list[str]]:
    """(leading assignments, the command and its arguments), redirections and wrappers removed."""
    plain: list[str] = []
    i = 0
    while i < len(words):
        if words[i] in _REDIRECTS:
            i += 2
        elif words[i].isdigit() and i + 1 < len(words) and words[i + 1] in _REDIRECTS:
            i += 1
        else:
            plain.append(words[i])
            i += 1
    assigns: dict[str, str] = {}
    i = 0
    while i < len(plain):
        word = plain[i]
        wrapper = os.path.basename(word)
        if _ASSIGNMENT.match(word):
            name, _, value = word.partition("=")
            assigns[name] = value
            i += 1
        elif word in _RESERVED:
            i += 1
        elif wrapper in _WRAPPER_ARGS:
            i += 1
            while i < len(plain) and plain[i].startswith("-") and plain[i] != "-":
                i += 2 if plain[i] in _WRAPPER_ARGS[wrapper] else 1
            if wrapper == "timeout" and i < len(plain):
                i += 1  # the duration
        else:
            break
    return assigns, plain[i:]


def _shell_script(args: list[str]) -> str | None:
    """The script of `sh -c '<script>'` (also `bash -lc`, `-ec`, `-o pipefail -c`)."""
    has_c = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-o", "+o"):
            i += 2
            continue
        if arg.startswith("-") and not arg.startswith("--"):
            has_c = has_c or "c" in arg[1:]
            i += 1
            continue
        if arg.startswith("--"):
            i += 1
            continue
        return arg if has_c else None
    return None


def _git_call(args: list[str], here: Path, disabled: bool) -> GitCall:
    c_dir, git_dir, work_tree = here, "", ""
    help_only = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _GIT_ARG_OPTS:
            value = args[i + 1] if i + 1 < len(args) else ""
            if arg == "-C" and value:
                c_dir = c_dir / os.path.expanduser(value)
            elif arg == "--git-dir":
                git_dir = value
            elif arg == "--work-tree":
                work_tree = value
            i += 2
            continue
        if arg.startswith("--git-dir="):
            git_dir = arg.split("=", 1)[1]
        elif arg.startswith("--work-tree="):
            work_tree = arg.split("=", 1)[1]
        elif arg in ("-h", "--help", "--version", "-v"):
            help_only = True
        elif not arg.startswith("-"):
            break
        i += 1
    start = c_dir
    if work_tree:
        start = c_dir / os.path.expanduser(work_tree)
    elif git_dir:
        gd = c_dir / os.path.expanduser(git_dir)
        start = gd.parent if gd.name == ".git" else gd
    verb = "" if help_only or i >= len(args) else args[i]
    return GitCall(verb=verb, args=args[i + 1:], cwd=c_dir, start=start, disabled=disabled)


def git_calls(command: str, cwd: str | Path = ".", _depth: int = 0) -> list[GitCall]:
    """Every git invocation in `command`, in order, with the directory it runs in. Raises ValueError."""
    calls: list[GitCall] = []
    here = Path(cwd)
    saved: list[tuple[Path, dict[str, str]]] = []  # a subshell's cd and export do not leak out of it
    exported: dict[str, str] = {}
    words: list[str] = []
    for tok in [*_tokens(command), "\n"]:
        if tok not in _SEPARATORS and tok not in ("(", ")"):
            words.append(tok)
            continue
        if words:
            here = _simple_command(words, here, exported, calls, _depth)
            words = []
        if tok == "(":
            saved.append((here, dict(exported)))
        elif tok == ")" and saved:
            here, outer = saved.pop()
            exported.clear()
            exported.update(outer)
    return calls


def _simple_command(words: list[str], here: Path, exported: dict[str, str], calls: list[GitCall],
                    depth: int) -> Path:
    """Record the git call in one simple command; return the working directory after it."""
    assigns, cmd = _command_words(words)
    if not cmd:
        return here
    name = os.path.basename(cmd[0].replace("\\", "/"))
    args = cmd[1:]
    if name in ("cd", "pushd"):
        target = next((a for a in args if not a.startswith("-") or a == "-"), "~")
        return here if target == "-" or "$" in target else here / os.path.expanduser(target)
    if name == "export":
        for arg in args:
            if _ASSIGNMENT.match(arg):
                key, _, value = arg.partition("=")
                exported[key] = value
        return here
    disabled = _truthy(assigns.get("MMU_HOOK_DISABLE", exported.get("MMU_HOOK_DISABLE")))
    script = " ".join(args) if name == "eval" else _shell_script(args) if name in _SHELLS else None
    if script is not None and depth < 3:
        for call in git_calls(script, here, depth + 1):
            call.disabled = call.disabled or disabled
            calls.append(call)
        return here
    if name in ("git", "git.exe"):
        calls.append(_git_call(args, here, disabled))
    return here


@dataclass
class _Commit:
    options: set[str]
    paths: list[str]


def _parse_commit(args: list[str]) -> _Commit:
    options: set[str] = set()
    paths: list[str] = []
    i = 0
    while i < len(args):
        tok = args[i]
        i += 1
        if tok == "--":
            paths.extend(args[i:])
            break
        if tok.startswith("--"):
            name = tok.split("=", 1)[0]
            options.add(name)
            if name in _COMMIT_ARG_OPTS and "=" not in tok:
                i += 1
            continue
        if tok.startswith("-") and len(tok) > 1:
            cluster = tok[1:]
            for j, ch in enumerate(cluster):
                options.add("-" + ch)
                if ch in "mFCct":
                    i += 1 if j == len(cluster) - 1 else 0  # `-m msg` takes the next token; `-mmsg` does not
                    break
                if ch in "Su":
                    break  # optional value attached: `-S<keyid>`, `-uno`
            continue
        paths.append(tok)
    return _Commit(options, paths)


def _parse_push(args: list[str]) -> tuple[set[str], list[str]]:
    options: set[str] = set()
    positional: list[str] = []
    i = 0
    while i < len(args):
        tok = args[i]
        i += 1
        if tok == "--":
            positional.extend(args[i:])
            break
        if tok.startswith("--"):
            name = tok.split("=", 1)[0]
            options.add(name)
            if name in _PUSH_ARG_OPTS and "=" not in tok:
                i += 1
            continue
        if tok.startswith("-") and len(tok) > 1:
            options.update("-" + ch for ch in tok[1:])
            if tok == "-o":
                i += 1
            continue
        positional.append(tok)
    return options, positional


def _push_revs(options: set[str], positional: list[str]) -> list[str] | None:
    """Revisions whose commits the push sends; None when it only deletes."""
    revs: list[str] = []
    if options & {"--all", "--branches", "--mirror"}:
        revs.append("--branches")
    if "--tags" in options:
        revs.append("--tags")
    refspecs = positional[1:]
    i = 0
    while i < len(refspecs):
        spec = refspecs[i]
        i += 1
        if spec == "tag" and i < len(refspecs):
            revs.append("refs/tags/" + refspecs[i])
            i += 1
            continue
        src = spec.lstrip("+").split(":", 1)[0]
        if src:
            revs.append("--branches" if "*" in src else src)
    if refspecs and not revs:
        return None
    return revs or ["HEAD"]


def _is_noop(call: GitCall) -> bool:
    if call.verb == "commit":
        return bool(_parse_commit(call.args).options & _COMMIT_NOOP)
    options, positional = _parse_push(call.args)
    return bool(options & _PUSH_NOOP) or _push_revs(options, positional) is None


def gated_call(command: str, cwd: str | Path = ".") -> GitCall | None:
    """The first `git commit` / `git push` in `command` that the gate checks, or None."""
    if env_on("MMU_HOOK_DISABLE"):
        return None
    push_only = env_on("MMU_HOOK_ON_PUSH_ONLY")
    try:
        calls = git_calls(command, cwd)
    except ValueError:
        m = _GIT_FALLBACK.search(command)
        if m is None or (push_only and m.group("verb") == "commit"):
            return None
        return GitCall(verb=m.group("verb"), args=[], cwd=Path(cwd), start=Path(cwd), unparsed=True)
    adds: list[tuple[Path, list[str]]] = []
    for call in calls:
        if call.verb in _ADD_VERBS:
            adds.append((call.cwd, call.args))
            continue
        if call.verb not in ("commit", "push") or call.disabled or _is_noop(call):
            continue
        if call.verb == "commit" and push_only:
            continue
        call.adds = adds
        return call
    return None


def should_gate(command: str) -> bool:
    return gated_call(command) is not None


def _git_out(args: list[str], cwd: Path, deadline: float, cap: float = 3.0) -> str | None:
    """stdout of a git command (may be empty), or None when it failed or could not run."""
    try:
        out = subprocess.run(
            # core.fsmonitor=false: never let the repository's own config run a command through the hook.
            ["git", "-c", "core.fsmonitor=false", *args], cwd=str(cwd), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=max(1.0, min(cap, deadline - time.monotonic())),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _git(args: list[str], cwd: Path, deadline: float) -> str | None:
    out = _git_out(args, cwd, deadline)
    return out.strip() if out and out.strip() else None


def _names(args: list[str], cwd: Path, deadline: float, cap: float = 3.0) -> set[str] | None:
    out = _git_out(args, cwd, deadline, cap)
    return None if out is None else {p for p in out.split("\0") if p.strip()}


def repo_root(call: GitCall, deadline: float) -> Path:
    """Git toplevel for the call (after `cd`, `-C`, `--work-tree`), falling back to where it starts."""
    top = _git(["rev-parse", "--show-toplevel"], call.start, deadline)
    return Path(top) if top else call.start


@dataclass
class Scope:
    """`mmu vibecheck` scope flags, plus the file list fed on stdin for `--files-from -`."""

    flags: list[str]
    files: list[str] | None = None

    @classmethod
    def listed(cls, files: set[str]) -> Scope:
        return cls(["--files-from", "-"], sorted(files))

    def stdin(self) -> str:
        return "".join(f"{p}\n" for p in self.files or [])


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return False
    return True


_DIFF_NAMES = ["--name-only", "-z", "--no-relative", "--diff-filter=d"]
_ADDED = re.compile(r"^add '(.*)'$")


def _commit_scope(call: GitCall, root: Path, deadline: float) -> Scope:
    """Exactly the files the commit records, when that differs from what is staged now."""
    commit = _parse_commit(call.args)
    opts = commit.options
    takes_all = bool(opts & {"-a", "--all"})
    if call.unparsed:
        return Scope(["--changed"])
    if not (takes_all or commit.paths or call.adds or opts & {"-p", "--patch", "--interactive",
                                                               "--pathspec-from-file"}):
        return Scope(["--staged"])
    if opts & {"-p", "--patch", "--interactive", "--pathspec-from-file"}:
        return Scope(["--changed"])
    staged = _names(["diff", "--cached", *_DIFF_NAMES], root, deadline)
    if staged is None:
        return Scope(["--changed"])
    # `git commit <paths>` records only those paths; staged changes elsewhere stay out (unless --include)
    files = set(staged) if not commit.paths or opts & {"-i", "--include"} else set()
    for add_cwd, add_args in call.adds:
        if set(add_args) & _ADD_INTERACTIVE:
            return Scope(["--changed"])
        top = _git(["rev-parse", "--show-toplevel"], add_cwd, deadline)
        if top is None or Path(top).resolve() != root.resolve():
            continue  # another repository
        out = _git_out(["add", "--dry-run", *add_args], add_cwd, deadline, cap=10.0) or ""
        files.update(m.group(1) for m in map(_ADDED.match, out.splitlines()) if m)
    if takes_all:
        tracked = _names(["diff", *_DIFF_NAMES], root, deadline)
        if tracked is None:
            return Scope(["--changed"])
        files |= tracked | staged
    if commit.paths:
        where = call.cwd if _inside(call.cwd, root) else root
        for diff in (["diff"], ["diff", "--cached"]):
            got = _names([*diff, *_DIFF_NAMES, "--", *commit.paths], where, deadline)
            if got is None:
                return Scope(["--changed"])
            files |= got
    return Scope.listed(files) if files else Scope(["--staged"])


def _push_scope(call: GitCall, root: Path, deadline: float) -> Scope | None:
    """Files touched by the commits the push sends that no remote-tracking ref has yet; None: nothing new."""
    options, positional = _parse_push(call.args)
    revs = _push_revs(options, positional) or ["HEAD"]
    if call.unparsed:
        revs = ["HEAD"]
    remotes = _git_out(["for-each-ref", "--count=1", "--format=%(refname)", "refs/remotes"], root, deadline)
    if not remotes or not remotes.strip():
        return Scope([])  # no remote-tracking refs (first push, or git failed): every file is new
    files = _names(["log", "-z", "--name-only", "--format=", "--no-renames", "--diff-filter=d", *revs,
                    "--not", "--remotes"], root, deadline, cap=10.0)
    if files is None:
        return Scope([])  # unknown revision or git error: the whole project, as before
    return Scope.listed(files) if files else None


def scope_for(call: GitCall, root: Path, deadline: float) -> Scope | None:
    """`mmu vibecheck` scope for a gated commit/push; None when there is nothing to check."""
    if call.verb == "commit":
        return _commit_scope(call, root, deadline)
    return _push_scope(call, root, deadline)


# --- scanner -----------------------------------------------------------------

# `-m` would put the scanned repo (the child's cwd) first on sys.path, so a `fnmatch.py` at its root would run.
# Isolated mode keeps the cwd and PYTHON* variables out; the package's own directory is added explicitly.
_BOOT = "import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module('mmu_cli', run_name='__main__', alter_sys=True)"


def _launcher() -> tuple[list[str], dict[str, str]]:
    """Run the scanner from the same source tree as this module (installed package or plugin bundle)."""
    src = str(Path(__file__).resolve().parents[1])
    return [sys.executable, "-I", "-X", "utf8", "-c", _BOOT, src, "vibecheck"], dict(os.environ)


def _run(args: list[str], root: Path, deadline: float, stdin: str = "") -> subprocess.CompletedProcess[str] | str:
    cmd, env = _launcher()
    remaining = deadline - time.monotonic()
    if remaining < 2:
        return "no time left before the hook deadline"
    if not root.is_dir():
        return f"{root} is not a directory"
    try:
        return subprocess.run(
            [*cmd, *args], input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=remaining, env=env, cwd=str(root),
        )
    except FileNotFoundError:
        return "python interpreter for the scanner was not found"
    except subprocess.TimeoutExpired:
        return f"scan exceeded {int(remaining)}s on {root} (large tree? add build dirs to `doctor.skip_paths`)"
    except OSError as exc:
        return f"scanner could not start: {exc}"


def run_scan(root: Path, scope: Scope, deadline: float) -> dict[str, Any] | str:
    """Return the parsed v1 document, or a short string saying why the scan could not run."""
    proc = _run(["--format", "json", *scope.flags], root, deadline, scope.stdin())
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


def narrowed_note(result: dict[str, Any], verb: str) -> str:
    """One visible line when the repo's own `.mmu/config.toml` kept part of this change out of the gate."""
    raw = result.get("scope")
    scope: dict[str, Any] = raw if isinstance(raw, dict) else {}
    parts: list[str] = []
    hidden = scope.get("skipped_by_config")
    if isinstance(hidden, int) and hidden > 0:
        paths = ", ".join(str(p) for p in (scope.get("config_skip_paths") or [])[:3])
        parts.append(f"{hidden} file(s) not scanned (skip_paths: {paths})")
    ignored = sorted({
        str(f.get("rule_id")) for f in result.get("findings", [])
        if isinstance(f, dict) and f.get("status") == "suppressed" and f.get("severity") == "P0"
        and isinstance(f.get("suppression"), dict) and f["suppression"].get("source") == "config"
    })
    if ignored:
        parts.append(f"P0 rule(s) ignored: {', '.join(ignored[:5])}")
    if not parts:
        return ""
    return f"mmu vibecheck: {verb} allowed, but .mmu/config.toml narrowed the check: {'; '.join(parts)}."


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


def build_reason(headline: str, fails: list[dict[str, Any]], root: Path, scope: Scope, deadline: float,
                 footer: str, use_agent_format: bool = True) -> str:
    """Headline + the scanner's own `--format agent` text (path:line, rule, fix, how to silence) + footer."""
    body = ""
    proc = (_run(["--format", "agent", *scope.flags], root, deadline, scope.stdin())
            if use_agent_format else "filtered findings")
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
            # Claude Code and Codex: a JSON deny with exit 0; the reason is handed to the model.
            return self._emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                       "permissionDecisionReason": reason}})
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


def _load_state(state: Path | None) -> dict[str, Any]:
    """Per-session state: {"blocks": stop blocks so far, "edited": repo-relative paths the agent edited}."""
    if state is None:
        return {}
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _stop_count(state: Path | None) -> int:
    try:
        return int(_load_state(state).get("blocks", 0))
    except (TypeError, ValueError):
        return 0


def _edited(state: Path | None) -> set[str]:
    edited = _load_state(state).get("edited")
    return {str(p) for p in edited} if isinstance(edited, list) else set()


def _save_state(state: Path | None, blocks: int | None = None, add_edited: set[str] | None = None,
                seen: set[str] | None = None) -> None:
    """Merge into the session state. `_clear_state` removes it."""
    if state is None:
        return
    try:
        data = _load_state(state)
        if blocks is not None:
            data["blocks"] = blocks
        if seen is not None:
            data["seen"] = sorted(seen)
        if add_edited:
            data["edited"] = sorted(_edited(state) | add_edited)
        data["updated"] = int(time.time())
        state.parent.mkdir(parents=True, exist_ok=True)
        cutoff = time.time() - 7 * 86400
        for old in state.parent.glob("stop-*.json"):
            if old != state and old.stat().st_mtime < cutoff:
                old.unlink(missing_ok=True)
        tmp = state.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, state)
    except OSError:
        pass


def _clear_state(state: Path | None) -> None:
    if state is not None:
        try:
            state.unlink(missing_ok=True)
        except OSError:
            pass


def _marks(fails: list[dict[str, Any]]) -> set[str]:
    """rule:path for each finding location (no line numbers: they move while the agent edits)."""
    return {f"{f.get('rule_id') or f.get('check')}:{loc.get('path')}"
            for f in fails for loc in f.get("locations") or [] if isinstance(loc, dict)}


def _session_id(payload: dict[str, Any]) -> str:
    return str(payload.get("session_id") or payload.get("conversation_id") or "default")


def _only_in(fails: list[dict[str, Any]], files: set[str]) -> list[dict[str, Any]]:
    """Findings narrowed to locations in `files`. A finding with no location in them (or none at all) is dropped."""
    out: list[dict[str, Any]] = []
    for f in fails:
        locs = [loc for loc in f.get("locations") or [] if isinstance(loc, dict) and loc.get("path") in files]
        if locs:
            out.append({**f, "locations": locs, "files": sorted({str(loc["path"]) for loc in locs})})
    return out


# --- event handlers ----------------------------------------------------------

_SILENCE = (
    "If a finding is a false positive, add a `mmu-ignore[<rule-id>]: <reason>` comment on the flagged line "
    "(a marker without a reason is ignored)."
)


def handle_pre_shell(payload: dict[str, Any], reply: Reply) -> int:
    deadline = time.monotonic() + DEADLINE_SECONDS
    command = shell_command(payload, reply.host)
    call = gated_call(command, payload_cwd(payload)) if command else None
    if call is None:
        return reply.allow()
    root = repo_root(call, deadline)
    scope = scope_for(call, root, deadline)
    if scope is None:
        return reply.allow()  # the push sends no commit that a remote does not already have
    verb = call.verb
    result = run_scan(root, scope, deadline)
    if isinstance(result, str):
        return reply.allow(f"mmu vibecheck gate did not run ({result}) — {verb} allowed unchecked.")
    fails = blocking(result)
    if not fails:
        return reply.allow(narrowed_note(result, verb))
    reason = build_reason(
        f"mmu vibecheck: {len(fails)} launch-blocking issue(s) in {root} — {verb} blocked.",
        fails, root, scope, deadline,
        f"Fix the P0 findings, then retry the {verb}. {_SILENCE} "
        "To skip the gate for one command, prefix it with MMU_HOOK_DISABLE=1.",
    )
    return reply.block(reason)


def handle_stop(payload: dict[str, Any], reply: Reply) -> int:
    if env_on("MMU_HOOK_DISABLE") or env_on("MMU_STOP_DISABLE"):
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
    cwd = Path(payload_cwd(payload))
    root = repo_root(GitCall(verb="", args=[], cwd=cwd, start=cwd), deadline)
    state = _state_file(root, _session_id(payload), deadline)
    if state is None:
        return reply.allow()  # not a git repository: nothing to scope the scan to, stay quiet
    # Claude Code and Codex report every edit through the post-edit hook, so the gate only holds the
    # agent to files it edited in this session; uncommitted work it never touched is not its problem.
    # Cursor and Gemini have no such hook here: every uncommitted change counts.
    tracks_edits = reply.host in ("claude", "codex")
    edited = _edited(state)
    if tracks_edits and not edited:
        return reply.allow()
    changed = Scope(["--changed"])
    result = run_scan(root, changed, deadline)
    if isinstance(result, str):
        return reply.allow(f"mmu vibecheck stop gate did not run ({result}).")
    all_fails = blocking(result)
    fails = _only_in(all_fails, edited) if tracks_edits else all_fails
    where = "files edited in this session" if tracks_edits else "uncommitted changes"
    if not fails:
        _clear_state(state)
        return reply.allow()
    # The cap counts attempts at the same findings: a new one starts the count again.
    marks = _marks(fails)
    seen = {str(m) for m in _load_state(state).get("seen") or []}
    count = _stop_count(state) if marks <= seen else 0
    if count >= limit:
        return reply.allow(
            f"mmu vibecheck: {len(fails)} launch-blocking issue(s) remain in {where}; the stop gate has "
            f"already sent the agent back {count} time(s) this session (MMU_STOP_MAX={limit}), so it is letting go. "
            "Run `mmu vibecheck --changed` to see them."
        )
    _save_state(state, blocks=count + 1, seen=seen | marks)
    reason = build_reason(
        f"mmu vibecheck: not done yet — {len(fails)} launch-blocking issue(s) in {where} ({root}).",
        fails, root, changed, deadline,
        "Fix the P0 findings and re-run `mmu vibecheck --changed --format agent` until they are gone "
        f"before telling the user the work is done. {_SILENCE} "
        "If the user explicitly asked to defer this hardening, do not fix it: list these P0s in your final "
        f"message and stop (the gate stops blocking after at most {limit} attempt(s)).",
        use_agent_format=len(fails) == len(all_fails) and all(
            len(f["locations"]) == len(o.get("locations") or []) for f, o in zip(fails, all_fails)
        ),
    )
    return reply.block(reason)


def handle_post_edit(payload: dict[str, Any], reply: Reply) -> int:
    if env_on("MMU_HOOK_DISABLE") or reply.host == "cursor":
        return reply.allow()
    files = edited_files(payload)
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
    touched: set[str] = set()
    for name in files:
        p = Path(name) if Path(name).is_absolute() else cwd / name
        try:
            touched.add(p.resolve().relative_to(root.resolve()).as_posix())
        except ValueError:
            continue
    if not touched:
        return reply.allow()
    # Remember what this session edited: the stop gate only holds the agent to these files.
    _save_state(_state_file(root, _session_id(payload), deadline), add_edited=touched)
    wanted = {rel for rel in touched if Path(rel).suffix.lower() in _CODE_SUFFIXES or Path(rel).name.startswith(".env")}
    if not wanted:
        return reply.allow()  # not a code or config file: no scan
    result = run_scan(root, Scope(["--changed"]), deadline)
    if isinstance(result, str):
        return reply.allow()  # feedback only; the commit and stop gates report scanner trouble
    lines: list[str] = []
    for f in _only_in(blocking(result), wanted):
        locs = f["locations"]
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
    try:
        args, _ = parser.parse_known_args(argv)
    except SystemExit as exc:
        # `--help` ends here; a bad --host/--event must not exit 2 (a block): detect both from the payload.
        return 0 if exc.code in (0, None) else run(None, None)
    return run(args.host, args.event)


if __name__ == "__main__":
    sys.exit(main())
