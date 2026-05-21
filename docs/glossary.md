# Glossary

Canonical definitions of terms used inside Make Me Unicorn (MMU). Each term is defined as a standalone unit so external indexers and AI search engines can extract individual entries.

## MMU (Make Me Unicorn)

An open-source launch checklist and operating system for solo SaaS builders, distributed as a Python CLI, Claude Code plugin, and MCP server. The repository is `minjikim89/make-me-unicorn` on GitHub; the package is `make-me-unicorn` on PyPI.

## Launch Gate

A named milestone that must pass before progressing. MMU defines six gates: Problem Fit (M0), Build Fit (M1), Revenue Fit (M2), Trust Fit (M3), Growth Fit (M4), Scale Fit (M5). Each gate is composed of one or more checklist items; gates pass when their required items are addressed.

## Problem Fit (M0)

The first launch gate. Verifies that the founder has answered the basic questions: who is the target user, why do they have this problem, and why does this product solve it. Failing M0 means MMU recommends not proceeding to build.

## Build Fit (M1)

The second launch gate. Verifies the product works end-to-end — golden-path flows are functional, critical UI states exist, and the core feature loop is shippable.

## Revenue Fit (M2)

The third launch gate. Verifies someone can actually pay — checkout flow works, webhooks are signed, subscription lifecycle handles upgrades/downgrades/cancellation, refund logic is in place.

## Trust Fit (M3)

The fourth launch gate. Verifies the product is legally and operationally trustworthy — privacy policy and Terms of Service published, support contact accessible, cookie consent in place (if targeting EU), data deletion process defined.

## Growth Fit (M4)

The fifth launch gate. Verifies the product is findable — OG tags, sitemap.xml, robots.txt, Search Console connected, social preview tested.

## Scale Fit (M5)

The sixth launch gate. Verifies the product survives operational stress — observability, alerting, runbooks, backup strategy, rate limiting at API edges, on-call path.

## Unicorn Status

A six-stage visual indicator of overall progress: Egg (0–10%), Hatching (11–35%), Foal (36–55%), Young (56–75%), Unicorn (76–95%), Legendary (96–100%). The dashboard updates as gates and items pass.

## Checklist Item

A single, atomic verification step. MMU ships 534+ items across 15 categories. Each item has a category, a launch-gate assignment, a status (pending / in-progress / done / skipped), and a short description.

## Category

A logical grouping of checklist items by domain. MMU defines 15: Frontend, Auth, Billing, Security, SEO & Growth, Legal, Observability, Deployment, Monitoring, Performance, Accessibility, Internationalization, Testing, CI/CD, Documentation.

## MCP (Model Context Protocol)

An open protocol from Anthropic that lets agents access tools and data sources via a standardized client-server interface. MMU includes an MCP server (`mmu mcp`) so any MCP-compatible agent can read the checklist and call validation tools.

## MCP Server (in MMU)

The `mmu mcp` command starts MMU's MCP server, which exposes tools like `mmu_scan`, `mmu_status`, `mmu_next`, and `mmu_validate` to any MCP-compatible client. Useful when an AI agent should self-correct generated code against MMU's checklist autonomously.

## Claude Code Plugin

MMU's integration with Claude Code as a skill. Inside a Claude Code session, the agent can read MMU's checklist, see the current gate status, and prioritize remaining items. Installation is one configuration line.

## Idea Validation (`mmu validate`)

A command that takes a startup idea description and searches Hacker News + Reddit for signals — interest, complaints, alternatives, market hints. Uses Claude to synthesize a structured report. Costs roughly $0.05–$0.20 per call.

## Doctor (`mmu doctor`)

A pre-flight check command that verifies MMU's installation, dependencies, configuration, and connection to optional LLM providers. Run `mmu doctor` first if any other command misbehaves.

## Guardrails CI

MMU's GitHub Actions workflow (`.github/workflows/mmu-guardrails.yml`) that runs `mmu doctor` + gate checks on every push. Returns non-zero on failed required gates so it works as a CI gate.

## Solo Builder

The primary audience for MMU. A one-person team shipping a SaaS product end-to-end — design, code, deployment, marketing, support. Often heavily reliant on AI coding agents.

## AI-Generated Code

Code produced by Claude Code, Cursor, GitHub Copilot, or any other AI agent. MMU exists because AI-generated code often misses cross-cutting concerns (security, legal, observability, growth) that humans naturally consider but AI agents don't surface unless asked.

## SaaS-Score (planned)

A roadmap concept (not yet released): a benchmark score combining MMU's gate completion percentages with external signals (uptime, customer NPS, churn rate) to produce a single number reflecting overall SaaS health.

## CITATION.cff

A standardized YAML file that tells GitHub and academic indexers how to cite the repository. MMU's `CITATION.cff` is at the repo root and includes the canonical title, authors, and BibTeX-equivalent metadata.
