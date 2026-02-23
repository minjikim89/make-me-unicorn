# 8-Week Execution PRD (Pre-10K Path)

## Goal

Validate product-market pull for a global developer audience by improving time-to-value and perceived utility.

## Positioning

- Tagline: `SaaS from scratch, without execution drift.`
- Core promise: `Catch what AI-generated SaaS code misses.`

## What we will build

### W1-W2: Activation baseline

1. Add `mmu init` scaffold command (local project bootstrap).
2. Publish package to PyPI (non-editable install path).
3. Ship `v0.3.0` release with clear install docs.

Success metric:

- New user can run first meaningful command in under 60 seconds.

### W3-W4: Killer workflow

1. Add `mmu export --target claude|cursor|copilot`.
2. Generate LLM-ready context instructions from current docs and sprint state.
3. Add examples showing before/after quality of AI-assisted implementation.

Success metric:

- Users can produce actionable LLM context artifacts in one command.

### W5-W6: Community loops

1. Add `mmu doctor --badge` output helper.
2. Add checklist packs structure (`stacks/*`, `verticals/*`) with 2-3 starter packs.
3. Add contribution docs for writing new packs.

Success metric:

- At least 3 external PRs on packs/templates.

### W7-W8: Distribution

1. Publish launch posts (HN, Reddit, Dev.to, X threads).
2. Publish demo content: "run doctor on real projects" style examples.
3. Track conversion funnel from views -> installs -> repeat usage.

Success metric:

- Clear week-over-week growth in installs and stars.

## Non-goals (for this 8-week window)

1. No ontology/graph layer.
2. No direct LLM API integration (keep provider-agnostic file export model).
3. No early monetization.
4. No broad plugin framework before usage signals justify complexity.

## KPIs

1. Time-to-first-value (TTFV): target < 60s.
2. Weekly active repos running `doctor`.
3. Exports generated per week (`mmu export`).
4. External contributors and merged PR count.
5. GitHub stars (leading signal, not sole KPI).

## Risks and mitigations

1. Risk: perceived as "just docs".
- Mitigation: prioritize `init` and `export` before adding more templates.

2. Risk: CI friction discourages adoption.
- Mitigation: keep strict gates opt-in (`gate_targets.txt`).

3. Risk: message remains too narrow.
- Mitigation: market as AI-built SaaS reliability tool, not founder-only framework.
