<div align="center">

# Make Me Unicorn

**别再闭眼开发了。带着信心上线你的 SaaS。**

面向独立开发者的开源上线检查清单与运营系统。

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![Status: v0.4](https://img.shields.io/badge/status-v0.4-blue.svg)](./ROADMAP.md)
[![CLI](https://img.shields.io/badge/cli-mmu-f59e0b.svg)](./SPEC.md)
[![Guardrails CI](https://img.shields.io/badge/ci-doctor%20%2B%20gates-22c55e.svg)](./.github/workflows/mmu-guardrails.yml)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-16a34a.svg)](./CONTRIBUTING.md)

[🇺🇸 English](./README.md) · [🇰🇷 한국어](./README.ko.md) · [🇯🇵 日本語](./README.ja.md) · **🇨🇳 简体中文** · [🇪🇸 Español](./README.es.md)

<img src="./assets/brand/unicorn-hero.png" alt="Make Me Unicorn mascot" width="960" />

</div>

## 问题所在

你正在做一个 SaaS 产品。你用 AI 写代码，速度前所未有。但接下来：

> "等等，我加了密码重置流程吗？"
>
> "支付 webhook... 做幂等了吗？"
>
> "隐私政策写了没？退款政策呢？OG 标签呢？"
>
> "上周关于认证方案的决定是什么来着？为什么选它？"

**你不是代码写不好，而是没有管好该管的事。**

每个独立开发者都会撞上同样的墙：

| 哪里出了问题 | 代价是什么 |
|-------------|-----------|
| 做登录的时候忘了密码重置 | 上线第一天用户就被锁在门外 |
| 跳过了 webhook 签名验证 | 攻击者重放支付事件 |
| 没加 OG 标签就上线了 | 分享出去的链接看起来都像坏掉了一样 |
| AI 会话之间丢失上下文 | 每次都要从头给 AI 解释你的项目 |
| 没有退款政策 | 第一次争议 = Stripe 账户直接冻结 |

MMU 在这些问题**让你损失用户、金钱或信任之前**就帮你拦住。

## 工作原理

```
mmu init                    # 1. 获取 15 个类别、534+ 检查项
mmu scan                    # 2. 自动检测你的技术栈，并自动勾选已完成项
mmu                         # 3. 一眼看到哪些做了、哪些没做
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

你的独角兽会随着项目进度不断进化：Egg → Hatching → Foal → Young → Unicorn → Legendary。

## MMU 覆盖的内容（让你不用再靠记忆）

<table>
<tr>
<td width="33%">

**构建产品**
- 前端（响应式、无障碍、表单）
- 后端（API、数据库、队列）
- 认证（登录、重置、OAuth、会话）
- 计费（Stripe、webhook、退款）
- 测试（单元测试、E2E、智能体安全）

</td>
<td width="33%">

**准备上线**
- SEO（OG 标签、站点地图、元数据）
- 法务（隐私政策、用户条款、GDPR）
- 安全（CORS、限流、密钥管理）
- 性能（缓存、懒加载）
- CI/CD（流水线、回滚方案）

</td>
<td width="34%">

**上线后运营**
- 监控（错误追踪、可用性、告警）
- 数据分析（漏斗、留存、事件）
- 邮件（事务邮件、模板）
- 无障碍（WCAG、键盘导航）
- 可靠性（备份、故障响应方案）

</td>
</tr>
</table>

**534+ 检查项。15 个类别。零猜测。**

## 适用人群

| 你是... | MMU 帮你... |
|---------|------------|
| **用 AI 写代码的创业者** | 不用每次开会话都从头解释项目。跨工具保持上下文。 |
| **前端开发者** | 清楚知道要做什么：认证流程、错误状态、响应式断点、OG 标签。 |
| **产品经理 / 策划** | 拿到结构化的 PRD、定价策略和上线清单——全是 Markdown。 |
| **全栈独立开发者** | 前端、后端、计费、合规，一个地方统一追踪。不遗漏任何细节。 |

## 快速开始

```bash
pip install -e .

# 方式 A：生成空模板，自己填写
mmu init

# 方式 B：让 Claude 生成项目文档（需要 API 密钥）
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=sk-ant-...
mmu init --interactive        # 回答 5 个问题 → 自动生成战略、产品、定价文档
```

然后：

```bash
mmu scan                      # 自动检测你的技术栈
mmu                           # 查看你的仪表盘
mmu show frontend             # 深入查看任意类别
mmu check frontend 3          # 将条目标记为已完成
mmu gate --stage M0           # 验证你是否准备好进入下一阶段
mmu doctor                    # 运行护栏健康检查
```

## 6 个上线关卡

把它们当成阶段性验收。别跳关。

```
M0 Problem Fit    →  你知道在给谁做、为什么做吗？
M1 Build Fit      →  核心产品能跑通全流程吗？
M2 Revenue Fit    →  用户能付款吗？能退款吗？
M3 Trust Fit      →  隐私政策？客服路径？日志？
M4 Growth Fit     →  分享链接好看吗？别人能搜到你吗？
M5 Scale Fit      →  凌晨三点出故障了怎么办？
```

运行 `mmu gate --stage M0` 进行验证。有未勾选项 = NOT PASS。

## 12 个工作模式

每次会话一个模式。每个模式只加载你需要的文档。

```bash
mmu start --mode backend      # 加载：architecture.md、sprint、ADR 日志
mmu start --mode billing      # 加载：pricing.md、计费清单、合规文档
mmu start --mode growth       # 加载：SEO 清单、指标文档
```

这解决了 AI 编程的头号问题：**上下文过载**。你的 AI 助手只拿到它需要的——而不是你整个项目的所有东西。

## AI 集成（可选）

MMU 不依赖任何 AI 也能用。但接入 Claude 后会更强大：

```bash
pip install make-me-unicorn[llm]
export ANTHROPIC_API_KEY=sk-ant-...
```

| 命令 | 效果 |
|------|------|
| `mmu init --interactive` | 回答 5 个关于你产品的问题。Claude 自动生成战略、产品规格、定价、架构和 UX 文档。 |
| `mmu start --mode X --agent` | 自动格式化会话上下文——直接粘贴到 Claude Code 或任何 LLM。 |
| `mmu doctor --deep` | Claude 阅读你的代码和文档，标记不一致、安全漏洞和盲区。 |
| `mmu generate strategy` | 基于当前项目状态生成或更新任何核心文档。 |

核心 CLI 零依赖。AI 功能可选，可平滑降级。

## 会话工作流

每个会话遵循相同的节奏：

```
1. mmu start --mode backend      ← 选一个聚焦方向，加载相关文档
2. Build / decide / validate      ← 干活
3. mmu close                      ← 记录变更和下一步
```

会话关闭时使用结构化标签记录：

- `[DONE]` — 完成了什么
- `[DECISION]` — 做了哪些决策（重要决策创建 ADR）
- `[ISSUE]` — 遇到了什么问题（分类：上下文丢失 / 方向错误 / 文档与代码不一致）
- `[NEXT]` — 下次会话的第一件事

这意味着你下次开工只需 **5 秒**，而不是花 15 分钟回忆“我上次做到哪了？”

## 示例：TaskNote

看一个完整填写的 MMU 实战示例：

```
examples/filled/tasknote/
├── docs/core/strategy.md      ← ICP、价值主张、竞品分析
├── docs/core/product.md       ← MVP 范围、用户旅程、P0/P1
├── docs/core/pricing.md       ← Free/Pro/Team、计费规则
├── docs/core/architecture.md  ← Next.js + FastAPI + Postgres
├── docs/adr/001_billing_provider_choice.md  ← 为什么选 Stripe？
└── current_sprint.md          ← 本周的 3 个目标
```

## 环境要求

- Python `3.10+`
- `pip`
- 核心 CLI：零外部依赖
- AI 功能：`pip install make-me-unicorn[llm]`

## 项目结构

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

## CI 护栏

`mmu doctor` 在每个 PR 上运行。`mmu gate` 对 `docs/ops/gate_targets.txt` 中列出的阶段运行。

## 贡献

参见 `CONTRIBUTING.md`。

## 许可证

MIT。参见 `LICENSE`。
