# Accessibility Blueprint

> Deep-dive checklist for WCAG 2.2 AA compliance and ARIA implementation.
> Gate-level checks → `docs/checklists/release_readiness.md`

## Semantic HTML

- [ ] Use correct heading hierarchy (`h1` → `h2` → `h3`, no skips).
- [ ] Use semantic elements (`nav`, `main`, `aside`, `footer`, `article`).
- [ ] Use `<button>` for actions and `<a>` for navigation (never reversed).
- [ ] Use lists (`ul`, `ol`) for groups of related items.
- [ ] Use `<table>` with `<th>` and `scope` for tabular data.

## Keyboard Navigation

- [ ] All interactive elements are reachable via Tab key.
- [ ] Focus order follows logical reading order.
- [ ] Visible focus indicator on all interactive elements.
- [ ] Escape key closes modals and dropdowns.
- [ ] Skip-to-content link is the first focusable element.
- [ ] No keyboard traps (user can always Tab away).

## ARIA

- [ ] Add `aria-label` or `aria-labelledby` to icon-only buttons.
- [ ] Use `role="alert"` for dynamic error messages.
- [ ] Use `aria-live` regions for dynamic content updates.
- [ ] Add `aria-expanded` to toggle buttons (dropdowns, accordions).
- [ ] Add `aria-current="page"` to active navigation links.
- [ ] Use `aria-describedby` to associate help text with form fields.

## Color and Contrast

- [ ] Text meets WCAG AA contrast ratio (4.5:1 normal, 3:1 large text).
- [ ] UI components meet 3:1 contrast against background.
- [ ] Information is not conveyed by color alone (add icons or text).
- [ ] Test with color blindness simulation tools.

## Forms

- [ ] Every input has a visible `<label>` or `aria-label`.
- [ ] Required fields are indicated (not by color alone).
- [ ] Error messages are associated with fields via `aria-describedby`.
- [ ] Form validation errors are announced to screen readers.
- [ ] Autocomplete attributes are set for common fields (`name`, `email`).

## Images and Media

- [ ] All `<img>` elements have meaningful `alt` text (or `alt=""` if decorative).
- [ ] Complex images have extended descriptions.
- [ ] Videos have captions or transcripts.
- [ ] Animations respect `prefers-reduced-motion` media query.

## Responsive and Zoom

- [ ] Content is usable at 200% browser zoom.
- [ ] Touch targets are at least 44x44 CSS pixels.
- [ ] No horizontal scrolling at 320px viewport width.
- [ ] Text resizes properly without breaking layout.

## Testing

- [ ] Test with screen reader (VoiceOver, NVDA, or JAWS).
- [ ] Run axe-core or Lighthouse accessibility audit.
- [ ] Test with keyboard-only navigation.
- [ ] Test with high contrast mode.
- [ ] Include accessibility in PR review checklist.

## Recommended Stack

| Tool | Type | Price | Why |
|---|---|---|---|
| axe-core | Accessibility Testing | Free | Industry-standard automated a11y checks |
| eslint-plugin-jsx-a11y | Linting | Free | Catch a11y issues during development |
| Radix UI | Accessible Components | Free | WAI-ARIA compliant primitives |
| Pa11y | Automated Testing | Free | CI-friendly accessibility testing |
| Stark | Design Plugin | Free tier | Contrast and a11y checks in Figma |
| WAVE | Browser Extension | Free | Visual accessibility evaluation tool |
