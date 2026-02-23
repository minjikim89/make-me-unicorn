# Auth and Security Checklist

## Identity

- [ ] Login policy (email/social) is defined.
- [ ] Email verification flow exists.
- [ ] Password reset flow exists.

## Session and Token

- [ ] Session expiration policy exists.
- [ ] Refresh token rotation policy exists.
- [ ] CSRF/XSS and baseline security headers are reviewed.

## Authorization

- [ ] RBAC model is defined.
- [ ] Sensitive actions are authorized server-side.
- [ ] Admin privilege escalation paths are controlled.

## Abuse and Audit

- [ ] Login rate limits are enforced.
- [ ] Security-relevant events are logged.
- [ ] Suspicious activity alerts are configured.

## Operations

- [ ] Secrets are not stored in source control.
- [ ] `dev/staging/prod` are separated.
- [ ] Security decisions are recorded in ADRs.
