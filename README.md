<div align="center">

# make-me-unicorn

**A launch gate for AI coding agents.**

Your agent cannot commit a webhook that trusts unsigned events, a Supabase table without RLS,<br>
or a `service_role` key in the browser bundle. Deterministic, offline, no account, no LLM, about 0.1 s.

[![PyPI](https://img.shields.io/pypi/v/make-me-unicorn?color=blue)](https://pypi.org/project/make-me-unicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![CI](https://github.com/minjikim89/make-me-unicorn/actions/workflows/mmu-guardrails.yml/badge.svg)](./.github/workflows/mmu-guardrails.yml)
[![Benchmark](https://img.shields.io/badge/P0%20false%20positives-0%20in%2020%20OSS%20repos-22c55e)](./docs/benchmark.md)

**English** · [한국어](./README.ko.md) · [日本語](./README.ja.md) · [简体中文](./README.zh-CN.md) · [Español](./README.es.md)

</div>

<!-- mcp-name: io.github.minjikim89/make-me-unicorn -->

```bash
uvx make-me-unicorn install --claude    # or --codex, --cursor, --gemini, --git, --all
```

That is the whole setup. From now on, when your agent runs `git commit`, the hook scans what is staged. A P0 finding denies the command and hands the agent a fix it can apply. Real output for the initial commit of a Next.js + Supabase + Stripe project (lines shortened, five P1 warnings cut):

```text
mmu vibecheck: 4 blocking (P0), 5 warning(s) (P1), 0 suppressed | scope: staged (22 file(s))
P0 secrets .env:3 (+1: components/AdminPanel.tsx:8)
  what: possible hardcoded secrets in 2 file(s): Supabase service_role JWT; ... (the service_role
        key is in a "use client" file: it bypasses RLS for every visitor)
P0 client-bundle-secrets .env:6 (+1: app/api/ai/summarize/route.ts:4)
  what: secret shipped to the browser bundle via public env prefix in 2 file(s): NEXT_PUBLIC_OPENAI_API_KEY ...
P0 webhook-signature app/api/webhooks/stripe-legacy/route.ts:5
  what: 1 of 2 webhook handler(s) trust the event without verifying its signature
  fix: Verify the signature on the raw body before trusting the event, and return 400 when it fails:
       event = stripe.webhooks.constructEvent(await req.text(), req.headers.get("stripe-signature")!,
       process.env.STRIPE_WEBHOOK_SECRET!) Do not call req.json() before this: the check needs the
       exact bytes the provider signed.
  silence (only if false positive): // mmu-ignore[webhook-signature]: <reason>
P0 supabase-rls supabase/migrations/0001_init.sql:1
  what: 1 table(s) created without ENABLE ROW LEVEL SECURITY: public.invoices
  fix: Add a migration for each listed table: `alter table <schema>.<table> enable row level security;`
       plus at least one policy, e.g. `create policy "owner can read" on <table> for select using
       (auth.uid() = user_id);`. ...
Fix every P0 above, then re-run `mmu vibecheck --format agent --staged` until it reports 0 blocking.
```

The agent fixes, re-runs, and commits. When the code is already right, the gate stays silent: in a live Claude Code test the agent wrote a verified Stripe webhook on the first try and the commit went straight through.

## Why absence checks

Secret scanners and SAST look for bad code that is there. Code written by agents more often fails on code that is not there: the signature check nobody wrote, the RLS policy that was never added, the rate limit in front of a paid LLM route.

- Tenzai had five coding agents build the same three apps (15 apps). None contained an exploitable SQLi or XSS; on security controls, "in almost all cases, they didn't even try" ([SecurityWeek, Jan 2026](https://www.securityweek.com/vibe-coding-tested-ai-agents-nail-sqli-but-fail-miserably-on-security-controls/)).
- GitGuardian measured a 3.2% secret-leak rate in Claude Code-assisted public commits against a 1.5% baseline ([State of Secrets Sprawl 2026](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/)).

A linter will not flag a function that does not exist. `mmu vibecheck` reads the project the way a reviewer would ask "where do you verify this webhook?" and blocks only when the answer is clearly "nowhere".

## How the gate works

Agents skip optional tools. They cannot skip hooks. `mmu install` writes hook entries that call `mmu hook`, which speaks each host's hook protocol.

| Host | Commit / push gate | "Not done yet" gate | Post-edit feedback | `mmu install` flag |
|------|--------------------|---------------------|--------------------|--------------------|
| Claude Code | `PreToolUse` on `Bash` | `Stop` | `PostToolUse` on `Edit`/`Write`/`MultiEdit` | `--claude` |
| Codex CLI | `PreToolUse` on `Bash` | `Stop` | `PostToolUse` on `apply_patch` | `--codex` |
| Cursor | `beforeShellExecution` | `stop` | not available | `--cursor` |
| Gemini CLI | `BeforeTool` on `run_shell_command` | `AfterAgent` | not available | `--gemini` |
| git | `pre-commit`, chaining any existing hook | | | `--git` |
| pre-commit framework | hook id `mmu-vibecheck` | | | `.pre-commit-hooks.yaml` |
| GitHub Actions | `uses: minjikim89/make-me-unicorn@v0.9.2`, SARIF to code scanning | | | |

- **Commit gate** scans what the commit will contain: staged files, or changed files for `git commit -a`, pathspecs and `git add ... && git commit`. A push scans what changed since the upstream.
- **"Not done yet" gate** runs when the agent tries to finish. It looks only at files the agent edited in this session, so it never makes the agent rewrite code it did not touch. It sends the agent back at most `MMU_STOP_MAX` times (default 3); if you told the agent to defer hardening, it lists the P0s and stops.
- **Post-edit feedback** returns P0 findings in the file just written as context. It never blocks.
- `mmu install --all`, `--dry-run`, `--uninstall`; `--agents-md` adds an instruction block to `AGENTS.md`, `--skill` copies the `mmu-vibecheck` Agent Skill into `.agents/skills/`. Existing settings are merged, never replaced.

Claude Code is tested in live sessions. Codex CLI, Cursor and Gemini CLI follow their documented hook contracts and are tested against documented payloads; reports from real sessions are welcome.

Design constraints, all tested:

- **Deterministic.** Same tree, same findings. No model call, no network, no account.
- **Fail-open.** If the scanner itself crashes or times out, the command goes through with a visible warning. A broken gate never bricks a session.
- **Bypassable by a human.** `MMU_HOOK_DISABLE=1 git commit ...` for one command; set it in the agent's environment to disable the gate for a session.
- **Fast.** Median 89 ms across 20 real repositories, 1.1 s on the largest (1,699 files).

## What it catches

P0 blocks. P1 warns. Every absence heuristic is P1 unless the evidence is specific.

| Rule | Sev | Finds |
|------|-----|-------|
| `secrets` | P0 | Live provider keys and Supabase `service_role` JWTs in source, config, or a dotenv file git does not ignore |
| `client-bundle-secrets` | P0 | Secrets behind `NEXT_PUBLIC_` / `VITE_` / `EXPO_PUBLIC_` prefixes or read in client code |
| `supabase-rls` | P0 | Tables created in migrations without `ENABLE ROW LEVEL SECURITY` |
| `webhook-signature` | P0 | Stripe, GitHub, Svix, Clerk... webhook handlers that use the event without verifying it |
| `sql-fstring` | P0 | SQL built with f-strings, `%`, `.format`, template literals or concatenation and passed to `execute` |
| `code-injection` | P0 | Request data reaching `eval`, `exec`, `Function` or a shell |
| `jwt-secret-default` | P0 | Signing secrets with a hardcoded value or `|| 'fallback'` |
| `unsafe-deserialization` | P0 | `yaml.load` without a safe loader, `pickle` on external input |
| `git-config-exec` | P0 | `.git/config` keys that run a program on ordinary git use (`core.fsmonitor`, `core.sshCommand`, `alias.x = !cmd`) |
| `llm-route-unthrottled` | P1 | Routes that call a paid LLM API with no auth and no rate limit |
| `admin-route-no-auth` | P1 | `/admin` routes without a session or role check |
| `password-reset` | P1 | Password login with no forgot/reset flow anywhere |
| `webhook-idempotency` | P1 | Webhook effects that are wrong when the provider retries |
| `rate-limiting` | P1 | A server with no rate limiting at all |
| `cors-wildcard` | P1 | `*` origins, `cors()` with no options, wildcard with credentials |
| `dangerous-html` | P1 | `dangerouslySetInnerHTML` / `v-html` on unsanitized values |
| `jwt-localstorage` | P1 | Auth tokens stored in `localStorage` / `sessionStorage` |
| `stack-trace-leak` | P1 | Exception details returned to the client |
| `sourcemaps-exposed` | P1 | Production source maps enabled |
| `env-not-ignored` | P1 | Dotenv files with credential-named values that git does not ignore |
| `disabled-ssl` | P1 | `verify=False`, `rejectUnauthorized: false` |
| `debug-mode` | P1 | `DEBUG = True`, `app.run(debug=True)`, `--reload` in a Dockerfile |
| `error-monitoring` | P1 | No Sentry or equivalent |

`mmu vibecheck --list-rules` prints this table; `mmu vibecheck --explain <rule>` prints what a rule looks for and how to fix it.

## Accuracy

Measured, reproducible, and written down with its limits in [`docs/benchmark.md`](./docs/benchmark.md).

| Measurement | Result |
|-------------|--------|
| 20 popular open-source apps (starters, SaaS kits, framework examples), default settings | 0 wrong P0 findings on review (11 before this release's rule rework) |
| 12 fixture projects with 55 planted issues | P0 precision 100%, P0 recall 100%, 52 of 55 planted issues found |
| Not detected | IDOR, plaintext password comparison, password column returned by login: no rule models authorization or data flow |

The fixtures were written alongside the rules, so treat them as a regression suite. The open-source sweep is the independent check.

## Use it directly

```bash
pip install make-me-unicorn          # or run any command through uvx make-me-unicorn ...
mmu vibecheck                        # whole project, human-readable
mmu vibecheck --staged               # what is about to be committed
mmu vibecheck --since origin/main    # what this branch changed
mmu vibecheck --format agent         # compact fix list for a coding agent
mmu vibecheck --format json          # schema mmu.vibecheck/v1
mmu vibecheck --format sarif --output mmu.sarif
```

Exit codes: `0` nothing blocking, `1` at least one finding at or above `--fail-on` (default `P0`), `2` the scan could not run. JSON schema: [`docs/vibecheck-json-schema.md`](./docs/vibecheck-json-schema.md).

### False positives

Suppress one line, with a reason (a suppression without a reason is ignored):

```ts
// mmu-ignore[webhook-signature]: verified by the API gateway before this handler runs
```

Or a path in `.mmu/config.toml`:

```toml
[vibecheck]
ignore = ["scripts/seed.ts:secrets", "examples/**:jwt-secret-default"]
```

Adopting the gate on an existing codebase: `mmu vibecheck --write-baseline` records today's findings, `mmu vibecheck --baseline` then reports only new ones.

## GitHub Actions

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@v4
  - uses: minjikim89/make-me-unicorn@v0.9.2
    with:
      sarif-file: mmu.sarif
  - uses: github/codeql-action/upload-sarif@v4
    if: always()
    with:
      sarif_file: mmu.sarif
```

Findings show up in the Security tab and as annotations on the pull request.

## Claude Code plugin

```text
/plugin marketplace add minjikim89/make-me-unicorn
/plugin install make-me-unicorn@make-me-unicorn
```

Registers the same three hooks from the plugin's bundled source (needs `python3` 3.10+, no `pip install`), plus a `/vibecheck` command, the `mmu-vibecheck` skill, and the MCP server (started with [uv](https://docs.astral.sh/uv/)).

## MCP server

For agents that prefer to ask: `mmu serve-mcp` exposes `mmu_vibecheck`, `mmu_explain_rule` and `mmu_list_rules` (read-only). Works with MCP SDK v1 and v2.

```json
{
  "mcpServers": {
    "mmu": { "command": "uvx", "args": ["--from", "make-me-unicorn[mcp]>=0.9", "mmu", "serve-mcp"] }
  }
}
```

The MCP tools are a convenience. The hooks are the gate.

## Add a rule

Rules live in [`src/mmu_cli/vibecheck/rules/`](./src/mmu_cli/vibecheck/rules/). A rule ships with a fixture in `bench/fixtures/`, the expected findings in `bench/expected/`, and must keep the benchmark at zero P0 false positives (`python -m unittest tests.test_bench`). See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Also in this repo: launch checklists

make-me-unicorn started as a launch checklist for solo builders, and that part still ships: 15 checklist categories, launch gates M0 to M5, focused session modes and an MCP blueprint server. It tracks what a project has decided and done; the gate above checks what the code actually does.

```bash
mmu init && mmu scan && mmu status
```

Details: [docs/checklists.md](./docs/checklists.md) and [SPEC.md](./SPEC.md).

## License

MIT
