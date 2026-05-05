# MMU Blueprints Index

This index points to the 15 core blueprints + 2 industry blueprints in the upstream Make Me Unicorn repo. Read the specific file your user needs — do not bulk-load everything.

## Core blueprints (15)

| # | Blueprint | When to use |
|---|-----------|-------------|
| 01 | Frontend | UI framework, performance, accessibility |
| 02 | Backend | API design, database, error handling |
| 03 | Auth | Login, sessions, password resets, MFA |
| 04 | Billing | Stripe, subscriptions, invoicing, dunning |
| 05 | DevOps | Hosting, CI, environment, secrets |
| 06 | Security | OWASP top 10, dependency hygiene |
| 07 | Monitoring | Logs, alerts, uptime, error tracking |
| 08 | SEO & Marketing | Meta, sitemap, content strategy |
| 09 | Legal & Compliance | ToS, privacy, GDPR/CCPA |
| 10 | Performance | Core Web Vitals, query optimization |
| 11 | Testing | Unit, integration, E2E |
| 12 | CI/CD | Pipelines, deploys, rollback |
| 13 | Email & Notifications | Transactional, templates, deliverability |
| 14 | Analytics | Events, funnels, retention |
| 15 | Accessibility | WCAG, keyboard, screen readers |

Canonical: `docs/blueprints/01-frontend.md` … `docs/blueprints/15-accessibility.md`

## Industry blueprints (2)

| Blueprint | Items | When to use |
|-----------|-------|-------------|
| AI Product | 45+ | LLM integration, cost control, prompt engineering, AI UX, data privacy, ethics |
| Marketplace | 55+ | Two-sided supply/demand, transactions, trust & safety, marketplace economics |

Canonical: `docs/blueprints/industry/ai-product.md`, `docs/blueprints/industry/marketplace.md`

## How to recommend

Most apps need 01, 02, 03, 04, 05, 06 as the spine. Add 08 once auth/billing exists. Add the relevant industry blueprint (AI product or marketplace) early — its constraints affect 01–07 choices.
