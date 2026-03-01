# Contributing

Thank you for considering contributing to Make Me Unicorn! Whether you're fixing a typo in a checklist or adding a new blueprint category, every contribution helps solo builders ship with more confidence.

## Principles

1. Prefer reducing operational friction over adding complexity.
2. Write checklists that are practical and verifiable.
3. Keep vendor-neutral guidance whenever possible.
4. Core CLI stays zero-dependency — LLM features go in the optional `[llm]` extra.
5. Follow the standards in `CODE_OF_CONDUCT.md`.

## Getting Started

### Prerequisites

- Python 3.10+
- Git

### Local Setup

```bash
git clone https://github.com/minjikim89/make-me-unicorn.git
cd make-me-unicorn

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# Core + dev tools
pip install -e ".[dev]"

# If working on LLM features
pip install -e ".[all]"
```

### Verify Your Setup

```bash
mmu --help                # CLI works
python -m unittest discover -s tests -p "test_*.py" -v   # all tests pass
ruff check src tests      # no lint errors
```

## Development Workflow

1. **Fork and branch** — create a feature branch from `main`
2. **Make changes** — keep commits focused and atomic
3. **Run checks** — see quality checks below
4. **Open a PR** — fill out the PR template

### Quality Checks (run before every PR)

```bash
ruff check src tests                                    # lint
mypy src/mmu_cli                                        # type check
python -m unittest discover -s tests -p "test_*.py" -v  # unit tests
```

These same checks run in CI via `.github/workflows/mmu-guardrails.yml`.

## What to Contribute

| Area | Examples |
|------|----------|
| **Checklist items** | Add missing items to `docs/blueprints/*.md`, fix outdated advice |
| **New blueprints** | Propose a new category (open an issue first) |
| **CLI improvements** | Bug fixes, UX improvements, new flags |
| **Examples** | Add filled examples for different SaaS types in `examples/filled/` |
| **Prompt quality** | Improve `prompts/start.md`, `prompts/close.md` templates |
| **Documentation** | Fix typos, clarify instructions, improve onboarding |
| **LLM features** | Improve `src/mmu_cli/llm.py` (requires `[llm]` extra) |

## Project Structure

```
make-me-unicorn/
├── src/mmu_cli/           # CLI source code
│   ├── cli.py             # main CLI entry point
│   └── llm.py             # optional LLM integration
├── docs/
│   ├── blueprints/        # 15 category checklists (534+ items)
│   ├── checklists/        # M0–M5 launch gate definitions
│   ├── core/              # strategy, product, pricing, architecture, UX
│   └── ops/               # operational docs
├── prompts/               # session start/close/ADR templates
├── examples/filled/       # concrete examples (TaskNote)
└── tests/                 # unit tests
```

## Writing Checklist Items

Blueprint items follow this format:

```markdown
- [ ] [P0] Item description — brief rationale
- [ ] [P1] Item description — brief rationale
```

- **P0** = must-have before launch
- **P1** = should-have, important but not blocking
- **P2** = nice-to-have, improves quality

Keep items actionable and verifiable. "Add error handling" is vague — "Return 4xx with error message for invalid input" is verifiable.

## PR Checklist

- [ ] Why is this change needed?
- [ ] Is it understandable for first-time founders?
- [ ] Is it still useful for experienced engineers?
- [ ] Does it stay consistent with the existing operating model?
- [ ] Do all tests pass? (`python -m unittest discover -s tests`)
- [ ] Does lint pass? (`ruff check src tests`)
