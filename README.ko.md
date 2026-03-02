<div align="center">

# Make Me Unicorn

**눈 감고 만들지 마세요. 확신을 갖고 런칭하세요.**

솔로 빌더를 위한 오픈소스 런칭 체크리스트 & 운영 시스템.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![Status: v0.4](https://img.shields.io/badge/status-v0.4-blue.svg)](./ROADMAP.md)
[![CLI](https://img.shields.io/badge/cli-mmu-f59e0b.svg)](./SPEC.md)
[![Guardrails CI](https://img.shields.io/badge/ci-doctor%20%2B%20gates-22c55e.svg)](./.github/workflows/mmu-guardrails.yml)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-16a34a.svg)](./CONTRIBUTING.md)

[🇺🇸 English](./README.md) · **🇰🇷 한국어** · [🇯🇵 日本語](./README.ja.md) · [🇨🇳 简体中文](./README.zh-CN.md) · [🇪🇸 Español](./README.es.md)

<img src="./assets/brand/unicorn-hero.png" alt="Make Me Unicorn mascot" width="960" />

</div>

## 문제

SaaS 제품을 만들고 있습니다. AI로 코딩 속도는 역대급으로 빨라졌죠. 그런데:

> "잠깐, 비밀번호 재설정 플로우 넣었나?"
>
> "결제 webhook... 멱등성 처리했나?"
>
> "개인정보처리방침은? 환불 정책은? OG 메타 태그는?"
>
> "지난주에 인증 제공자 뭘로 하기로 했더라? 이유가 뭐였지?"

**코딩을 못 하는 게 아닙니다. 중요한 걸 놓치고 있는 겁니다.**

혼자 만드는 사람이라면 누구나 같은 벽에 부딪힙니다:

| 놓치는 것 | 치르는 대가 |
|-----------|------------|
| 로그인 만들면서 비밀번호 재설정을 빠뜨림 | 런칭 첫날부터 유저가 계정에 못 들어감 |
| webhook 서명 검증을 건너뜀 | 공격자가 결제 이벤트를 재전송함 |
| OG 태그 없이 런칭 | 공유한 링크가 전부 깨져 보임 |
| AI 세션 간 컨텍스트가 유실됨 | 매번 프로젝트를 처음부터 다시 설명함 |
| 환불 정책이 없음 | 첫 분쟁 = Stripe 계정 동결 |

MMU는 이런 문제들이 **유저, 매출, 신뢰를 잃기 전에** 잡아냅니다.

## 작동 방식

```
mmu init                    # 1. 15개 카테고리, 534개 이상의 체크리스트 항목 생성
mmu scan                    # 2. 기술 스택 자동 감지 — 이미 구현된 항목 자동 체크
mmu                         # 3. 완료된 것과 빠진 것을 한눈에 확인
mmu status --why            # 4. 점수 산출 근거 확인 — 반영된 항목, 제외된 항목
mmu next                    # 5. 우선순위 기반 다음 액션 추천
```

```text
  🦄  MAKE ME UNICORN — STATUS DASHBOARD

          .--*--.
         / °v°  \          Stage: HATCHING    ██████░░░░░░░░░░░░░░  22%
        |       |
         \ ___ /           📋 LAUNCH GATES
          '---'              M0 Problem Fit   ████████████████  ✓ PASS
                             M1 Build Fit     ████████████████  ✓ PASS
  🗺️ BLUEPRINTS (124/551)   M2 Revenue Fit   ████████████████  ✓ PASS
    Frontend    ██████░░ 41%   M3 Trust Fit     ████████████████  ✓ PASS
    Backend     ████████ 53%   M4 Growth Fit    ████████████░░░░  ✗ OPEN
    Auth        ██████░░ 38%   M5 Scale Fit     ███░░░░░░░░░░░░░  ✗ OPEN
    ...13 more
```

유니콘은 빌드 진행에 따라 성장합니다: Egg → Hatching → Foal → Young → Unicorn → Legendary.

## 나에게 맞는 체크리스트로 커스터마이즈

모든 프로젝트에 결제가 필요한 건 아닙니다. 모든 제품에 다국어가 필요한 것도 아닙니다. MMU는 적응합니다:

```bash
mmu init                      # 기술 스택 선택 (Next.js, Django, Rails, ...)
```

`.mmu/config.toml`이 생성됩니다 — 해당하지 않는 항목을 자동 제외하는 피처 플래그:

```toml
[features]
billing = false               # Stripe 안 쓰나요? 결제 관련 항목이 점수에 반영되지 않습니다
i18n = false
native_mobile = false

[architecture]
framework = "nextjs"
```

점수는 **내 프로젝트에 해당하는 항목만** 반영됩니다. `mmu status --why`로 산출 근거를 투명하게 확인할 수 있습니다 — Lighthouse처럼, 하지만 SaaS 런칭 준비도 버전.

## MMU가 챙겨주는 것 (당신이 기억하지 않아도)

<table>
<tr>
<td width="33%">

**제품 만들기**
- Frontend (반응형, a11y, 폼)
- Backend (API, DB, 큐)
- Auth (로그인, 재설정, OAuth, 세션)
- Billing (Stripe, webhook, 환불)
- Testing (유닛, E2E, 에이전트 안전성)

</td>
<td width="33%">

**런칭 준비하기**
- SEO (OG 태그, sitemap, 메타)
- Legal (개인정보처리방침, 이용약관, GDPR)
- Security (CORS, rate limit, 시크릿 관리)
- Performance (캐싱, 레이지 로드)
- CI/CD (파이프라인, 롤백 플랜)

</td>
<td width="34%">

**런칭 후 운영하기**
- Monitoring (에러, 업타임, 알림)
- Analytics (퍼널, 리텐션, 이벤트)
- Email (트랜잭션, 템플릿)
- Accessibility (WCAG, 키보드 내비게이션)
- Reliability (백업, 장애 대응 플랜)

</td>
</tr>
</table>

**534개 이상의 항목. 15개 카테고리. 추측 제로.**

## 이런 분들을 위해 만들었습니다

| 당신이... | MMU가 도와주는 것 |
|-----------|-------------------|
| **AI로 코딩하는 창업자** | 매 세션마다 프로젝트를 처음부터 설명하는 걸 그만두세요. 도구 간 컨텍스트를 유지하세요. |
| **프론트엔드 개발자** | 정확히 뭘 만들어야 하는지 알 수 있습니다: 인증 플로우, 에러 상태, 반응형 브레이크포인트, OG 태그. |
| **PM / 기획자** | 구조화된 PRD, 가격 전략, 런칭 체크리스트를 마크다운으로 한 번에 받으세요. |
| **풀스택 빌더** | 프론트엔드, 백엔드, 결제, 컴플라이언스를 한곳에서 추적하세요. 빠지는 것 없이. |

## 빠른 시작

```bash
pip install -e .

# 옵션 A: 빈 템플릿으로 시작하고 직접 채우기
mmu init

# 옵션 B: Claude가 프로젝트 문서를 생성 (API 키 필요)
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=sk-ant-...
mmu init --interactive        # 5가지 질문에 답하면 → 전략, 제품, 가격 문서가 자동 생성
```

그다음:

```bash
mmu scan                      # 기술 스택 자동 감지
mmu                           # 대시보드 확인
mmu status --why              # 점수 산출 근거 상세 확인
mmu next                      # 우선순위 기반 다음 액션 Top 3 확인
mmu show frontend             # 특정 카테고리 상세 보기
mmu check frontend 3          # 항목 완료 처리
mmu gate --stage M0           # 다음 단계 진입 가능 여부 확인
mmu doctor                    # 가드레일 헬스 체크 실행
```

## 6개의 Launch Gates

단계별 출구 조건이라고 생각하세요. 건너뛰지 마세요.

```
M0 Problem Fit    →  누구를 위해, 왜 만드는지 알고 있는가?
M1 Build Fit      →  핵심 제품이 실제로 끝까지 동작하는가?
M2 Revenue Fit    →  결제가 가능한가? 환불도 되는가?
M3 Trust Fit      →  개인정보처리방침? 고객 지원 경로? 로깅?
M4 Growth Fit     →  공유 링크가 제대로 보이는가? 검색에서 찾을 수 있는가?
M5 Scale Fit      →  새벽 3시에 장애 나면 어떻게 되는가?
```

`mmu gate --stage M0`으로 검증하세요. 미체크 항목이 하나라도 있으면 = NOT PASS.

## 12개의 운영 모드

세션당 하나의 모드. 각 모드는 필요한 문서만 로드합니다.

```bash
mmu start --mode backend      # 로드: architecture.md, sprint, ADR 로그
mmu start --mode billing      # 로드: pricing.md, 결제 체크리스트, 컴플라이언스
mmu start --mode growth       # 로드: SEO 체크리스트, 지표 문서
```

AI 코딩의 1순위 문제인 **컨텍스트 과부하**를 방지합니다. AI 어시스턴트에게 프로젝트 전체가 아닌, 딱 필요한 것만 전달됩니다.

## AI 연동 (선택)

MMU는 AI 없이도 동작합니다. 하지만 Claude와 함께 쓰면 훨씬 강력해집니다:

```bash
pip install make-me-unicorn[llm]
export ANTHROPIC_API_KEY=sk-ant-...
```

| 명령어 | 하는 일 |
|--------|---------|
| `mmu init --interactive` | 제품에 대한 5가지 질문에 답하면 Claude가 전략, 제품 스펙, 가격, 아키텍처, UX 문서를 작성합니다. |
| `mmu start --mode X --agent` | 세션 컨텍스트를 자동 포맷 — Claude Code나 다른 LLM에 바로 붙여넣으세요. |
| `mmu doctor --deep` | Claude가 코드와 문서를 읽고, 불일치, 보안 취약점, 놓친 부분을 찾아냅니다. |
| `mmu generate strategy` | 현재 프로젝트 상태를 기반으로 핵심 문서를 생성하거나 업데이트합니다. |

코어 CLI는 외부 의존성 제로. AI 기능은 선택이며, 없어도 정상 동작합니다.

## 세션 워크플로우

모든 세션은 같은 리듬을 따릅니다:

```
1. mmu start --mode backend      ← 포커스를 정하고, 관련 문서를 로드
2. Build / decide / validate      ← 작업 수행
3. mmu close                      ← 변경 사항과 다음 할 일을 기록
```

세션 종료 시 구조화된 태그로 기록합니다:

- `[DONE]` — 완료한 작업
- `[DECISION]` — 내린 결정 (중요하면 ADR 생성)
- `[ISSUE]` — 문제 발생 (유형 분류: 컨텍스트 유실 / 잘못된 방향 / 문서-코드 불일치)
- `[NEXT]` — 다음 세션의 첫 번째 할 일

다음 세션이 "어디까지 했더라?"로 15분 낭비하는 대신, **5초 만에** 시작됩니다.

## 예제: TaskNote

MMU를 실제로 채워 넣은 예제를 확인하세요:

```
examples/filled/tasknote/
├── docs/core/strategy.md      ← ICP, 가치 제안, 경쟁사
├── docs/core/product.md       ← MVP 범위, 유저 저니, P0/P1
├── docs/core/pricing.md       ← Free/Pro/Team, 결제 규칙
├── docs/core/architecture.md  ← Next.js + FastAPI + Postgres
├── docs/adr/001_billing_provider_choice.md  ← 왜 Stripe를 결제 제공자로 선택했는가?
└── current_sprint.md          ← 이번 주 3가지 목표
```

## 요구 사항

- Python `3.10+`
- `pip`
- Core CLI: 외부 의존성 없음
- AI 기능: `pip install make-me-unicorn[llm]`

## 프로젝트 구조

```
make-me-unicorn/
├── src/mmu_cli/           # CLI source (Python)
├── docs/
│   ├── core/              # Strategy, Product, Pricing, Architecture, UX
│   ├── ops/               # Roadmap, Metrics, Compliance, Reliability
│   ├── blueprints/        # 15 category checklists (534+ items)
│   ├── checklists/        # M0–M5 launch gates
│   └── adr/               # Decision log templates
├── prompts/               # Session start/close/ADR templates
├── examples/filled/       # Concrete example (TaskNote)
└── tests/                 # Unit tests
```

## CI 가드레일

`mmu doctor`는 모든 PR에서 실행됩니다. `mmu gate`는 `docs/ops/gate_targets.txt`에 명시된 단계에 대해 실행됩니다.

## 기여하기

`CONTRIBUTING.md`를 참고하세요.

## 라이선스

MIT. `LICENSE` 파일을 참고하세요.
