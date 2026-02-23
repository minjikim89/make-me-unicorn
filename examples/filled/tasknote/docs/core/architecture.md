# Architecture

## System Overview

- Frontend: Next.js app router
- Backend: FastAPI service
- Database: Postgres
- Queue/Worker: lightweight async worker for webhook retries
- External integrations: Stripe, PostHog

## Data Flow

1. Input: user creates/updates milestone
2. Processing: server validates and computes gate state
3. Storage: writes to Postgres
4. Output: dashboard and next-action recommendations

## Security Baseline

- Authentication method: email/password with reset flow
- Authorization model: user-owned resources + admin override
- Sensitive data handling: secrets in env vars only

## Reliability Baseline

- Logging: structured app logs
- Monitoring: error tracker + uptime ping
- Backup and recovery: daily DB backup with weekly restore drill

## Deployment

- Environment split (`dev/staging/prod`): enforced
- CI/CD: push to main deploys staging, manual promote to prod
- Rollback strategy: previous image rollback and DB migration down plan
