<div align="center">

# Make Me Unicorn

**手探りで作るのは、もうやめよう。自信を持って SaaS をリリースしよう。**

個人開発者のための、オープンソースのローンチチェックリスト＆運用システム。

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](./LICENSE)
[![Status: v0.4](https://img.shields.io/badge/status-v0.4-blue.svg)](./ROADMAP.md)
[![CLI](https://img.shields.io/badge/cli-mmu-f59e0b.svg)](./SPEC.md)
[![Guardrails CI](https://img.shields.io/badge/ci-doctor%20%2B%20gates-22c55e.svg)](./.github/workflows/mmu-guardrails.yml)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-16a34a.svg)](./CONTRIBUTING.md)

[🇺🇸 English](./README.md) · [🇰🇷 한국어](./README.ko.md) · **🇯🇵 日本語** · [🇨🇳 简体中文](./README.zh-CN.md) · [🇪🇸 Español](./README.es.md)

<img src="./assets/brand/unicorn-hero.png" alt="Make Me Unicorn mascot" width="960" />

</div>

## 課題

あなたは SaaS プロダクトを開発しています。AI を使って、かつてないスピードでコードを書いています。でも、ふと気づくと――

> 「あれ、パスワードリセットのフロー入れたっけ？」
>
> 「決済の webhook…冪等性ちゃんと担保してる？」
>
> 「プライバシーポリシーは？返金ポリシーは？OGタグは？」
>
> 「先週、認証プロバイダについて何を決めたんだっけ？なんでその結論になったんだ？」

**コーディング力が足りないのではありません。大事なことを管理できていないのです。**

個人開発者なら誰もがぶつかる壁があります：

| よくある失敗 | その代償 |
|-------------|---------|
| ログイン実装に集中して、パスワードリセットを忘れる | 初日からユーザーがロックアウトされる |
| webhook の署名検証をスキップする | 攻撃者に決済イベントをリプレイされる |
| OGタグなしでリリースする | SNS でシェアされたリンクが全部壊れて見える |
| AI セッション間でコンテキストが消える | 毎回プロジェクトの説明をゼロからやり直す |
| 返金ポリシーがない | 最初のチャージバック = Stripe アカウント凍結 |

MMU はこれらを**ユーザー・売上・信頼を失う前に**キャッチします。

## 仕組み

```
mmu init                    # 1. 15カテゴリ、534以上のチェックリスト項目を取得
mmu scan                    # 2. 技術スタックを自動検出 — 既存の対応済み項目を事前チェック
mmu                         # 3. 完了項目と未対応項目を一覧表示
mmu status --why            # 4. スコアの内訳を表示 — 反映された項目、除外された項目
mmu next                    # 5. 優先度ベースの次のアクションを提案
```

```text
  MAKE ME UNICORN - STATUS DASHBOARD

          .--*--.
         / *v*  \
        |       |
         \ ___ /
          '---'

  Stage: HATCHING    ######..............  22%  (124/551)

  LAUNCH GATES  (16/26)
    M0 Problem Fit         ################   4/4   PASS
    M1 Build Fit           ################   5/5   PASS
    M2 Revenue Fit         ############....   3/4   OPEN
    M3 Trust Fit           ################   4/4   PASS
    M4 Growth Fit          ########........   2/4   OPEN
    M5 Scale Fit           ####............   1/5   OPEN

  BLUEPRINTS  (124/551)
    Frontend           ##########......  18/35  51%
    Backend            ############....  24/46  52%
    Auth               ##########......  16/42  38%
    Billing            ########........  11/36  30%
    ...11 more
```

開発が進むにつれ、ユニコーンが成長します：Egg → Hatching → Foal → Young → Unicorn → Legendary。

## チェックリストをあなたのプロジェクトに合わせる

すべてのプロジェクトに課金が必要なわけではありません。すべてのプロダクトに多言語対応が必要なわけでもありません。MMU は適応します：

```bash
mmu init                      # 技術スタックを選択（Next.js、Django、Rails、...）
```

`.mmu/config.toml` が生成されます — 関係ない項目をスキップするフィーチャーフラグ：

```toml
[features]
billing = false               # Stripe 不要？課金関連の項目はスコアに影響しません
i18n = false
native_mobile = false

[architecture]
framework = "nextjs"
```

スコアは**あなたのプロジェクトに関係する項目のみ**を反映します。`mmu status --why` でその内訳を透明に確認できます — Lighthouse のように、ただし SaaS ローンチ準備度版。

## MMU がカバーする範囲（あなたが覚えなくていいように）

<table>
<tr>
<td width="33%">

**プロダクト開発**
- Frontend（レスポンシブ、a11y、フォーム）
- Backend（API、DB、キュー）
- Auth（ログイン、リセット、OAuth、セッション）
- Billing（Stripe、webhook、返金）
- Testing（ユニットテスト、E2E、エージェント安全性）

</td>
<td width="33%">

**ローンチ準備**
- SEO（OGタグ、サイトマップ、メタ情報）
- Legal（プライバシー、利用規約、GDPR）
- Security（CORS、レート制限、シークレット管理）
- Performance（キャッシュ、遅延読み込み）
- CI/CD（パイプライン、ロールバック計画）

</td>
<td width="34%">

**ローンチ後の運用**
- Monitoring（エラー検知、稼働監視、アラート）
- Analytics（ファネル、リテンション、イベント）
- Email（トランザクションメール、テンプレート）
- Accessibility（WCAG、キーボードナビゲーション）
- Reliability（バックアップ、インシデント対応計画）

</td>
</tr>
</table>

**534以上の項目。15カテゴリ。抜け漏れゼロ。**

## こんな人のためのツール

| あなたは… | MMU がこう助けます |
|----------|------------------|
| **AI を使ってコードを書いている個人開発者** | 毎セッション、プロジェクトの説明をやり直す必要がなくなります。ツール間でコンテキストを維持できます。 |
| **フロントエンドエンジニア** | 何を実装すべきかが明確になります：認証フロー、エラーステート、レスポンシブ対応、OGタグ。 |
| **PM / プロダクト企画** | 構造化された PRD、料金設計、ローンチチェックリストが手に入ります。すべて Markdown で。 |
| **フルスタックエンジニア** | フロントエンド、バックエンド、課金、コンプライアンスを一箇所で管理。見落としがなくなります。 |

## クイックスタート

```bash
pip install -e .

# オプションA: 空のテンプレートから始めて、自分で埋める
mmu init

# オプションB: Claude にプロジェクトドキュメントを生成させる（API キーが必要）
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=sk-ant-...
mmu init --interactive        # 5つの質問に答える → 戦略・プロダクト・料金設計のドキュメントが生成される
```

次に：

```bash
mmu scan                      # 技術スタックを自動検出
mmu                           # ダッシュボードを表示
mmu status --why              # スコアの算出根拠を詳細表示
mmu next                      # 優先度順の次のアクション Top 3 を表示
mmu show frontend             # 任意のカテゴリを詳細表示
mmu check frontend 3          # 項目を完了としてマーク
mmu gate --stage M0           # 次のフェーズに進む準備ができているか検証
mmu doctor                    # ガードレールのヘルスチェックを実行
```

## 6つのローンチゲート

フェーズの出口条件として考えてください。飛ばさないこと。

```
M0 Problem Fit    →  誰のために、なぜ作るのか明確か？
M1 Build Fit      →  コアプロダクトがエンドツーエンドで動くか？
M2 Revenue Fit    →  課金できるか？返金はできるか？
M3 Trust Fit      →  プライバシーポリシーは？サポート導線は？ログは？
M4 Growth Fit     →  シェアされたリンクはちゃんと表示されるか？検索で見つかるか？
M5 Scale Fit      →  深夜3時に障害が起きたらどうなる？
```

`mmu gate --stage M0` で検証できます。未チェック項目がある = NOT PASS。

## 12のオペレーティングモード

1セッションにつき1モード。そのモードに必要なドキュメントだけが読み込まれます。

```bash
mmu start --mode backend      # 読み込み: architecture.md, sprint, ADRログ
mmu start --mode billing      # 読み込み: pricing.md, 課金チェックリスト, コンプライアンス
mmu start --mode growth       # 読み込み: SEOチェックリスト, 指標
```

これにより、AI コーディングにおける最大の問題である**コンテキストの過負荷**を防ぎます。AI アシスタントには必要な情報だけが渡されます。プロジェクト全体ではありません。

## AI 連携（オプション）

MMU は AI なしでも動作します。ただし、Claude と組み合わせるとさらに強力になります：

```bash
pip install make-me-unicorn[llm]
export ANTHROPIC_API_KEY=sk-ant-...
```

| コマンド | 実行内容 |
|---------|---------|
| `mmu init --interactive` | プロダクトについて5つの質問に答えます。Claude が戦略、プロダクト仕様、料金設計、アーキテクチャ、UX のドキュメントを生成します。 |
| `mmu start --mode X --agent` | セッションコンテキストを自動整形します。Claude Code や他の LLM にそのまま貼り付けできます。 |
| `mmu doctor --deep` | Claude がコードとドキュメントを読み込み、不整合、セキュリティ上の抜け漏れ、見落としを指摘します。 |
| `mmu generate strategy` | 現在のプロジェクト状態に基づいて、コアドキュメントを生成・更新します。 |

コア CLI は外部依存ゼロ。AI 機能はオプションであり、なくても正常に動作します。

## セッションワークフロー

毎回のセッションは同じリズムで進みます：

```
1. mmu start --mode backend      ← フォーカスを選び、関連ドキュメントを読み込む
2. Build / decide / validate      ← 実作業
3. mmu close                      ← 変更内容と次のアクションを記録
```

セッション終了時に構造化タグでメモリを残します：

- `[DONE]` — 完了したこと
- `[DECISION]` — 決定事項（重要なものは ADR を作成）
- `[ISSUE]` — うまくいかなかったこと（分類：コンテキスト喪失 / 方向性の誤り / ドキュメントとコードの不整合）
- `[NEXT]` — 次のセッションの最初のタスク

これにより、次のセッション開始が**5秒**で済みます。「どこまでやったっけ？」に15分かかることはもうありません。

## 使用例：TaskNote

MMU を実際に使った完成例をご覧ください：

```
examples/filled/tasknote/
├── docs/core/strategy.md      ← ICP、バリュープロップ、競合分析
├── docs/core/product.md       ← MVP スコープ、ユーザージャーニー、P0/P1
├── docs/core/pricing.md       ← Free/Pro/Team、課金ルール
├── docs/core/architecture.md  ← Next.js + FastAPI + Postgres
├── docs/adr/001_billing_provider_choice.md  ← なぜ決済プロバイダとして Stripe を選んだか？
└── current_sprint.md          ← 今週の3つの目標
```

## 動作要件

- Python `3.10+`
- `pip`
- コア CLI：外部依存なし
- AI 機能：`pip install make-me-unicorn[llm]`

## プロジェクト構成

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

## CI ガードレール

`mmu doctor` はすべての PR で実行されます。`mmu gate` は `docs/ops/gate_targets.txt` に記載されたステージに対して実行されます。

## コントリビューション

`CONTRIBUTING.md` をご覧ください。

## ライセンス

MIT。`LICENSE` をご覧ください。
