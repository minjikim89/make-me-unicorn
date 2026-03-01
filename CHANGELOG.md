# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic intent.

## [Unreleased]

### Added

- **LLM integration module** (`src/mmu_cli/llm.py`) — optional Claude-powered features via `pip install make-me-unicorn[llm]`.
- `mmu init --interactive` — Claude-guided project setup: answer 5 questions, get 5 filled core docs.
- `mmu start --agent` — auto-format session context for direct LLM injection.
- `mmu doctor --deep` — semantic code review using Claude (doc-code mismatches, security gaps, blind spots).
- `mmu generate <doc>` — generate or update core docs based on current project state.
- `docs/ops/known_issues.md` — failure tracking template with 3-category classification.
- Agent Safety Rules section in `docs/blueprints/11-testing.md` — anti-cheat DoD items.
- Parallel Session Rules in `docs/ops/mode_playbook.md` — git worktree guidance.
- LLM usage logging to `.mmu/llm_usage.log`.
- Unit tests for LLM module (`tests/test_llm_unittest.py`).
- `mmu init` command for baseline workspace scaffolding.
- `mmu snapshot` command to invoke snapshot diagnostics through the Python CLI.
- GitHub metadata checklist at `docs/ops/github_metadata.md`.
- Unit tests for `init` and `snapshot` command paths.

### Changed

- `prompts/close.md` — restructured with `[DONE]/[DECISION]/[ISSUE]/[NEXT]` memory tags.
- `prompts/start.md` — added Forbidden Patterns section and known_issues reference.
- `pyproject.toml` — added `[llm]` optional dependency group.
- README quick-start and CLI sections now include LLM features, `init`, and `snapshot`.
- CLI badge now reflects the expanded command surface.

### Fixed

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
