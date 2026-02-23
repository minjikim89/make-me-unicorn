# Contributing

## Principles

1. Prefer reducing operational friction over adding complexity.
2. Write checklists that are practical and verifiable.
3. Keep vendor-neutral guidance whenever possible.
4. Follow the standards in `CODE_OF_CONDUCT.md`.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .[dev]
```

## Local quality checks

```bash
ruff check src tests
mypy src/mmu_cli
python -m unittest discover -s tests -p "test_*.py" -v
./scripts/ci_guardrails.sh
```

## PR Scope

- Bug fixes
- Checklist improvements
- Mode playbook improvements
- Prompt quality improvements
- Better examples for founders and developers

## PR Checklist

- [ ] Why is this change needed?
- [ ] Is it understandable for first-time founders?
- [ ] Is it still useful for experienced engineers?
- [ ] Does it stay consistent with the existing operating model?
