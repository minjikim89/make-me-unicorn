#!/usr/bin/env python3
"""Record the README demo cast by running real mmu commands in a fixture project.

Builds a small Next.js-flavoured fixture (with the classic AI-generated
mistakes: unverified Stripe webhook, auth without password reset), runs
`mmu init` / `mmu scan` / `mmu vibecheck` / `mmu`, captures real colored
output, and writes an asciinema v2 cast with simulated typing.

Usage:
    python scripts/record_demo_cast.py assets/demo.cast
    python scripts/render_cast_gif.py assets/demo.cast assets/demo.gif
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

COLS, ROWS = 90, 38
TYPE_DELAY = 0.045
LINE_DELAY = 0.024
AFTER_CMD_PAUSE = 1.6

FIXTURE_FILES = {
    "package.json": '{\n  "name": "acme-notes",\n  "dependencies": { "next": "^14", "stripe": "^14" }\n}\n',
    "next.config.js": "module.exports = {};\n",
    "app/layout.tsx": "export default function RootLayout({ children }) { return children; }\n",
    "src/app/api/webhooks/stripe/route.ts": (
        "export async function POST(req: Request) {\n"
        "  const event = await req.json(); // TODO: verify signature\n"
        "  await handleEvent(event);\n"
        "  return Response.json({ ok: true });\n"
        "}\n"
    ),
    "src/lib/auth.ts": (
        "export async function login(email: string, password: string) {\n"
        "  const session = await createSession(email, password);\n"
        "  return session;\n"
        "}\n"
    ),
}


def run_mmu(argv: list[str], cwd: Path) -> str:
    """Run an mmu command in-process and capture colored stdout."""
    from mmu_cli import cli, display

    display._NO_COLOR = False  # force colors even though stdout is captured
    old_argv, old_cwd = sys.argv, Path.cwd()
    buf = io.StringIO()
    try:
        os.chdir(cwd)
        sys.argv = ["mmu", *argv]
        with contextlib.redirect_stdout(buf):
            try:
                cli.main()
            except SystemExit:
                pass
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
    return buf.getvalue()


def elide(text: str, head: int, tail: int) -> list[str]:
    lines = text.rstrip("\n").split("\n")
    if len(lines) <= head + tail + 1:
        return lines
    return lines[:head] + ["  \x1b[2m…\x1b[0m"] + lines[-tail:]


def wrap_plain(line: str, cols: int) -> list[str]:
    """Word-wrap ANSI-free lines with a hanging indent; pass colored lines through."""
    if "\x1b" in line or len(line) <= cols:
        return [line]
    lead = len(line) - len(line.lstrip(" "))
    indent = " " * (lead + 2)
    out: list[str] = []
    current = " " * lead
    for word in line.lstrip(" ").split(" "):
        candidate = f"{current} {word}" if current.strip() else current + word
        if len(candidate) > cols and current.strip():
            out.append(current)
            current = indent + word
        else:
            current = candidate
    if current.strip():
        out.append(current)
    return out


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "assets" / "demo.cast"

    tmp = Path(tempfile.mkdtemp(prefix="mmu-demo-"))
    for rel, content in FIXTURE_FILES.items():
        path = tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    scenes: list[tuple[str, list[str], tuple[int, int] | None]] = [
        ("mmu init", ["init"], (9, 7)),
        ("mmu scan", ["scan"], (14, 2)),
        ("mmu vibecheck", ["vibecheck"], None),
        ("mmu", [], None),
    ]

    events: list[list] = []
    t = 0.6

    def emit(data: str, dt: float) -> None:
        nonlocal t
        events.append([round(t, 3), "o", data])
        t += dt

    for shown, argv, trim in scenes:
        emit("\x1b[2m$\x1b[0m ", 0.4)
        for ch in shown:
            emit(ch, TYPE_DELAY)
        emit("\r\n", 0.35)
        output = run_mmu(argv, tmp)
        lines = elide(output, *trim) if trim else output.rstrip("\n").split("\n")
        for line in lines:
            for wrapped in wrap_plain(line, COLS - 1):
                emit(wrapped + "\r\n", LINE_DELAY)
        emit("", AFTER_CMD_PAUSE)

    header = {
        "version": 2,
        "width": COLS,
        "height": ROWS,
        "timestamp": int(time.time()),
        "env": {"SHELL": "/bin/zsh", "TERM": "xterm-256color"},
        "title": "Make Me Unicorn — v0.7 Demo",
    }
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(header) + "\n")
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Wrote {out_path} — {len(events)} events, {t:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
