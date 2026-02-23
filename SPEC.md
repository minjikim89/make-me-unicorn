# MMU CLI Spec (v0.3)

This document defines the current runtime behavior for `Make Me Unicorn`.

## Design goals

1. Keep markdown files as source of truth.
2. Reduce founder overhead during context handoff.
3. Enforce critical SaaS checks before release.
4. Stay provider-agnostic for LLM workflows.

## Command surface

| Command | Purpose | Output | Exit Code |
|---|---|---|---|
| `mmu init` | Bootstrap baseline docs/checklists/prompts | created/skipped file report | `0` success |
| `mmu start --mode <mode>` | Start a focused session | mode file list and optional context bundle | `0` success |
| `mmu snapshot --target <path>` | Run project diagnostic snapshot | terminal summary + optional markdown report | `0` success |
| `mmu close` | End a session safely | close checklist and update reminders | `0` success |
| `mmu doctor` | Validate operating baseline | pass/fail report for docs and codebase guardrails | `0` pass, `2` fail |
| `mmu gate --stage <M#>` | Stage-gate readiness check | pass/fail for unresolved checklist items | `0` pass, `3` fail |

Installable command: `mmu` (via `pip install -e .`).
Wrapper command: `scripts/mmu.sh`.

## Global options

- `--json`: print structured JSON instead of plain text.

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

- `--force`: overwrite existing scaffold files.

Behavior:

- Creates baseline docs/checklists/prompts used by `doctor`, `gate`, and mode sessions.
- Skips existing files unless `--force` is provided.

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
