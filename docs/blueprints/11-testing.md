# Testing Blueprint

> Deep-dive checklist for unit, integration, and end-to-end testing.
> Gate-level checks → `docs/checklists/release_readiness.md`

## Testing Strategy

- [ ] Define testing pyramid ratios (many unit, some integration, few E2E).
- [ ] Choose test runner (Vitest, Jest, or Bun test).
- [ ] Configure test environment with proper mocking.
- [ ] Set minimum code coverage target (80%+ for critical paths).
- [ ] Document what to test vs what not to test.

## Unit Testing

- [ ] Test all utility functions and helpers.
- [ ] Test business logic in isolation.
- [ ] Test data transformations and formatters.
- [ ] Test validation schemas.
- [ ] Mock external dependencies (API clients, databases).
- [ ] Test edge cases: null, undefined, empty strings, boundary values.

## Integration Testing

- [ ] Test API endpoint request/response contracts.
- [ ] Test database operations (CRUD) with test database.
- [ ] Test authentication and authorization middleware.
- [ ] Test webhook handler logic.
- [ ] Test background job processing.
- [ ] Test email sending with mock transport.

## End-to-End Testing

- [ ] Choose E2E framework (Playwright or Cypress).
- [ ] Test critical user flows: signup, login, core action, payment.
- [ ] Test across browsers (Chrome, Firefox, Safari).
- [ ] Test responsive behavior (desktop and mobile viewports).
- [ ] Implement visual regression testing for key pages.

## Component Testing

- [ ] Test interactive components (forms, modals, dropdowns).
- [ ] Test loading, error, and empty states render correctly.
- [ ] Test accessibility of components (keyboard navigation, ARIA).
- [ ] Use Storybook for isolated component development and testing.

## Test Infrastructure

- [ ] Configure test database that resets between test runs.
- [ ] Set up test fixtures and factories for consistent test data.
- [ ] Configure CI to run tests on every PR.
- [ ] Generate and publish test coverage reports.
- [ ] Implement test parallelization for faster CI runs.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Vitest | Unit/Integration | Free | Fast, Vite-native, Jest-compatible API |
| Playwright | E2E Testing | Free | Cross-browser, auto-wait, codegen |
| Cypress | E2E Testing | Free tier | Developer-friendly, time-travel debugging |
| Testing Library | Component Testing | Free | Tests from user perspective |
| MSW | API Mocking | Free | Mock Service Worker for realistic API mocks |
| Storybook | Component Dev | Free | Isolated component development and docs |
| Faker.js | Test Data | Free | Realistic fake data generation |

## Agent Safety Rules

Rules for AI-assisted coding sessions to prevent false completion.

- [ ] [P0] No test stubs or placeholder assertions (`assert True`, `pass`, `return nil`).
- [ ] [P0] Existing tests must not be modified solely to make them pass.
- [ ] [P0] Code coverage must not decrease after an agent session.
- [ ] [P0] No `# TODO` or `# FIXME` left as implementation placeholders.
- [ ] [P1] All new public functions have at least one test.
- [ ] [P1] Edge cases are covered (null, empty, boundary values).
- [ ] [P1] No tests skip or xfail without a documented reason.
- [ ] Agent must report: what was done, what DoD items are met, what remains.
