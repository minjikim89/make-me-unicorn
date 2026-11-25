---
name: mmu-vibecheck
description: Deterministic launch gate for code you just wrote. Run it after writing or changing webhook handlers, auth/login/password or session code, payment or Stripe code, Supabase migrations or RLS policies, CORS or rate-limit config, env vars or API keys, raw SQL, or build config. Always run it before committing, opening a PR, deploying, or telling the user the work is done or production-ready. No LLM, no account, under a second.
license: MIT
compatibility: Needs Python 3.10+ with `mmu` (pip install make-me-unicorn) or `uvx` on PATH. Scoped scans need a git repository.
metadata:
  homepage: https://github.com/minjikim89/make-me-unicorn
---

# mmu vibecheck: the launch gate

`mmu vibecheck` is a static scanner for the gaps AI-written apps ship most: hardcoded secrets, secrets behind public env prefixes, unverified webhooks, Supabase tables without RLS, f-string SQL, wildcard CORS, missing rate limits, debug mode, disabled TLS verification, unsafe deserialization. It does not call a model or the network. Treat its exit code as the definition of "safe to commit".

## Run it

```bash
mmu vibecheck --changed --format agent
```

- `--changed` limits findings to files changed vs `HEAD` plus untracked files. Use `--staged` right before a commit, `--since <ref>` before a push or PR, and no scope flag for a full pre-launch scan.
- `--format agent` prints compact text: rule id, `path:line`, what is wrong, the fix, and how to silence a false positive. Use `--format json` when you need to parse it (`docs/vibecheck-json-schema.md`, schema `mmu.vibecheck/v1`).
- Not installed? Run `uvx make-me-unicorn vibecheck --changed --format agent`. It needs no setup and no account.
- The MCP tool `mmu_vibecheck(project_root, scope="changed", format="agent")` returns the same result when the MMU MCP server is connected.

## Read the result

| Exit | Meaning | What to do |
|------|---------|------------|
| 0 | No blocking findings | Proceed. Mention open P1 warnings to the user if they touch the task. |
| 1 | P0 (launch-blocking) findings | Do not commit, deploy, or say "done". Fix them. |
| 2 | The scanner could not run (bad path, not a git repo for a scoped scan) | Read the error, fix the invocation (for example drop `--changed` outside git), and run again. |

- **P0** blocks. Each one names a `path:line` and a concrete fix.
- **P1** warns and does not change the exit code. Fix it when it is in the scope of the task; otherwise report it.
- A P0 found only in test or fixture paths is reported as P1.
- `confidence: low` marks absence heuristics (for example "no rate limiting found"). Verify by reading the code before acting.

## The loop

1. Run `mmu vibecheck --changed --format agent`.
2. For each P0: open the reported `path:line`, apply the `fix` line, keep the change minimal.
3. Run the same command again.
4. Repeat until it prints `0 blocking`. Only then commit or report the work as done, and say that the gate passed.

`mmu vibecheck --explain <rule-id>` shows what a rule detects, why it matters, and the fix in full. `mmu vibecheck --list-rules` lists every rule.

## Silencing a finding

Never silence a finding to get past the gate. Only when you have read the code and it is a real false positive:

```python
STRIPE_DOCS_SAMPLE = "sk_test_..."  # mmu-ignore[secrets]: published sample key from the Stripe docs
```

- The marker goes in a comment on the flagged line or alone on the line above it: `mmu-ignore[<rule-id>]: <reason>`.
- A marker without a reason is not applied.
- Project-wide exceptions go in `.mmu/config.toml` under `[vibecheck] ignore = ["rule-id", "path/glob/**:rule-id"]`.
- Tell the user which findings you silenced and why.

## Make it automatic

`mmu install --claude` (or `--codex`, `--cursor`, `--gemini`, `--git`, `--agents-md`, `--all`) registers hooks that run this gate before `git commit` / `git push` and when the agent is about to stop. If a hook blocks you, its message is this scanner's output: fix the findings and retry; do not bypass it.
