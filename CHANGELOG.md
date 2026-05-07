# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic intent.

## [Unreleased]

## [0.6.3] - 2026-05-08

### Fixed

- **`mmu serve-mcp` no longer crashes when called without `--root`.** The serve-mcp subparser sets `--root` default to `None` (so the MCP server can fall back to the package install location), but the shared dispatch in `main()` ran `root_path(None)` unconditionally — which raised `TypeError: argument should be a str ... not 'NoneType'`. `root_path()` now handles `None` by returning `Path.cwd()`. This was a latent regression in v0.6.0/0.6.1/0.6.2 — the published CLI's serve-mcp entry point was unusable without an explicit `--root`.
- 2 new unit tests (`test_root_path_handles_none`, `test_root_path_handles_string`) lock the contract.

### How it was caught

While building a demo GIF of `mmu serve-mcp` driven by an `mcp` Python SDK client, the server crashed at startup. The bug had slipped past three previous releases because every smoke test passed `--root` explicitly.

## [0.6.2] - 2026-05-07

### Fixed

- **`mmu serve-mcp` now actually fails fast on invalid `--root`.** v0.6.1 fixed `_resolve_repo_root` itself, but it was only called lazily inside each MCP tool function — so the server happily started up with a bad root and only errored once a client called a tool. `build_server` now validates the root once at startup, and `cli.py` translates the `FileNotFoundError` into a clean exit code 2 with the error message on stderr (no traceback).
- New unit test (`test_build_server_fails_fast_on_invalid_root`) skips gracefully when the `[mcp]` extra is absent.

## [0.6.1] - 2026-05-06

### Security

- **Prompt-injection defense in `mmu validate --llm`** — scraped Reddit/HN content is now wrapped in `<thread>` tags with sanitized close-tags, and the system prompt explicitly tells the model to treat thread content as data only. Reduces the surface for a hostile thread to override the validation prompt.

### Fixed

- **`mmu serve-mcp --root` now fails loudly on invalid paths.** Previously, an invalid `--root` silently fell back to the package install location, masking config mistakes. Explicit `--root` arguments must point at a checkout containing `docs/blueprints/`.
- **`mmu_validate_idea` MCP tool stub message** rewritten to clearly explain why MCP doesn't expose the full validator (network + LLM in stdio context) and direct users to the `mmu validate` CLI.
- **`mmu validate` no longer crashes on network errors.** HN or Reddit fetch failures are caught, reported on stderr, and the run continues with whatever data was retrieved. Both sources failing returns exit code 2 with a friendly message.

### Added

- 4 new unit tests (86 total) covering `_sanitize` and the explicit/None branches of `_resolve_repo_root`.

## [0.6.0] - 2026-05-06

### Added

- **Claude Code plugin packaging** (`.claude-plugin/`) — install MMU as a plugin via `/plugin marketplace add minjikim89/make-me-unicorn`. Compatible with Claude Code, Claude Desktop, and OpenAI Codex CLI (Anthropic Agent Skills spec, Dec 2025).
- **Agent Skill** (`skills/mmu-startup/`) — `SKILL.md` with auto-trigger phrases for "startup idea", "validate my idea", "launch checklist", and "Product Hunt prep". Uses progressive disclosure to load blueprints and the launch kit only when relevant.
- **MCP server mode** (`mmu serve-mcp`) — exposes MMU as a Model Context Protocol server so any MCP-compatible agent (Claude Code, Claude Desktop, Cursor, Gemini CLI) can call blueprints and templates as native tools. Tools: `mmu_list_blueprints`, `mmu_get_blueprint`, `mmu_list_idea_templates`, `mmu_validate_idea` (stub). Install with `pip install make-me-unicorn[mcp]`.
- New `[mcp]` optional-dependency group pinning `mcp>=1.27,<2`.
- **`mmu validate <idea>`** — pull real HN + Reddit discussions about a startup idea, compute local VADER sentiment, surface candidate competitors via capitalized-token NER. Saves markdown report to `reports/validate/<slug>.md`. Default mode is free (no API key, no paid calls).
- **`mmu validate --llm`** — opt-in Anthropic synthesis (verdict + pain points + competitors + risks + next experiments). Prompts for cost confirmation (~$0.05-0.20); use `--yes` / `-y` to skip.
- New `[validate]` optional-dependency group: `vaderSentiment>=3.3`, `requests>=2.28`. spaCy intentionally not used (heavy install; capitalized-token heuristic ships with v0.6, full NER planned for later).
- 10 new unit tests (75 total).
- 7 new unit tests for MCP server (82 total in main).

### Theme

v0.6 "Agent-Native" — extends v0.5's distribution thesis from human virality (badge/share) to agent virality (Skills marketplace + MCP registry). MMU is now installable as a Claude Code plugin and callable as an MCP server, so any LLM-backed agent can surface blueprints and validate ideas natively.

## [0.5.0] - 2026-04-12

### Added

- `mmu badge` — generate README badges in Markdown, SVG, or HTML format. Each badge links back to the project, creating organic growth through other READMEs.
- `mmu badge --format svg -o badge.svg` — save badge as local SVG file.
- `mmu badge --clipboard` — copy badge snippet to clipboard.
- **Stage-based badge colors** — badge color changes with unicorn stage (gray → orange → blue → purple → pink → gold).
- **Industry Blueprints** — new `docs/blueprints/industry/` directory with domain-specific checklists:
  - AI Product Blueprint (45+ items): model integration, cost control, prompt engineering, AI-specific UX, data privacy, ethical/legal.
  - Marketplace Blueprint (55+ items): supply/demand sides, transactions, trust & safety, marketplace economics.
- **Landing page** — Next.js Static Export website with interactive checklist demo, live score tracking, and unicorn stage evolution.
- GitHub Pages deployment workflow (`deploy-website.yml`).
- Product Hunt launch kit (`docs/launch/product-hunt.md`) with taglines, maker story, social templates, and success metrics.
- 7 new unit tests for badge generation (65 total, up from 58).

### Changed

- `mmu share` now includes GitHub URL and CTA line below the score card for better social sharing conversion.
- README restructured as distribution-first: demo → badge → share → problem → details (previously: problem → how it works → details).

## [0.4.0] - 2026-03-02

### Added

- `mmu share` — plain-text shareable score card with gate progress bars, stage name, stack info, and `#MakeMeUnicorn` hashtag.
- `mmu share --clipboard` — copy score card to clipboard (macOS).
- `mmu status --why` — Lighthouse-style score decomposition showing formula, per-blueprint breakdown, and skipped items.
- `mmu next [-n N]` — prioritized next-action recommendations with diversity cap (max 2 per blueprint).
- `mmu show <blueprint>` / `mmu check <blueprint> <#>` / `mmu uncheck` — drill-down and toggle individual checklist items.
- `mmu scan` — auto-detect tech stack and pre-check blueprint items.
- `mmu init` — baseline workspace scaffolding with stack selection (Next.js, Django, Rails, etc.) and `.mmu/config.toml` generation.
- `mmu init --interactive` — Claude-guided project setup (5 questions → 5 filled core docs).
- `mmu start --agent` — auto-format session context for direct LLM injection.
- `mmu doctor --deep` — semantic code review using Claude.
- `mmu generate <doc>` — generate or update core docs based on current project state.
- `mmu snapshot` — invoke snapshot diagnostics through the Python CLI.
- **Feature flag system** — `.mmu/config.toml` with 17 flags across features/architecture/market sections. Condition markers (`<!-- if:flag -->` / `<!-- endif -->`) in blueprints skip non-applicable items.
- **Visual status dashboard** with unicorn evolution art (Egg → Legendary).
- **Priority system** `[P0]`/`[P1]`/`[P2]` for blueprint items.
- **Full-Stack SaaS Blueprint** — 15 checklists, 400+ items covering frontend through accessibility.
- **LLM integration module** (`src/mmu_cli/llm.py`) — optional Claude-powered features via `pip install make-me-unicorn[llm]`.
- Multi-language READMEs: KO, JA, ZH-CN, ES.
- CLI demo GIF and 60-second quickstart in all READMEs.
- "Share your score" section in all READMEs.
- 58 unit tests (up from 24 in v0.3.0).

### Changed

- `prompts/close.md` — restructured with `[DONE]/[DECISION]/[ISSUE]/[NEXT]` memory tags.
- `prompts/start.md` — added Forbidden Patterns section and known_issues reference.
- `pyproject.toml` — added `[llm]` optional dependency group.
- Score calculation now excludes items in disabled feature flag sections (no more false-pass).
- `show`/`check` item numbering is condition-aware — hidden items don't shift visible numbers.

### Fixed

- `lstrip("[ ] ")` priority parsing bug → replaced with `re.sub()`.
- `next -n 0` no longer shows false "all done" (defaults to 3).
- Show/check item numbering mismatch when condition markers are active.
- Diversity cap remaining count uses actual selected count.
- `snapshot.sh` now parses `.snapshotrc` safely instead of sourcing arbitrary shell code.

## [0.3.0] - 2026-02-23

### Added

- Installable Python CLI command (`mmu`) via `pyproject.toml`.
- `start --emit bundle`, `--output`, and `--clipboard` options.
- JSON output mode (`--json`) for all commands.
- Unit test suite under `tests/`.
- CI lint/typecheck/tests in `.github/workflows/mmu-guardrails.yml`.
- Community files: `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates.

### Changed

- `gate` parsing now supports flexible heading spacing and indented unchecked items.
- Stage format supports `M<number>` dynamically (for example `M6`).
- `doctor` now reports read failures instead of silently swallowing all file IO errors.
- Code scanning uses pruned directory walking and configurable skip paths via `.mmu/config.toml`.

### Fixed

- CI gate-target parsing bug that merged multiple stages into one token.

## [0.2.0] - 2026-02-23

### Added

- Initial founder OS docs and mode playbook.
- `mmu` prototype commands: `start`, `close`, `doctor`, `gate`.
- Guardrail workflow scaffold.
