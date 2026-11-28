<div align="center">

# make-me-unicorn

**AI 코딩 에이전트를 위한 출시 게이트입니다.**

서명을 검증하지 않고 이벤트를 신뢰하는 webhook, RLS가 없는 Supabase 테이블,<br>
브라우저 번들에 들어간 `service_role` 키는 에이전트가 commit할 수 없습니다. 결정적이고, 오프라인으로 동작하며, 계정과 LLM이 필요 없고, 약 0.1초면 끝납니다.

[![PyPI](https://img.shields.io/pypi/v/make-me-unicorn?color=blue)](https://pypi.org/project/make-me-unicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![CI](https://github.com/minjikim89/make-me-unicorn/actions/workflows/mmu-guardrails.yml/badge.svg)](./.github/workflows/mmu-guardrails.yml)
[![Benchmark](https://img.shields.io/badge/P0%20false%20positives-0%20in%2020%20OSS%20repos-22c55e)](./docs/benchmark.md)

[English](./README.md) · **한국어** · [日本語](./README.ja.md) · [简体中文](./README.zh-CN.md) · [Español](./README.es.md)

</div>

<!-- mcp-name: io.github.minjikim89/make-me-unicorn -->

```bash
uvx make-me-unicorn install --claude    # or --codex, --cursor, --gemini, --git, --all
```

설정은 이것으로 끝입니다. 이제부터 에이전트가 `git commit`을 실행하면 hook이 staged 상태의 내용을 스캔합니다. P0 finding이 나오면 명령을 거부하고, 에이전트가 바로 적용할 수 있는 수정 방법을 넘겨줍니다. 아래는 Next.js + Supabase + Stripe 프로젝트의 첫 commit에서 나온 실제 출력입니다(줄은 줄였고, P1 경고 5건은 생략):

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

에이전트는 수정하고, 다시 실행한 뒤 commit합니다. 코드가 이미 올바르면 게이트는 아무것도 출력하지 않습니다. 실제 Claude Code 세션 테스트에서 에이전트는 서명을 검증하는 Stripe webhook을 한 번에 작성했고, commit은 그대로 통과했습니다.

## 부재 검사가 필요한 이유

Secret 스캐너와 SAST는 이미 존재하는 나쁜 코드를 찾습니다. 에이전트가 작성한 코드는 존재하지 않는 코드 때문에 문제가 되는 경우가 더 많습니다. 아무도 작성하지 않은 서명 검증, 추가된 적 없는 RLS 정책, 유료 LLM route 앞에 빠져 있는 rate limit이 그 예입니다.

- Tenzai는 코딩 에이전트 5종에 같은 앱 3개를 만들게 했습니다(총 15개 앱). 악용 가능한 SQLi나 XSS가 있는 앱은 하나도 없었지만, 보안 통제에 대해서는 "in almost all cases, they didn't even try"(거의 모든 경우 시도조차 하지 않았다)였습니다 ([SecurityWeek, 2026년 1월](https://www.securityweek.com/vibe-coding-tested-ai-agents-nail-sqli-but-fail-miserably-on-security-controls/)).
- GitGuardian의 측정에 따르면 Claude Code를 사용한 공개 commit의 secret 유출률은 3.2%였고, 기준치는 1.5%였습니다 ([State of Secrets Sprawl 2026](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/)).

Linter는 존재하지 않는 함수를 지적하지 못합니다. `mmu vibecheck`는 리뷰어가 "이 webhook은 어디에서 검증하나요?"라고 묻듯이 프로젝트를 읽고, 답이 분명히 "어디에도 없음"일 때만 차단합니다.

## 게이트 동작 방식

에이전트는 선택 사항인 도구는 건너뜁니다. hook은 건너뛸 수 없습니다. `mmu install`은 `mmu hook`을 호출하는 hook 항목을 기록하고, `mmu hook`은 각 호스트의 hook 프로토콜에 맞춰 응답합니다.

| 호스트 | Commit / push 게이트 | "미완료" 게이트 | 편집 후 피드백 | `mmu install` 플래그 |
|------|--------------------|---------------------|--------------------|--------------------|
| Claude Code | `Bash`에 대한 `PreToolUse` | `Stop` | `Edit`/`Write`/`MultiEdit`에 대한 `PostToolUse` | `--claude` |
| Codex CLI | `Bash`에 대한 `PreToolUse` | `Stop` | `apply_patch`에 대한 `PostToolUse` | `--codex` |
| Cursor | `beforeShellExecution` | `stop` | 미지원 | `--cursor` |
| Gemini CLI | `run_shell_command`에 대한 `BeforeTool` | `AfterAgent` | 미지원 | `--gemini` |
| git | `pre-commit`, 기존 hook이 있으면 이어서 실행 | | | `--git` |
| pre-commit 프레임워크 | hook id `mmu-vibecheck` | | | `.pre-commit-hooks.yaml` |
| GitHub Actions | `uses: minjikim89/make-me-unicorn@v0.9.2`, SARIF를 code scanning으로 전송 | | | |

- **Commit 게이트**는 commit에 들어갈 내용을 스캔합니다. 기본 대상은 staged 파일이고, `git commit -a`, pathspec, `git add ... && git commit`의 경우에는 변경된 파일입니다. push는 upstream 이후 변경된 내용을 스캔합니다.
- **"미완료" 게이트**는 에이전트가 작업을 끝내려 할 때 실행됩니다. 이번 세션에서 에이전트가 편집한 파일만 보기 때문에, 건드리지 않은 코드를 다시 쓰게 만드는 일은 없습니다. 에이전트를 되돌려 보내는 횟수는 최대 `MMU_STOP_MAX`번(기본값 3)입니다. 보안 강화를 나중으로 미루라고 에이전트에 지시한 경우에는 P0 목록을 보여주고 멈춥니다.
- **편집 후 피드백**은 방금 작성한 파일의 P0 finding을 컨텍스트로 돌려줍니다. 차단은 하지 않습니다.
- `mmu install --all`, `--dry-run`, `--uninstall`을 지원합니다. `--agents-md`는 `AGENTS.md`에 지시 블록을 추가하고, `--skill`은 `mmu-vibecheck` Agent Skill을 `.agents/skills/`에 복사합니다. 기존 설정은 병합하며, 덮어쓰지 않습니다.

Claude Code는 실제 세션에서 테스트했습니다. Codex CLI, Cursor, Gemini CLI는 문서화된 hook 계약을 따르며, 문서에 나온 payload로 테스트했습니다. 실제 세션에서 사용해 본 결과 제보를 환영합니다.

설계 제약(모두 테스트로 확인):

- **결정적.** 같은 트리에서는 같은 finding이 나옵니다. 모델 호출, 네트워크, 계정이 없습니다.
- **Fail-open.** 스캐너 자체가 crash하거나 timeout되면 눈에 보이는 경고와 함께 명령을 통과시킵니다. 게이트가 고장 나도 세션이 멈추지 않습니다.
- **사람은 우회 가능.** 명령 하나만 우회하려면 `MMU_HOOK_DISABLE=1 git commit ...`을 사용합니다. 에이전트의 환경 변수로 설정하면 해당 세션에서 게이트가 꺼집니다.
- **빠름.** 실제 저장소 20개 기준 중앙값 89 ms, 가장 큰 저장소(파일 1,699개)에서 1.1 s입니다.

## 탐지 항목

P0는 차단하고 P1은 경고합니다. 부재를 추정하는 휴리스틱은 근거가 구체적이지 않으면 모두 P1입니다.

| Rule | 심각도 | 탐지 대상 |
|------|-----|-------|
| `secrets` | P0 | 소스, 설정 파일, 또는 git이 ignore하지 않는 dotenv 파일에 들어 있는 실제 provider 키와 Supabase `service_role` JWT |
| `client-bundle-secrets` | P0 | `NEXT_PUBLIC_` / `VITE_` / `EXPO_PUBLIC_` prefix가 붙었거나 client 코드에서 읽는 secret |
| `supabase-rls` | P0 | migration에서 `ENABLE ROW LEVEL SECURITY` 없이 생성된 테이블 |
| `webhook-signature` | P0 | 이벤트를 검증하지 않고 사용하는 Stripe, GitHub, Svix, Clerk... webhook handler |
| `sql-fstring` | P0 | f-string, `%`, `.format`, template literal 또는 문자열 연결로 만들어 `execute`에 전달하는 SQL |
| `code-injection` | P0 | `eval`, `exec`, `Function` 또는 shell에 도달하는 요청 데이터 |
| `jwt-secret-default` | P0 | 값이 하드코딩되었거나 `|| 'fallback'`이 있는 서명용 secret |
| `unsafe-deserialization` | P0 | safe loader 없는 `yaml.load`, 외부 입력에 대한 `pickle` |
| `git-config-exec` | P0 | 일반적인 git 사용 중에 프로그램을 실행하는 `.git/config` 키 (`core.fsmonitor`, `core.sshCommand`, `alias.x = !cmd`) |
| `llm-route-unthrottled` | P1 | 인증과 rate limit 없이 유료 LLM API를 호출하는 route |
| `admin-route-no-auth` | P1 | 세션 또는 role 확인이 없는 `/admin` route |
| `password-reset` | P1 | 비밀번호 로그인은 있지만 비밀번호 찾기/재설정 흐름이 어디에도 없음 |
| `webhook-idempotency` | P1 | provider가 재시도하면 결과가 잘못되는 webhook 처리 |
| `rate-limiting` | P1 | rate limiting이 전혀 없는 서버 |
| `cors-wildcard` | P1 | `*` origin, 옵션 없는 `cors()`, credentials와 함께 쓴 wildcard |
| `dangerous-html` | P1 | sanitize하지 않은 값에 쓴 `dangerouslySetInnerHTML` / `v-html` |
| `jwt-localstorage` | P1 | `localStorage` / `sessionStorage`에 저장한 인증 토큰 |
| `stack-trace-leak` | P1 | client에 반환되는 예외 상세 정보 |
| `sourcemaps-exposed` | P1 | production source map 활성화 |
| `env-not-ignored` | P1 | credential로 보이는 이름의 값이 들어 있는데 git이 ignore하지 않는 dotenv 파일 |
| `disabled-ssl` | P1 | `verify=False`, `rejectUnauthorized: false` |
| `debug-mode` | P1 | `DEBUG = True`, `app.run(debug=True)`, Dockerfile의 `--reload` |
| `error-monitoring` | P1 | Sentry 또는 동급 도구 없음 |

`mmu vibecheck --list-rules`는 이 표를 출력하고, `mmu vibecheck --explain <rule>`은 해당 rule이 무엇을 찾는지와 수정 방법을 출력합니다.

## 정확도

측정했고, 재현할 수 있으며, 한계까지 [`docs/benchmark.md`](./docs/benchmark.md)에 기록했습니다.

| 측정 | 결과 |
|-------------|--------|
| 인기 오픈소스 앱 20개(starter, SaaS kit, 프레임워크 예제), 기본 설정 | 검토 결과 잘못된 P0 finding 0건 (이번 릴리스의 rule 재작업 전에는 11건) |
| 문제 55개를 심어 둔 fixture 프로젝트 12개 | P0 precision 100%, P0 recall 100%, 심어 둔 문제 55개 중 52개 탐지 |
| 탐지하지 못함 | IDOR, 평문 비밀번호 비교, 로그인 응답에 포함된 password 컬럼: 인가나 데이터 흐름을 모델링하는 rule이 없음 |

Fixture는 rule과 함께 작성했으므로 회귀 테스트 모음으로 보아야 합니다. 독립적인 검증은 오픈소스 저장소 대상 스캔입니다.

## 직접 실행하기

```bash
pip install make-me-unicorn          # or run any command through uvx make-me-unicorn ...
mmu vibecheck                        # whole project, human-readable
mmu vibecheck --staged               # what is about to be committed
mmu vibecheck --since origin/main    # what this branch changed
mmu vibecheck --format agent         # compact fix list for a coding agent
mmu vibecheck --format json          # schema mmu.vibecheck/v1
mmu vibecheck --format sarif --output mmu.sarif
```

종료 코드: `0`은 차단할 항목 없음, `1`은 `--fail-on`(기본값 `P0`) 이상의 finding이 1건 이상, `2`는 스캔을 실행하지 못함. JSON schema: [`docs/vibecheck-json-schema.md`](./docs/vibecheck-json-schema.md).

### False positive

이유를 적어 한 줄만 억제할 수 있습니다(이유가 없는 억제는 무시됩니다):

```ts
// mmu-ignore[webhook-signature]: verified by the API gateway before this handler runs
```

또는 `.mmu/config.toml`에서 경로 단위로 지정합니다:

```toml
[vibecheck]
ignore = ["scripts/seed.ts:secrets", "examples/**:jwt-secret-default"]
```

기존 코드베이스에 게이트를 도입할 때: `mmu vibecheck --write-baseline`으로 현재 finding을 기록해 두면, 이후 `mmu vibecheck --baseline`은 새로 생긴 finding만 보고합니다.

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

Finding은 Security 탭에 표시되고, pull request에는 annotation으로 표시됩니다.

## Claude Code 플러그인

```text
/plugin marketplace add minjikim89/make-me-unicorn
/plugin install make-me-unicorn@make-me-unicorn
```

플러그인에 포함된 소스로 동일한 hook 3개를 등록하고(`python3` 3.10+ 필요, `pip install` 불필요), `/vibecheck` 명령, `mmu-vibecheck` skill, MCP 서버([uv](https://docs.astral.sh/uv/)로 실행)를 함께 제공합니다.

## MCP 서버

직접 물어보는 방식을 선호하는 에이전트를 위한 기능입니다. `mmu serve-mcp`는 `mmu_vibecheck`, `mmu_explain_rule`, `mmu_list_rules`를 제공합니다(읽기 전용). MCP SDK v1과 v2에서 동작합니다.

```json
{
  "mcpServers": {
    "mmu": { "command": "uvx", "args": ["--from", "make-me-unicorn[mcp]>=0.9", "mmu", "serve-mcp"] }
  }
}
```

MCP 도구는 편의 기능입니다. 게이트는 hook입니다.

## Rule 추가하기

Rule은 [`src/mmu_cli/vibecheck/rules/`](./src/mmu_cli/vibecheck/rules/)에 있습니다. Rule에는 `bench/fixtures/`의 fixture와 `bench/expected/`의 예상 finding이 함께 있어야 하고, 벤치마크의 P0 false positive를 0으로 유지해야 합니다(`python -m unittest tests.test_bench`). [CONTRIBUTING.md](./CONTRIBUTING.md)를 참고하세요.

## 이 저장소의 다른 기능: 출시 체크리스트

make-me-unicorn은 솔로 빌더를 위한 출시 체크리스트로 시작했고, 그 기능도 계속 제공합니다. 체크리스트 카테고리 15개, 출시 게이트 M0~M5, 집중 세션 모드, MCP blueprint 서버가 있습니다. 체크리스트는 프로젝트에서 결정하고 완료한 내용을 추적하고, 위의 게이트는 코드가 실제로 하는 일을 검사합니다.

```bash
mmu init && mmu scan && mmu status
```

자세한 내용: [docs/checklists.md](./docs/checklists.md), [SPEC.md](./SPEC.md).

## 라이선스

MIT
