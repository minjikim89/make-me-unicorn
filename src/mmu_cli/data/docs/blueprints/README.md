# Full-Stack SaaS Blueprint

> 300+ actionable checks across 15 categories — everything a solo founder needs to ship production SaaS.

## Gate Checks vs Blueprints

| | Gate Checklists (`docs/checklists/`) | Blueprints (`docs/blueprints/`) |
|---|---|---|
| Purpose | Pass/fail phase validation | Deep-dive implementation guide |
| Depth | High-level (15–20 items) | Detailed (20–40 items per file) |
| When to use | Before moving to next milestone | While building each layer |

## How to Use

1. **Copy** the blueprint files into your project.
2. **Check items** as you implement (`- [x]`).
3. **Run `mmu doctor`** to validate gate-level readiness.
4. **Track progress** — count checked items vs total per file.

> Tip: Use `grep -c '\- \[x\]' docs/blueprints/*.md` to see progress per file.

## Blueprint Index

| # | Blueprint | Items | Extends |
|---|---|---|---|
| 01 | [Frontend](./01-frontend.md) | 35 | `from_scratch.md` |
| 02 | [Backend](./02-backend.md) | 40 | `from_scratch.md` |
| 03 | [Auth](./03-auth.md) | 30 | `auth_security.md` |
| 04 | [Billing](./04-billing.md) | 25 | `billing_tax.md` |
| 05 | [DevOps](./05-devops.md) | 30 | `from_scratch.md` |
| 06 | [Security](./06-security.md) | 30 | `auth_security.md` |
| 07 | [Monitoring](./07-monitoring.md) | 25 | `release_readiness.md` |
| 08 | [SEO & Marketing](./08-seo-marketing.md) | 25 | `seo_distribution.md` |
| 09 | [Legal & Compliance](./09-legal-compliance.md) | 25 | `release_readiness.md` |
| 10 | [Performance](./10-performance.md) | 25 | `release_readiness.md` |
| 11 | [Testing](./11-testing.md) | 25 | `release_readiness.md` |
| 12 | [CI/CD](./12-cicd.md) | 20 | `release_readiness.md` |
| 13 | [Email & Notifications](./13-email-notifications.md) | 20 | `release_readiness.md` |
| 14 | [Analytics](./14-analytics.md) | 20 | `from_scratch.md` |
| 15 | [Accessibility](./15-accessibility.md) | 25 | `release_readiness.md` |

**Total: 400+ checks**

## Quick Stack Reference

| Category | Recommended | Alternative |
|---|---|---|
| Frontend | Next.js + Tailwind + shadcn/ui | Nuxt, SvelteKit |
| Backend | Node.js + Prisma + PostgreSQL | Python/FastAPI, Go |
| Auth | Auth.js (NextAuth) | Clerk, Supabase Auth |
| Payments | Stripe (Checkout + Portal) | Lemon Squeezy, Paddle |
| Hosting | Vercel + Railway | Fly.io, AWS |
| CI/CD | GitHub Actions | GitLab CI, CircleCI |
| Monitoring | Sentry + Grafana | Datadog, New Relic |
| Email | Resend + React Email | Postmark, SendGrid |
| Analytics | PostHog | Mixpanel, Amplitude |
| Web Analytics | Plausible | Fathom, Umami |
| Testing | Vitest + Playwright | Jest + Cypress |
| Security | Dependabot + Snyk | CodeQL, Semgrep |
| Legal | CookieYes | Osano, Iubenda |
| Notifications | Novu | OneSignal, Knock |
| Accessibility | axe-core + Radix UI | Pa11y, WAVE |
