# Roadmap

## v0.1 Template Pack

- Complete documentation structure
- SaaS from scratch checklists
- Start/close/ADR prompt pack

## v0.2 CLI Helpers (prototype shipped)

- installable Python CLI: `mmu start|close|doctor|gate`
- shell wrapper: `./scripts/mmu.sh ...`
- codebase-aware doctor checks (metadata, webhook safety, env split)
- CI workflow for doctor + configured gates

## v0.3 Workflow Integrations

- Prompt packs for Claude/GPT/Gemini wrappers
- JSON output mode for CI
- Filled examples by SaaS category
- `start --emit bundle` workflow for practical LLM handoff

## v0.4 LLM Integration + Agentic Engineering

- Optional Claude integration via `pip install make-me-unicorn[llm]`
- `init --interactive`: Claude-guided project setup (5 questions → 5 docs)
- `start --agent`: auto-format context for LLM injection
- `doctor --deep`: semantic code review with Claude
- `generate <doc>`: LLM-powered doc generation
- Failure recovery framework (`docs/ops/known_issues.md`)
- Agent safety rules for testing blueprints
- Structured session memory with `[DECISION]/[DONE]/[ISSUE]/[NEXT]` tags

## v1.0 Founder OS

- Stable CLI package (beyond shell prototype)
- Community playbooks (B2B SaaS, AI app, commerce SaaS)
- Hardened release gates with CI templates
