# Legal and Compliance Blueprint

> Deep-dive checklist for GDPR, CCPA, legal documents, and compliance.
> Gate-level checks → `docs/checklists/release_readiness.md`

## Privacy Policy

- [ ] Draft privacy policy covering data collection, use, sharing, retention.
- [ ] List all third-party services that receive user data.
- [ ] Describe cookies and tracking technologies used.
- [ ] Include data controller contact information.
- [ ] Publish privacy policy at `/privacy` with last-updated date.

## Terms of Service

- [ ] Draft terms of service covering acceptable use, liability, disputes.
- [ ] Define service availability and uptime commitments (if any).
- [ ] Include intellectual property and content ownership clauses.
- [ ] Define account termination conditions.
- [ ] Publish terms at `/terms` with last-updated date.

## Cookie Consent

- [ ] Implement cookie consent banner.
- [ ] Categorize cookies (necessary, analytics, marketing).
- [ ] Allow granular opt-in/opt-out per category.
- [ ] Store consent preferences and respect them.
- [ ] Do not load tracking scripts before consent is given.

<!-- if:targets_eu -->
## GDPR Compliance

- [ ] Implement data access request workflow (Right of Access).
- [ ] Implement data deletion request workflow (Right to Erasure).
- [ ] Implement data portability export (Right to Data Portability).
- [ ] Document lawful basis for each data processing activity.
- [ ] Maintain a record of processing activities (ROPA).
- [ ] Implement data breach notification procedure (72-hour rule).
<!-- endif -->

<!-- if:targets_california -->
## CCPA Compliance

- [ ] Add "Do Not Sell My Personal Information" link if applicable.
- [ ] Allow California residents to opt out of data sale.
- [ ] Respond to consumer requests within 45 days.
- [ ] Do not discriminate against users who exercise CCPA rights.
<!-- endif -->

## Data Handling

- [ ] Define data retention periods per data type.
- [ ] Implement automated data cleanup for expired data.
- [ ] Encrypt sensitive data at rest.
- [ ] Encrypt all data in transit (TLS 1.2+).
- [ ] Minimize data collection to what is necessary.

## Business Legal

- [ ] Display required business information (company name, address, VAT).
- [ ] Define refund and cancellation policy.
- [ ] Implement accessible support/contact mechanism.
- [ ] Review compliance with local business registration requirements.
- [ ] Maintain insurance coverage if applicable.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| CookieYes | Cookie Consent | Free tier | GDPR/CCPA compliant consent management |
| Osano | Privacy Compliance | Free tier | Cookie consent and data privacy platform |
| Iubenda | Legal Documents | $29/yr+ | Auto-generated privacy policy and terms |
| OneTrust | Enterprise Privacy | Custom | Full privacy management platform |
| Termly | Policy Generator | Free tier | Privacy policy and cookie consent |
