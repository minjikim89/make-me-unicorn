# Launch checklists

Before it was a gate, make-me-unicorn was a launch checklist for solo builders, and that part still ships. It tracks what a project has decided and done; [`mmu vibecheck`](../README.md) checks what the code actually does.

## Contents

- 15 blueprint categories in [`docs/blueprints/`](./blueprints/) (frontend, backend, auth, billing, devops, security, monitoring, SEO, legal, performance, testing, CI/CD, email, analytics, accessibility), about 570 checklist items, plus industry blueprints for AI products and marketplaces
- Six launch gates, M0 to M5
- Focused session modes that load only the documents a session needs
- Optional LLM-assisted setup and review (`[llm]` extra)
- Idea validation against Hacker News and Reddit threads (`[validate]` extra)

## Quick start

```bash
pip install make-me-unicorn
cd your-project
mmu init          # writes .mmu/config.toml and the checklist docs
mmu scan          # ticks items it can verify from the code (use --dry-run to preview)
mmu status --why  # score breakdown
mmu next          # what to do next
```

`mmu init --force` refreshes the checklist templates and keeps your progress, edited docs and config. `mmu init --reset` starts over.

## Personalize

Not every project needs billing or i18n:

```toml
# .mmu/config.toml
[features]
billing = false
i18n = false

[architecture]
framework = "nextjs"
```

Items for disabled features do not count against the score.

## Launch gates

```
M0 Problem Fit    Do you know who it is for and why?
M1 Build Fit      Does the core product work end to end?
M2 Revenue Fit    Can someone pay you, and get a refund?
M3 Trust Fit      Privacy policy, support path, logging?
M4 Growth Fit     Will shared links look right? Can people find you?
M5 Scale Fit      What happens at 3 a.m.?
```

```bash
mmu gate --stage M0
```

## Session modes

One mode per session; each loads only the documents it needs.

```bash
mmu start --mode backend      # architecture, sprint, ADR logs
mmu start --mode billing      # pricing, billing checklist, compliance
mmu start --mode growth       # SEO checklist, metrics
mmu close                     # end the session with structured notes
```

## LLM features (optional)

```bash
pip install 'make-me-unicorn[llm]'
export ANTHROPIC_API_KEY=...
```

| Command | What it does |
|---------|-------------|
| `mmu init --interactive` | Five questions, then drafts strategy, product, pricing, architecture and UX docs |
| `mmu start --mode X --agent` | Formats session context for a coding agent |
| `mmu doctor --deep` | Reviews the code against the docs |
| `mmu generate strategy` | Generates or updates core docs |

The default model is `claude-sonnet-5-5`; override it with `MMU_MODEL`. Without the extra, these commands are unavailable and everything else works.

## Validate an idea

```bash
pip install 'make-me-unicorn[validate]'
mmu validate "AI tutor for kids" --limit 30
```

Free by default: public Reddit and HN Algolia search, local VADER sentiment, no API keys. The report is saved to `reports/validate/<slug>-<hash>.md`. `--llm` adds an Anthropic-written summary after a cost prompt.

## Badge and score card

```bash
mmu badge                                   # markdown badge
mmu badge --format svg --output badge.svg
mmu badge --format endpoint --output badge.json   # shields.io endpoint JSON for a live badge
mmu share                                   # text score card
```

## MCP blueprint tools

`mmu serve-mcp` also exposes `mmu_list_blueprints`, `mmu_get_blueprint`, `mmu_list_idea_templates` and `mmu_validate_idea` next to the vibecheck tools.

## Command reference

```bash
mmu init | scan | status --why | next | show <area> | check <area> <n> | uncheck <area> <n>
mmu gate --stage M0..M5 | doctor | doctor --deep | start --mode <mode> | close
mmu badge | share | validate "<idea>" | generate <doc> | serve-mcp
```

Full specification: [SPEC.md](../SPEC.md). A filled example project lives in [`examples/filled/tasknote/`](../examples/filled/tasknote/).
