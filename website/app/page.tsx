"use client";

import { useState } from "react";

const CATEGORIES = [
  {
    name: "Frontend",
    icon: "🖥",
    items: [
      "Responsive layout tested on mobile, tablet, desktop",
      "Form validation with clear error messages",
      "Loading states for all async operations",
      "Empty states for lists and dashboards",
      "404 and error pages styled consistently",
    ],
  },
  {
    name: "Auth",
    icon: "🔐",
    items: [
      "Password reset flow works end-to-end",
      "Session expiry handled gracefully",
      "OAuth callback URLs configured for prod",
      "Rate limiting on login attempts",
      "Email verification for new accounts",
    ],
  },
  {
    name: "Billing",
    icon: "💳",
    items: [
      "Webhook signature verification enabled",
      "Idempotency keys on payment endpoints",
      "Refund policy page exists and is linked",
      "Subscription lifecycle: upgrade, downgrade, cancel",
      "Failed payment retry logic configured",
    ],
  },
  {
    name: "Security",
    icon: "🛡",
    items: [
      "CORS configured for production domains only",
      "API rate limiting enabled",
      "Secrets stored in env vars, not code",
      "SQL injection prevention verified",
      "HTTPS enforced on all routes",
    ],
  },
  {
    name: "SEO & Growth",
    icon: "📈",
    items: [
      "OG meta tags on all public pages",
      "Sitemap.xml generated and submitted",
      "robots.txt configured correctly",
      "Google Search Console connected",
      "Social share preview tested",
    ],
  },
  {
    name: "Legal",
    icon: "⚖️",
    items: [
      "Privacy policy published",
      "Terms of service published",
      "Cookie consent banner (if targeting EU)",
      "Data deletion request process defined",
      "Contact information accessible",
    ],
  },
];

const STAGES = [
  { min: 0, max: 15, name: "Egg", emoji: "🥚" },
  { min: 16, max: 30, name: "Hatching", emoji: "🐣" },
  { min: 31, max: 50, name: "Foal", emoji: "🐴" },
  { min: 51, max: 75, name: "Young Unicorn", emoji: "🦄" },
  { min: 76, max: 94, name: "Unicorn", emoji: "✨" },
  { min: 95, max: 100, name: "Legendary", emoji: "👑" },
];

function getStage(pct: number) {
  return STAGES.find((s) => pct >= s.min && pct <= s.max) ?? STAGES[0];
}

export default function Home() {
  const totalItems = CATEGORIES.reduce((a, c) => a + c.items.length, 0);
  const [checked, setChecked] = useState<Set<string>>(new Set());

  const toggle = (key: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const pct = totalItems > 0 ? Math.round((checked.size / totalItems) * 100) : 0;
  const stage = getStage(pct);

  return (
    <div style={styles.page}>
      <style>{globalStyles}</style>

      {/* Hero */}
      <header style={styles.hero}>
        <h1 style={styles.title}>Make Me Unicorn</h1>
        <p style={styles.subtitle}>
          Catch what AI-generated SaaS code misses &mdash; before it costs you
          users, money, or trust.
        </p>
        <p style={styles.tagline}>
          670+ checklist items &middot; 15 categories &middot; 6 launch gates
          &middot; Zero guesswork
        </p>
        <p style={styles.tagline}>
          MCP-native: runs as a Claude Code plugin, an Agent Skill, and an MCP
          server &mdash; your AI agent reads the same checklist you do.
        </p>
        <div style={styles.cta}>
          <code style={styles.install}>pip install make-me-unicorn</code>
        </div>
      </header>

      {/* Interactive Demo */}
      <section style={styles.demo}>
        <h2 style={styles.sectionTitle}>Try it now &mdash; check some items</h2>
        <p style={styles.sectionDesc}>
          Showing {totalItems} of 670+ items. Install the CLI for the full
          checklist with all 15 categories.
        </p>

        {/* Score Bar */}
        <div style={styles.scoreBar}>
          <span style={styles.stageEmoji}>{stage.emoji}</span>
          <div style={styles.progressOuter}>
            <div
              style={{
                ...styles.progressInner,
                width: `${pct}%`,
              }}
            />
          </div>
          <span style={styles.scoreText}>
            {pct}% &mdash; {stage.name}
          </span>
        </div>

        {/* Categories */}
        <div style={styles.grid}>
          {CATEGORIES.map((cat) => (
            <div key={cat.name} style={styles.card}>
              <h3 style={styles.cardTitle}>
                {cat.icon} {cat.name}
              </h3>
              <ul style={styles.list}>
                {cat.items.map((item) => {
                  const key = `${cat.name}:${item}`;
                  const done = checked.has(key);
                  return (
                    <li
                      key={key}
                      style={styles.listItem}
                      onClick={() => toggle(key)}
                    >
                      <span style={done ? styles.checkDone : styles.checkTodo}>
                        {done ? "✓" : " "}
                      </span>
                      <span style={done ? styles.textDone : undefined}>
                        {item}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Gates */}
      <section style={styles.gates}>
        <h2 style={styles.sectionTitle}>6 Launch Gates</h2>
        <div style={styles.gateGrid}>
          {[
            { id: "M0", name: "Problem Fit", q: "Do you know WHO and WHY?" },
            { id: "M1", name: "Build Fit", q: "Does the product work end-to-end?" },
            { id: "M2", name: "Revenue Fit", q: "Can someone pay you?" },
            { id: "M3", name: "Trust Fit", q: "Privacy policy? Support path?" },
            { id: "M4", name: "Growth Fit", q: "Will people find you?" },
            { id: "M5", name: "Scale Fit", q: "What happens at 3am?" },
          ].map((g) => (
            <div key={g.id} style={styles.gateCard}>
              <strong>{g.id}</strong> {g.name}
              <br />
              <span style={styles.gateQ}>{g.q}</span>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={styles.ctaSection}>
        <h2 style={styles.sectionTitle}>Ready to ship with confidence?</h2>
        <code style={styles.installLg}>
          pip install make-me-unicorn && mmu init && mmu scan
        </code>
        <p style={styles.ctaLinks}>
          <a
            href="https://github.com/minjikim89/make-me-unicorn"
            style={styles.link}
          >
            GitHub
          </a>
          {" · "}
          <a
            href="https://pypi.org/project/make-me-unicorn/"
            style={styles.link}
          >
            PyPI
          </a>
          {" · "}
          <a
            href="https://github.com/minjikim89/make-me-unicorn/blob/main/CONTRIBUTING.md"
            style={styles.link}
          >
            Contribute
          </a>
        </p>
      </section>

      <footer style={styles.footer}>
        MIT License &middot; Built by{" "}
        <a href="https://github.com/minjikim89" style={styles.link}>
          @minjikim89
        </a>
      </footer>
    </div>
  );
}

const globalStyles = `
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e5e5e5; }
  a { color: #a78bfa; text-decoration: none; }
  a:hover { text-decoration: underline; }
`;

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 960, margin: "0 auto", padding: "0 24px" },
  hero: { textAlign: "center", padding: "80px 0 48px" },
  title: { fontSize: 48, fontWeight: 800, color: "#fff", marginBottom: 16 },
  subtitle: { fontSize: 20, color: "#a3a3a3", maxWidth: 600, margin: "0 auto 12px" },
  tagline: { fontSize: 14, color: "#737373", marginBottom: 32 },
  cta: { display: "inline-block" },
  install: {
    background: "#1a1a2e",
    border: "1px solid #333",
    borderRadius: 8,
    padding: "12px 24px",
    fontSize: 16,
    color: "#a78bfa",
  },
  demo: { padding: "48px 0" },
  sectionTitle: { fontSize: 28, fontWeight: 700, color: "#fff", marginBottom: 8, textAlign: "center" },
  sectionDesc: { fontSize: 15, color: "#737373", textAlign: "center", marginBottom: 32 },
  scoreBar: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    background: "#1a1a2e",
    borderRadius: 12,
    padding: "16px 24px",
    marginBottom: 32,
  },
  stageEmoji: { fontSize: 32 },
  progressOuter: {
    flex: 1,
    height: 12,
    background: "#262626",
    borderRadius: 6,
    overflow: "hidden",
  },
  progressInner: {
    height: "100%",
    background: "linear-gradient(90deg, #a78bfa, #e879f9)",
    borderRadius: 6,
    transition: "width 0.3s ease",
  },
  scoreText: { fontSize: 16, fontWeight: 600, color: "#fff", whiteSpace: "nowrap" },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: 16,
  },
  card: {
    background: "#141420",
    border: "1px solid #262626",
    borderRadius: 12,
    padding: 20,
  },
  cardTitle: { fontSize: 16, fontWeight: 600, color: "#fff", marginBottom: 12 },
  list: { listStyle: "none" },
  listItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: 8,
    padding: "6px 0",
    cursor: "pointer",
    fontSize: 14,
    lineHeight: 1.4,
  },
  checkTodo: {
    width: 20,
    height: 20,
    minWidth: 20,
    border: "2px solid #404040",
    borderRadius: 4,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    color: "transparent",
  },
  checkDone: {
    width: 20,
    height: 20,
    minWidth: 20,
    border: "2px solid #a78bfa",
    borderRadius: 4,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    color: "#a78bfa",
    background: "rgba(167, 139, 250, 0.1)",
  },
  textDone: { textDecoration: "line-through", color: "#525252" },
  gates: { padding: "48px 0" },
  gateGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
    gap: 12,
    marginTop: 24,
  },
  gateCard: {
    background: "#141420",
    border: "1px solid #262626",
    borderRadius: 8,
    padding: 16,
    fontSize: 14,
  },
  gateQ: { color: "#737373", fontSize: 13 },
  ctaSection: { textAlign: "center", padding: "64px 0 48px" },
  installLg: {
    display: "inline-block",
    background: "#1a1a2e",
    border: "1px solid #333",
    borderRadius: 8,
    padding: "16px 32px",
    fontSize: 16,
    color: "#a78bfa",
    marginTop: 16,
    marginBottom: 16,
  },
  ctaLinks: { fontSize: 15, color: "#737373" },
  link: { color: "#a78bfa" },
  footer: {
    textAlign: "center",
    padding: "32px 0",
    borderTop: "1px solid #1a1a1a",
    fontSize: 13,
    color: "#525252",
  },
};
