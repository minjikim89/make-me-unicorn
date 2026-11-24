"""Git config rules: command-executing keys in `.git/config`."""

from __future__ import annotations

from pathlib import Path

from mmu_cli.vibecheck.engine import _REF_GITSPAWN, Finding, Location, Rule, _read, _rel, clean_snippet, register

register(Rule(
    id="git-config-exec",
    title="Command-executing git config key",
    severity="P0",
    summary="Keys such as core.fsmonitor or alias.x = !cmd make git run a program on ordinary commands, so opening a hostile repo in an agent executes code before any approval prompt.",
    fix=(
        "Stop running git in this checkout and show the flagged keys to the user.\n"
        "If the user did not set them, delete those lines from .git/config (or an included config file) in an editor and treat the repository source as untrusted."
    ),
    ref=_REF_GITSPAWN,
    tags=("supply-chain", "agents"),
    confidence="high",
))

# `.git/config` keys that make git run a command when an agent (or you) opens the repo,
# with the values that are ordinary tooling rather than an attack.
_GIT_BOOL = {"true", "false", "1", "0", "yes", "no", "on", "off"}


def _parse_git_config(text: str) -> list[tuple[str, str, str]]:
    """Return (section, key, value) triples; section is lower-cased and includes subsection (e.g. filter.lfs)."""
    return [(section, key, value) for section, key, value, _ in _parse_git_config_lines(text)]


def _parse_git_config_lines(text: str) -> list[tuple[str, str, str, int]]:
    """(section, key, value, line number) for every entry.

    Handles the one-line form `[core] fsmonitor = x` that git accepts.
    """
    out: list[tuple[str, str, str, int]] = []
    section = ""
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            close = line.find("]")
            header = line[1:close].strip() if close > 0 else line.strip("[]").strip()
            parts = header.split(None, 1)
            section = parts[0].lower()
            if len(parts) > 1:
                section += "." + parts[1].strip().strip('"').lower()
            line = line[close + 1:].strip() if close > 0 else ""
            if not line:
                continue
        if "=" in line:
            key, _, value = line.partition("=")
            out.append((section, key.strip().lower(), value.strip(), lineno))
    return out


def _git_config_path(root: Path) -> Path | None:
    """The config git would read for this checkout: `.git/config`, or via a `gitdir:` pointer (worktrees, submodules)."""
    dot_git = root / ".git"
    if dot_git.is_dir():
        cfg = dot_git / "config"
        return cfg if cfg.is_file() else None
    if dot_git.is_file():
        text = _read(dot_git).strip()
        if text.startswith("gitdir:"):
            gitdir = (root / text.split(":", 1)[1].strip()).resolve()
            common = gitdir / "commondir"
            if common.is_file():
                gitdir = (gitdir / _read(common).strip()).resolve()
            cfg = gitdir / "config"
            return cfg if cfg.is_file() else None
    return None


def _git_config_entries(cfg: Path, seen: set[Path] | None = None) -> list[tuple[str, str, str]]:
    """Entries of a config file plus one level of `include.path` files (relative to the config's directory)."""
    return [(section, key, value) for section, key, value, _, _ in _git_config_entries_located(cfg, seen)]


def _git_config_entries_located(cfg: Path, seen: set[Path] | None = None) -> list[tuple[str, str, str, Path, int]]:
    """Like `_git_config_entries`, with the file and line each entry came from."""
    seen = seen if seen is not None else set()
    if cfg in seen or len(seen) > 8:
        return []
    seen.add(cfg)
    entries = [(section, key, value, cfg, lineno) for section, key, value, lineno in _parse_git_config_lines(_read(cfg))]
    for section, key, value, _, _ in list(entries):
        if section.split(".", 1)[0] in {"include", "includeif"} and key == "path":
            inc = (cfg.parent / Path(value).expanduser()).resolve()
            if inc.is_file():
                entries.extend(_git_config_entries_located(inc, seen))
    return entries


def _is_shellish(value: str) -> bool:
    return value.startswith("!") or any(ch in value for ch in "|;&$`")


def _git_config_exec_hit(root: Path, section: str, key: str, value: str) -> bool:
    """True when this entry runs a program on ordinary git use and is not a known-benign tool setting."""
    top = section.split(".", 1)[0]
    v = value.strip().strip('"').strip("'")
    if top == "core":
        if key == "fsmonitor":
            return v.lower() not in _GIT_BOOL  # `true` = builtin daemon; anything else is a command
        if key == "sshcommand":
            first = v.split(None, 1)[0].strip('"').strip("'").lower() if v else ""
            return not (Path(first).name in {"ssh", "plink", "putty"} and not _is_shellish(v))
        if key == "hookspath":
            # husky/lefthook point inside the repo (`.husky/_`); a path outside it or absolute is not yours
            return v.startswith(("/", "~")) or ".." in Path(v).parts
        return key == "askpass"
    if top == "alias":
        return v.startswith("!")
    if top == "credential" and key == "helper":
        return _is_shellish(v) or "/" in v
    if top == "filter" and key in {"clean", "smudge", "process", "required"} and key != "required":
        return not v.startswith("git-lfs ")  # `git lfs install --local` writes exactly these
    if top == "diff" and key == "external":
        return True
    if top == "merge" and key == "driver":
        return True
    return False


def check_git_config_exec(root: Path, code_files: list[Path]) -> Finding:
    """`.git/config` entries that execute commands when the repo is opened.

    GitSpawn (Sep 2026): coding agents run `git status` etc. on startup; keys like
    core.fsmonitor turn that into arbitrary code execution before any approval prompt.
    Follows `gitdir:` pointers (worktrees) and one level of `include.path`.
    """
    cfg = _git_config_path(root)
    if cfg is None:
        return Finding("git-config-exec", "P0", "skip", "no git config found for this checkout")
    hits: list[str] = []
    locations: list[Location] = []
    for section, key, value, src, lineno in _git_config_entries_located(cfg):
        if _git_config_exec_hit(root, section, key, value):
            hits.append(f"{section}.{key} = {value[:60]}")
            locations.append(Location(_rel(src, root), lineno, snippet=clean_snippet(f"{section}.{key} = {value}")))
    if hits:
        return Finding(
            "git-config-exec",
            "P0",
            "fail",
            f"git config contains {len(hits)} command-executing key(s): " + "; ".join(hits[:5]),
            files=[_rel(cfg, root)],
            locations=locations,
        )
    return Finding("git-config-exec", "P0", "ok", "no command-executing keys in git config")
