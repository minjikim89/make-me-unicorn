<div align="center">

# make-me-unicorn

**AI コーディングエージェントのためのローンチゲート。**

署名を検証せずにイベントを信頼する webhook、RLS のない Supabase テーブル、<br>
ブラウザバンドルに含まれた `service_role` キーを、エージェントは commit できません。決定的、オフライン、アカウント不要、LLM 不要、約 0.1 秒。

[![PyPI](https://img.shields.io/pypi/v/make-me-unicorn?color=blue)](https://pypi.org/project/make-me-unicorn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![CI](https://github.com/minjikim89/make-me-unicorn/actions/workflows/mmu-guardrails.yml/badge.svg)](./.github/workflows/mmu-guardrails.yml)
[![Benchmark](https://img.shields.io/badge/P0%20false%20positives-0%20in%2020%20OSS%20repos-22c55e)](./docs/benchmark.md)

[English](./README.md) · [한국어](./README.ko.md) · **日本語** · [简体中文](./README.zh-CN.md) · [Español](./README.es.md)

</div>

<!-- mcp-name: io.github.minjikim89/make-me-unicorn -->

```bash
uvx make-me-unicorn install --claude    # or --codex, --cursor, --gemini, --git, --all
```

セットアップはこれだけです。以降、エージェントが `git commit` を実行すると、hook が staged の内容をスキャンします。P0 の finding があるとコマンドは拒否され、エージェントがそのまま適用できる修正方法が渡されます。以下は、Next.js + Supabase + Stripe プロジェクトの最初の commit に対する実際の出力です(行は短縮し、P1 の警告 5 件は省略):

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

エージェントは修正し、再実行して、commit します。コードがすでに正しい場合、ゲートは何も出力しません。Claude Code の実セッションでのテストでは、エージェントが署名検証付きの Stripe webhook を一度で書き、commit はそのまま通りました。

## なぜ不在を検査するのか

シークレットスキャナーや SAST は、そこにある悪いコードを探します。エージェントが書いたコードは、そこにないコードが原因で問題になることのほうが多くなります。誰も書かなかった署名検証、追加されなかった RLS ポリシー、有料 LLM ルートの手前にない rate limit などです。

- Tenzai は 5 つのコーディングエージェントに同じ 3 つのアプリを作らせました(計 15 アプリ)。悪用可能な SQLi や XSS を含むものは 1 つもありませんでしたが、セキュリティ制御については "in almost all cases, they didn't even try"(ほぼすべてのケースで、試みてすらいなかった)という結果でした([SecurityWeek、2026 年 1 月](https://www.securityweek.com/vibe-coding-tested-ai-agents-nail-sqli-but-fail-miserably-on-security-controls/))。
- GitGuardian の計測では、Claude Code を使った公開 commit のシークレット漏洩率は 3.2% で、ベースラインは 1.5% でした([State of Secrets Sprawl 2026](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/))。

linter は存在しない関数を指摘しません。`mmu vibecheck` は、レビュアーが「この webhook はどこで検証していますか?」と尋ねるようにプロジェクトを読み、答えが明らかに「どこにもない」ときだけブロックします。

## ゲートの仕組み

エージェントは、任意のツールは使わずに済ませます。hook は飛ばせません。`mmu install` は `mmu hook` を呼び出す hook エントリを書き込み、`mmu hook` は各ホストの hook プロトコルに従って応答します。

| ホスト | commit / push ゲート | 「未完了」ゲート | 編集後フィードバック | `mmu install` のフラグ |
|------|--------------------|---------------------|--------------------|--------------------|
| Claude Code | `Bash` に対する `PreToolUse` | `Stop` | `Edit`/`Write`/`MultiEdit` に対する `PostToolUse` | `--claude` |
| Codex CLI | `Bash` に対する `PreToolUse` | `Stop` | `apply_patch` に対する `PostToolUse` | `--codex` |
| Cursor | `beforeShellExecution` | `stop` | 利用不可 | `--cursor` |
| Gemini CLI | `run_shell_command` に対する `BeforeTool` | `AfterAgent` | 利用不可 | `--gemini` |
| git | `pre-commit`(既存の hook があれば続けて実行) | | | `--git` |
| pre-commit フレームワーク | hook id `mmu-vibecheck` | | | `.pre-commit-hooks.yaml` |
| GitHub Actions | `uses: minjikim89/make-me-unicorn@v0.9.0`、SARIF を code scanning へ送信 | | | |

- **commit ゲート**は、commit に含まれる内容をスキャンします。対象は staged のファイルで、`git commit -a`、pathspec、`git add ... && git commit` の場合は変更されたファイルです。push では upstream 以降の変更をスキャンします。
- **「未完了」ゲート**は、エージェントが作業を終えようとしたときに実行されます。このセッションでエージェントが編集したファイルだけを見るため、触れていないコードを書き直させることはありません。エージェントを差し戻すのは最大 `MMU_STOP_MAX` 回(デフォルト 3)です。ハードニングを後回しにするようエージェントに指示している場合は、P0 を一覧表示して止まります。
- **編集後フィードバック**は、書き込んだばかりのファイルの P0 finding をコンテキストとして返します。ブロックはしません。
- `mmu install --all`、`--dry-run`、`--uninstall` が使えます。`--agents-md` は `AGENTS.md` に指示ブロックを追加し、`--skill` は `mmu-vibecheck` Agent Skill を `.agents/skills/` にコピーします。既存の設定はマージされ、置き換えられることはありません。

Claude Code は実セッションでテストしています。Codex CLI、Cursor、Gemini CLI は公開されている hook の仕様に従っており、ドキュメントに記載されたペイロードでテストしています。実セッションでの報告を歓迎します。

設計上の制約(すべてテスト済み):

- **決定的。** 同じツリーなら同じ finding。モデル呼び出しなし、ネットワークなし、アカウントなし。
- **Fail-open。** スキャナー自体がクラッシュまたはタイムアウトした場合は、警告を表示したうえでコマンドを通します。ゲートが壊れてもセッションが使えなくなることはありません。
- **人間はバイパス可能。** 1 回のコマンドだけなら `MMU_HOOK_DISABLE=1 git commit ...`。エージェントの環境変数に設定すると、そのセッションでゲートが無効になります。
- **高速。** 実在する 20 リポジトリで中央値 89 ms、最大のリポジトリ(1,699 ファイル)で 1.1 s。

## 検出する内容

P0 はブロックし、P1 は警告します。不在を推定するヒューリスティックは、根拠が具体的でない限りすべて P1 です。

| ルール | 重大度 | 検出対象 |
|------|-----|-------|
| `secrets` | P0 | ソース、設定ファイル、または git が ignore していない dotenv ファイルにある、有効なプロバイダーキーと Supabase の `service_role` JWT |
| `client-bundle-secrets` | P0 | `NEXT_PUBLIC_` / `VITE_` / `EXPO_PUBLIC_` プレフィックス付き、またはクライアントコードで読み込まれるシークレット |
| `supabase-rls` | P0 | migration で `ENABLE ROW LEVEL SECURITY` なしに作成されたテーブル |
| `webhook-signature` | P0 | イベントを検証せずに使う Stripe、GitHub、Svix、Clerk... の webhook ハンドラー |
| `sql-fstring` | P0 | f-string、`%`、`.format`、テンプレートリテラル、文字列連結で組み立てて `execute` に渡す SQL |
| `code-injection` | P0 | `eval`、`exec`、`Function`、またはシェルに到達するリクエストデータ |
| `jwt-secret-default` | P0 | 値がハードコードされた、または `|| 'fallback'` を持つ署名用シークレット |
| `unsafe-deserialization` | P0 | safe loader なしの `yaml.load`、外部入力に対する `pickle` |
| `git-config-exec` | P0 | 通常の git 操作でプログラムを実行する `.git/config` のキー(`core.fsmonitor`、`core.sshCommand`、`alias.x = !cmd`) |
| `llm-route-unthrottled` | P1 | 認証も rate limit もなしに有料 LLM API を呼び出すルート |
| `admin-route-no-auth` | P1 | セッションまたはロールのチェックがない `/admin` ルート |
| `password-reset` | P1 | パスワードログインがあるのに、パスワード再設定のフローがどこにもない |
| `webhook-idempotency` | P1 | プロバイダーがリトライすると結果が不正になる webhook の処理 |
| `rate-limiting` | P1 | rate limiting がまったくないサーバー |
| `cors-wildcard` | P1 | `*` の origin、オプションなしの `cors()`、credentials と併用したワイルドカード |
| `dangerous-html` | P1 | サニタイズしていない値に対する `dangerouslySetInnerHTML` / `v-html` |
| `jwt-localstorage` | P1 | `localStorage` / `sessionStorage` に保存された認証トークン |
| `stack-trace-leak` | P1 | クライアントに返される例外の詳細 |
| `sourcemaps-exposed` | P1 | 本番環境で有効になっている source map |
| `env-not-ignored` | P1 | 認証情報らしい名前の値を含み、git が ignore していない dotenv ファイル |
| `disabled-ssl` | P1 | `verify=False`、`rejectUnauthorized: false` |
| `debug-mode` | P1 | `DEBUG = True`、`app.run(debug=True)`、Dockerfile 内の `--reload` |
| `error-monitoring` | P1 | Sentry または同等のツールがない |

`mmu vibecheck --list-rules` はこの表を出力します。`mmu vibecheck --explain <rule>` は、そのルールが何を探すのかと修正方法を出力します。

## 精度

計測済みで、再現可能です。限界も含めて [`docs/benchmark.md`](./docs/benchmark.md) に記載しています。

| 計測 | 結果 |
|-------------|--------|
| 人気のオープンソースアプリ 20 件(スターター、SaaS キット、フレームワークのサンプル)、デフォルト設定 | レビューの結果、誤った P0 finding は 0 件(今回のリリースでのルール見直し前は 11 件) |
| 55 件の問題を仕込んだ 12 の fixture プロジェクト | P0 precision 100%、P0 recall 100%、仕込んだ 55 件のうち 52 件を検出 |
| 検出しないもの | IDOR、平文でのパスワード比較、ログインで返される password カラム: 認可やデータフローをモデル化するルールはありません |

fixture はルールと並行して書かれたものなので、回帰テストスイートとして扱ってください。独立した検証にあたるのは、オープンソースリポジトリに対するスキャンです。

## 直接使う

```bash
pip install make-me-unicorn          # or run any command through uvx make-me-unicorn ...
mmu vibecheck                        # whole project, human-readable
mmu vibecheck --staged               # what is about to be committed
mmu vibecheck --since origin/main    # what this branch changed
mmu vibecheck --format agent         # compact fix list for a coding agent
mmu vibecheck --format json          # schema mmu.vibecheck/v1
mmu vibecheck --format sarif --output mmu.sarif
```

終了コード: `0` はブロック対象なし、`1` は `--fail-on`(デフォルト `P0`)以上の finding が 1 件以上、`2` はスキャンを実行できなかった場合です。JSON スキーマ: [`docs/vibecheck-json-schema.md`](./docs/vibecheck-json-schema.md)。

### 誤検知

理由を付けて 1 行を抑制します(理由のない抑制は無視されます):

```ts
// mmu-ignore[webhook-signature]: verified by the API gateway before this handler runs
```

または `.mmu/config.toml` でパスを指定します:

```toml
[vibecheck]
ignore = ["scripts/seed.ts:secrets", "examples/**:jwt-secret-default"]
```

既存のコードベースにゲートを導入する場合: `mmu vibecheck --write-baseline` で現時点の finding を記録すると、以降 `mmu vibecheck --baseline` は新しい finding だけを報告します。

## GitHub Actions

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@v4
  - uses: minjikim89/make-me-unicorn@v0.9.0
    with:
      sarif-file: mmu.sarif
  - uses: github/codeql-action/upload-sarif@v4
    if: always()
    with:
      sarif_file: mmu.sarif
```

finding は Security タブに表示され、pull request にはアノテーションとして表示されます。

## Claude Code プラグイン

```text
/plugin marketplace add minjikim89/make-me-unicorn
/plugin install make-me-unicorn@make-me-unicorn
```

プラグインに同梱されたソースから同じ 3 つの hook を登録します(`python3` 3.10+ が必要、`pip install` は不要)。あわせて `/vibecheck` コマンド、`mmu-vibecheck` skill、MCP サーバー([uv](https://docs.astral.sh/uv/) で起動)も登録します。

## MCP サーバー

自分から問い合わせるほうを好むエージェント向けです。`mmu serve-mcp` は `mmu_vibecheck`、`mmu_explain_rule`、`mmu_list_rules` を公開します(読み取り専用)。MCP SDK v1 と v2 で動作します。

```json
{
  "mcpServers": {
    "mmu": { "command": "uvx", "args": ["--from", "make-me-unicorn[mcp]>=0.9", "mmu", "serve-mcp"] }
  }
}
```

MCP ツールは補助的な手段です。ゲートは hook です。

## ルールを追加する

ルールは [`src/mmu_cli/vibecheck/rules/`](./src/mmu_cli/vibecheck/rules/) にあります。ルールには `bench/fixtures/` の fixture と `bench/expected/` の期待される finding を添える必要があり、ベンチマークの P0 誤検知をゼロに保たなければなりません(`python -m unittest tests.test_bench`)。[CONTRIBUTING.md](./CONTRIBUTING.md) を参照してください。

## このリポジトリにあるもう 1 つの機能: ローンチチェックリスト

make-me-unicorn はソロビルダー向けのローンチチェックリストとして始まり、その機能は現在も提供されています。15 のチェックリストカテゴリ、M0 から M5 までのローンチゲート、フォーカスセッションモード、MCP blueprint サーバーがあります。チェックリストはプロジェクトで決めたことと済ませたことを追跡し、上記のゲートはコードが実際に何をするかを検査します。

```bash
mmu init && mmu scan && mmu status
```

詳細: [docs/checklists.md](./docs/checklists.md) と [SPEC.md](./SPEC.md)。

## ライセンス

MIT
