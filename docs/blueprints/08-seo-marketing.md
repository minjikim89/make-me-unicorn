# SEO and Marketing Blueprint

> Deep-dive checklist for technical SEO and marketing infrastructure.
> Gate-level checks → `docs/checklists/seo_distribution.md`

## Technical SEO

- [ ] Set `<title>` and `<meta name="description">` per page.
- [ ] Set canonical URLs to prevent duplicate content.
- [ ] Generate `sitemap.xml` dynamically.
- [ ] Configure `robots.txt` with correct allow/disallow rules.
- [ ] Implement structured data (JSON-LD) for key pages.
- [ ] Ensure all pages return correct HTTP status codes.

## Open Graph and Social

- [ ] Set `og:title`, `og:description`, `og:image` per page.
- [ ] Set `og:type`, `og:url`, `og:site_name`.
- [ ] Create OG thumbnail template (1200x630px).
- [ ] Set Twitter Card meta tags (`twitter:card`, `twitter:image`).
- [ ] Verify previews on Slack, X, Kakao, Messenger, LinkedIn.

## Performance for SEO

- [ ] Achieve Lighthouse performance score 90+.
- [ ] Optimize Largest Contentful Paint (LCP < 2.5s).
- [ ] Minimize Cumulative Layout Shift (CLS < 0.1).
- [ ] Optimize First Input Delay (FID < 100ms).
- [ ] Implement server-side rendering for indexable pages.

## Content Strategy

- [ ] Identify primary keyword for landing page.
- [ ] Create comparison pages (vs competitors).
- [ ] Write use-case specific landing pages.
- [ ] Publish a blog or changelog for organic traffic.
- [ ] Implement internal linking strategy.

## Link Building

- [ ] Submit to relevant directories (Product Hunt, Indie Hackers, etc.).
- [ ] Create shareable resources (checklists, templates, tools).
- [ ] Build backlinks through guest posts or mentions.
- [ ] Monitor backlink profile with Google Search Console.

## Analytics and Attribution

- [ ] Set up UTM parameter convention for campaigns.
- [ ] Track source/medium/campaign for all marketing channels.
- [ ] Implement conversion tracking for key goals.
- [ ] Set up Google Search Console and verify domain.
- [ ] Monitor keyword rankings weekly.

## Email Marketing

- [ ] Build email capture mechanism (newsletter, lead magnet).
- [ ] Set up email marketing platform (ConvertKit, Resend, Loops).
- [ ] Create welcome email sequence.
- [ ] Implement email preference center.
- [ ] Comply with CAN-SPAM / GDPR for email.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Google Search Console | SEO Monitoring | Free | Official search performance data |
| Ahrefs / Semrush | SEO Analysis | $99/mo+ | Keyword research, backlink analysis |
| next-seo | SEO Library | Free | Easy meta tag management for Next.js |
| Vercel OG | OG Image Generation | Free | Dynamic OG image generation |
| ConvertKit | Email Marketing | Free tier | Creator-focused email automation |
| Loops | Email for SaaS | Free tier | Built for SaaS product emails |
