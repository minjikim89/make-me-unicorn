#!/usr/bin/env python3
"""Render an asciinema v2 .cast file to an animated GIF with Pillow.

Purpose-built for MMU demo casts: supports the ANSI subset the CLI emits
(SGR bold/dim/bright colors/reset, CR/LF scrolling) plus a glyph-fallback
chain for symbols that DejaVu Sans Mono lacks.

Usage:
    python scripts/render_cast_gif.py assets/demo.cast assets/demo.gif
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_SIZE = 16
PAD = 14
MIN_FRAME_MS = 30
COALESCE_S = 0.05
FINAL_HOLD_MS = 2800

BG = (13, 17, 23)
FG = (230, 237, 243)
DIM = (139, 148, 158)
PALETTE = {
    91: (255, 123, 114),
    92: (63, 185, 80),
    93: (210, 153, 34),
    94: (88, 166, 255),
    95: (188, 140, 255),
    96: (57, 197, 207),
}

# Glyphs the CLI prints that DejaVu Sans Mono can't draw.
SUBSTITUTIONS = {
    "🦄": "*",
    "✨": "*",
    "📝": "»",
    "🥚": "o",
    "🐣": "o",
    "🐴": "~",
    "⋮": "…",
    "️": "",  # emoji variation selector
}

_SGR = re.compile(r"\x1b\[([0-9;]*)m")


@dataclass
class Cell:
    ch: str = " "
    fg: tuple = FG
    bold: bool = False


@dataclass
class Terminal:
    cols: int
    rows: int
    grid: list = field(default_factory=list)
    cx: int = 0
    cy: int = 0
    fg: tuple = FG
    bold: bool = False

    def __post_init__(self):
        self.grid = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]

    def _apply_sgr(self, params: str) -> None:
        codes = [int(p) for p in params.split(";") if p] or [0]
        for code in codes:
            if code == 0:
                self.fg, self.bold = FG, False
            elif code == 1:
                self.bold = True
            elif code == 2:
                self.fg = DIM
            elif code in (22,):
                self.bold = False
            elif code == 39:
                self.fg = FG
            elif code in PALETTE:
                self.fg = PALETTE[code]
            elif 30 <= code <= 37 and (code + 60) in PALETTE:
                self.fg = PALETTE[code + 60]

    def _newline(self) -> None:
        self.cy += 1
        if self.cy >= self.rows:
            self.grid.pop(0)
            self.grid.append([Cell() for _ in range(self.cols)])
            self.cy = self.rows - 1

    def feed(self, text: str) -> None:
        i = 0
        while i < len(text):
            m = _SGR.match(text, i)
            if m:
                self._apply_sgr(m.group(1))
                i = m.end()
                continue
            ch = text[i]
            i += 1
            if ch == "\r":
                self.cx = 0
            elif ch == "\n":
                self._newline()
            elif ch == "\x1b":
                # Unsupported escape: skip the sequence terminator-agnostically
                while i < len(text) and text[i] not in "mHJKhl":
                    i += 1
                i += 1
            else:
                ch = SUBSTITUTIONS.get(ch, ch)
                if ch and ord(ch[0]) >= 0x1F000:
                    ch = ""  # emoji outside font coverage: drop rather than tofu
                if not ch:
                    continue
                if self.cx >= self.cols:
                    self.cx = 0
                    self._newline()
                self.grid[self.cy][self.cx] = Cell(ch, self.fg, self.bold)
                self.cx += 1


class GlyphFonts:
    """Mono font with a proportional fallback for missing symbols."""

    def __init__(self) -> None:
        self.mono = ImageFont.truetype(str(FONT_DIR / "DejaVuSansMono.ttf"), FONT_SIZE)
        self.mono_bold = ImageFont.truetype(str(FONT_DIR / "DejaVuSansMono-Bold.ttf"), FONT_SIZE)
        self.fallback = ImageFont.truetype(str(FONT_DIR / "DejaVuSans.ttf"), FONT_SIZE)
        self._known: dict[str, bool] = {}

    def has_glyph(self, ch: str) -> bool:
        if ch not in self._known:
            mask = self.mono.getmask(ch)
            self._known[ch] = ch == " " or (mask.getbbox() is not None)
        return self._known[ch]

    def pick(self, ch: str, bold: bool):
        if self.has_glyph(ch):
            return self.mono_bold if bold else self.mono
        return self.fallback


def render_frame(term: Terminal, fonts: GlyphFonts, cell_w: int, cell_h: int, cursor: bool) -> Image.Image:
    img = Image.new("RGB", (term.cols * cell_w + PAD * 2, term.rows * cell_h + PAD * 2), BG)
    draw = ImageDraw.Draw(img)
    for y, row in enumerate(term.grid):
        for x, cell in enumerate(row):
            if cell.ch == " ":
                continue
            draw.text(
                (PAD + x * cell_w, PAD + y * cell_h),
                cell.ch,
                fill=cell.fg,
                font=fonts.pick(cell.ch, cell.bold),
            )
    if cursor and term.cy < term.rows and term.cx < term.cols:
        x0 = PAD + term.cx * cell_w
        y0 = PAD + term.cy * cell_h
        draw.rectangle([x0, y0 + 2, x0 + cell_w - 1, y0 + cell_h - 1], fill=DIM)
    return img


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    cast_path, gif_path = Path(sys.argv[1]), Path(sys.argv[2])
    lines = [json.loads(line) for line in cast_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    header, events = lines[0], [e for e in lines[1:] if e[1] == "o"]
    if not events:
        print(f"No output events in {cast_path}; nothing to render.", file=sys.stderr)
        return 1

    term = Terminal(cols=header.get("width", 90), rows=header.get("height", 38))
    fonts = GlyphFonts()
    bbox = fonts.mono.getbbox("M")
    cell_w = bbox[2] - bbox[0] + 1
    cell_h = FONT_SIZE + 4

    # Coalesce bursts of events into single frames.
    groups: list[tuple[float, str]] = []
    for t, _, data in events:
        if groups and t - groups[-1][0] < COALESCE_S:
            groups[-1] = (groups[-1][0], groups[-1][1] + data)
        else:
            groups.append((t, data))

    frames: list[Image.Image] = []
    durations: list[int] = []
    for idx, (t, data) in enumerate(groups):
        term.feed(data)
        next_t = groups[idx + 1][0] if idx + 1 < len(groups) else t
        duration = max(MIN_FRAME_MS, int((next_t - t) * 1000))
        frames.append(render_frame(term, fonts, cell_w, cell_h, cursor=True))
        durations.append(duration)
    durations[-1] = FINAL_HOLD_MS

    # Quantize every frame against one shared palette built from a composite of
    # frames across all scenes, so no scene's colors get washed out.
    n = len(frames)
    samples = [frames[i] for i in sorted({n // 4, n // 2, (3 * n) // 4, n - 1})]
    w, h = samples[0].size
    composite = Image.new("RGB", (w, h * len(samples)), BG)
    for i, sample in enumerate(samples):
        composite.paste(sample, (0, i * h))
    palette_img = composite.quantize(colors=128, dither=Image.Dither.NONE)
    quantized = [f.quantize(palette=palette_img, dither=Image.Dither.NONE) for f in frames]
    quantized[0].save(
        gif_path,
        save_all=True,
        append_images=quantized[1:],
        duration=durations,
        loop=0,
        disposal=1,
    )
    size_kb = gif_path.stat().st_size // 1024
    print(f"Wrote {gif_path} — {len(frames)} frames, {frames[0].size[0]}x{frames[0].size[1]}, {size_kb} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
