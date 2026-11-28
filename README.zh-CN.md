<div align="center">

# make-me-unicorn

**面向 AI 编码智能体的发布关卡。**

你的智能体无法 commit 信任未签名事件的 webhook、未启用 RLS 的 Supabase 表,<br>
也无法 commit 打进浏览器 bundle 的 `service_role` 密钥。确定性、离线运行、无需账号、不调用 LLM,耗时约 0.1 秒。

[![PyPI](https://img.shields.io/pypi/v/make-me-unicorn?color=blue)](https://pypi.org/project/make-me-unicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![CI](https://github.com/minjikim89/make-me-unicorn/actions/workflows/mmu-guardrails.yml/badge.svg)](./.github/workflows/mmu-guardrails.yml)
[![Benchmark](https://img.shields.io/badge/P0%20false%20positives-0%20in%2020%20OSS%20repos-22c55e)](./docs/benchmark.md)

[English](./README.md) · [한국어](./README.ko.md) · [日本語](./README.ja.md) · **简体中文** · [Español](./README.es.md)

</div>

<!-- mcp-name: io.github.minjikim89/make-me-unicorn -->

```bash
uvx make-me-unicorn install --claude    # or --codex, --cursor, --gemini, --git, --all
```

全部配置就是这一步。此后,当智能体运行 `git commit` 时,hook 会扫描已 staged 的内容。出现 P0 问题时,命令会被拒绝,并把智能体可以直接应用的修复方法交给它。下面是一个 Next.js + Supabase + Stripe 项目首次 commit 时的真实输出(行有删减,省略了 5 条 P1 警告):

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

智能体修复、重新运行,然后 commit。代码本身没有问题时,关卡不会输出任何内容:在一次真实的 Claude Code 测试中,智能体第一次就写出了带签名验证的 Stripe webhook,commit 直接通过。

## 为什么要检查缺失

密钥扫描器和 SAST 查找的是已经存在的坏代码。智能体写出的代码更常见的问题是该有的代码不存在:没人写的签名验证、从未添加的 RLS 策略、付费 LLM 路由前面缺少的 rate limit。

- Tenzai 让 5 个编码智能体分别构建相同的 3 个应用(共 15 个应用)。没有一个包含可利用的 SQLi 或 XSS;而在安全控制方面,"in almost all cases, they didn't even try"(几乎在所有情况下,它们甚至没有尝试)([SecurityWeek,2026 年 1 月](https://www.securityweek.com/vibe-coding-tested-ai-agents-nail-sqli-but-fail-miserably-on-security-controls/))。
- GitGuardian 测得,由 Claude Code 协助的公开 commit 中密钥泄露率为 3.2%,基线为 1.5%([State of Secrets Sprawl 2026](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/))。

linter 不会标记一个不存在的函数。`mmu vibecheck` 阅读项目的方式,就像审查者在问"这个 webhook 是在哪里验证的?",并且只有当答案明确是"哪里都没有"时才会阻止。

## 关卡的工作方式

智能体会跳过可选的工具,但跳不过 hook。`mmu install` 会写入调用 `mmu hook` 的 hook 条目,`mmu hook` 则按各宿主的 hook 协议进行应答。

| 宿主 | commit / push 关卡 | "尚未完成"关卡 | 编辑后反馈 | `mmu install` 参数 |
|------|--------------------|---------------------|--------------------|--------------------|
| Claude Code | `Bash` 上的 `PreToolUse` | `Stop` | `Edit`/`Write`/`MultiEdit` 上的 `PostToolUse` | `--claude` |
| Codex CLI | `Bash` 上的 `PreToolUse` | `Stop` | `apply_patch` 上的 `PostToolUse` | `--codex` |
| Cursor | `beforeShellExecution` | `stop` | 不支持 | `--cursor` |
| Gemini CLI | `run_shell_command` 上的 `BeforeTool` | `AfterAgent` | 不支持 | `--gemini` |
| git | `pre-commit`,并串联已有的 hook | | | `--git` |
| pre-commit 框架 | hook id `mmu-vibecheck` | | | `.pre-commit-hooks.yaml` |
| GitHub Actions | `uses: minjikim89/make-me-unicorn@v0.9.2`,SARIF 上传到 code scanning | | | |

- **commit 关卡**扫描本次 commit 将包含的内容:staged 的文件;对于 `git commit -a`、pathspec 和 `git add ... && git commit`,则是有改动的文件。push 时扫描自 upstream 以来的改动。
- **"尚未完成"关卡**在智能体准备结束任务时运行。它只检查智能体在本次会话中编辑过的文件,因此不会让智能体重写它没有碰过的代码。它最多把智能体退回 `MMU_STOP_MAX` 次(默认 3 次);如果你已经让智能体把加固工作推后,它会列出 P0 问题然后停止。
- **编辑后反馈**把刚写入的文件中的 P0 问题作为上下文返回,不会阻止任何操作。
- 支持 `mmu install --all`、`--dry-run`、`--uninstall`;`--agents-md` 向 `AGENTS.md` 添加一段指令,`--skill` 把 `mmu-vibecheck` Agent Skill 复制到 `.agents/skills/`。已有的设置会被合并,不会被替换。

Claude Code 已在真实会话中测试。Codex CLI、Cursor 和 Gemini CLI 遵循各自文档中的 hook 约定,并使用文档中的 payload 进行了测试;欢迎提供真实会话中的使用反馈。

设计约束(均有测试覆盖):

- **确定性。** 相同的代码树得到相同的结果。不调用模型,不访问网络,无需账号。
- **Fail-open。** 如果扫描器自身崩溃或超时,命令会放行,并给出明显的警告。关卡出故障也不会让会话无法继续。
- **人可以绕过。** 对单条命令使用 `MMU_HOOK_DISABLE=1 git commit ...`;在智能体的环境变量中设置它,则在整个会话中禁用关卡。
- **快。** 在 20 个真实仓库上的中位数为 89 ms,最大的仓库(1,699 个文件)为 1.1 s。

## 检测内容

P0 阻止,P1 警告。所有推断缺失的启发式规则,除非证据具体,否则一律为 P1。

| 规则 | 级别 | 检测内容 |
|------|-----|-------|
| `secrets` | P0 | 源码、配置文件或未被 git 忽略的 dotenv 文件中的有效服务商密钥和 Supabase `service_role` JWT |
| `client-bundle-secrets` | P0 | 带有 `NEXT_PUBLIC_` / `VITE_` / `EXPO_PUBLIC_` 前缀或在客户端代码中读取的密钥 |
| `supabase-rls` | P0 | migration 中创建时未 `ENABLE ROW LEVEL SECURITY` 的表 |
| `webhook-signature` | P0 | 未验证事件就直接使用的 Stripe、GitHub、Svix、Clerk... webhook 处理器 |
| `sql-fstring` | P0 | 用 f-string、`%`、`.format`、模板字面量或字符串拼接构造并传给 `execute` 的 SQL |
| `code-injection` | P0 | 流入 `eval`、`exec`、`Function` 或 shell 的请求数据 |
| `jwt-secret-default` | P0 | 值被硬编码或带有 `|| 'fallback'` 的签名密钥 |
| `unsafe-deserialization` | P0 | 未使用 safe loader 的 `yaml.load`,对外部输入使用 `pickle` |
| `git-config-exec` | P0 | 在日常 git 操作中会执行程序的 `.git/config` 配置项(`core.fsmonitor`、`core.sshCommand`、`alias.x = !cmd`) |
| `llm-route-unthrottled` | P1 | 既无认证也无 rate limit 就调用付费 LLM API 的路由 |
| `admin-route-no-auth` | P1 | 没有会话或角色检查的 `/admin` 路由 |
| `password-reset` | P1 | 有密码登录,但整个项目中没有找回/重置密码的流程 |
| `webhook-idempotency` | P1 | 服务商重试时会产生错误结果的 webhook 处理逻辑 |
| `rate-limiting` | P1 | 完全没有 rate limiting 的服务端 |
| `cors-wildcard` | P1 | `*` origin、不带选项的 `cors()`、通配符与 credentials 同时使用 |
| `dangerous-html` | P1 | 对未经净化的值使用 `dangerouslySetInnerHTML` / `v-html` |
| `jwt-localstorage` | P1 | 存放在 `localStorage` / `sessionStorage` 中的认证 token |
| `stack-trace-leak` | P1 | 返回给客户端的异常详情 |
| `sourcemaps-exposed` | P1 | 生产环境启用了 source map |
| `env-not-ignored` | P1 | 含有凭据类命名的值且未被 git 忽略的 dotenv 文件 |
| `disabled-ssl` | P1 | `verify=False`、`rejectUnauthorized: false` |
| `debug-mode` | P1 | `DEBUG = True`、`app.run(debug=True)`、Dockerfile 中的 `--reload` |
| `error-monitoring` | P1 | 没有 Sentry 或同类工具 |

`mmu vibecheck --list-rules` 输出这张表;`mmu vibecheck --explain <rule>` 输出某条规则检测什么以及如何修复。

## 准确性

经过实测,可复现,其局限也一并记录在 [`docs/benchmark.md`](./docs/benchmark.md) 中。

| 测量项 | 结果 |
|-------------|--------|
| 20 个流行的开源应用(starter、SaaS 套件、框架示例),默认设置 | 经人工复核,错误的 P0 结果为 0 个(本次版本重写规则之前为 11 个) |
| 12 个 fixture 项目,共埋入 55 个问题 | P0 precision 100%,P0 recall 100%,55 个埋入的问题中发现 52 个 |
| 未检测 | IDOR、明文密码比较、登录接口返回 password 列:没有规则对授权或数据流建模 |

这些 fixture 是与规则同时编写的,因此应把它们看作回归测试集。对开源仓库的扫描才是独立的验证。

## 直接使用

```bash
pip install make-me-unicorn          # or run any command through uvx make-me-unicorn ...
mmu vibecheck                        # whole project, human-readable
mmu vibecheck --staged               # what is about to be committed
mmu vibecheck --since origin/main    # what this branch changed
mmu vibecheck --format agent         # compact fix list for a coding agent
mmu vibecheck --format json          # schema mmu.vibecheck/v1
mmu vibecheck --format sarif --output mmu.sarif
```

退出码:`0` 表示没有需要阻止的问题,`1` 表示至少有一个达到或高于 `--fail-on`(默认 `P0`)的问题,`2` 表示扫描未能运行。JSON schema:[`docs/vibecheck-json-schema.md`](./docs/vibecheck-json-schema.md)。

### 误报

抑制某一行,并写明原因(没有原因的抑制会被忽略):

```ts
// mmu-ignore[webhook-signature]: verified by the API gateway before this handler runs
```

或者在 `.mmu/config.toml` 中按路径配置:

```toml
[vibecheck]
ignore = ["scripts/seed.ts:secrets", "examples/**:jwt-secret-default"]
```

在已有代码库中引入关卡:`mmu vibecheck --write-baseline` 记录当前的全部问题,之后 `mmu vibecheck --baseline` 只报告新增的问题。

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

检测结果会显示在 Security 标签页中,并以注释形式出现在 pull request 上。

## Claude Code 插件

```text
/plugin marketplace add minjikim89/make-me-unicorn
/plugin install make-me-unicorn@make-me-unicorn
```

从插件自带的源码注册相同的 3 个 hook(需要 `python3` 3.10+,无需 `pip install`),另外还有 `/vibecheck` 命令、`mmu-vibecheck` skill 和 MCP 服务器(通过 [uv](https://docs.astral.sh/uv/) 启动)。

## MCP 服务器

面向更愿意主动查询的智能体:`mmu serve-mcp` 提供 `mmu_vibecheck`、`mmu_explain_rule` 和 `mmu_list_rules`(只读)。兼容 MCP SDK v1 和 v2。

```json
{
  "mcpServers": {
    "mmu": { "command": "uvx", "args": ["--from", "make-me-unicorn[mcp]>=0.9", "mmu", "serve-mcp"] }
  }
}
```

MCP 工具只是便利手段。真正的关卡是 hook。

## 添加规则

规则位于 [`src/mmu_cli/vibecheck/rules/`](./src/mmu_cli/vibecheck/rules/)。每条规则都要附带 `bench/fixtures/` 中的 fixture 和 `bench/expected/` 中的预期结果,并且必须让基准测试的 P0 误报保持为零(`python -m unittest tests.test_bench`)。参见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 本仓库的另一部分:发布检查清单

make-me-unicorn 最初是面向独立开发者的发布检查清单,这部分仍然提供:15 个检查清单类别、M0 到 M5 的发布关卡、专注会话模式和 MCP blueprint 服务器。检查清单跟踪项目已经决定和完成的事项;上面的关卡检查代码实际做了什么。

```bash
mmu init && mmu scan && mmu status
```

详情:[docs/checklists.md](./docs/checklists.md) 和 [SPEC.md](./SPEC.md)。

## 许可证

MIT
