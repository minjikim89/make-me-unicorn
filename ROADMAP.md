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

## v0.4 LLM Integration + Agentic Engineering (shipped 2026-03-02)

- Optional Claude integration via `pip install make-me-unicorn[llm]`
- `init --interactive`: Claude-guided project setup (5 questions → 5 docs)
- `start --agent`: auto-format context for LLM injection
- `doctor --deep`: semantic code review with Claude
- `generate <doc>`: LLM-powered doc generation
- Failure recovery framework (`docs/ops/known_issues.md`)
- Agent safety rules for testing blueprints
- Structured session memory with `[DECISION]/[DONE]/[ISSUE]/[NEXT]` tags

## v0.5 Distribution Engine (shipped 2026-04-12)

- `mmu badge` — README badge generator (Markdown / SVG / HTML), stage-aware color
- `mmu share` enhancements (CTA + GitHub URL on the score card)
- Industry blueprints — `docs/blueprints/industry/` for AI Product (45+ items) and Marketplace (55+ items)
- Web demo (Next.js Static Export → GitHub Pages)
- Product Hunt launch kit (`docs/launch/product-hunt.md`)
- Distribution-first README restructure (demo → badge → share → details)

## v0.6 Agent-Native (shipped 2026-05-06 → 0.6.3 on 2026-05-08)

- **Claude Code plugin / Anthropic Agent Skill** packaging — `/plugin marketplace add minjikim89/make-me-unicorn`. Compatible with Claude Code, Claude Desktop, and OpenAI Codex CLI (Agent Skills spec, Dec 2025).
- **MCP server mode** — `mmu serve-mcp`, FastMCP-based. Tools: `mmu_list_blueprints`, `mmu_get_blueprint`, `mmu_list_idea_templates`, `mmu_validate_idea` (stub). Install via `[mcp]` extra.
- **`mmu validate <idea>`** — pulls real HN + Reddit threads, local VADER sentiment, capitalized-token competitor extraction. Free by default; `--llm` opt-in for Anthropic synthesis with cost prompt.
- 0.6.1 — prompt-injection defense in `--llm`, friendly HTTP error handling, fail-loud `--root` validation
- 0.6.2 — MCP startup root validation
- 0.6.3 — `root_path` handles `None` for `mmu serve-mcp` (no `--root`)

## v0.7 Maturity Pass + Vibe Check (shipped 2026-06-10)

- ✅ **Bundle blueprints + prompts in the wheel** — `pip install make-me-unicorn` now works without a clone (`mmu_cli/data/`, synced by `scripts/sync_packaged_data.py`, verified in CI)
- ✅ Wire `mmu_validate_idea` MCP tool through to the actual validate command (parallel HN + Reddit, free mode)
- ✅ **`mmu vibecheck`** — one-command scan for AI-generated code blind spots (secrets, webhook safety, password reset, f-string SQL, rate limits, CORS, debug mode, error monitoring)
- ✅ Test coverage: `report.py` formatters, `reddit.py` parser, VADER boundary tests (125 tests total, up from 89)
- ✅ VADER verdict threshold documented as `VERDICT_THRESHOLD` constant with boundary tests
- ✅ Competitor stopwords expansion (~80 sentence-starters)
- ✅ Validate report file naming: `<slug>-<hash8>.md` prevents overwrites and truncation collisions
- ✅ `server.json` for the official MCP Registry
- Deferred: blueprint slug collision protection in `mmu_get_blueprint` (slugs are currently unique; revisit when blueprints are user-extensible)
- Deferred: `--llm` synthesize path test coverage

## v0.8 Distribution Push (folded into 0.9)

- ✅ Reusable GitHub Action (`action.yml`) — runs `mmu vibecheck` in any workflow; SARIF output for code scanning added in 0.9
- ✅ Copy-paste distribution kit (`docs/launch/distribution-kit.md`)
- ✅ Live badge endpoint — `mmu badge --format endpoint`
- Registry and awesome-list submissions moved to v0.9 follow-ups

## v0.9 Agent Launch Gate (shipped 2026-11-26)

- ✅ `mmu install` for Claude Code, Codex CLI, Cursor, Gemini CLI, git pre-commit, AGENTS.md and the Agent Skill; `.pre-commit-hooks.yaml`
- ✅ `mmu hook`: commit/push gate, session-scoped "not done yet" gate, post-edit feedback; fail-open
- ✅ Vibecheck engine v2: `path:line` locations, rule registry, `--format agent|json|sarif`, `--staged|--changed|--since`, suppressions with required reasons, baseline
- ✅ Rule rework for precision and seven new rules (23 total); `docs/benchmark.md` with a 20-repo open-source sweep
- ✅ MCP server on SDK v1 and v2 with `mmu_vibecheck`, `mmu_explain_rule`, `mmu_list_rules`
- ✅ `make-me-unicorn` console script (`uvx make-me-unicorn ...`), `--version`, UTF-8 output
- Next: live-session verification on Codex CLI, Cursor and Gemini CLI; MCP Registry and directory listings; IDOR/authorization rules need data-flow analysis and are out of scope for the heuristic engine

## v1.0 Stable gate contract

- Freeze the hook protocol, `mmu.vibecheck/v1` JSON schema and rule ids
- Rules contributed with fixtures and expected findings, held to zero P0 false positives in the benchmark
- Community playbooks for the launch checklists (B2B SaaS, AI app, commerce SaaS)
