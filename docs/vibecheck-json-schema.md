# `mmu vibecheck` JSON contract (`mmu.vibecheck/v1`)

`mmu vibecheck --format json` (alias `--json`) prints one JSON document on stdout.
Hooks, the MCP tool `mmu_vibecheck`, and the GitHub Action all consume this shape.
Fields are only added within `v1`; a removal or a change of meaning bumps the `schema` string.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | No blocking findings (warnings and suppressed findings may exist) |
| `1` | Blocking findings at or above `--fail-on` (default `P0`) |
| `2` | Usage or runtime error: bad `--root`, git unavailable for a scoped scan, unknown rule id |

## Document

| Field | Type | Notes |
|-------|------|-------|
| `schema` | string | Always `mmu.vibecheck/v1` |
| `tool` | object | `{"name": "mmu", "version": "<package version>"}` |
| `root` | string | Absolute path that was scanned |
| `scope` | object | `{"mode": "all"}`, or `{"mode": "changed" \| "staged" \| "since", "files": <n>, "since": "<ref>"}` (`since` only in that mode) |
| `summary` | object | Counts of findings by status: `blocking` (fail), `warnings` (warn), `passed` (ok), `skipped` (skip), `suppressed` |
| `findings` | array | `fail`, `warn` and `suppressed` findings; `--all` adds `ok` and `skip` |

## Finding

| Field | Type | Notes |
|-------|------|-------|
| `rule_id` | string | Stable kebab-case id (`mmu vibecheck --list-rules`) |
| `check` | string | Deprecated alias of `rule_id` |
| `severity` | `P0` \| `P1` | `P0` blocks, `P1` warns. A `P0` found only in test/fixture paths is reported as `P1` |
| `status` | string | `fail` (P0, blocking), `warn` (P1), `suppressed`, and with `--all`: `ok`, `skip` |
| `title` | string | Rule title |
| `message` | string | What was found in this project |
| `locations` | array | `{"path", "line", "end_line", "snippet"}`. `path` is relative to `root` with forward slashes; `line` is 1-based, `null` when the finding is about the file as a whole; `snippet` is the trimmed source line with secret values redacted |
| `files` | array | Unique paths of `locations` (kept for older consumers) |
| `fix` | string | Concrete instructions, up to 4 lines |
| `hint` | string | Deprecated alias of `fix` |
| `ref` | string | Incident data or authoritative documentation; may be empty |
| `confidence` | `high` \| `medium` \| `low` | `low` = absence-of-marker heuristic; verify before acting |
| `suppression` | object \| null | `{"reason", "source": "inline" \| "config"}` when `status` is `suppressed` |
| `notes` | array | Remarks such as an `mmu-ignore` marker that was not applied because it has no reason |
| `fingerprint` | string | 16 hex chars: sha256 of rule id, path and whitespace-normalised snippet of the first location. Stable when lines shift; usable as a baseline key |

A finding with several locations is one finding. When only some locations are suppressed, the
active locations stay in the original finding and the suppressed ones follow as a second
finding with `status: "suppressed"`.

## Example

```json
{
  "schema": "mmu.vibecheck/v1",
  "tool": {"name": "mmu", "version": "0.9.0"},
  "root": "/work/app",
  "scope": {"mode": "changed", "files": 3},
  "summary": {"blocking": 1, "warnings": 0, "passed": 9, "skipped": 4, "suppressed": 1},
  "findings": [
    {
      "rule_id": "sql-fstring",
      "check": "sql-fstring",
      "severity": "P0",
      "status": "fail",
      "title": "SQL built with an f-string",
      "message": "f-string SQL queries in 1 file(s)",
      "locations": [
        {"path": "app/routers/notes.py", "line": 39, "end_line": null, "snippet": "rows = db.execute(text(f\"SELECT * FROM notes WHERE title LIKE '%{q}%'\"))"}
      ],
      "files": ["app/routers/notes.py"],
      "fix": "Pass values as bound parameters instead of interpolating them: ...",
      "hint": "Pass values as bound parameters instead of interpolating them: ...",
      "ref": "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
      "confidence": "high",
      "suppression": null,
      "notes": [],
      "fingerprint": "5f0c1d2e3a4b6978"
    },
    {
      "rule_id": "secrets",
      "check": "secrets",
      "severity": "P0",
      "status": "suppressed",
      "title": "Hardcoded secret",
      "message": "possible hardcoded secrets in 1 file(s): Stripe test secret key",
      "locations": [
        {"path": "app/billing.py", "line": 7, "end_line": null, "snippet": "DOCS_EXAMPLE = \"sk_tes…\"  # mmu-ignore[secrets]: published sample key from the Stripe docs"}
      ],
      "files": ["app/billing.py"],
      "fix": "Replace the literal with an environment lookup ...",
      "hint": "Replace the literal with an environment lookup ...",
      "ref": "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
      "confidence": "high",
      "suppression": {"reason": "published sample key from the Stripe docs", "source": "inline"},
      "notes": [],
      "fingerprint": "a91b7c3d5e2f4061"
    }
  ]
}
```

## Error object

With `--format json`, an exit-2 error is reported on stdout instead of the document:

```json
{"schema": "mmu.vibecheck/v1", "error": {"code": "not-a-git-repo", "message": "/work/app is not a git repository; scoped scans need one"}}
```

Codes: `bad-root`, `git-unavailable`, `not-a-git-repo`, `git-failed`, `bad-ref`, `unknown-rule`, `output-failed`, `usage`.

## Suppressions

- Inline: `mmu-ignore[<rule-id>]: <reason>` in any comment syntax, on the flagged line or alone on the line directly above it. Several ids may be comma-separated. A marker without a reason is not applied and is reported in `notes`.
- Config: `.mmu/config.toml`

  ```toml
  [vibecheck]
  ignore = ["error-monitoring", "legacy/**:sql-fstring"]
  ```

  A bare rule id ignores the rule; `glob:rule-id` ignores it for matching paths.

## Other formats

- `--format agent`: compact plain text for an LLM's context (rule id, `path:line`, fix, how to silence).
- `--format sarif`: SARIF 2.1.0 for GitHub code scanning, one result per location; `P0` maps to `error` (`security-severity` 8.0), `P1` to `warning` (5.0); each result carries `partialFingerprints.primaryLocationLineHash` (`<fingerprint>:1`); suppressed findings carry `suppressions`.
- `--list-rules --format json` returns `{"schema", "rules": [{id, title, severity, summary, fix, ref, tags, confidence}]}`; `--explain <rule-id> --format json` returns one such rule object.
