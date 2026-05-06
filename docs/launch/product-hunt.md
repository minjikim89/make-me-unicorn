# Product Hunt Launch Kit

## Tagline (60 chars max)

**Primary:** `MCP-native launch OS for solo SaaS builders`
**Alt 1:** `Validate, ship, and launch your SaaS — agent-native`
**Alt 2:** `Claude can now run your launch checklist for you`
**Alt 3 (legacy v0.5):** `534+ checks to catch what AI-generated code misses`

## Description

Building a SaaS with AI agents like Cursor, Claude Code, or Codex? You're shipping faster than ever — but the *checklist around the code* (auth, billing, legal, growth, scale) keeps getting deferred until launch day.

Make Me Unicorn is the open-source launch operating system for solo SaaS builders. v0.6 makes it **agent-native** — three new ways to use it without leaving your terminal:

1. **Install as a Claude Code plugin / Anthropic Agent Skill** — `/plugin marketplace add minjikim89/make-me-unicorn`. Auto-triggers when you say "validate my SaaS idea" or "what should I check before launch?". Works in Claude Code, Claude Desktop, and OpenAI Codex CLI.
2. **Run as an MCP server** — `mmu serve-mcp`. Any MCP client (Claude Code, Cursor, Gemini CLI) can call MMU's 17 blueprints, idea templates, and Product Hunt kit as native tools.
3. **Validate ideas against the real internet** — `mmu validate "your idea"`. Pulls actual HN + Reddit threads, scores sentiment locally (free, no API key), surfaces competitors. Add `--llm` for a 1-page validation verdict.

The original CLI is still there: 534+ launch readiness items, 15 core blueprints + 2 industry blueprints (AI Product, Marketplace), 6 launch gates (M0–M5), 12 operating modes.

```
pip install make-me-unicorn
mmu init && mmu scan && mmu status --why
mmu validate "your startup idea"
```

**Why this matters now:** the MCP registry hit 9,400+ servers in April 2026 (78% enterprise adoption). Anthropic's Agent Skills spec was adopted by OpenAI Codex in Dec 2025. Distribution for solo-builder tools has shifted from human-discovered to agent-invoked. v0.6 plants MMU on both rails.

## First Comment (Maker Story)

Hi PH! I built Make Me Unicorn after watching the same pattern: builders ship AI-generated code incredibly fast, then get burned by everything *around* the code — auth flows, webhook verification, OG tags, refund policies, monitoring.

v0.5 was the "Distribution Engine" release: badges, share cards, industry blueprints. It got the kit out into other people's READMEs.

v0.6 is "Agent-Native". The realization: in 2026, more developers ask Claude or Cursor "what should I check before launch?" than search Google for a checklist. So MMU now lives where the agents live.

**What I'd love feedback on:**

1. If you build with Claude Code or Codex daily — is the Skill auto-trigger phrase ("validate my SaaS idea", "launch checklist") natural, or would you phrase it differently?
2. The free `mmu validate` mode pulls HN + Reddit + local NLP — would you trust the verdict to gate a build/no-build decision, or is `--llm` synthesis a must?
3. What MCP tool would unlock your workflow? (currently: list/get blueprints, list templates; on the roadmap: write back results, score-from-MCP)

Everything is MIT licensed. PRs welcome.

## Topics

- Developer Tools
- Open Source
- Artificial Intelligence
- SaaS
- Productivity

(Add "MCP" / "Claude" / "Anthropic" tags if PH has them on launch day.)

## Target Launch Day

- **Best days:** Tuesday, Wednesday, or Thursday
- **Best time:** 12:01 AM PT (to maximize 24-hour window)

## Pre-Launch Checklist

- [ ] Product page draft submitted 7 days before
- [ ] 4+ high-quality screenshots/GIFs ready (status dashboard, badge, `mmu validate` output, MCP tool list in Claude Desktop)
- [ ] Social preview image (1200x630) updated with v0.6 angle
- [ ] 10+ supporters notified for launch day upvotes
- [ ] First comment (maker story) pre-written and reviewed
- [ ] Twitter/LinkedIn announcement post drafted
- [ ] Reply templates for common questions prepared
- [ ] Landing page / web demo live and updated for v0.6
- [ ] PyPI v0.6.0 published and verified (`pip install make-me-unicorn==0.6.0`)
- [ ] Plugin marketplace install verified end-to-end in a fresh Claude Code session

## Screenshots to Prepare

1. **Status dashboard** — `mmu` showing Egg → Unicorn evolution
2. **`mmu validate` output** — terminal showing real HN + Reddit threads + sentiment for a recognizable idea
3. **MCP tool list in Claude Desktop** — screenshot of the four MMU tools available
4. **Skill auto-trigger** — Claude Code conversation where mentioning "startup idea" auto-loads MMU
5. **Score breakdown** — `mmu status --why` Lighthouse-style decomposition
6. **Badge in README** — `mmu badge` output embedded in a real project
7. **Web demo** — Interactive checklist on the landing page

## Social Announcement Templates

### Twitter/X

```
🦄 Make Me Unicorn v0.6 is live on Product Hunt.

In 2026 your launch checklist should live where your agent lives:

→ Claude Code plugin (auto-loads on "validate my idea")
→ MCP server for Cursor / Claude Desktop / Gemini CLI
→ `mmu validate <idea>` pulls real HN + Reddit threads

Free, open source, MIT.

pip install make-me-unicorn

{PH link} #MakeMeUnicorn #MCP #ClaudeCode
```

### LinkedIn

```
I just launched Make Me Unicorn v0.6 on Product Hunt.

The shift this release: solo-builder tools have to be agent-native now.

In 2026, more developers ask Claude or Cursor "what should I check before launch?" than search Google. The MCP registry hit 9,400+ servers in April. Anthropic's Agent Skills spec was adopted by OpenAI Codex in December.

So MMU v0.6 plants on both rails:

→ Claude Code plugin / Anthropic Agent Skill — auto-triggers on phrases like "validate my SaaS idea" or "launch checklist". Compatible with Claude Code, Claude Desktop, and OpenAI Codex CLI.

→ `mmu serve-mcp` — exposes 17 blueprints + idea templates as native MCP tools, callable from any MCP client.

→ `mmu validate <idea>` — pulls real HN + Reddit threads, scores sentiment locally (free, no API key), surfaces competitors. Add --llm for a synthesized verdict.

The original CLI is still there. 534+ launch readiness items. 15 core blueprints + 2 industry blueprints (AI Product, Marketplace). 6 launch gates. 12 operating modes.

MIT licensed. Zero dependencies for the core CLI.

Check it out: {PH link}

#SaaS #OpenSource #MCP #ClaudeCode #DeveloperTools #BuildInPublic
```

## Success Metrics

**Primary:** PyPI installs of v0.6.0 in launch week + Claude Code plugin installs (track via marketplace if visible)
**Secondary:**
- GitHub stars gained on launch day
- Unique visitors to web demo
- MCP tool invocations (if telemetry is added — currently zero by design)
- Badge adoptions in external READMEs (track via GitHub search)
- `mmu validate` reports saved (proxy: Reddit/HN threads referencing MMU)

## Post-Launch

- [ ] Thank PH community in comment
- [ ] Address all questions/feedback in comments within 24h
- [ ] Write "Lessons from our PH launch (v0.6 Agent-Native edition)" blog post
- [ ] Update README with PH badge if top 5
- [ ] Open a v0.7 roadmap issue inviting community input on next agent-tier features
