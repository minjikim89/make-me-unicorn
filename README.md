<div align="center">

# Make Me Unicorn

**Stop building blind. Ship your SaaS with confidence.**

The open-source launch checklist and operating system for solo builders.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![Status: v0.4](https://img.shields.io/badge/status-v0.4-blue.svg)](./ROADMAP.md)
[![CLI](https://img.shields.io/badge/cli-mmu-f59e0b.svg)](./SPEC.md)
[![Guardrails CI](https://img.shields.io/badge/ci-doctor%20%2B%20gates-22c55e.svg)](./.github/workflows/mmu-guardrails.yml)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-16a34a.svg)](./CONTRIBUTING.md)

**English** · [🇰🇷 한국어](./README.ko.md) · [🇯🇵 日本語](./README.ja.md) · [🇨🇳 简体中文](./README.zh-CN.md) · [🇪🇸 Español](./README.es.md)

<img src="./assets/brand/unicorn-hero.png" alt="Make Me Unicorn mascot" width="960" />

<img src="./assets/demo.gif" alt="MMU CLI demo — init, scan, status, next" width="720" />

</div>

## The Problem

You are building a SaaS product. You use AI to code faster than ever. But then:

> "Wait, did I add a password reset flow?"
>
> "The payment webhook... is it idempotent?"
>
> "Do I have a privacy policy? A refund policy? OG meta tags?"
>
> "What did I decide last week about the auth provider? Why?"

**You are not failing at coding. You are failing at tracking what matters.**

Every solo builder hits the same walls:

| What goes wrong | What it costs you |
|-----------------|-------------------|
| You forget password reset while building login | Users get locked out on day 1 |
| You skip webhook signature verification | Attackers replay payment events |
| You launch without OG tags | Every shared link looks broken |
| You lose context between AI sessions | You re-explain your project from scratch, every time |
| You have no refund policy | First dispute = frozen Stripe account |

MMU catches these **before they cost you users, money, or trust**.

## How It Works

```
mmu init                    # 1. Get 534+ checklist items across 15 categories
mmu scan                    # 2. Auto-detect your stack — pre-check what you already have
mmu                         # 3. See what's done, what's missing
mmu status --why            # 4. Understand your score — what counts, what's skipped
mmu next                    # 5. Get prioritized next actions
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

  BLUEPRINTS  (124/551)
    Frontend           ##########......  18/35  51%
    Backend            ############....  24/46  52%
    Auth               ##########......  16/42  38%
    Billing            ########........  11/36  30%
    ...11 more
```

Your unicorn evolves as you build: Egg → Hatching → Foal → Young → Unicorn → Legendary.

## Personalize Your Checklist

Not every project needs billing. Not every product needs i18n. MMU adapts:

```bash
mmu init                      # select your stack (Next.js, Django, Rails, ...)
```

This generates `.mmu/config.toml` — feature flags that skip irrelevant items:

```toml
[features]
billing = false               # no Stripe? billing items won't count against you
i18n = false
native_mobile = false

[architecture]
framework = "nextjs"
```

Your score reflects **only what applies to your project**. `mmu status --why` shows the breakdown transparently — like Lighthouse, but for your SaaS launch readiness.

## What MMU Covers (So You Don't Have To Remember)

<table>
<tr>
<td width="33%">

**Building the product**
- Frontend (responsive, a11y, forms)
- Backend (API, DB, queues)
- Auth (login, reset, OAuth, sessions)
- Billing (Stripe, webhooks, refunds)
- Testing (unit, E2E, agent safety)

</td>
<td width="33%">

**Preparing to launch**
- SEO (OG tags, sitemap, meta)
- Legal (privacy, terms, GDPR)
- Security (CORS, rate limits, secrets)
- Performance (caching, lazy load)
- CI/CD (pipeline, rollback plan)

</td>
<td width="34%">

**Running it after launch**
- Monitoring (errors, uptime, alerts)
- Analytics (funnel, retention, events)
- Email (transactional, templates)
- Accessibility (WCAG, keyboard nav)
- Reliability (backup, incident plan)

</td>
</tr>
</table>

**534+ items. 15 categories. Zero guesswork.**

## Who This Is For

| You are... | MMU helps you... |
|------------|------------------|
| **A founder coding with AI** | Stop re-explaining your project every session. Keep context across tools. |
| **A frontend developer** | Know exactly what to build: auth flows, error states, responsive breakpoints, OG tags. |
| **A product manager / planner** | Get a structured PRD, pricing strategy, and launch checklist — all in markdown. |
| **A fullstack builder** | Track frontend, backend, billing, and compliance in one place. Nothing slips through. |

## Try It in 60 Seconds

```bash
pip install make-me-unicorn
cd your-project
mmu init && mmu scan && mmu status --why
```

That's it. You'll see your launch readiness score, what's checked, what's missing, and why.

Then run `mmu next` to see what to do first.

## Quick Start

```bash
pip install -e .

# Option A: Start with empty templates, fill them yourself
mmu init

# Option B: Let Claude generate your project docs (requires API key)
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=sk-ant-...
mmu init --interactive        # answer 5 questions → get filled strategy, product, pricing docs
```

Then:

```bash
mmu scan                      # auto-detect your tech stack
mmu                           # see your dashboard
mmu status --why              # see exactly how your score is calculated
mmu next                      # get your top 3 prioritized next actions
mmu show frontend             # drill into any category
mmu check frontend 3          # mark items as done
mmu gate --stage M0           # verify you're ready for the next phase
mmu doctor                    # run guardrail health checks
```

## Share Your Score

Show off your launch readiness. Paste it in your README, tweet it, or drop it in Discord.

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
│  #MakeMeUnicorn                             │
└─────────────────────────────────────────────┘
```

## 6 Launch Gates

Think of these as phase exits. Don't skip ahead.

```
M0 Problem Fit    →  Do you know WHO you're building for and WHY?
M1 Build Fit      →  Does the core product actually work end-to-end?
M2 Revenue Fit    →  Can someone pay you? And get a refund?
M3 Trust Fit      →  Privacy policy? Support path? Logging?
M4 Growth Fit     →  Will shared links look right? Can people find you?
M5 Scale Fit      →  What happens when something breaks at 3am?
```

Run `mmu gate --stage M0` to verify. All unchecked items = NOT PASS.

## 12 Operating Modes

One mode per session. Each mode loads only the docs you need.

```bash
mmu start --mode backend      # loads: architecture.md, sprint, ADR logs
mmu start --mode billing      # loads: pricing.md, billing checklist, compliance
mmu start --mode growth       # loads: SEO checklist, metrics
```

This prevents the #1 problem with AI coding: **context overload**. Your AI assistant gets only what it needs — not your entire project.

## AI Integration (Optional)

MMU works without any AI. But with Claude, it gets powerful:

```bash
pip install make-me-unicorn[llm]
export ANTHROPIC_API_KEY=sk-ant-...
```

| Command | What happens |
|---------|-------------|
| `mmu init --interactive` | Answer 5 questions about your product. Claude writes your strategy, product spec, pricing, architecture, and UX docs. |
| `mmu start --mode X --agent` | Auto-formats your session context — paste directly into Claude Code or any LLM. |
| `mmu doctor --deep` | Claude reads your code and docs, flags mismatches, security gaps, and blind spots. |
| `mmu generate strategy` | Generates or updates any core doc based on your current project state. |

Core CLI stays zero-dependency. AI features are optional and degrade gracefully.

## Session Workflow

Every session follows the same rhythm:

```
1. mmu start --mode backend      ← pick a focus, load relevant docs
2. Build / decide / validate      ← do the work
3. mmu close                      ← log what changed, what's next
```

Session close uses structured tags for memory:

- `[DONE]` — what you completed
- `[DECISION]` — choices made (create ADR if significant)
- `[ISSUE]` — what went wrong (categorize: context gap / wrong direction / doc-code conflict)
- `[NEXT]` — first task for next session

This means your next session starts in **5 seconds**, not 15 minutes of "where was I?"

## Example: TaskNote

See a fully filled-out example of MMU in action:

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
- `pip`
- Core CLI: zero external dependencies
- AI features: `pip install make-me-unicorn[llm]`

## Project Structure

```
make-me-unicorn/
├── src/mmu_cli/           # CLI source (Python)
├── docs/
│   ├── core/              # Strategy, Product, Pricing, Architecture, UX
│   ├── ops/               # Roadmap, Metrics, Compliance, Reliability
│   ├── blueprints/        # 15 category checklists (534+ items)
│   ├── checklists/        # M0–M5 launch gates
│   └── adr/               # Decision log templates
├── prompts/               # Session start/close/ADR templates
├── examples/filled/       # Concrete example (TaskNote)
└── tests/                 # Unit tests
```

## CI Guardrails

`mmu doctor` runs on every PR. `mmu gate` runs for stages listed in `docs/ops/gate_targets.txt`.

## Contributing

See `CONTRIBUTING.md`.

## License

MIT. See `LICENSE`.
