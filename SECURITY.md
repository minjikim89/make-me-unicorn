# Security Policy

## Reporting a Vulnerability

Please do not open public issues for security vulnerabilities.

Use GitHub private reporting:

- `Security` tab -> `Report a vulnerability`
- Or create a security advisory draft for this repository

Include:

- Impacted files and versions
- Reproduction steps
- Expected vs actual behavior
- Suggested mitigation if available

## Scope

This project provides workflow guardrails and checklist automation.

Security reports are most useful when they involve:

- Credential leakage risks
- Unsafe default behavior in `mmu doctor` checks
- Unsafe CI workflow behavior
- Data exposure in generated bundles/context output

## Response Targets

- Initial triage: within 72 hours
- Status update: within 7 days
- Fix target: case-by-case based on severity
