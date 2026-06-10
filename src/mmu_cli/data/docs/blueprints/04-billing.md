<!-- if:has_billing -->
# Billing Blueprint

> Deep-dive checklist for payments, subscriptions, and revenue operations.
> Gate-level checks → `docs/checklists/billing_tax.md`

## Payment Provider Setup

- [ ] Choose payment provider (Stripe, Lemon Squeezy, or Paddle).
- [ ] Configure API keys for `dev/staging/prod` environments.
- [ ] Set up webhook endpoints with signature verification.
- [ ] Enable test mode and create test cards/accounts.
- [ ] Configure payout schedule and bank account.

## Pricing Model

- [ ] Define pricing tiers (Free, Pro, Enterprise).
- [ ] Document feature entitlements per tier.
- [ ] Set up usage-based billing if applicable.
- [ ] Create pricing page with clear tier comparison.
- [ ] Implement annual vs monthly billing toggle.

## Checkout Flow

- [ ] Implement Checkout Session or embedded payment form.
- [ ] Add success redirect with order confirmation.
- [ ] Add cancel redirect with recovery messaging.
- [ ] Pre-fill customer email from logged-in session.
- [ ] Track checkout abandonment events.

## Subscription Lifecycle

- [ ] Handle `subscription.created` webhook event.
- [ ] Handle `subscription.updated` webhook event.
- [ ] Handle `subscription.deleted` webhook event.
- [ ] Sync subscription status to local database.
- [ ] Gate features based on active subscription status.
- [ ] Handle grace period for failed payments.

## Upgrade and Downgrade

- [ ] Implement plan upgrade with proration.
- [ ] Implement plan downgrade at period end.
- [ ] Handle feature access changes on plan switch.
- [ ] Send confirmation email on plan change.

## Cancellation and Refund

- [ ] Implement cancel-at-period-end flow.
- [ ] Implement immediate cancellation option.
- [ ] Show cancellation reason survey.
- [ ] Define refund policy and criteria.
- [ ] Implement refund processing workflow.
- [ ] Handle chargeback/dispute notifications.

## Customer Portal

- [ ] Enable self-service billing portal (Stripe Customer Portal or custom).
- [ ] Allow payment method update.
- [ ] Show invoice history and download links.
- [ ] Display upcoming invoice preview.
- [ ] Allow subscription management without support tickets.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Stripe | Payment Provider | 2.9% + $0.30/txn | Industry standard, excellent API |
| Lemon Squeezy | MoR Provider | 5% + $0.50/txn | Handles tax/compliance as Merchant of Record |
| Paddle | MoR Provider | 5% + $0.50/txn | Global tax handling, no Stripe Atlas needed |
| stripe-node | SDK | Free | Official Stripe Node.js library |
| Webhooks.fyi | Testing | Free | Webhook inspection and debugging |
| Tier | Entitlements | Free | Feature flag-based pricing entitlements |
<!-- endif -->
