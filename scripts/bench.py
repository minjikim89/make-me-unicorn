#!/usr/bin/env python3
"""Benchmark `mmu vibecheck` against the fixtures in bench/fixtures.

Each fixture is materialized into a temp dir (see bench/materialize.py), scanned with the
engine, and compared with its ground truth in bench/expected/<fixture>.toml:

    [[expect]]      rule, path, severity, optional line, optional id (planted issue)
    [[must_not]]    rule, path: correct code that must never be reported
    [[uncovered]]   id, issue, path: planted issues no rule targets (counted as misses)

Scoring is strict: a reported (rule, path, severity) that is not expected is a false
positive, an expected one that is not reported is a false negative.

Usage:
    python scripts/bench.py               # print the tables
    python scripts/bench.py --markdown    # also rewrite the fixture section of docs/benchmark.md
    python scripts/bench.py --json        # machine-readable result
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from bench.materialize import fixture_names, materialize  # noqa: E402
from mmu_cli.vibecheck.engine import scan, tool_version  # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

EXPECTED = REPO / "bench" / "expected"
DOC = REPO / "docs" / "benchmark.md"
BEGIN, END = "<!-- bench:fixtures:begin -->", "<!-- bench:fixtures:end -->"

Key = tuple[str, str, str]  # (rule, path, severity)


@dataclass
class FixtureResult:
    name: str
    tp: list[Key] = field(default_factory=list)
    fp: list[Key] = field(default_factory=list)
    fn: list[Key] = field(default_factory=list)
    violations: list[tuple[str, str]] = field(default_factory=list)  # must_not entries that were reported
    planted: dict[str, bool] = field(default_factory=dict)  # planted issue id -> detected
    seconds: float = 0.0


def load_expected(name: str) -> dict:
    path = EXPECTED / f"{name}.toml"
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def run_fixture(name: str) -> FixtureResult:
    truth = load_expected(name)
    with tempfile.TemporaryDirectory(prefix="mmu-bench-") as tmp:
        root = materialize(name, Path(tmp) / name)
        # The temp dir may sit inside some other git work tree; its ignore rules must not leak into the result.
        previous = os.environ.get("GIT_CEILING_DIRECTORIES")
        os.environ["GIT_CEILING_DIRECTORIES"] = str(Path(tmp).resolve())
        try:
            started = time.perf_counter()
            result = scan(root)
            seconds = time.perf_counter() - started
        finally:
            if previous is None:
                os.environ.pop("GIT_CEILING_DIRECTORIES", None)
            else:
                os.environ["GIT_CEILING_DIRECTORIES"] = previous
    reported: dict[Key, set[int | None]] = {}
    for finding in result.findings:
        if finding.status not in {"fail", "warn"}:
            continue
        locations = finding.locations or [None]
        for loc in locations:
            key = (finding.check, loc.path if loc else "", finding.severity)
            reported.setdefault(key, set()).add(loc.line if loc else None)
    out = FixtureResult(name=name, seconds=seconds)
    matched: set[Key] = set()
    for entry in truth.get("expect", []):
        key = (entry["rule"], entry.get("path", ""), entry.get("severity", "P0"))
        lines = reported.get(key)
        hit = lines is not None and ("line" not in entry or entry["line"] in lines)
        if hit:
            matched.add(key)
            if key not in out.tp:
                out.tp.append(key)
        else:
            out.fn.append(key)
        for issue in str(entry.get("id", "")).split(","):
            if issue.strip():
                out.planted[issue.strip()] = out.planted.get(issue.strip(), False) or hit
    for entry in truth.get("uncovered", []):
        out.planted.setdefault(entry["id"], False)
    out.fp = sorted(key for key in reported if key not in matched)
    for entry in truth.get("must_not", []):
        for rule, path, _ in reported:
            if rule == entry["rule"] and path == entry.get("path", path):
                out.violations.append((rule, path))
    return out


def run_all() -> list[FixtureResult]:
    return [run_fixture(name) for name in fixture_names()]


def _ratio(num: int, den: int) -> float:
    return num / den if den else 1.0


def summarize(results: list[FixtureResult]) -> dict:
    def count(keys: list[Key], severity: str) -> int:
        return sum(1 for key in keys if key[2] == severity)

    summary: dict = {"fixtures": len(results), "tool_version": tool_version()}
    for severity in ("P0", "P1"):
        tp = sum(count(r.tp, severity) for r in results)
        fp = sum(count(r.fp, severity) for r in results)
        fn = sum(count(r.fn, severity) for r in results)
        summary[severity] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(_ratio(tp, tp + fp), 4), "recall": round(_ratio(tp, tp + fn), 4),
        }
    rules: dict[str, dict[str, int]] = {}
    for r in results:
        for bucket, keys in (("tp", r.tp), ("fp", r.fp), ("fn", r.fn)):
            for rule, _, _ in keys:
                rules.setdefault(rule, {"tp": 0, "fp": 0, "fn": 0})[bucket] += 1
    summary["rules"] = dict(sorted(rules.items()))
    planted = [hit for r in results for hit in r.planted.values()]
    summary["planted"] = {"total": len(planted), "detected": sum(planted), "recall": round(_ratio(sum(planted), len(planted)), 4)}
    summary["must_not_violations"] = sum(len(r.violations) for r in results)
    summary["max_seconds"] = round(max((r.seconds for r in results), default=0.0), 3)
    return summary


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def render_markdown(results: list[FixtureResult], summary: dict) -> str:
    p0, p1, planted = summary["P0"], summary["P1"], summary["planted"]
    lines = [
        f"{summary['fixtures']} fixtures. Regenerate with `python scripts/bench.py --markdown`.",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| P0 precision | {_pct(p0['precision'])} ({p0['tp']} true positives, {p0['fp']} false positives) |",
        f"| P0 recall | {_pct(p0['recall'])} ({p0['tp']} of {p0['tp'] + p0['fn']} expected P0 findings) |",
        f"| P1 precision | {_pct(p1['precision'])} ({p1['tp']} true positives, {p1['fp']} false positives) |",
        f"| P1 recall | {_pct(p1['recall'])} ({p1['tp']} of {p1['tp'] + p1['fn']} expected P1 findings) |",
        f"| Planted issues detected | {planted['detected']} of {planted['total']} ({_pct(planted['recall'])}), including issues no rule targets |",
        f"| `must_not` entries reported | {summary['must_not_violations']} |",
        "",
        "### Per rule",
        "",
        "| Rule | TP | FP | FN |",
        "|------|----|----|----|",
    ]
    for rule, c in summary["rules"].items():
        lines.append(f"| `{rule}` | {c['tp']} | {c['fp']} | {c['fn']} |")
    lines += ["", "### Per fixture", "", "| Fixture | TP | FP | FN | Planted issues detected | Missed |", "|---------|----|----|----|-------------------------|--------|"]
    for r in results:
        missed = ", ".join(sorted(issue for issue, hit in r.planted.items() if not hit)) or "none"
        lines.append(
            f"| `{r.name}` | {len(r.tp)} | {len(r.fp)} | {len(r.fn)} | {sum(r.planted.values())} of {len(r.planted)} | {missed} |"
        )
    return "\n".join(lines)


def render_text(results: list[FixtureResult], summary: dict) -> str:
    lines = []
    for r in results:
        lines.append(f"{r.name}: TP={len(r.tp)} FP={len(r.fp)} FN={len(r.fn)} ({r.seconds * 1000:.0f} ms)")
        for label, keys in (("FP", r.fp), ("FN", r.fn)):
            for rule, path, severity in keys:
                lines.append(f"    {label} {severity} {rule} {path}")
        for rule, path in r.violations:
            lines.append(f"    MUST-NOT violated: {rule} {path}")
    lines.append("")
    lines.append(f"{'rule':28s} TP FP FN")
    for rule, c in summary["rules"].items():
        lines.append(f"{rule:28s} {c['tp']:2d} {c['fp']:2d} {c['fn']:2d}")
    lines.append("")
    for severity in ("P0", "P1"):
        s = summary[severity]
        lines.append(f"{severity}: precision {_pct(s['precision'])} recall {_pct(s['recall'])} (TP {s['tp']}, FP {s['fp']}, FN {s['fn']})")
    planted = summary["planted"]
    lines.append(f"planted issues detected: {planted['detected']}/{planted['total']} ({_pct(planted['recall'])})")
    lines.append(f"slowest fixture scan: {summary['max_seconds'] * 1000:.0f} ms")
    return "\n".join(lines)


def doc_section() -> str | None:
    """The generated fixture section currently in docs/benchmark.md, or None when the markers are missing."""
    text = DOC.read_text(encoding="utf-8") if DOC.is_file() else ""
    if BEGIN not in text or END not in text:
        return None
    return text.split(BEGIN, 1)[1].split(END, 1)[0].strip()


def update_doc(section: str) -> None:
    text = DOC.read_text(encoding="utf-8") if DOC.is_file() else f"# Benchmark\n\n{BEGIN}\n{END}\n"
    if BEGIN not in text or END not in text:
        raise SystemExit(f"{DOC} has no {BEGIN} / {END} markers")
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    DOC.write_text(f"{head}{BEGIN}\n{section}\n{END}{tail}", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--markdown", action="store_true", help="rewrite the fixture section of docs/benchmark.md")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args()
    results = run_all()
    summary = summarize(results)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(render_text(results, summary))
    if args.markdown:
        update_doc(render_markdown(results, summary))
        print(f"\nwrote {DOC.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
