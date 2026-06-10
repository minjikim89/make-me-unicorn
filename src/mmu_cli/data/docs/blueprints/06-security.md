# Security Blueprint

> Deep-dive checklist for application security (OWASP-aligned).
> Gate-level checks → `docs/checklists/auth_security.md`

## OWASP Top 10 Coverage

- [ ] **Injection** — Parameterize all database queries, no raw SQL with user input.
- [ ] **Broken Auth** — Enforce strong passwords, MFA, session timeout.
- [ ] **Sensitive Data Exposure** — Encrypt data at rest and in transit (TLS 1.2+).
- [ ] **XML External Entities** — Disable XML external entity processing if using XML.
- [ ] **Broken Access Control** — Verify authorization server-side on every request.
- [ ] **Security Misconfiguration** — Remove default credentials, disable debug in production.
- [ ] **XSS** — Escape all user-generated output, use CSP headers.
- [ ] **Insecure Deserialization** — Validate and sanitize all serialized data.
- [ ] **Vulnerable Components** — Audit dependencies with `npm audit` or Snyk.
- [ ] **Insufficient Logging** — Log security events with enough context for investigation.

## HTTP Security Headers

- [ ] Set `Content-Security-Policy` header.
- [ ] Set `X-Content-Type-Options: nosniff`.
- [ ] Set `X-Frame-Options: DENY` (or `SAMEORIGIN`).
- [ ] Set `Referrer-Policy: strict-origin-when-cross-origin`.
- [ ] Set `Permissions-Policy` to restrict browser features.
- [ ] Set `Strict-Transport-Security` (HSTS) with `max-age` and `includeSubDomains`.

## Input Validation

- [ ] Validate all input on the server side (never trust client only).
- [ ] Sanitize HTML input if rich text is allowed.
- [ ] Limit file upload types, sizes, and scan for malware.
- [ ] Validate and sanitize URL parameters and query strings.

## API Security

- [ ] Implement rate limiting per IP and per authenticated user.
- [ ] Use API keys or tokens for all external-facing endpoints.
- [ ] Validate request content type headers.
- [ ] Implement request size limits.
- [ ] Add CORS allowlist for trusted origins only.

## Dependency Security

- [ ] Enable Dependabot or Renovate for automated updates.
- [ ] Run `npm audit` / `pip audit` in CI pipeline.
- [ ] Review and pin critical dependency versions.
- [ ] Remove unused dependencies.
- [ ] Check licenses for compliance.

## Secrets and Credentials

- [ ] Store all secrets in environment variables or secrets manager.
- [ ] Scan codebase for leaked secrets (GitGuardian, gitleaks).
- [ ] Rotate compromised secrets immediately.
- [ ] Use separate credentials per environment.
- [ ] Document secret rotation procedure.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Dependabot | Dependency Updates | Free | GitHub-native, auto PRs for updates |
| Snyk | Vulnerability Scanning | Free tier | Deep dependency vulnerability analysis |
| CodeQL | Static Analysis | Free | GitHub-native SAST |
| Semgrep | Code Scanning | Free tier | Custom rule-based code analysis |
| GitGuardian | Secret Detection | Free tier | Prevents secret leaks in commits |
| Helmet.js | HTTP Headers | Free | Express middleware for security headers |
| OWASP ZAP | DAST | Free | Dynamic application security testing |
