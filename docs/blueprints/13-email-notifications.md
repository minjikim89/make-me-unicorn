# Email and Notifications Blueprint

> Deep-dive checklist for transactional email, marketing email, and in-app notifications.
> Gate-level checks → `docs/checklists/release_readiness.md`

## Email Infrastructure

- [ ] Choose email provider (Resend, Postmark, or SendGrid).
- [ ] Configure SPF, DKIM, and DMARC DNS records.
- [ ] Verify sending domain.
- [ ] Set up separate sending domains for transactional vs marketing email.
- [ ] Configure bounce and complaint webhook handlers.

## Transactional Email

- [ ] Implement welcome email on signup.
- [ ] Implement email verification message.
- [ ] Implement password reset email.
- [ ] Implement payment receipt/invoice email.
- [ ] Implement subscription change confirmation email.
- [ ] Implement account deletion confirmation email.

## Email Templates

- [ ] Choose template approach (React Email, MJML, or HTML).
- [ ] Create base layout template (header, footer, branding).
- [ ] Implement responsive email design (mobile-friendly).
- [ ] Add plain-text fallback for all emails.
- [ ] Preview and test emails across clients (Gmail, Outlook, Apple Mail).

## Marketing Email

- [ ] Implement newsletter subscription opt-in.
- [ ] Add unsubscribe link to all marketing emails.
- [ ] Track email open and click rates.
- [ ] Implement email preference center.
- [ ] Comply with CAN-SPAM and GDPR for email marketing.

## In-App Notifications

- [ ] Design notification data model (type, read/unread, timestamp).
- [ ] Implement notification bell with unread count.
- [ ] Implement mark-as-read and mark-all-as-read.
- [ ] Add notification preferences (per-type opt-in/opt-out).
- [ ] Implement real-time notifications (WebSocket or SSE).

## Push Notifications

- [ ] Implement web push notification opt-in.
- [ ] Configure push notification service (Firebase FCM or OneSignal).
- [ ] Respect user notification preferences.
- [ ] Implement notification grouping to avoid spam.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Resend | Transactional Email | Free tier (3k/mo) | Developer-first API, React Email support |
| Postmark | Transactional Email | $15/mo (10k) | Best deliverability, fast delivery |
| React Email | Email Templates | Free | React components for email templates |
| SendGrid | Email Platform | Free tier (100/day) | Full email platform with analytics |
| Novu | Notification Infra | Free tier | Multi-channel notification orchestration |
| OneSignal | Push Notifications | Free tier | Cross-platform push notifications |
