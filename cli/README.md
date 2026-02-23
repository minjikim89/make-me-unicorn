# CLI

The project ships an installable Python CLI and a shell wrapper.

- Installable command: `mmu`
- Wrapper command: `scripts/mmu.sh`

## Install

```bash
cd make-me-unicorn
pip install -e .
```

## Run

```bash
mmu start --mode product
mmu doctor
mmu gate --stage M2
mmu close
```

## No-install fallback

```bash
PYTHONPATH=src python3 -m mmu_cli doctor
```

## CI integration

- Guardrail workflow: `.github/workflows/mmu-guardrails.yml`
- Gate targets: `docs/ops/gate_targets.txt`
