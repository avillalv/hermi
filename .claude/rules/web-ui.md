---
description: Use when writing or changing web UI, UI copy, design tokens or Playwright tests. Screens must match the design kit, use tokens only and ship every state.
paths:
  - "apps/web/src/**"
  - "apps/web/e2e/**"
  - "packages/tokens/**"
---

# Web UI rules

Authority: `05-ui-ux-spec.md` sections 2 and 7, `design/README.md` and `design/DESIGN-LANGUAGE.md`. If you need to
break one of these, change the document in the same commit and say why. Before UI work, read `design/README.md`
and `brand/BRAND.md`.

## Look: tokens, components, screens

- **Tokens only.** Colors, type, spacing, radii, elevation and motion come from `packages/tokens`, a copy of
  `design/tokens.css` whose values equal 05 section 2. No hex, `rgb()` or `hsl()` in a component, a Tailwind
  arbitrary value or a style prop. The logo mark is the one exception.
- **Build components from the kit.** Take the block in `design/hermi.css` named for the 05 section 4 component.
  Keep its class names (the React wrappers emit the `h-` classes) or map them one to one to utilities; never
  change a number. A missing block is added to `hermi.css` and `components.html` by the ticket that needs it.
- **Match the mockup.** A screen with a mockup in `design/screens/` looks the same at 390 by 844 in light and
  dark. Check it with the `verify-ui-against-kit` skill before calling the ticket done. A screen without one
  follows `design/DESIGN-LANGUAGE.md` section 11 (the new screen checklist). Every UI ticket has a `Kit:` line in
  09 that names its 05 section and mockup.
- **When sources disagree:** 05 section 2 token values first, then `hermi.css` and the mockups (they win over the
  prose in 05 sections 4 and 6), then the ASCII wireframes in 05 section 6. Behavior and copy always come from 05.
- **Fonts are bundled.** Fredoka, Atkinson Hyperlegible Next and Atkinson Hyperlegible Mono come from the
  `@fontsource-variable` packages and are listed first in the token stacks. Never link Google Fonts: no
  `googleapis` or `gstatic` request may be made, and the CSP does not allow them.
- **Native code stays in `src/lib/native/`.** The rest of `apps/web` does not know Capacitor exists; the adapter
  returns no-ops on the web.

## States and behavior

- Every state in 05 (loading, empty, error, offline, limit) ships with a component test. Offline and error also
  get a Playwright test.
- A price shows its currency, its source and its age. A partner action shows the exact disclosure and a free
  route beside it.
- Never rank, sort, highlight or label by commission (non-negotiable 2). Use the neutral sort statements in 05
  section 7.4 ("Sorted by price, lowest first"), never "recommended" or "top picks" for anything that can carry
  a commission.

## Copy

- Sentence case, plain verbs, no em or en dashes (use a comma, a period or "to" for ranges). Errors say what
  happened and how to fix it (05 section 7).
- The disclosure is exact and fixed: **We earn a commission if you book here.** It sits beside every partner
  button.
- Strings live in `locales/en.json`, and `scripts/check-copy.mjs` checks them.

## Accessibility

- axe is clean on every screen. Targets are at least 44 pt, text is at least 13 px and set in `rem`, contrast
  meets the ratios in 05 section 2.3, every control has a visible focus state, and reduced motion shows final
  states.
- Layouts reflow at large text sizes (05 section 9.3). Ticket stubs use `min-height`, so text grows instead of
  being clipped.

## What must not change without a decision

- **Token names and values in `packages/tokens`.** The token test (WF-005) compares them with 05 section 2 and
  recomputes every contrast ratio, so a drifted token fails it.
- **The `h-` class names.** The kit, the screens and the visual checks all select on them.

## Checkable by grep

```bash
# em or en dashes in the web source (prints nothing when clean)
grep -rIl -e $'\xe2\x80\x94' -e $'\xe2\x80\x93' apps/web/src apps/web/e2e
# raw colors outside packages/tokens (only the logo mark and generated API types may match)
grep -rnE "#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b|rgba?\(|hsla?\(" apps/web/src --include=*.ts --include=*.tsx --include=*.css | grep -v "lib/api/schema.d.ts"
# Google Fonts (prints nothing when clean)
grep -rnE "googleapis|gstatic" apps/web/src apps/web/index.html apps/web/public
```
