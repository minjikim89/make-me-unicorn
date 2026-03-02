# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic intent.

## [Unreleased]

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
