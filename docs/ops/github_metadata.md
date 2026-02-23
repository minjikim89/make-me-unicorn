# GitHub Metadata Checklist

Use this checklist before public launch or major updates.

## Repository Description

Recommended description:

`AI-built SaaS blind-spot catcher: context, stage gates, and reliability checks for solo builders.`

## Topics

Recommended topics (8-12):

- `saas`
- `solo-founder`
- `developer-tools`
- `productivity`
- `checklist`
- `llm`
- `ai-coding`
- `reliability`
- `devops`
- `startup`

Optional automation:

```bash
./scripts/set_github_metadata.sh <owner/repo>
```

## Social Preview

- Upload `assets/brand/og-cover.png` in:
  - `GitHub Repo Settings -> General -> Social preview`

## Release Metadata

- Ensure version alignment:
  - `README` status badge
  - `pyproject.toml` version
  - `CHANGELOG.md` latest entry

## Quick Verification

- README hero image renders correctly on repository home.
- Link preview looks correct in Slack/X/Discord.
- Topics appear in repo sidebar and search discovery.
