# `mmu vibecheck` JSON contract (`mmu.vibecheck/v1`)

`mmu vibecheck --format json` (alias `--json`) prints one JSON document on stdout.
Hooks, the MCP tool `mmu_vibecheck`, and the GitHub Action all consume this shape.
Fields are only added within `v1`; a removal or a change of meaning bumps the `schema` string.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | No blocking findings (warnings and suppressed findings may exist) |
| `1` | Blocking findings at or above `--fail-on` (default `P0`) |
| `2` | Usage or runtime error: bad `--root`, git unavailable for a scoped scan, unknown rule id, unreadable baseline |

## Document

| Field | Type | Notes |
|-------|------|-------|
| `schema` | string | Always `mmu.vibecheck/v1` |
| `tool` | object | `{"name": "mmu", "version": "<package version>"}` |
| `root` | string | Absolute path that was scanned |
| `scope` | object | `{"mode": "all"}`, or `{"mode": "changed" \| "staged" \| "since", "files": <n>, "since": "<ref>"}` (`since` only in that mode). `truncated: <n>` is added when more than 20,000 code files were found and the last `n` (in path order) were left out |
| `summary` | object | Counts of findings by status: `blocking` (fail), `warnings` (warn), `passed` (ok), `skipped` (skip), `suppressed`, `baselined` |
| `findings` | array | `fail`, `warn`, `suppressed` and `baselined` findings; `--all` adds `ok` and `skip` |

## Finding

| Field | Type | Notes |
|-------|------|-------|
| `rule_id` | string | Stable kebab-case id (`mmu vibecheck --list-rules`) |
| `check` | string | Deprecated alias of `rule_id` |
| `severity` | `P0` \| `P1` | `P0` blocks, `P1` warns. A `P0` found only in test/fixture paths is reported as `P1` |
| `status` | string | `fail` (P0, blocking), `warn` (P1), `suppressed`, `baselined`, and with `--all`: `ok`, `skip` |
| `title` | string | Rule title |
| `message` | string | What was found in this project |
| `locations` | array | `{"path", "line", "end_line", "snippet"}`. `path` is relative to `root` with forward slashes; `line` is 1-based, `null` when the finding is about the file as a whole; `snippet` is the trimmed source line with secret values redacted |
| `files` | array | Unique paths of `locations` (kept for older consumers) |
| `fix` | string | Concrete instructions, up to 4 lines, written for the framework of the first location (Next.js, Express, Hono, FastAPI, Flask, Django, Supabase) when the rule has a variant for it |
| `hint` | string | Deprecated alias of `fix` |
| `ref` | string | Incident data or authoritative documentation; may be empty |
| `confidence` | `high` \| `medium` \| `low` | `low` = absence-of-marker heuristic; verify before acting |
| `suppression` | object \| null | `{"reason", "source": "inline" \| "config"}` when `status` is `suppressed` |
| `notes` | array | Remarks such as an `mmu-ignore` marker that was not applied because it has no reason |
| `fingerprint` | string | 16 hex chars: sha256 of rule id, path and whitespace-normalised snippet of the first location. Stable when lines shift; usable as a baseline key |

A finding with several locations is one finding. When only some locations are suppressed, the
active locations stay in the original finding and the suppressed ones follow as a second
finding with `status: "suppressed"`. Locations recorded in a baseline are split off the same way
with `status: "baselined"`. A rule can also report twice with different severities
(`unsafe-deserialization`: `P0` for unsafe YAML loaders and pickle on external input, `P1` for
other pickle loads).

## Severity policy

`P0` means high confidence and launch-blocking: an exact pattern (a key signature, interpolated
SQL at a query call, request data in `eval`, a webhook handler that trusts an unverified event).
Findings about something being absent from the project (password reset flow, rate limiting,
error monitoring, webhook idempotency, auth on an LLM or admin route) are `P1`: they describe a
gap, not an incident, and must not block every commit in a project that has not built the
feature yet. Comments never count as evidence that a safeguard exists.

Measured precision and recall: [benchmark.md](benchmark.md).

## Example

```json
{
  "schema": "mmu.vibecheck/v1",
  "tool": {"name": "mmu", "version": "0.7.0"},
  "root": "/work/app",
  "scope": {"mode": "changed", "files": 3},
  "summary": {"blocking": 1, "warnings": 0, "passed": 15, "skipped": 6, "suppressed": 1, "baselined": 0},
  "findings": [
    {
      "rule_id": "sql-fstring",
      "check": "sql-fstring",
      "severity": "P0",
      "status": "fail",
      "title": "SQL built with string interpolation",
      "message": "SQL built by interpolating values in 1 file(s)",
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

Codes: `bad-root`, `git-unavailable`, `not-a-git-repo`, `git-failed`, `bad-ref`, `unknown-rule`, `output-failed`, `bad-baseline`, `usage`.

## Suppressions

- Inline: `mmu-ignore[<rule-id>]: <reason>` in any comment syntax, on the flagged line or alone on the line directly above it. Several ids may be comma-separated. A marker without a reason is not applied and is reported in `notes`.
- Config: `.mmu/config.toml`

  ```toml
  [vibecheck]
  ignore = ["error-monitoring", "legacy/**:sql-fstring"]
  ```

  A bare rule id ignores the rule; `glob:rule-id` ignores it for matching paths.

## What is scanned

- Code files (`.py .js .jsx .ts .tsx .mjs .mts .cjs .cts .vue .svelte .go .rb .java .cs`) and, for the `secrets` rule, config files (`.json .yaml .yml .toml .ini .properties .tf .tfvars .sh`, `Dockerfile*`, `docker-compose*`, dotenv files and more). Lockfiles, minified bundles, `.env.example`-style templates and files over 1 MB are left out.
- Vendor and build directories are skipped at any depth (`node_modules`, `.next`, `dist`, `build`, `venv`, `site-packages`, `vendor`, `target`, `out`, `.vercel`, `.output`, ...). Everything else is scanned, including `scripts/`, `tests/`, `docs/` and `examples/`.
- Add root-anchored excludes in `.mmu/config.toml`:

  ```toml
  [vibecheck]
  skip_paths = ["tools/generated", "docs"]
  ```

  (`[doctor] skip_paths` is honoured too.)
- Dotenv files are checked against git: inside a work tree `git check-ignore` decides (a tracked file is never "ignored"); elsewhere the `.gitignore` files are matched directly, including patterns such as `/.env`, `.env*`, `*.env` and `!` negations.
- Files are processed in path order, so two runs on the same tree give the same result.

## Scoping and repo-level findings

`--changed`, `--staged` and `--since` keep only findings with a location in the selected files. Findings about the repository as a whole are never filtered out: `git-config-exec`, `env-not-ignored`, and any location in a dotenv file (`secrets`, `client-bundle-secrets`), because git-ignored and untracked-by-design files never appear in a diff.

## Baseline

For a repository that already has findings:

```bash
mmu vibecheck --write-baseline          # writes .mmu/vibecheck-baseline.json, exits 0
mmu vibecheck --baseline                # findings in the baseline are reported as "baselined" and do not block
mmu vibecheck --baseline ci/base.json   # both flags take an optional path, relative to --root
```

`--write-baseline` always records the whole project (scope flags are ignored) and prints `{"schema": "mmu.vibecheck/v1", "baseline": {"path", "entries"}}` with `--format json`.

The file is meant to be committed:

```json
{
  "schema": "mmu.vibecheck-baseline/v1",
  "tool": {"name": "mmu", "version": "0.8.0"},
  "entries": [
    {"fingerprint": "5f0c1d2e3a4b6978", "rule_id": "sql-fstring", "path": "app/routers/notes.py"}
  ]
}
```

One entry per finding location. Matching is by `fingerprint` (rule id, path, whitespace-normalised source line), so moving a line does not un-baseline it and editing the line does. A baselined finding has `status: "baselined"`, is counted in `summary.baselined`, never affects the exit code, and in SARIF carries `baselineState: "unchanged"` with level `note`. A missing or malformed baseline file is exit code 2 (`bad-baseline`).

## Other formats

- `--format agent`: compact plain text for an LLM's context (rule id, `path:line`, fix, how to silence).
- `--format sarif`: SARIF 2.1.0 for GitHub code scanning, one result per location; `P0` maps to `error` (`security-severity` 8.0), `P1` to `warning` (5.0); each result carries `partialFingerprints.primaryLocationLineHash` (`<fingerprint>:1`); suppressed findings carry `suppressions`.
- `--list-rules --format json` returns `{"schema", "rules": [{id, title, severity, summary, fix, fix_variants, ref, tags, confidence}]}`; `--explain <rule-id> --format json` returns one such rule object. `fix_variants` maps a framework name to the fix text used for findings in files of that framework.
