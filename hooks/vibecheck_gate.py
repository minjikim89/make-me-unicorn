#!/usr/bin/env python3
"""Plugin hook entry point: run `mmu hook` from the plugin's bundled source.

The logic lives in src/mmu_cli/hooks.py. This wrapper only makes the plugin work
without `pip install make-me-unicorn`: it puts the plugin's `src/` on sys.path
(CLAUDE_PLUGIN_ROOT in Claude Code, PLUGIN_ROOT in Codex, else this file's parent)
and calls the same code as `mmu hook`.

Fallbacks, in order: bundled source (Python >= 3.10) → an installed `mmu` on PATH →
allow the action with one visible line. A broken gate never blocks the agent.

Arguments are passed through (`--host`, `--event`); without them the host and the
event are detected from the JSON payload on stdin.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _plugin_root() -> Path:
    for var in ("CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT"):
        value = os.environ.get(var)
        if value and (Path(value) / "src" / "mmu_cli").is_dir():
            return Path(value)
    return Path(__file__).resolve().parent.parent


def _fail_open(why: str) -> int:
    print(json.dumps({"systemMessage": "mmu vibecheck gate did not run (" + why + ") - action allowed unchecked."}))
    return 0


def main() -> int:
    src = _plugin_root() / "src"
    if sys.version_info >= (3, 10) and (src / "mmu_cli" / "hooks.py").is_file():
        sys.path.insert(0, str(src))
        try:
            from mmu_cli.hooks import main as hook_main
        except Exception as exc:  # noqa: BLE001
            return _fail_open("bundled mmu_cli failed to import: " + type(exc).__name__)
        return hook_main(sys.argv[1:])
    mmu = shutil.which("mmu")
    if mmu:
        try:
            return subprocess.run([mmu, "hook", *sys.argv[1:]], timeout=55).returncode
        except (OSError, subprocess.SubprocessError) as exc:
            return _fail_open("installed mmu failed: " + type(exc).__name__)
    return _fail_open(
        "needs Python >= 3.10 as `python3` or `mmu` on PATH; found Python %d.%d" % sys.version_info[:2]
    )


if __name__ == "__main__":
    sys.exit(main())
