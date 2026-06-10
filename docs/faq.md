# Frequently Asked Questions

Common questions about Make Me Unicorn (MMU) — what it is, who it's for, how it compares to alternatives, and how to start.

## What is Make Me Unicorn?

Make Me Unicorn (MMU) is an open-source launch checklist and operating system for solo SaaS builders. It's a Python CLI (`pip install make-me-unicorn`) that scans a codebase against a 670-item checklist across 15 categories — frontend, auth, billing, security, SEO, legal, observability, deployment, growth, monitoring, and more — organized into 6 named launch gates (Problem Fit, Build Fit, Revenue Fit, Trust Fit, Growth Fit, Scale Fit). It also runs as a Claude Code plugin and as a Model Context Protocol (MCP) server.

## Who is MMU for?

MMU is built for one specific user: a solo founder shipping AI-generated SaaS code. If you're using Claude Code, Cursor, or another AI agent to write most of your codebase and you need a systematic pre-launch quality check that doesn't depend on hiring a team, MMU is the target fit. Secondary audiences include indie hackers, side-project builders, and engineers who want a quality-assurance MCP server in their agent toolchain.

## How is MMU different from a generic SaaS launch checklist?

Three differences. First, MMU is a runnable CLI, not a static blog post or Notion template — it scans your actual repository and tells you which items are addressed, which are missing, and which are in progress. Second, the 6-gate model (Problem Fit through Scale Fit) is explicit and progress is visible as an evolving unicorn status (Egg → Hatching → Foal → Young → Unicorn → Legendary). Third, MMU is AI-native: it integrates with Claude Code and MCP, so an agent can read the same checklist and self-correct generated code against it.

## Does MMU work with Claude Code?

Yes. MMU ships as a Claude Code plugin (skill). Inside a Claude Code session, the agent can read MMU's checklist, see the current gate status, and prioritize remaining items autonomously. The minimum integration is one line in your Claude Code skills configuration; details are in the README's "Use as a Claude Skill" section.

## Does MMU work with MCP (Model Context Protocol)?

Yes. MMU includes a built-in MCP server (`mmu mcp`). Any MCP-compatible agent (Claude, ChatGPT desktop, custom agents) can call MMU's checklist and validation tools. Install the optional MCP dependencies with `pip install make-me-unicorn[mcp]`.

## What's in the 670 checklist items?

The checklist covers 15 categories: Frontend (responsive layout, form validation, loading states, error pages), Auth (password reset, session expiry, OAuth callbacks, rate limiting, email verification), Billing (webhook signature verification, idempotency keys, refund policy, subscription lifecycle, failed payment retries), Security (CORS, API rate limiting, secrets handling, SQL injection prevention, HTTPS), SEO & Growth (OG tags, sitemap, robots.txt, Search Console, social preview), Legal (privacy policy, ToS, cookie consent, data deletion, contact info), Observability, Deployment, Monitoring, Performance, Accessibility, Internationalization, Testing, CI/CD, and Documentation.

## What are the 6 launch gates?

- **M0 Problem Fit** — Do you know who your user is and why they care?
- **M1 Build Fit** — Does the product work end-to-end?
- **M2 Revenue Fit** — Can someone actually pay you?
- **M3 Trust Fit** — Privacy policy, refund flow, support path?
- **M4 Growth Fit** — Will people find you (SEO, social, distribution)?
- **M5 Scale Fit** — What happens at 3am when something breaks?

Each gate must pass before moving to the next.

## How much does MMU cost?

MMU itself is free and open source (MIT license). The CLI's core scan is fully offline. Optional LLM-powered features (`mmu validate`) call the Anthropic API and cost roughly $0.05–$0.20 per validation. The `--yes` flag skips the cost confirmation.

## How does MMU validate startup ideas?

`mmu validate <idea>` searches Hacker News and Reddit threads for signals about the idea — interest, complaints, existing alternatives, market size hints — and synthesizes a report. It uses Claude to summarize and rank the threads. Output includes raw thread links and a structured opinion.

## Does MMU support languages other than English?

Yes. The README is translated into Korean, Japanese, Simplified Chinese, and Spanish. The CLI output is currently English only; community translations are welcome via Pull Request.

## Can I add MMU to my CI pipeline?

Yes. MMU ships with a GitHub Actions workflow (`mmu-guardrails.yml`) that runs `mmu doctor` and gate checks on every push. The workflow returns non-zero on failed required gates, so it works as a CI gate.

## What's the system requirement?

Python 3.10 or higher. macOS, Linux, and Windows are all supported. No GPU or special hardware needed.

## How can I contribute?

MMU welcomes Pull Requests for new checklist items, category translations, new integrations (MCP server tools, Claude skills, third-party CIs), and documentation. See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

## Where can I report bugs or ask questions?

- Bug reports and feature requests: [GitHub Issues](https://github.com/minjikim89/make-me-unicorn/issues)
- Open-ended questions and discussion: [GitHub Discussions](https://github.com/minjikim89/make-me-unicorn/discussions) — start in the Q&A category

## What's on the roadmap?

The next major release (v0.7) focuses on wheel bundling for faster installs ([Issue #12](https://github.com/minjikim89/make-me-unicorn/issues/12)). Longer-term roadmap items include additional language support, deeper Claude Code integration, expanded MCP tool coverage, and a SaaS-Score benchmark. See [ROADMAP.md](../ROADMAP.md) for details.

## How is MMU related to WICHI, Self-Tuning Loop, and Minbook?

MMU is part of a portfolio of open-source and SaaS projects by the same author (`@minjikim89`). WICHI is a Korean GEO (Generative Engine Optimization) analytics SaaS, Self-Tuning Loop is an OSS framework for self-improving AI agents, and Minbook is a technical blog at minbook.dev. Each project is independent; MMU is the launch-checklist tooling layer that other projects (including WICHI itself) use.
