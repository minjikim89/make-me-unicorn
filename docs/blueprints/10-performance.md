# Performance Blueprint

> Deep-dive checklist for frontend, backend, and infrastructure performance.
> Gate-level checks → `docs/checklists/release_readiness.md`

## Frontend Performance

- [ ] Achieve Lighthouse performance score 90+.
- [ ] Optimize Largest Contentful Paint (LCP) below 2.5s.
- [ ] Minimize Cumulative Layout Shift (CLS) below 0.1.
- [ ] Optimize Interaction to Next Paint (INP) below 200ms.
- [ ] Implement code splitting per route.
- [ ] Tree-shake unused JavaScript.
- [ ] Compress images (WebP/AVIF with fallback).

## Asset Optimization

- [ ] Enable Brotli or gzip compression for all text assets.
- [ ] Minify CSS and JavaScript in production builds.
- [ ] Configure aggressive caching for static assets (hashed filenames).
- [ ] Use CDN for static asset delivery.
- [ ] Preload critical assets (`<link rel="preload">`).
- [ ] Lazy-load below-the-fold images and components.

## Font Optimization

- [ ] Self-host fonts or use `font-display: swap`.
- [ ] Subset fonts to include only needed characters.
- [ ] Preconnect to font origins.
- [ ] Limit font variants (2-3 weights max).

## API Performance

- [ ] Set response time targets per endpoint (p95 < 200ms for reads).
- [ ] Implement response caching for frequently accessed data.
- [ ] Use pagination for list endpoints.
- [ ] Optimize N+1 query patterns.
- [ ] Implement database query indexing for hot paths.

## Database Performance

- [ ] Add indexes for all frequently queried columns.
- [ ] Use `EXPLAIN ANALYZE` to profile slow queries.
- [ ] Implement connection pooling (PgBouncer or built-in).
- [ ] Set up read replicas if read-heavy.
- [ ] Implement query result caching (Redis).
- [ ] Archive or partition old data.

## Infrastructure Performance

- [ ] Choose regions close to your users.
- [ ] Configure auto-scaling for traffic spikes.
- [ ] Implement CDN for global content delivery.
- [ ] Monitor and optimize cold start times (serverless).
- [ ] Set up load testing for critical paths.

## Monitoring Performance

- [ ] Track Core Web Vitals in production (CrUX or RUM).
- [ ] Set up performance budgets in CI.
- [ ] Alert on performance regression.
- [ ] Run Lighthouse CI on every pull request.
- [ ] Monitor real user metrics (not just synthetic).

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Lighthouse CI | Performance Testing | Free | Automated performance scoring in CI |
| Bundlephobia | Bundle Analysis | Free | Check package sizes before installing |
| webpack-bundle-analyzer | Bundle Visualization | Free | Visualize what makes your bundle large |
| Cloudflare | CDN | Free tier | Global CDN, edge caching |
| PgBouncer | Connection Pooling | Free | PostgreSQL connection pooler |
| k6 | Load Testing | Free | Developer-friendly load testing tool |
| Unlighthouse | Site-wide Auditing | Free | Run Lighthouse across all pages |
