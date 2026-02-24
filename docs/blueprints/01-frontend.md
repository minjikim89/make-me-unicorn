# Frontend Blueprint

> Deep-dive checklist for frontend implementation.
> Gate-level checks → `docs/checklists/from_scratch.md`

## Core Setup

- [ ] Choose framework (Next.js App Router, Nuxt, or SvelteKit) for SSR/SSG.
- [ ] Configure TypeScript with `strict: true`.
- [ ] Set up component library (shadcn/ui, Radix UI, or Headless UI).
- [ ] Configure path aliases (`@/components`, `@/lib`, etc.).
- [ ] Set up CSS strategy (Tailwind CSS, CSS Modules, or styled-components).

## Routing and Navigation

- [ ] Implement file-based routing with dynamic segments.
- [ ] Add loading states for route transitions.
- [ ] Configure 404 and error boundary pages.
- [ ] Implement breadcrumb navigation for nested routes.
- [ ] Set up route guards for authenticated pages.

## State Management

- [ ] Choose client state solution (Zustand, Jotai, or Context API).
- [ ] Implement server state caching (TanStack Query or SWR).
- [ ] Define cache invalidation strategy for mutations.
- [ ] Separate UI state from server state.

## Forms and Validation

- [ ] Set up form library (React Hook Form or Formik).
- [ ] Implement schema validation (Zod or Yup).
- [ ] Add inline error messages with accessible markup.
- [ ] Handle server-side validation errors gracefully.
- [ ] Implement optimistic updates for form submissions.

## Layout and Responsive Design

- [ ] Build responsive layout shell (sidebar, header, main content).
- [ ] Implement mobile-first breakpoints.
- [ ] Add skeleton loaders for async content.
- [ ] Implement empty states with clear CTAs.
- [ ] Handle viewport meta tag for mobile devices.

## Authentication UI

- [ ] Build login/signup/forgot-password pages.
- [ ] Implement OAuth social login buttons.
- [ ] Add loading and error states for auth flows.
- [ ] Redirect authenticated users away from auth pages.
- [ ] Show user avatar/name in navigation after login.

## Performance

- [ ] Enable static rendering (SSG) for all eligible pages.
- [ ] Implement code splitting per route.
- [ ] Lazy-load heavy components (charts, editors, modals).
- [ ] Optimize images with `next/image` or equivalent.
- [ ] Configure font loading strategy (`font-display: swap`).
- [ ] Add `rel="preconnect"` for third-party origins.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| Next.js (App Router) | Framework | Free | SSR/SSG, React Server Components |
| shadcn/ui | Component Library | Free | Radix-based, highly customizable |
| Tailwind CSS | Styling | Free | Utility-first, fast prototyping |
| Zustand | State Management | Free | Lightweight, minimal boilerplate |
| TanStack Query | Server State | Free | Caching, background refetch, pagination |
| React Hook Form | Forms | Free | Performant, minimal re-renders |
| Zod | Validation | Free | TypeScript-first schema validation |
