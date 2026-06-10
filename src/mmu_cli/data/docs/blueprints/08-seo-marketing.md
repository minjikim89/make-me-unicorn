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
- [ ] Set up `www` ↔ non-www redirect (pick one canonical form).
- [ ] Enforce trailing slash consistency across all URLs.
- [ ] Implement 301 redirects for any renamed/moved pages.

## Search Console Registration

- [ ] Register site in Google Search Console (domain property recommended for custom domains).
- [ ] Complete DNS TXT record verification for domain property.
- [ ] Submit `sitemap.xml` in Search Console → Sitemaps.
- [ ] Request indexing for key pages via URL Inspection tool.
- [ ] Link Search Console to GA4 property.
- [ ] Register site in Bing Webmaster Tools.
- [ ] Register site in Naver Search Advisor (if targeting Korean market).

<!-- if:has_i18n -->
## Internationalization (i18n) SEO

- [ ] Add `hreflang` tags for each language version.
- [ ] Set `x-default` hreflang for the primary/fallback language.
- [ ] Generate per-language sitemaps or a single sitemap with hreflang entries.
- [ ] Ensure translated pages have unique `<title>` and `<meta description>`.
- [ ] Avoid auto-redirect by IP/locale — let users and crawlers choose language.
<!-- endif -->

## Open Graph and Social

- [ ] Set `og:title`, `og:description`, `og:image` per page.
- [ ] Set `og:type`, `og:url`, `og:site_name`, `og:locale`.
- [ ] Create OG thumbnail template (1200x630px).
- [ ] Set Twitter Card meta tags (`twitter:card`, `twitter:image`).
- [ ] Verify previews on Slack, X, Kakao, Messenger, LinkedIn.

## Performance for SEO

- [ ] Achieve Lighthouse performance score 90+.
- [ ] Optimize Largest Contentful Paint (LCP < 2.5s).
- [ ] Minimize Cumulative Layout Shift (CLS < 0.1).
- [ ] Optimize Interaction to Next Paint (INP < 200ms).
- [ ] Implement server-side rendering or static generation for indexable pages.

## Post-Deploy Verification

- [ ] Run Google Rich Results Test on key pages.
- [ ] Run Google Mobile-Friendly Test.
- [ ] Check PageSpeed Insights for Core Web Vitals pass.
- [ ] Validate OG previews on real channels (not just validators).
- [ ] Confirm sitemap is accessible and returns 200.
- [ ] Confirm `robots.txt` does not accidentally block important paths.

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

- [ ] Set up GA4 property and install Measurement ID.
- [ ] Verify GA4 is receiving data (Realtime report or DebugView).
- [ ] Link GA4 ↔ Google Search Console for search query data.
- [ ] Set up UTM parameter convention for campaigns.
- [ ] Track source/medium/campaign for all marketing channels.
- [ ] Implement conversion tracking for key goals.
- [ ] Monitor keyword rankings weekly.

<!-- if:has_email_marketing -->
## Email Marketing

- [ ] Build email capture mechanism (newsletter, lead magnet).
- [ ] Set up email marketing platform (ConvertKit, Resend, Loops).
- [ ] Create welcome email sequence.
- [ ] Implement email preference center.
- [ ] Comply with CAN-SPAM / GDPR for email.
<!-- endif -->

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Google Search Console | SEO Monitoring | Free | Official search performance data |
| Google Analytics 4 | Web Analytics | Free | Traffic, conversions, Search Console integration |
| Bing Webmaster Tools | SEO Monitoring | Free | Bing/DuckDuckGo search coverage |
| Naver Search Advisor | SEO Monitoring | Free | Required for Korean search traffic |
| Ahrefs / Semrush | SEO Analysis | $99/mo+ | Keyword research, backlink analysis |
| next-seo | SEO Library | Free | Easy meta tag management for Next.js |
| Vercel OG | OG Image Generation | Free | Dynamic OG image generation |
| ConvertKit | Email Marketing | Free tier | Creator-focused email automation |
| Loops | Email for SaaS | Free tier | Built for SaaS product emails |
