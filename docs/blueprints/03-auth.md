# Auth Blueprint

> Deep-dive checklist for authentication and authorization.
> Gate-level checks → `docs/checklists/auth_security.md`

## Identity Provider Setup

- [ ] Choose auth provider (Auth.js/NextAuth, Clerk, Supabase Auth, or custom).
- [ ] Configure email/password authentication.
- [ ] Implement OAuth providers (Google, GitHub, etc.).
- [ ] Set up magic link / passwordless login option.
- [ ] Configure provider-specific scopes and permissions.

## Registration Flow

- [ ] Implement signup with email verification.
- [ ] Add password strength requirements (min length, complexity).
- [ ] Prevent disposable email addresses if needed.
- [ ] Capture minimal required fields at signup.
- [ ] Implement duplicate account detection (same email, different provider).
- [ ] Send welcome email after successful registration.

## Login Flow

- [ ] Implement login with email/password.
- [ ] Implement OAuth social login flow.
- [ ] Add "Remember me" option with extended session.
- [ ] Implement account lockout after failed attempts.
- [ ] Log all login attempts with IP and user agent.
- [ ] Show last login info for security awareness.

## Session Management

- [ ] Choose session strategy (JWT vs server-side sessions).
- [ ] Set appropriate token expiration times.
- [ ] Implement refresh token rotation.
- [ ] Add session revocation capability.
- [ ] Handle concurrent sessions policy (allow/limit/deny).
- [ ] Implement "Sign out everywhere" feature.

## Password Recovery

- [ ] Implement "Forgot password" with time-limited tokens.
- [ ] Rate limit password reset requests.
- [ ] Invalidate old reset tokens when new one is requested.
- [ ] Notify user after successful password change.
- [ ] Do not reveal whether email exists in reset flow.

<!-- if:has_mfa -->
## Multi-Factor Authentication

- [ ] Implement TOTP-based MFA (Google Authenticator, Authy).
- [ ] Add MFA recovery codes generation and storage.
- [ ] Allow MFA enforcement per role (admin required).
- [ ] Implement MFA challenge during sensitive operations.
<!-- endif -->

## Authorization and RBAC

- [ ] Define roles and permissions model.
- [ ] Implement middleware-level role checks.
- [ ] Add resource-level authorization (ownership checks).
- [ ] Protect admin routes and API endpoints.
- [ ] Implement team/organization-based access if multi-tenant.

## Account Management

- [ ] Allow email change with re-verification.
- [ ] Allow password change with current password confirmation.
- [ ] Implement account deletion with data cleanup.
- [ ] Allow linking/unlinking OAuth providers.
- [ ] Export user data on request (GDPR right of access).

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Auth.js (NextAuth) | Auth Library | Free | Flexible, supports 50+ providers |
| Clerk | Auth Service | Free tier | Hosted UI, MFA, org support |
| Supabase Auth | Auth Service | Free tier | PostgreSQL-native, Row Level Security |
| bcrypt / Argon2 | Password Hashing | Free | Industry-standard hashing algorithms |
| otplib | TOTP Library | Free | RFC-compliant OTP generation |
| CASL | Authorization | Free | Isomorphic permission management |
