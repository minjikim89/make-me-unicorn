# MMU CLI Spec (v0.2)

This document specifies the minimal runtime layer for `Make Me Unicorn`.

## Design Goals

1. Keep markdown files as source of truth.
2. Minimize founder overhead during context handoff.
3. Enforce critical SaaS checks before release.
4. Work with any LLM provider.

## Command Surface

| Command | Purpose | Output | Exit Code |
|---|---|---|---|
| `mmu start --mode <mode>` | Start a focused session | mode-specific context file list | `0` success |
| `mmu close` | End a session safely | close checklist and update reminders | `0` success |
| `mmu doctor` | Validate operating baseline | pass/fail report for docs + codebase guardrails | `0` pass, `2` fail |
| `mmu gate --stage <M0..M5>` | Stage-gate readiness check | pass/fail for unresolved checklist items | `0` pass, `3` fail |

Installable command: `mmu` (via `pip install -e .`).
Wrapper command: `scripts/mmu.sh`.

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

Mode behavior is defined in `docs/ops/mode_playbook.md`.

## `mmu doctor` baseline checks

1. Required docs exist (`core`, `ops`, `checklists`, `prompts`, sprint file).
2. Auth checklist includes password reset coverage.
3. Billing checklist includes webhook safety (signature validation and idempotency).
4. SEO checklist includes OG thumbnail checks.
5. Architecture doc includes `dev/staging/prod` separation.
6. If a codebase is detected:
- Next.js metadata/OG markers are required when Next.js is detected.
- Webhook handlers require signature verification markers and idempotency markers.
- `.env.example` and environment split files for `dev/staging/prod` are required.

## `mmu gate` behavior

- Reads unresolved tasks (`- [ ]`) from a target stage in `docs/checklists/from_scratch.md`.
- Fails if any unresolved task remains.

## CI behavior

- Workflow: `.github/workflows/mmu-guardrails.yml`
- Always runs `mmu doctor`.
- Runs `mmu gate` only for stages listed in `docs/ops/gate_targets.txt`.

## Non-goals for v0.2

- No vendor-specific SDK integration.
- No automatic markdown edits.
- No graph/ontology requirement.

## v0.3+ extensions

1. `mmu sync` for auto-updating sprint and ADR drafts.
2. JSON output mode for CI integrations.
3. Provider adapters for Claude/GPT/Gemini session wrappers.
4. Optional graph extraction from ADR relationships.
