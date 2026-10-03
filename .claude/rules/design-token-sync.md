---
description: Use when editing design tokens, brand colors, component CSS, screen mockups, logo files or the UI spec's token section. Token values live in five places that must agree, and the logo files are generated.
paths:
  - "app-buildout/phase-1-launch/05-ui-ux-spec.md"
  - "app-buildout/phase-1-launch/design/**"
  - "app-buildout/brand/**"
  - "packages/tokens/**"
---

# Design token and brand sync

Authority: `app-buildout/phase-1-launch/design/README.md` ("Changing the design") and
`app-buildout/brand/BRAND.md`. If you need to break one of these, change the doc in the same
commit and say why.

## Keep in sync

- **Token values live in five places:** `05-ui-ux-spec.md` section 2, `design/tokens.css`,
  `packages/tokens` (a copy of `design/tokens.css` that must stay equal; the token test in WF-005
  checks it), `brand/BRAND.md` (Colors) and the color constants at the top of
  `brand/generate_logo.py`. 05 section 2 wins; if `tokens.css` differs from it, `tokens.css` is the
  one that is wrong. Change all of them in one commit.
- **A change to `tokens.css` or `hermi.css` changes the screens.** Update `components.html` and
  every screen that uses the block, then re-render the affected PNGs in `design/png/`. The command
  is in `design/README.md` ("Previewing"). Keep `--blink-settings=preferredColorScheme=1`, or
  headless Edge follows the Windows theme and may render a light page dark.

## What must not change without a decision

- **The SVGs in `brand/` are generated.** Regenerate with `generate_logo.py` (steps in BRAND.md,
  "Regenerating"), do not hand-edit. The script writes bytes on purpose so Windows does not put
  CRLF in them; switching it to `write_text` would.
- **Pink on the left, yellow on the right, the plane points right.** No recoloring, gradients,
  shadows or rotation (BRAND.md, "Rules").
- **`hermi-app-icon-1024.png` must be RGB with no alpha channel.** It is the App Store icon. After
  rendering, check `Image.open(...).mode == 'RGB'`.
- **`--heat-ink-1` to `--heat-ink-5`, `--viz-band` and `--tp-ticket` are defined in 05 section 2 first,
  then `tokens.css`, in one commit** (DECISIONS.md, setup, Decision 8).

## Checkable by grep

```bash
# the brand sky must agree in the spec, tokens, BRAND.md and the generator
grep -rIil -e '2AA5FF' app-buildout/phase-1-launch/05-ui-ux-spec.md app-buildout/phase-1-launch/design/tokens.css app-buildout/brand/BRAND.md app-buildout/brand/generate_logo.py
```
