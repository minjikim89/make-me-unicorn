# Mode Playbook

Modes lock context and reduce execution drift.

## Rules

1. Use one primary mode per session.
2. If mode changes, log the reason in `current_sprint.md`.
3. If a decision is made, create or update an ADR.

## Modes

### problem

- Purpose: define ICP, pain, and hypothesis
- Inject: `docs/core/strategy.md`, `docs/research/*`
- Output: validated problem statement and assumptions

### product

- Purpose: scope and prioritize features
- Inject: `docs/core/product.md`, `docs/ops/roadmap.md`
- Output: P0/P1 list and sprint scope

### design

- Purpose: UX flows, UI decisions, copy
- Inject: `docs/core/ux.md`, `docs/core/product.md`
- Output: UX decisions and content draft

### frontend

- Purpose: implement user-facing experience
- Inject: `docs/core/architecture.md`, `current_sprint.md`
- Output: feature implementation with UI states

### backend

- Purpose: implement API, data model, async jobs
- Inject: `docs/core/architecture.md`, `current_sprint.md`, `docs/adr/*`
- Output: backend changes and operational notes

### auth

- Purpose: identity, session, and access control
- Inject: `docs/checklists/auth_security.md`, `docs/core/architecture.md`
- Output: verified auth and authorization baseline

### billing

- Purpose: plans, checkout, subscription lifecycle
- Inject: `docs/core/pricing.md`, `docs/checklists/billing_tax.md`, `docs/ops/compliance.md`
- Output: pricing and billing flows validated

### growth

- Purpose: discoverability and distribution readiness
- Inject: `docs/checklists/seo_distribution.md`, `docs/ops/metrics.md`
- Output: metadata/OG/indexing/attribution baseline

### compliance

- Purpose: legal and data-handling baseline
- Inject: `docs/ops/compliance.md`, `docs/core/pricing.md`
- Output: policy and process alignment

### reliability

- Purpose: monitoring, backup, and incident readiness
- Inject: `docs/ops/reliability.md`, `docs/checklists/release_readiness.md`
- Output: reliability checklist closure

### analytics

- Purpose: event model and experiment operations
- Inject: `docs/ops/metrics.md`, `docs/core/product.md`
- Output: event schema and experiment plan

### launch

- Purpose: release and operational handoff
- Inject: `docs/checklists/release_readiness.md`, `docs/ops/roadmap.md`
- Output: go/no-go release decision

## Parallel Session Rules

When running multiple agent sessions simultaneously (e.g., git worktrees):

1. **Branch isolation**: each session works on a separate branch.
2. **No shared state files**: `current_sprint.md` and `.mmu/` are branch-local.
3. **Conflict prevention**:
   - Only one session modifies `docs/core/*` at a time.
   - `docs/ops/known_issues.md` uses append-only entries.
   - ADR files use timestamp-prefixed names to avoid collisions.
4. **Worktree setup**: `git worktree add ../project-billing billing-work`
5. **Sync points**: check in after each session close before starting the next.
6. **Merge order**: merge decision-heavy sessions first, execution sessions second.
