# Product Hunt Launch Kit

## Tagline (60 chars max)

**Primary:** `The open-source launch checklist for solo SaaS builders`
**Alt 1:** `534+ checks to catch what AI-generated code misses`
**Alt 2:** `Stop building blind — ship your SaaS with confidence`

## Description

Building a SaaS with AI tools like Cursor, Claude, or Copilot? You're shipping code faster than ever — but are you shipping *complete* products?

Make Me Unicorn is an open-source CLI that tracks 534+ launch readiness items across 15 categories: from auth flows to billing webhooks, from OG tags to privacy policies, from rate limiting to backup plans.

**What makes it different:**
- Zero-dependency Python CLI — works offline, no account needed
- Feature flags skip what doesn't apply to your project
- 6 launch gates (M0–M5) ensure you don't skip critical phases
- 12 operating modes prevent AI context overload
- Optional Claude integration for smart doc generation

**Your project evolves visually:** Egg → Hatching → Foal → Young Unicorn → Unicorn → Legendary

```
pip install make-me-unicorn
mmu init && mmu scan && mmu status --why
```

## First Comment (Maker Story)

Hi PH! I built Make Me Unicorn after watching the same pattern repeat: builders ship AI-generated code incredibly fast, then get burned by everything *around* the code.

Forgot password reset? Users locked out on day 1.
No webhook verification? Payment replay attacks.
Missing OG tags? Every shared link looks broken.
No refund policy? First dispute = frozen Stripe account.

The problem isn't coding ability — it's tracking what matters beyond code. That's what MMU does.

**What I'd love feedback on:**
1. Are there categories or items you'd add to the checklist?
2. Would you use the badge feature to show launch readiness in your README?
3. What industry blueprints would you want next? (We have AI Products and Marketplace so far)

Everything is MIT licensed. PRs welcome.

## Topics

- Developer Tools
- Open Source
- SaaS
- Artificial Intelligence
- Productivity

## Target Launch Day

- **Best days:** Tuesday, Wednesday, or Thursday
- **Best time:** 12:01 AM PT (to maximize 24-hour window)

## Pre-Launch Checklist

- [ ] Product page draft submitted 7 days before
- [ ] 3+ high-quality screenshots/GIFs ready
- [ ] Social preview image (1200x630) uploaded
- [ ] 10+ supporters notified for launch day upvotes
- [ ] First comment (maker story) pre-written
- [ ] Twitter/LinkedIn announcement post drafted
- [ ] Reply templates for common questions prepared
- [ ] Landing page / web demo live and tested

## Screenshots to Prepare

1. **Status dashboard** — `mmu` showing Egg → Unicorn evolution
2. **Score breakdown** — `mmu status --why` Lighthouse-style decomposition
3. **Next actions** — `mmu next` prioritized recommendations
4. **Badge in README** — `mmu badge` output embedded in a real project
5. **Share card** — `mmu share` terminal output
6. **Web demo** — Interactive checklist on the landing page

## Social Announcement Templates

### Twitter/X

```
🦄 Make Me Unicorn is live on Product Hunt!

534+ things your AI-generated SaaS code probably forgot:
✓ Password reset flows
✓ Webhook verification
✓ OG tags
✓ Refund policies
✓ ...and 530 more

Free, open source, zero dependencies.

pip install make-me-unicorn

{PH link} #MakeMeUnicorn
```

### LinkedIn

```
I just launched Make Me Unicorn on Product Hunt.

The problem: AI tools like Cursor and Claude help you code 10x faster. But they don't remind you to:
→ Add a password reset flow
→ Verify webhook signatures
→ Write a privacy policy
→ Set up monitoring alerts

Make Me Unicorn is an open-source CLI that tracks 534+ launch readiness items across 15 categories.

Your project evolves as you complete items: Egg → Hatching → Foal → Young Unicorn → Unicorn → Legendary.

MIT licensed. Zero dependencies. Works offline.

Check it out: {PH link}

#SaaS #OpenSource #DeveloperTools #BuildInPublic
```

## Success Metrics

**Primary:** signups / pip installs (not PH ranking)
**Secondary:**
- GitHub stars gained on launch day
- Unique visitors to web demo
- Badge adoptions in external READMEs (track via GitHub search)

## Post-Launch

- [ ] Thank PH community in comment
- [ ] Address all questions/feedback in comments within 24h
- [ ] Write "Lessons from our PH launch" blog post (SEO + community)
- [ ] Update README with PH badge if top 5
