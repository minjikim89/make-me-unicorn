# Use Cases

Concrete scenarios where Make Me Unicorn (MMU) fits. Each scenario maps to specific MMU commands and integrations.

## 1. Solo founder pre-launch audit

**Situation**: You've been shipping a SaaS product for 4–8 weeks. Most of the code is Claude Code- or Cursor-generated. You're 1–2 weeks from launch but worried something critical is missing — security headers, refund flow, Search Console, cookie consent.

**MMU workflow**:
```bash
pip install make-me-unicorn
cd your-project
mmu init           # writes .mmu/ config + a baseline scan
mmu scan           # 670-item check across all 15 categories
mmu                # show status dashboard with 6 gate progress bars
mmu next           # show the highest-priority missing item
```

**Outcome**: A ranked list of missing items by launch gate. You fix M0–M3 items first (Problem/Build/Revenue/Trust), then M4–M5 (Growth/Scale). Each gate must pass before proceeding to the next.

## 2. AI agent self-correction loop (Claude Code)

**Situation**: You're running Claude Code in autonomous mode. The agent ships features but routinely forgets cross-cutting concerns (security headers, error pages, OAuth callbacks).

**MMU workflow**: Install MMU as a Claude Code skill. The agent reads MMU's checklist mid-session and self-corrects.

```yaml
# .claude/skills.yaml
skills:
  - make-me-unicorn
```

In Claude Code:
```
> Use the mmu skill to scan and fix the top 3 missing M3 (Trust Fit) items.
```

**Outcome**: The agent runs `mmu scan`, identifies the top 3 missing Trust Fit items (e.g., privacy policy missing, support contact 404, refund policy absent), generates code/content to address them, and re-scans to confirm.

## 3. CI gate for solo or small team

**Situation**: You don't have a QA engineer but want every push to be checked against pre-launch readiness.

**MMU workflow**: Add MMU's guardrails workflow to `.github/workflows/`:

```yaml
- uses: actions/setup-python@v5
- run: pip install make-me-unicorn
- run: mmu doctor && mmu scan --gate M1 --fail-fast
```

**Outcome**: Push fails CI if required Build Fit items break. Same pattern works for M2/M3 once those gates apply.

## 4. MCP server in a multi-agent system

**Situation**: You're building or running a multi-agent system. One agent writes code, another reviews it. You want the reviewer to use MMU's checklist as its evaluation rubric.

**MMU workflow**:
```bash
pip install "make-me-unicorn[mcp]"
mmu mcp            # starts MCP server on stdio
```

Configure your MCP client (Claude Desktop, custom agent, etc.) to connect to the MMU MCP server. The reviewer agent now has access to `mmu_scan`, `mmu_status`, `mmu_next`, and `mmu_validate` tools.

**Outcome**: Reviewer agent rejects PRs that drop gate completion percentages or skip required Trust Fit / Security items.

## 5. Idea validation before building

**Situation**: You have a SaaS idea but you're not sure if anyone wants it. You don't want to spend 4 weeks building only to discover the problem doesn't exist.

**MMU workflow**:
```bash
mmu validate "A CLI tool that audits AI-generated SaaS code against a launch checklist"
```

**Outcome**: MMU searches Hacker News and Reddit threads, ranks signal by interest and pain, and returns a structured report — existing alternatives, frustrations voiced, indicators of demand. Costs ~$0.05–$0.20 (Claude API).

## 6. Hand-off to a contractor or co-founder

**Situation**: You've been solo until now and you're bringing in a contractor or co-founder. You need a single document that shows "where the project is" without writing a 20-page status report.

**MMU workflow**:
```bash
mmu scan --report markdown > STATUS.md
```

**Outcome**: A single Markdown report showing per-category completion, per-gate progress, list of remaining items, and the current unicorn status. New contributor can read this in 10 minutes and start picking up items.

## 7. Public roadmap and accountability

**Situation**: You want to be transparent with your users or open-source community about where the product stands.

**MMU workflow**: Add an MMU badge to your README:

```markdown
[![MMU Score](https://img.shields.io/badge/MMU-67%25-purple.svg)](https://github.com/minjikim89/make-me-unicorn)
```

Push regular `mmu scan` updates as part of your release notes or weekly update.

**Outcome**: Users see at-a-glance how close the product is to a stable launch. Builds trust through transparency.

## 8. Korean / Japanese / Spanish solo founders

**Situation**: You're a non-English-speaking solo founder. The internet's launch advice is overwhelmingly US-centric — different legal jurisdictions, different payment systems, different SEO expectations.

**MMU workflow**: Read the localized README (`README.ko.md`, `README.ja.md`, `README.zh-CN.md`, `README.es.md`). Use the CLI normally — checklist items are universal even if your launch context differs. Country-specific items (Korean PG vs Stripe, Japanese tax handling, EU VAT) are flagged separately.

**Outcome**: Same systematic readiness check, with localized context where it matters.

## Not a fit for

- Large engineering teams with dedicated QA, security, and launch ops — MMU's surface area is solo-friendly and intentionally lightweight; an enterprise will outgrow it.
- Hardware, embedded, or game-dev projects — MMU's checklist is SaaS/web-app specific.
- Pre-MVP prototypes that haven't decided what they're building yet — start with `mmu validate` for the idea, but skip the scan until there's actual code.
