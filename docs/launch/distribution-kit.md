# Distribution kit (0.9.0)

Copy-paste posts for the 0.9.0 launch. Every number below is from `docs/benchmark.md` or a linked source; update them if the benchmark changes. Post from a personal account, one channel at a time, and answer comments yourself.

Links:

- Repo: https://github.com/minjikim89/make-me-unicorn
- Benchmark: https://github.com/minjikim89/make-me-unicorn/blob/main/docs/benchmark.md
- PyPI: https://pypi.org/project/make-me-unicorn/

## Show HN

Title (pick one, under 80 characters):

- `Show HN: A git-commit gate that stops coding agents from shipping unsigned webhooks`
- `Show HN: Make-me-unicorn, a deterministic launch gate for AI coding agents`

URL: the repo.

First comment:

> Coding agents are good at the code that is there and bad at the code that is not: the Stripe webhook that never verifies the signature, the Supabase migration without RLS, the paid LLM route with no auth. Linters and secret scanners do not flag a function that does not exist, and agents skip optional tools.
>
> So this is a hook. `uvx make-me-unicorn install --claude` (also `--codex`, `--cursor`, `--gemini`, `--git`) registers a PreToolUse hook on git commit/push, a Stop hook and a post-edit hook. A P0 finding denies the commit and gives the agent file:line plus a concrete fix; the agent fixes it and commits again.
>
> Choices I made:
>
> - Deterministic heuristics (regex plus Python AST), no LLM, no network, no account. Median 89 ms on 20 real repos, 1.1 s on the largest (1,699 files).
> - P0 only on specific evidence. Anything about something being absent is a warning unless the evidence is clear.
> - Fail-open: if the scanner crashes, the commit goes through with a visible warning. `MMU_HOOK_DISABLE=1` bypasses it.
> - The stop gate only looks at files the agent edited in that session.
> - Suppressions need a written reason.
>
> Accuracy: I ran it on 20 popular open-source starters, SaaS kits and framework examples. The previous rule set produced 16 P0 findings there, 11 of them wrong; after the rework there are 4, all matching what the rule describes (hardcoded session secrets in example apps). There is also a fixture benchmark, but I wrote the fixtures alongside the rules, so treat it as a regression suite.
>
> What it does not do: authorization logic (IDOR), data flow, anything that needs to run the app. Claude Code is tested in live sessions; Codex, Cursor and Gemini CLI follow their documented hook contracts but have not been tested in real sessions yet, reports welcome.
>
> The repo started as a launch checklist for solo founders. That part still ships, but the gate is the point now.

## X thread

1/
> Coding agents rarely write SQL injection anymore. What they skip is the code that should exist: webhook signature checks, Supabase RLS, auth on the paid LLM route.
>
> make-me-unicorn 0.9 is a git-commit gate for that. Deterministic, offline, no LLM.
> https://github.com/minjikim89/make-me-unicorn

2/
> One command:
> `uvx make-me-unicorn install --claude`
> (or --codex, --cursor, --gemini, --git)
>
> A P0 finding denies the agent's `git commit` and hands it file:line plus a fix. It fixes, re-runs, commits.

3/
> Why a hook: agents skip optional tools. They cannot skip a hook.
> Why no LLM: a gate has to give the same answer twice, run in 0.1 s, and work offline.

4/
> Measured on 20 open-source starters and SaaS kits: 0 wrong P0 findings after review (the old rules had 11).
> Benchmark and its limits: https://github.com/minjikim89/make-me-unicorn/blob/main/docs/benchmark.md

5/
> 23 rules, all in plain Python, each with a fixture. P0s: secrets, client-bundle secrets, Supabase RLS, webhook signature, interpolated SQL, code injection, hardcoded JWT secrets, unsafe deserialization, command-executing git config.

## GeekNews (news.hada.io)

제목: `make-me-unicorn 0.9: AI 코딩 에이전트의 git commit을 막는 결정적 출시 게이트`

본문:

> - AI 코딩 에이전트가 자주 빠뜨리는 "있어야 할 코드"를 commit 시점에 검사하는 CLI. 대상은 Stripe 등 webhook 서명 검증, Supabase 테이블 RLS, 브라우저 번들에 들어간 secret, 문자열 보간 SQL, 인증 없는 유료 LLM route 등 23개 규칙
> - `uvx make-me-unicorn install --claude`로 Claude Code의 PreToolUse·Stop·PostToolUse hook에 등록. Codex CLI, Cursor, Gemini CLI, git pre-commit, GitHub Actions(SARIF)도 지원
> - P0 발견 시 commit이 거부되고 에이전트에게 파일:라인과 수정 방법이 전달됨. 에이전트가 수정 후 다시 commit
> - LLM·네트워크·계정 없이 결정적으로 동작. 실제 저장소 20개 기준 중앙값 89ms
> - 스캐너 오류 시 차단하지 않고 통과(fail-open). suppress에는 사유 필수
> - 공개 저장소 20개(스타터·SaaS 키트·프레임워크 예제) 스윕에서 검토 후 오탐 P0 0건(이전 규칙은 16건 중 11건 오탐). 결과와 한계는 docs/benchmark.md에 공개
> - IDOR 같은 권한 로직과 데이터 흐름 분석은 범위 밖

## Directory and list submissions

| Destination | How | Text |
|---|---|---|
| Official MCP Registry | `mcp-publisher publish` after the PyPI release (README carries the `mcp-name` marker) | from `server.json` |
| mcpservers.org (wong2/awesome-mcp-servers) | web form at https://mcpservers.org/submit | "Deterministic launch gate for AI-written code: scans for unverified webhooks, missing Supabase RLS, leaked keys and 20 more gaps; read-only tools mmu_vibecheck, mmu_explain_rule, mmu_list_rules." |
| Glama (needed for punkpeye/awesome-mcp-servers) | sign in at https://glama.ai, add the GitHub repo as an MCP server, then open the awesome-mcp-servers PR with the Glama badge | one line: "make-me-unicorn: deterministic launch gate for AI-written code (webhook signatures, Supabase RLS, leaked keys); read-only scan tools." |
| hesreallyhim/awesome-claude-code | web issue form on that repo (human submission only) | Category: Hooks. "make-me-unicorn: PreToolUse/Stop/PostToolUse hooks that block git commit when the agent ships an unverified webhook, a Supabase table without RLS or a leaked key. Deterministic, offline, fail-open." |
