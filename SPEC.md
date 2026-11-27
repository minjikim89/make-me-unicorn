# MMU CLI Spec (v0.9)

This document defines the current runtime behavior for `Make Me Unicorn`.

## Design goals

1. Stop launch-blocking gaps in agent-written code at the commit: deterministic, offline, no account, fail-open.
2. Keep markdown files as source of truth.
3. Reduce founder overhead during context handoff.
4. Enforce critical SaaS checks before release.
5. Stay provider-agnostic for LLM workflows.

## Command surface

| Command | Purpose | Output | Exit Code |
|---|---|---|---|
| `mmu` (no subcommand) | Same as `mmu vibecheck` on the current directory | vibecheck report | as `mmu vibecheck` |
| `mmu install --claude\|--codex\|--cursor\|--gemini\|--git\|--agents-md\|--skill\|--all` | Register the gate as agent hooks, a git pre-commit hook, an AGENTS.md block or an Agent Skill | created/updated/unchanged report (`--dry-run`, `--uninstall`) | `0` success, `2` nothing to install or invalid config |
| `mmu hook [--host H] [--event E]` | Hook entry point called by agent hosts; reads the host's hook JSON on stdin | host-specific block/allow response | host-specific (see "Hook contract") |
| `mmu serve-mcp` | MCP server over stdio (extra `[mcp]`) | MCP protocol | `0` on shutdown |
| `mmu init` | Bootstrap baseline docs/checklists/prompts | created/skipped file report | `0` success |
| `mmu start --mode <mode>` | Start a focused session | mode file list and optional context bundle | `0` success |
| `mmu snapshot --target <path>` | Run project diagnostic snapshot | terminal summary + optional markdown report | `0` success |
| `mmu close` | End a session safely | close checklist and update reminders | `0` success |
| `mmu doctor` | Validate operating baseline | pass/fail report for docs and codebase guardrails | `0` pass, `2` fail |
| `mmu vibecheck` | Scan for AI-generated code blind spots | per-rule findings with `path:line`, fix, and rule id (`--format text\|json\|sarif\|agent`) | `0` no blockers, `1` P0 findings, `2` scanner error |
| `mmu gate --stage <M#>` | Stage-gate readiness check | pass/fail for unresolved checklist items | `0` pass, `3` fail |
| `mmu badge` | Generate README badge (markdown/svg/html) | badge snippet | `0` success |
| `mmu share` | Generate shareable score card | plain-text card with CTA | `0` success |

Installed commands: `mmu` and `make-me-unicorn` (same entry point), via `pip install make-me-unicorn` or `uvx make-me-unicorn ...`.
Wrapper command: `scripts/mmu.sh`.

## Global options

- `--json`: print structured JSON instead of plain text.
- `--root <path>`: project root.
- Both work before or after the subcommand (`mmu --json --root ../app doctor`).
- `--version`: print the package version.
- Output is UTF-8 on every platform.

## Start command

```bash
mmu start --mode backend --emit bundle --output .mmu/context.md
```

Options:

- `--mode`: one of the 12 operating modes.
- `--emit list|bundle`: show file list (default) or full context bundle.
- `--output <path>`: write generated bundle to file.
- `--clipboard`: copy bundle to clipboard on macOS (`pbcopy`).

## Init command

```bash
mmu init --root .
```

Options:

- `--force`: refresh existing checklist templates (`docs/blueprints/`, `docs/checklists/`). Checked items are carried over; other existing docs and `.mmu/config.toml` are kept.
- `--reset`: overwrite everything, wiping checklist progress and regenerating `.mmu/config.toml`.

Behavior:

- Creates baseline docs/checklists/prompts used by `doctor`, `gate`, and mode sessions.
- Skips existing files unless `--force` or `--reset` is provided.

## Snapshot command

```bash
mmu snapshot --target ../my-project --no-md
```

Options:

- `--target <path>`: project path to scan (default: current directory).
- `--output <path>`: markdown report path (default: `SNAPSHOT.md`).
- `--no-md`: terminal-only output without saving a report.

## Modes

- `problem`
- `product`
- `design`
- `frontend`
- `backend`
- `auth`
- `billing`
- `growth`
- `compliance`
- `reliability`
- `analytics`
- `launch`

Mode behavior is documented in `docs/ops/mode_playbook.md`.

## Doctor checks

Baseline checks:

1. Required docs exist (`core`, `ops`, `checklists`, `prompts`, sprint file).
2. Auth checklist includes password-reset coverage.
3. Billing checklist includes webhook and idempotency coverage.
4. SEO checklist includes OG coverage.
5. Architecture doc includes `dev/staging/prod` split.

Codebase checks (only when source files are detected):

1. Next.js detected -> metadata/OG markers required.
2. Webhook handlers detected -> signature and idempotency markers required.
3. `.env.example` required.
4. Environment split files for `dev/staging/prod` required.

Config override:

- `.mmu/config.toml`
- `[doctor] skip_paths = ["path/to/skip", "another/path"]`

## Vibecheck checks

Deterministic, read-only scan. No network, no LLM. `mmu vibecheck --list-rules` prints the registry and `mmu vibecheck --explain <rule-id>` prints one rule's detection logic and framework-specific fixes.

- P0 (blocking): `secrets`, `client-bundle-secrets`, `supabase-rls`, `webhook-signature`, `sql-fstring`, `code-injection`, `jwt-secret-default`, `unsafe-deserialization`, `git-config-exec`.
- P1 (warning): `llm-route-unthrottled`, `admin-route-no-auth`, `password-reset`, `webhook-idempotency`, `rate-limiting`, `cors-wildcard`, `dangerous-html`, `jwt-localstorage`, `stack-trace-leak`, `sourcemaps-exposed`, `env-not-ignored`, `disabled-ssl`, `debug-mode`, `error-monitoring`.
- Severity policy: P0 only with specific evidence; findings about something being absent are P1. Comments are never evidence.
- Scope: whole project by default; `--staged`, `--changed`, `--since <ref>`, `--files-from <file|->` limit findings to those files. Repo-level findings (dotenv files, `.git/config`) stay in scope.
- Skipped: vendor and build directories at any depth, files over 1 MB, minified bundles, git-ignored files. Extra excludes: `[vibecheck] skip_paths` (or `[doctor] skip_paths`) in `.mmu/config.toml`.
- Suppression: `mmu-ignore[<rule-id>]: <reason>` on the flagged line or the line above (a reason is required), or `[vibecheck] ignore = ["glob:rule-id"]`. Baseline: `--write-baseline`, `--baseline`.
- Output: `--format text|json|sarif|agent`, `--output <file>`. JSON schema `mmu.vibecheck/v1`: `docs/vibecheck-json-schema.md`.
- Exit codes: `0` nothing at or above `--fail-on` (default `P0`), `1` blocking findings, `2` the scan could not run.
- Accuracy and limits: `docs/benchmark.md`.

## Hook contract

`mmu hook` reads one hook payload on stdin and answers in the host's format. `mmu install` writes the `--host` and `--event` arguments explicitly.

| Event | Claude Code | Codex CLI | Cursor | Gemini CLI |
|---|---|---|---|---|
| `pre-shell` (git commit / push) | `PreToolUse` on `Bash`; block = `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` | same as Claude Code | `beforeShellExecution`; block = `{"permission": "deny"}` | `BeforeTool` on `run_shell_command`; block = `{"decision": "deny"}` |
| `stop` | `Stop`; block = `{"decision": "block", "reason": ...}` | same | `stop`; `followup_message` | `AfterAgent`; `{"decision": "deny"}` |
| `post-edit` | `PostToolUse` on `Edit\|Write\|MultiEdit`; `additionalContext` | `PostToolUse` on `apply_patch` | not registered | not registered |

- Gated: `git commit` / `git push` in command position, as a POSIX shell splits the command. Text that only mentions them (an `echo`, a comment, a heredoc body, a commit message) is not gated; `cd`, `pushd`, `git -C`, `--git-dir` and `--work-tree` pick the repository; `bash -c` and `eval` are followed. Not followed: a variable in command position and git aliases.
- Commit scope: `--staged`; when the commit records other content (`-a`, pathspecs, `git add ... && git commit`), exactly those files (`--files-from -`). Push scope: files touched by the commits that no remote-tracking ref has yet; nothing new, no scan; no remote-tracking refs at all, the whole project.
- Exit code: always `0`, blocks included. A host reads exit 2 as a block, so a launcher failure must not produce one; `mmu install` ends the command in `|| true` on macOS and Linux for the same reason.
- Stop scope (Claude Code, Codex): P0 findings in files the agent edited in this session, recorded by the post-edit hook under the git dir. No recorded edits: allow. Cursor and Gemini: `--changed`.
- Loop bounds: the host's own flag (`stop_hook_active`, `loop_count`) and `MMU_STOP_MAX` (default 3 per session).
- Fail-open: if the scanner errors or times out, the action is allowed and one line says so.
- Environment: `MMU_HOOK_DISABLE=1` (all hooks; per command as a prefix or exported earlier in the same command), `MMU_HOOK_ON_PUSH_ONLY=1` (gate pushes only), `MMU_STOP_DISABLE=1`, `MMU_STOP_MAX`.

## Gate behavior

- Stage format supports `M<number>` (`M0`, `M1`, `M6`, ...).
- Headings are parsed from `docs/checklists/from_scratch.md` using markdown stage headers.
- Unresolved checkboxes (`- [ ]`) in the matching stage cause `NOT PASS`.

## CI behavior

Workflow: `.github/workflows/mmu-guardrails.yml`

1. Lint (`ruff`)
2. Type check (`mypy`)
3. Unit tests (`unittest`)
4. Guardrails (`doctor` + configured `gate`s)

Configured gates are read from `docs/ops/gate_targets.txt`.

## Non-goals (current)

- Vendor-specific SDK integration.
- Full semantic security validation beyond heuristics.
- Automatic writing of business docs without explicit user control.
