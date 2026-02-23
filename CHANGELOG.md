# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic intent.

## [Unreleased]

### Added

- `mmu init` command for baseline workspace scaffolding.
- `mmu snapshot` command to invoke snapshot diagnostics through the Python CLI.
- GitHub metadata checklist at `docs/ops/github_metadata.md`.
- Unit tests for `init` and `snapshot` command paths.

### Changed

- README quick-start and CLI sections now include `init` and `snapshot`.
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
