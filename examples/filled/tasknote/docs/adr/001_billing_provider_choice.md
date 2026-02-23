# ADR-001 Billing Provider Choice

Date: 2026-02-23
Status: Accepted
Mode: billing

## Context

Need recurring subscription billing with webhook events and low setup overhead for solo operations.

## Options

- Option A: Stripe direct
- Option B: Paddle
- Option C: Lemon Squeezy

## Decision

- Selected option: Stripe direct

## Why

- Strong webhook ecosystem and robust docs for subscription lifecycle.

## Consequences

- Upside: flexible API and mature event model
- Downside: more responsibility for tax/compliance details
- Operational impact: billing runbook must include webhook replay and idempotency checks

## Revisit Trigger

- Re-evaluate if tax burden exceeds 5 hrs/month or enterprise invoicing becomes dominant.
