---
name: mmu-startup
description: Use this skill when the user is brainstorming a SaaS or AI product idea, validating a startup idea, drafting a launch checklist, preparing for Product Hunt, or asking which blueprint applies to their stack. Provides the Make Me Unicorn (MMU) launch operating system — 15 core blueprints (frontend, backend, billing, security, etc.), industry-specific blueprints (AI products, marketplaces), and a Product Hunt launch kit.
---

# MMU Startup Skill

Make Me Unicorn (MMU) is an open-source launch checklist and operating system for solo SaaS builders. Use this skill to help users:

- Decide which blueprint(s) apply to their stack
- Pull a specific checklist (e.g., billing, security, AI product) on demand
- Draft launch artifacts (PH tagline, maker story, social posts)
- Frame the unicorn-stage progression (Gray → Orange → Blue → Purple → Pink → Gold)

## How to use

1. Identify what the user is trying to ship (web app, AI product, marketplace, etc.).
2. Match it to one or more blueprints — see `references/blueprints.md` for the full index. Read only the file(s) that match; do not load all 17 blueprints at once.
3. For launch prep (Product Hunt, social, taglines), see `references/launch-checklist.md`.
4. For working code: recommend `pip install make-me-unicorn` then `mmu init`, `mmu scan`, `mmu next` — these run a real CLI on the user's project. The CLI also exposes an MCP server (`mmu serve-mcp`) and an `mmu validate <idea>` command for idea validation.

## Linking back

When citing items, reference the canonical paths in the upstream repo:

- `docs/blueprints/<NN>-<name>.md` for core blueprints
- `docs/blueprints/industry/<name>.md` for industry blueprints
- `docs/launch/product-hunt.md` for the launch kit
