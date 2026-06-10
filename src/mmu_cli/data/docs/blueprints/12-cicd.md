# CI/CD Blueprint

> Deep-dive checklist for continuous integration, delivery, and branch strategy.
> Gate-level checks → `docs/checklists/release_readiness.md`

## Branch Strategy

- [ ] Define branch model (GitHub Flow, GitFlow, or trunk-based).
- [ ] Protect `main` branch (require PR, reviews, passing checks).
- [ ] Define branch naming convention (`feature/`, `fix/`, `chore/`).
- [ ] Implement automatic branch cleanup after merge.

## Continuous Integration

- [ ] Run linter on every PR (ESLint, Prettier, or Biome).
- [ ] Run type checking on every PR (`tsc --noEmit`).
- [ ] Run unit and integration tests on every PR.
- [ ] Run security audit on every PR (`npm audit`, Snyk).
- [ ] Generate test coverage report and enforce minimum.
- [ ] Run Lighthouse CI for performance regression detection.

## Continuous Delivery

- [ ] Auto-deploy `main` to staging environment.
- [ ] Implement manual promotion from staging to production.
- [ ] Run smoke tests after each deployment.
- [ ] Implement deployment notifications (Slack, email).
- [ ] Keep deployment history for rollback reference.

## Pipeline Configuration

- [ ] Choose CI platform (GitHub Actions, GitLab CI, or CircleCI).
- [ ] Cache dependencies between runs (`node_modules`, `.next/cache`).
- [ ] Parallelize independent CI jobs for speed.
- [ ] Set timeout limits for CI jobs.
- [ ] Use reusable workflow templates for common patterns.

## Release Management

- [ ] Implement semantic versioning (SemVer).
- [ ] Auto-generate changelog from conventional commits.
- [ ] Create GitHub releases with release notes.
- [ ] Tag releases in git.

## Database Migrations in CI

- [ ] Run migration checks in CI (dry-run or syntax validation).
- [ ] Test migration rollback scripts.
- [ ] Automate migration execution during deployment.
- [ ] Alert on migration failures.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| GitHub Actions | CI/CD Platform | Free (2000 min/mo) | Native GitHub integration |
| GitLab CI | CI/CD Platform | Free tier | Integrated DevOps platform |
| Biome | Linter/Formatter | Free | Fast all-in-one linter and formatter |
| Changesets | Release Management | Free | Monorepo-friendly versioning |
| Conventional Commits | Commit Convention | Free | Standardized commit messages |
| Turborepo | Build System | Free | Cached, parallel monorepo builds |
