"""`mmu vibecheck` command: argument definitions and the run loop.

Exit codes: 0 = no blocking findings, 1 = blocking findings (see --fail-on),
2 = usage or runtime error (bad root, git unavailable for a scoped scan, unknown rule id).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from mmu_cli.vibecheck.engine import (
    DEFAULT_BASELINE,
    ScanError,
    ScanResult,
    all_rules,
    baseline_path,
    get_rule,
    scan,
    write_baseline,
)
from mmu_cli.vibecheck.output import (
    FORMATS,
    error_json,
    render_agent,
    render_rule,
    render_rule_list,
    render_text,
    to_json,
    to_sarif,
)


def _fail_on(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "never":
        return "never"
    if normalized.upper() in {"P0", "P1"}:
        return normalized.upper()
    raise argparse.ArgumentTypeError("choose P0, P1, or never")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    # SUPPRESS keeps a value given before the subcommand (`mmu --json vibecheck`, `mmu --root X vibecheck`).
    parser.add_argument("--root", default=argparse.SUPPRESS, help="Project root path")
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Alias of --format json")
    parser.add_argument(
        "--format", choices=FORMATS, default=None,
        help="Output format: text (default), json (mmu.vibecheck/v1), sarif (2.1.0), agent (compact, for LLM context)",
    )
    parser.add_argument("--all", action="store_true", help="json: also include ok/skip findings")
    parser.add_argument("--output", metavar="FILE", help="Write the formatted output to FILE instead of stdout")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--changed", action="store_true", help="Only findings in files changed vs HEAD or untracked")
    scope.add_argument("--staged", action="store_true", help="Only findings in staged files")
    scope.add_argument("--since", metavar="REF", help="Only findings in files changed since the git ref REF")
    parser.add_argument(
        "--fail-on", type=_fail_on, default="P0", metavar="{P0,P1,never}",
        help="Exit 1 when findings at this severity or above exist (default: P0)",
    )
    parser.add_argument(
        "--baseline", nargs="?", const=DEFAULT_BASELINE, default=None, metavar="FILE",
        help=f"Report findings recorded in FILE as `baselined` (non-blocking); default FILE: {DEFAULT_BASELINE}",
    )
    parser.add_argument(
        "--write-baseline", nargs="?", const=DEFAULT_BASELINE, default=None, metavar="FILE",
        help=f"Record every current finding in FILE and exit 0; default FILE: {DEFAULT_BASELINE}",
    )
    parser.add_argument("--list-rules", action="store_true", help="List every rule id and exit")
    parser.add_argument("--explain", metavar="RULE_ID", help="Show what a rule detects and how to fix it, then exit")


def render(result: ScanResult, fmt: str, include_all: bool = False) -> str:
    if fmt == "json":
        return json.dumps(to_json(result, include_all), ensure_ascii=False, indent=2)
    if fmt == "sarif":
        return json.dumps(to_sarif(result), ensure_ascii=False, indent=2)
    if fmt == "agent":
        return render_agent(result)
    return render_text(result)


def _emit(text: str, output: str | None, colorize: bool = False) -> None:
    if output:
        path = Path(output).expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            raise ScanError("output-failed", f"cannot write --output {path}: {exc}") from None
        return
    if colorize:
        from mmu_cli.display import colorize_message

        text = "\n".join(colorize_message(line) for line in text.splitlines())
    print(text)


def _scope(args: argparse.Namespace) -> tuple[str, str | None]:
    if getattr(args, "changed", False):
        return "changed", None
    if getattr(args, "staged", False):
        return "staged", None
    since = getattr(args, "since", None)
    return ("since", since) if since else ("all", None)


def run(args: argparse.Namespace, root: Path) -> int:
    fmt = args.format or ("json" if getattr(args, "json", False) else "text")
    as_json = fmt == "json"
    try:
        if args.list_rules:
            rules = all_rules()
            listing: Any = {"schema": "mmu.vibecheck/v1", "rules": [rule.to_dict() for rule in rules]}
            _emit(json.dumps(listing, ensure_ascii=False, indent=2) if as_json else render_rule_list(rules), args.output)
            return 0
        if args.explain:
            rule = get_rule(args.explain)
            _emit(json.dumps(rule.to_dict(), ensure_ascii=False, indent=2) if as_json else render_rule(rule), args.output)
            return 0
        mode, since = _scope(args)
        write_to = getattr(args, "write_baseline", None)
        if write_to is not None:
            target = baseline_path(root, write_to)
            count = write_baseline(scan(root), target)  # always the whole project: a baseline of a diff is meaningless
            summary: Any = {"schema": "mmu.vibecheck/v1", "baseline": {"path": str(target), "entries": count}}
            text = f"Wrote {count} finding(s) to {target}. Run `mmu vibecheck --baseline` to report only new ones."
            _emit(json.dumps(summary, ensure_ascii=False, indent=2) if as_json else text, args.output)
            return 0
        use = getattr(args, "baseline", None)
        result = scan(root, scope=mode, since=since, baseline=baseline_path(root, use) if use is not None else None)
        _emit(render(result, fmt, include_all=args.all), args.output, colorize=fmt == "text")
    except ScanError as exc:
        if as_json:
            print(json.dumps(error_json(exc.code, exc.message), ensure_ascii=False, indent=2))
        else:
            print(f"mmu vibecheck: error: {exc.message}", file=sys.stderr)
        return 2
    return result.exit_code(args.fail_on)
