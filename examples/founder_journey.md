# Example Founder Journey (Week 1)

## Day 1: Problem Mode

- Command: `./scripts/mmu.sh start --mode problem`
- Work: refine ICP and core pain
- Output: update `docs/core/strategy.md`

## Day 2: Product Mode

- Command: `./scripts/mmu.sh start --mode product`
- Work: define P0 features and cut scope
- Output: update `docs/core/product.md`, `docs/ops/roadmap.md`

## Day 3: Backend Mode

- Command: `./scripts/mmu.sh start --mode backend`
- Work: implement first API and data model
- Output: update architecture notes, create ADR

## Day 4: Auth Mode

- Command: `./scripts/mmu.sh start --mode auth`
- Work: add reset flow and role checks
- Output: run `./scripts/mmu.sh doctor`

## Day 5: Billing and Growth Mode

- Command: `./scripts/mmu.sh start --mode billing`
- Work: set plan logic and webhook handling
- Output: run `./scripts/mmu.sh gate --stage M2`

## Every Day

- End with: `./scripts/mmu.sh close`
