# Analytics Blueprint

> Deep-dive checklist for product, business, and web analytics.
> Gate-level checks → `docs/checklists/from_scratch.md`

## Analytics Strategy

- [ ] Define key metrics per stage (acquisition, activation, retention, revenue, referral).
- [ ] Choose analytics platform (PostHog, Mixpanel, or Amplitude).
- [ ] Document event naming convention (`snake_case`, `noun_verb` pattern).
- [ ] Define user identity resolution strategy (anonymous → authenticated).

## Product Analytics

- [ ] Track signup and onboarding funnel steps.
- [ ] Track core feature usage events.
- [ ] Track upgrade/downgrade/cancellation events.
- [ ] Implement feature adoption tracking.
- [ ] Track error occurrences surfaced to users.
- [ ] Measure time-to-value for new users.

## Business Metrics

- [ ] Track Monthly Recurring Revenue (MRR).
- [ ] Track churn rate (monthly and annual).
- [ ] Track Customer Lifetime Value (LTV).
- [ ] Track Customer Acquisition Cost (CAC).
- [ ] Track trial-to-paid conversion rate.
- [ ] Set up revenue dashboard with trends.

## Web Analytics

- [ ] Set up GA4 property and install Measurement ID in app.
- [ ] Verify GA4 receives data via Realtime report or DebugView.
- [ ] Link GA4 to Google Search Console for organic search query data.
- [ ] Optionally add privacy-friendly analytics (Plausible, Fathom, or PostHog).
- [ ] Track page views and unique visitors.
- [ ] Track referral sources and UTM parameters.
- [ ] Monitor bounce rate for key landing pages.
- [ ] Track outbound link clicks.

## Experimentation

- [ ] Implement A/B testing framework (PostHog, Statsig, or GrowthBook).
- [ ] Define experiment hypothesis and success metrics before launch.
- [ ] Implement feature flags for gradual rollout.
- [ ] Track experiment results with statistical significance.

## Data Privacy

- [ ] Respect Do Not Track and cookie consent preferences.
- [ ] Anonymize or pseudonymize analytics data where required.
- [ ] Implement data retention policies for analytics.
- [ ] Disclose analytics in privacy policy.
- [ ] Ensure analytics provider is GDPR-compliant.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| PostHog | Product Analytics | Free tier (1M events) | Open-source, session replay, feature flags |
| Mixpanel | Product Analytics | Free tier (20M events) | Powerful funnel and retention analysis |
| Plausible | Web Analytics | $9/mo | Privacy-friendly, lightweight, no cookies |
| Stripe Dashboard | Revenue Metrics | Free | Built-in MRR, churn, LTV tracking |
| GrowthBook | A/B Testing | Free (self-hosted) | Open-source experimentation platform |
| Google Analytics 4 | Web Analytics | Free | Industry standard, Search Console linkable |
| Statsig | Feature Flags + A/B | Free tier | Feature gates with auto-analysis |
