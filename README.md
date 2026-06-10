<div align="center">

# Make Me Unicorn

**Catch what AI-generated SaaS code misses — before it costs you users, money, or trust.**

The open-source launch checklist and operating system for solo builders.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/make-me-unicorn?color=blue)](https://pypi.org/project/make-me-unicorn/)
[![PyPI downloads](https://img.shields.io/pypi/dm/make-me-unicorn?color=blue)](https://pypi.org/project/make-me-unicorn/)
[![CLI](https://img.shields.io/badge/cli-mmu-f59e0b.svg)](./SPEC.md)
[![Guardrails CI](https://img.shields.io/badge/ci-doctor%20%2B%20gates-22c55e.svg)](./.github/workflows/mmu-guardrails.yml)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-16a34a.svg)](./CONTRIBUTING.md)

**English** · [🇰🇷 한국어](./README.ko.md) · [🇯🇵 日本語](./README.ja.md) · [🇨🇳 简体中文](./README.zh-CN.md) · [🇪🇸 Español](./README.es.md)

<img src="./assets/brand/unicorn-hero.png" alt="Make Me Unicorn mascot" width="960" />

<img src="./assets/demo.gif" alt="MMU CLI demo — init, scan, status, next" width="720" />

</div>

## 60-Second Demo

```bash
pip install make-me-unicorn   # or zero-install: uvx make-me-unicorn
cd your-project
mmu init && mmu scan && mmu
```

```text
  MAKE ME UNICORN - STATUS DASHBOARD

          .--*--.
         / *v*  \
        |       |
         \ ___ /
          '---'

  Stage: HATCHING    ######..............  22%  (124/551)

  LAUNCH GATES  (16/26)
    M0 Problem Fit         ################   4/4   PASS
    M1 Build Fit           ################   5/5   PASS
    M2 Revenue Fit         ############....   3/4   OPEN
    M3 Trust Fit           ################   4/4   PASS
    M4 Growth Fit          ########........   2/4   OPEN
    M5 Scale Fit           ####............   1/5   OPEN
```

Your unicorn evolves as you build: **Egg → Hatching → Foal → Young → Unicorn → Legendary.**

## Add a Badge to Your README

Show your launch readiness to the world. One command:

```bash
mmu badge                          # get markdown badge
mmu badge --format svg -o badge.svg  # save as SVG file
mmu badge --clipboard              # copy to clipboard
```

Then paste in your README:

[![Launch Readiness 68% — Young Unicorn](https://img.shields.io/badge/launch%20readiness-68%25%20young%20unicorn-9c27b0?style=flat-square)](https://github.com/minjikim89/make-me-unicorn)

*Every badge links back here. Every README becomes a growth channel.*

## Share Your Score

```bash
mmu share                     # print shareable score card
mmu share --clipboard         # copy to clipboard (macOS)
```

```
┌─────────────────────────────────────────────┐
│  Make Me Unicorn — Launch Readiness         │
│                                             │
│  Score: 68%  Stage: YOUNG UNICORN           │
│                                             │
│  M0 Problem Fit    ████████████████  PASS   │
│  M1 Build Fit      ████████████████  PASS   │
│  M2 Revenue Fit    ██████████░░░░░░  OPEN   │
│  M3 Trust Fit      ████████████████  PASS   │
│  M4 Growth Fit     ████████░░░░░░░░  OPEN   │
│  M5 Scale Fit      ████░░░░░░░░░░░░  OPEN   │
│                                             │
│  Stack: Next.js · Stripe · SSR              │
│  pip install make-me-unicorn                │
│  github.com/minjikim89/make-me-unicorn      │
│  #MakeMeUnicorn                             │
└─────────────────────────────────────────────┘

Check your SaaS launch readiness:
https://github.com/minjikim89/make-me-unicorn
```

## The Problem

You code with AI. You ship fast. But then:

| What goes wrong | What it costs you |
|-----------------|-------------------|
| Forget password reset while building login | Users locked out on day 1 |
| Skip webhook signature verification | Attackers replay payment events |
| Launch without OG tags | Every shared link looks broken |
| Lose context between AI sessions | Re-explain your project from scratch |
| No refund policy | First dispute = frozen Stripe account |

**You're not failing at coding. You're failing at tracking what matters.**

## What MMU Covers

<table>
<tr>
<td width="33%">

**Building**
- Frontend (responsive, a11y, forms)
- Backend (API, DB, queues)
- Auth (login, reset, OAuth, sessions)
- Billing (Stripe, webhooks, refunds)
- Testing (unit, E2E, agent safety)

</td>
<td width="33%">

**Launching**
- SEO (OG tags, sitemap, meta)
- Legal (privacy, terms, GDPR)
- Security (CORS, rate limits, secrets)
- Performance (caching, lazy load)
- CI/CD (pipeline, rollback plan)

</td>
<td width="34%">

**Operating**
- Monitoring (errors, uptime, alerts)
- Analytics (funnel, retention, events)
- Email (transactional, templates)
- Accessibility (WCAG, keyboard nav)
- Reliability (backup, incident plan)

</td>
</tr>
</table>

**670+ items. 15 categories. 6 launch gates. Zero guesswork.**

## How Is MMU Different?

| | Scope | Lives where | Agent-native | Tracks progress |
|---|---|---|---|---|
| **MMU** | Full SaaS: code + billing + legal + growth + ops | Your repo, plain markdown | ✅ Claude plugin + MCP server | ✅ Score, gates, evolving dashboard |
| Lighthouse | Frontend performance/a11y/SEO only | Browser/CI | ❌ | Per-run score, no project memory |
| Vendor launch checklists (Vercel, Stripe docs) | One vendor's slice | Their docs site | ❌ | ❌ Read-only |
| Static checklist repos / Notion templates | Varies, usually unverifiable | Copy-paste | ❌ | ❌ Manual, goes stale |
| AI code reviewers (CodeRabbit etc.) | Code diffs | PR workflow | Partially | Per-PR, no launch view |

MMU is not a linter and not a docs site — it's the **operating layer between your AI coding sessions and an actual launch**: a verifiable checklist your CLI, CI, and AI agents all read and update.

## Vibe Check Your AI-Generated Code

45% of AI-generated code ships with vulnerabilities. One command scans for the gaps AI assistants miss most:

```bash
mmu vibecheck
```

```text
Vibe check — what AI-generated code usually misses

  ✗ (P0) secrets: possible hardcoded secrets in 1 file(s): Stripe live secret key
  ✗ (P0) webhook-signature: webhook handlers found but no signature verification markers
        ↳ Verify provider signatures or attackers can forge payment events.
  ✗ (P0) password-reset: auth code detected but no password reset flow markers
        ↳ The #1 day-one lockout: users who can log in but can never get back in.
  ⚠ (P1) rate-limiting: server framework detected but no rate limiting markers

Vibe check result: 3 launch-blocking issue(s), 1 warning(s)
```

Checks: hardcoded secrets · unignored `.env` · webhook signature + idempotency · password reset flow · f-string SQL · rate limiting · wildcard CORS · `DEBUG = True` · error monitoring. P0 findings exit non-zero, so it drops straight into CI.

## Personalize Your Checklist

Not every project needs billing or i18n. MMU adapts:

```bash
mmu init                      # generates .mmu/config.toml
```

```toml
[features]
billing = false               # no Stripe? billing items won't count against you
i18n = false

[architecture]
framework = "nextjs"
```

Your score reflects **only what applies to your project**. `mmu status --why` shows the breakdown — like Lighthouse, but for SaaS readiness.

## 6 Launch Gates

Phase exits. Don't skip ahead.

```
M0 Problem Fit    →  Do you know WHO and WHY?
M1 Build Fit      →  Does the core product work end-to-end?
M2 Revenue Fit    →  Can someone pay you? And get a refund?
M3 Trust Fit      →  Privacy policy? Support path? Logging?
M4 Growth Fit     →  Will links look right? Can people find you?
M5 Scale Fit      →  What happens at 3am?
```

Run `mmu gate --stage M0` to verify.

## 12 Operating Modes

One mode per session. Each loads only the docs you need — prevents the #1 problem with AI coding: **context overload**.

```bash
mmu start --mode backend      # loads: architecture.md, sprint, ADR logs
mmu start --mode billing      # loads: pricing.md, billing checklist, compliance
mmu start --mode growth       # loads: SEO checklist, metrics
```

## AI Integration (Optional)

MMU works without AI. But with Claude, it gets powerful:

```bash
pip install make-me-unicorn[llm]
export ANTHROPIC_API_KEY=sk-ant-...
```

| Command | What happens |
|---------|-------------|
| `mmu init --interactive` | Answer 5 questions → Claude writes your strategy, product, pricing, architecture, and UX docs |
| `mmu start --mode X --agent` | Auto-formats session context for Claude Code or any LLM |
| `mmu doctor --deep` | Claude reads your code, flags mismatches, security gaps, blind spots |
| `mmu generate strategy` | Generates or updates core docs based on current project state |

Core CLI stays zero-dependency. AI features degrade gracefully.

## Use as a Claude Skill

MMU is also packaged as a Claude Code plugin and Anthropic Agent Skill, so any Claude-based agent (Claude Code, Claude Desktop, or any tool that supports the Agent Skills spec — including OpenAI Codex CLI) can auto-invoke MMU when the user mentions a startup idea, validation, launch checklist, or Product Hunt prep.

```bash
# In Claude Code:
/plugin marketplace add minjikim89/make-me-unicorn
/plugin install make-me-unicorn
```

The skill auto-loads only the blueprint(s) relevant to the conversation (progressive disclosure), so it stays cheap on context.

## MCP Server Mode

MMU also runs as an MCP (Model Context Protocol) server, so any MCP-compatible agent (Claude Code, Claude Desktop, Cursor, Gemini CLI) can call MMU's blueprints and templates as native tools.

```bash
pip install make-me-unicorn[mcp]
mmu serve-mcp                          # stdio transport (default)
mmu serve-mcp --transport sse          # SSE transport
```

Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mmu": {
      "command": "mmu",
      "args": ["serve-mcp", "--root", "/path/to/cloned/make-me-unicorn"]
    }
  }
}
```

Tools exposed:

- `mmu_list_blueprints` — list 17 blueprints (15 core + 2 industry)
- `mmu_get_blueprint(name)` — fetch full blueprint markdown
- `mmu_list_idea_templates` — list start/close/ADR prompts + Product Hunt kit
- `mmu_validate_idea(idea)` — validate against real HN + Reddit threads: verdict, sentiment, competitors, top threads (free mode, no API keys; needs the `[validate]` extra)

## Validate an Idea

Pull real signal from HN + Reddit before you build:

```bash
pip install make-me-unicorn[validate]
mmu validate "AI tutor for kids" --limit 30
```

Default mode is **free** — no API keys, no paid calls. Public Reddit + HN Algolia search, local VADER sentiment, capitalized-token competitor surface. Saves a markdown report to `reports/validate/<slug>.md`.

For a 1-page validation verdict synthesized from the threads:

```bash
mmu validate "AI tutor for kids" --llm
# Prompts for cost confirmation (~$0.05-0.20). Use -y to skip.
```

`--llm` is opt-in — the default flow never calls the Anthropic API.

## Full Command Reference

```bash
mmu                           # status dashboard
mmu init                      # bootstrap project
mmu init --interactive        # LLM-guided setup (5 questions → 5 docs)
mmu scan                      # auto-detect tech stack
mmu status --why              # score breakdown
mmu next                      # prioritized next actions
mmu show frontend             # drill into any category
mmu check frontend 3          # mark item done
mmu gate --stage M0           # verify gate readiness
mmu doctor                    # guardrail health checks
mmu doctor --deep             # LLM-powered semantic review
mmu vibecheck                 # scan for AI-generated code blind spots (secrets, webhooks, …)
mmu share                     # shareable score card
mmu badge                     # README badge (markdown/svg/html)
mmu start --mode backend      # start focused session
mmu close                     # end session with structured memory
```

## Who This Is For

| You are... | MMU helps you... |
|------------|------------------|
| **A founder coding with AI** | Stop re-explaining your project. Keep context across tools. |
| **A frontend developer** | Know exactly what to build: auth flows, error states, OG tags. |
| **A product manager** | Structured PRD, pricing strategy, launch checklist — all in markdown. |
| **A fullstack builder** | Track everything in one place. Nothing slips through. |

## Example: TaskNote

A fully filled-out example:

```
examples/filled/tasknote/
├── docs/core/strategy.md      ← ICP, value prop, competitors
├── docs/core/product.md       ← MVP scope, user journey, P0/P1
├── docs/core/pricing.md       ← Free/Pro/Team, billing rules
├── docs/core/architecture.md  ← Next.js + FastAPI + Postgres
├── docs/adr/001_billing_provider_choice.md  ← Why Stripe?
└── current_sprint.md          ← This week's 3 goals
```

## Requirements

- Python `3.10+`
- Core CLI: zero external dependencies
- AI features: `pip install make-me-unicorn[llm]`

## CI Guardrails

`mmu doctor` runs on every PR. `mmu gate` runs for stages listed in `docs/ops/gate_targets.txt`.

## Contributing

See `CONTRIBUTING.md`.

## License

MIT. See `LICENSE`.

<!-- MCP Registry ownership proof -->
mcp-name: io.github.minjikim89/make-me-unicorn
