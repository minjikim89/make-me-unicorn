# Monitoring Blueprint

> Deep-dive checklist for observability, alerting, and incident management.
> Gate-level checks → `docs/checklists/release_readiness.md`

## Error Tracking

- [ ] Set up error tracking service (Sentry, Bugsnag, or Rollbar).
- [ ] Configure source maps for readable stack traces.
- [ ] Add user context to error reports (user ID, plan).
- [ ] Set up error grouping and deduplication rules.
- [ ] Configure alert thresholds for error spike detection.

## Application Logging

- [ ] Implement structured logging (JSON format).
- [ ] Define log levels and use them consistently.
- [ ] Add request IDs for distributed tracing.
- [ ] Ship logs to centralized platform (Grafana Loki, Datadog, Logtail).
- [ ] Set log retention policies per environment.

## Infrastructure Monitoring

- [ ] Monitor CPU, memory, and disk usage.
- [ ] Monitor database connection pool utilization.
- [ ] Monitor queue depth and job processing latency.
- [ ] Track container/instance health and restarts.
- [ ] Set up uptime monitoring with external checks.

## Application Performance Monitoring (APM)

- [ ] Track API response times (p50, p95, p99).
- [ ] Monitor database query performance.
- [ ] Track frontend page load times (LCP, FID, CLS).
- [ ] Identify slow endpoints and optimize.
- [ ] Set performance budgets and alert on regression.

## Alerting

- [ ] Define alert severity levels (P1 critical, P2 high, P3 medium).
- [ ] Configure alert routing (Slack, PagerDuty, email).
- [ ] Set up on-call rotation if team grows.
- [ ] Avoid alert fatigue — tune thresholds to reduce noise.
- [ ] Document escalation procedures per severity.

## Dashboards

- [ ] Create system health overview dashboard.
- [ ] Create business metrics dashboard (signups, conversions, churn).
- [ ] Create API performance dashboard.
- [ ] Create error rate dashboard.
- [ ] Make dashboards accessible to all team members.

## Incident Management

- [ ] Define incident severity classification.
- [ ] Create incident response checklist.
- [ ] Set up status page (Instatus, Cachet, or Atlassian Statuspage).
- [ ] Template post-mortem documents.
- [ ] Schedule regular incident review meetings.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Sentry | Error Tracking | Free tier | Best-in-class error grouping, source maps |
| Grafana + Loki | Dashboards + Logs | Free (self-hosted) | Open-source observability stack |
| Datadog | Full Observability | $15/host/mo | All-in-one APM, logs, infra monitoring |
| Better Uptime | Uptime Monitoring | Free tier | Simple uptime checks with status page |
| PagerDuty | Incident Management | Free tier | On-call scheduling and escalation |
| Instatus | Status Page | Free tier | Beautiful hosted status pages |
