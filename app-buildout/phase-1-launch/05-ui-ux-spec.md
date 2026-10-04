# 05. UI and UX specification, Phase 1

Part of the [Phase 1 build specification](README.md). The shared decisions in [../README.md](../README.md) and the Phase 1 scope in [README.md](README.md) are final and override anything here. Brand files are in [../brand/](../brand/BRAND.md). API names are in [04-api-spec.md](04-api-spec.md), tables in [03-database-schema.md](03-database-schema.md), product behavior and limits in [01-product-spec.md](01-product-spec.md), pricing and entitlement logic in [07-monetization-spec.md](07-monetization-spec.md), AI behavior in [06-ai-agents-spec.md](06-ai-agents-spec.md).

Written 2026-09-30. This file is the source of truth for how Hermi looks, moves and reads. It starts from the design system that already exists in the Trip Planner repository (`frontend/src/index.css`, `frontend/src/components/ui/`, `frontend/src/components/brand/`) and keeps its token plumbing and neutral token names, but replaces the old passport palette, type and motifs with the Hermi design language: two routes, one trip. Where this file adds or renames a token (for example `--tp-sky`), it says so.

This Phase 1 file keeps the whole design system and every Phase 1 screen and paywall trigger. Screens and triggers that ship later are not specified here; where a reader would look for one there is a one-line pointer ("Later: Phase 2, see ...").

Contents: 1 Design principles, 2 Design tokens, 3 Logo usage, 4 Component library, 5 Navigation and information architecture, 6 Screens, 7 Microcopy rules, 8 Paywall design rules, 9 Accessibility, 10 Responsive breakpoints, 11 Haptics, 12 Dark mode, 13 Analytics conventions.

**Visual reference.** The look is defined by the design kit in [design/](design/README.md): `tokens.css` mirrors section 2, `hermi.css` holds the component classes, and `screens/` has an HTML mockup of each key screen with its PNG in `png/` (each PNG is also shown under the section it covers). The design canvas the kit was cut from is at [claude.ai/artifact/VeWM3tJksFdPZSa2p7qhCP](https://claude.ai/artifact/VeWM3tJksFdPZSa2p7qhCP), which is private and for the owner only. When two sources differ, for how the UI looks the section 2 values win, then the kit, then the ASCII wireframes in section 6; for behavior, states, copy and events this file wins.

## 1. Design principles

1. **Two routes, one trip.** A warm paper ground, deep ink, sky blue as the brand, and the people on the trip drawn as colored dotted routes that meet at a plane. Every trip has its own seeded route pattern in its travelers' colors, so a trip feels like a journey you share. Trip facts are boarding-pass tickets on a calm trip map: notched cards with a tear line and a stub that carries the status, the votes or the action.
2. **Value before asking.** No account wall, no paywall, no permission prompt before the person has built something. Ask for sign-in when there is something to save, and for a purchase only at a limit they actually hit.
3. **The free path is always visible.** Every paywall, credit prompt and partner card shows the no-cost route beside the paid one, in the same visual weight class ("Not now" is a real button, not a gray X).
4. **Show the source.** Anything an agent found shows the page it came from, the date it was seen and what it was based on. Prices say "at last check". Nothing is presented as the lowest or best price.
5. **Numbers are a calm, honest voice.** Prices, credits and fares are set in the data face (Atkinson Hyperlegible Mono, tabular figures), always with currency, date or age, and a plain statement of how a list is sorted.
6. **Plan together.** Who did what is always visible: avatars, "added by Sam", vote counts with names. Shared state is never silent; changes from others appear with a quiet highlight.
7. **Never blocks the trip.** Offline, rate limited, out of credits or downgraded: the plan stays readable and editable where possible and always exportable. Errors say what happened and how to fix it.
8. **Quiet commerce.** Partner cards are useful, labeled and few. No banners, no countdowns, no fake scarcity, nothing ranked by commission, nothing inside AI output.
9. **One screen, one job.** A phone screen has one primary action. Advanced controls live behind a sheet or a "More" row.
10. **Accessible by construction.** WCAG 2.2 AA is the floor, not a polish pass. Color never carries meaning alone, and every motion has a reduced version.

## 2. Design tokens

All tokens are CSS custom properties defined in `packages/tokens` (CSS and TS) and imported by `apps/web`, exposed to Tailwind 4 through `@theme inline`. The token plumbing and the neutral names (`--tp-paper`, `--tp-ink`, `--tp-brand` and the rest) are ported from the Trip Planner's `frontend/src/index.css`; the values are not. Every value below replaces the old passport palette, and where a token is new or renamed this file says so. Components use the semantic names (`--background`, `--card`, `--primary`) and the Hermi names (`--tp-*`). Never hard-code a hex value in a component.

### 2.1 Color: surfaces and ink

The tables in 2.1 to 2.3 are machine-readable: one token per row, the token name in backticks in the first column, each color value in backticks. WF-005 parses them and compares them with `design/tokens.css`. Keep that shape.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--tp-paper` (`--background`) | `#FBF5EA` | `#0B1A2A` | Page ground, warm paper |
| `--tp-ticket` | `#FBF5EA` | `#0B1A2A` | A named alias for the ticket surface; always equal to `--tp-paper` in both modes |
| `--tp-sheet` (`--card`, `--popover`) | `#FFFDF8` | `#12263A` | Cards, tickets, sheets, inputs, popovers; a warm white |
| `--tp-sunken` (`--secondary`, `--muted`, `--accent`) | `#F5ECDA` | `#1A3149` | Wells, chips, ticket stubs, hover fill, skeleton base |
| `--tp-ink` (`--foreground`) | `#17324A` | `#E6F2FF` | Primary text, icons |
| `--tp-ink-soft` (`--muted-foreground`) | `#4A6580` | `#9DB5CC` | Secondary text, captions |
| `--tp-rule` (`--border`, `--input`) | `#E3D6BC` | `#27405A` | Decorative dividers, card and ticket borders only |
| `--tp-edge` (new) | `#6A86A0` | `#6C88A3` | Borders of interactive controls (inputs, checkboxes, segmented controls). Needed because `--tp-rule` is only about 1.4 to 1 against a card, which fails the 3 to 1 non-text contrast rule |
| `--tp-brand` (`--primary`, `--ring`) | `#0B6BC0` | `#6CC4FF` | Primary buttons, links, focus ring, active tab. This is the text-safe sky; the logo's own sky `#2AA5FF` is `--tp-sky` |
| `--tp-brand-ink` (`--primary-foreground`) | `#FFFFFF` | `#0B1A2A` | Text on brand fills |
| `--tp-brand-soft` | `#DCEFFF` | `#123A5C` | Selected row, your own vote, soft emphasis |
| `--tp-success` | `#1d7a52` | `#4cc38a` | Done, price fell, booked |
| `--tp-warning` | `#a86a12` | `#e0a44a` | Caution, price rose, limit near. Light value is 4.36 to 1 on a card, so use it for icons, bars and text of 18 px bold or larger; small text uses `--tp-warning-ink` |
| `--tp-warning-ink` (new) | `#8a5a10` | `#e0a44a` | Small warning text (5.82 to 1 on a card in light) |
| `--tp-danger` (`--destructive`) | `#b42318` | `#f07167` | Errors, destructive actions, price rose when the user is buying |

The light surfaces are warm (paper, sheet, sunken and rule), chosen in the 2026-10-03 design review; the dark values are unchanged.

### 2.2 Color: sky, routes, travelers and data

| Token | Light | Dark | Use |
|---|---|---|---|
| `--tp-sky` (`--sidebar`; renamed from `--tp-cover`) | `#2AA5FF` | `#0E3F66` | The logo tile and the brand surfaces: splash, web sidebar, paywall header, trip header band. A fill, never a text color (white on it is 2.65 to 1) |
| `--tp-sky-ink` | `#17324A` | `#E6F2FF` | Text and icons on sky |
| `--tp-sky-soft` | `#17324A` | `#B9D3EA` | Secondary text on sky. In light it equals `--tp-sky-ink`, because nothing lighter passes 4.5 to 1 on sky; use size and weight for hierarchy there |
| `--tp-sky-raised` | `#E8F5FF` | `#155487` | Hover and active row on sky (the active row is a pill) |
| `--tp-sky-rule` | `#1B8EE6` | `#1A5A8C` | Dividers on sky |
| `--tp-cream` (new) | `#FFF8EC` | `#FFF8EC` | The plane, small highlights on sky |
| `--tp-route-a` (new, replaces `--tp-teal` and `--tp-line-a`) | `#FF5E7E` | `#FF7A93` | Route pink: traveler 1 and the left route of the logo. A decorative fill |
| `--tp-route-a-ink` (new) | `#C4264D` | `#FF8FA5` | Pink when it is text or the only carrier of meaning |
| `--tp-route-b` (new, replaces `--tp-violet` and `--tp-line-b`) | `#FFCB2E` | `#FFD45C` | Route yellow: traveler 2 and the right route of the logo. A decorative fill |
| `--tp-route-b-ink` (new) | `#8A5A00` | `#FFD45C` | Yellow when it is text or the only carrier of meaning |
| `--tp-traveler-1` | `#FF5E7E` | `#FF5E7E` | One color per person on a trip, in the order they joined: avatar fill, their route on the map and the timeline, their "added by" highlight. Initials use `--tp-traveler-ink-1` to `-8` (at least 5.1 to 1 for all eight). |
| `--tp-traveler-2` | `#FFCB2E` | `#FFCB2E` | Traveler color 2 |
| `--tp-traveler-3` | `#2BBFAD` | `#2BBFAD` | Traveler color 3 |
| `--tp-traveler-4` | `#6A45F2` | `#6A45F2` | Traveler color 4 |
| `--tp-traveler-5` | `#FF8A3D` | `#FF8A3D` | Traveler color 5 |
| `--tp-traveler-6` | `#3DBE6B` | `#3DBE6B` | Traveler color 6 |
| `--tp-traveler-7` | `#0B6BC0` | `#0B6BC0` | Traveler color 7 |
| `--tp-traveler-8` | `#B92E86` | `#B92E86` | Traveler color 8 |
| `--tp-traveler-ink-1` | `#10283D` | `#10283D` | Initials on `--tp-traveler-1` |
| `--tp-traveler-ink-2` | `#17324A` | `#17324A` | Initials on `--tp-traveler-2` |
| `--tp-traveler-ink-3` | `#17324A` | `#17324A` | Initials on `--tp-traveler-3` |
| `--tp-traveler-ink-4` | `#FFFFFF` | `#FFFFFF` | Initials on `--tp-traveler-4` |
| `--tp-traveler-ink-5` | `#17324A` | `#17324A` | Initials on `--tp-traveler-5` |
| `--tp-traveler-ink-6` | `#17324A` | `#17324A` | Initials on `--tp-traveler-6` |
| `--tp-traveler-ink-7` | `#FFFFFF` | `#FFFFFF` | Initials on `--tp-traveler-7` |
| `--tp-traveler-ink-8` | `#FFFFFF` | `#FFFFFF` | Initials on `--tp-traveler-8` |
| `--viz-live` | `#00909a` | `#0f9aa2` | Chart series: live fare (Google Flights) |
| `--viz-cached` | `#a86a12` | `#c2851f` | Chart series: cached fare (Aviasales) |
| `--viz-agent` | `#5b47b0` | `#8a76e4` | Chart series: agent-found fare |
| `--viz-google` | `#c24472` | `#d9598a` | Chart series: Google price history |
| `--heat-1` | `#ceeff1` | `#083a3d` | Date-grid price steps, one hue; the most prominent step is the cheapest. Text on each step uses `--heat-ink-1` to `--heat-ink-5` |
| `--heat-2` | `#93d9dc` | `#00565a` | Date-grid price step 2 |
| `--heat-3` | `#4fbec4` | `#007378` | Date-grid price step 3 |
| `--heat-4` | `#009da3` | `#00a0a6` | Date-grid price step 4 |
| `--heat-5` | `#007980` | `#5ac8cd` | Date-grid price step 5 |
| `--heat-ink-1` | `#17324A` | `#E6F2FF` | Text on `--heat-1` |
| `--heat-ink-2` | `#17324A` | `#E6F2FF` | Text on `--heat-2` |
| `--heat-ink-3` | `#17324A` | `#E6F2FF` | Text on `--heat-3` |
| `--heat-ink-4` | `#0B1A2A` | `#0B1A2A` | Text on `--heat-4` |
| `--heat-ink-5` | `#FFFFFF` | `#0B1A2A` | Text on `--heat-5` |
| `--viz-band` | `#DCEFFF` | `#123A5C` | The typical-price band on the price chart; an alias of `--tp-brand-soft` |
| `--cat-culture` | `#5b47b0` | `#a07fe0` | Plan blocks and pins: sights, museums |
| `--cat-food` | `#e0621e` | `#d95926` | Food, nightlife |
| `--cat-outdoors` | `#0f9f76` | `#1a9f71` | Parks, hikes, beaches |
| `--cat-shopping` | `#2f86d8` | `#2869cc` | Shopping |
| `--cat-neutral` | `#55607a` | `#9ba7be` | Getting around, other |

Rules: chart series follow the price source, never its rank, so a partner's color can never signal "best". Activity groups are validated for color-blind separation; an icon and a text label always accompany the color. Traveler colors identify people, never status or price: a person's color always comes with their name or initials, and the old `--tp-rose` is gone.

The `--cat-*` tokens are color groups over the eight `itinerary_items.category` values of 03 (`item_category`): `--cat-culture` is `sights` and `museum`, `--cat-food` is `food` and `nightlife`, `--cat-outdoors` is `nature`, `--cat-shopping` is `shopping`, and `--cat-neutral` is `travel` (getting around) and `other`. Every item has exactly one category; the UI labels are Sights, Museums, Food, Outdoors, Nightlife, Shopping, Getting around and Other.

### 2.3 Measured contrast (WCAG 2.x ratios)

| Pair | Light | Dark |
|---|---|---|
| Ink on paper | 12.16 | 15.48 |
| Ink on card | 12.98 | 13.57 |
| Soft ink on paper | 5.59 | 8.29 |
| Soft ink on card | 5.96 | 7.27 |
| Brand on card (links, text buttons) | 5.33 | 8.05 |
| Brand ink on brand (primary button label) | 5.41 | 9.18 |
| Success on card | 5.22 | 6.95 |
| Warning on card | 4.36 (large text only) | 7.02 |
| Warning ink on card | 5.82 | 7.02 |
| Danger on card | 6.47 | 5.32 |
| Sky ink on sky | 4.98 | 9.63 |
| Sky soft on sky | 4.98 | 7.06 |
| Sky ink on sky raised (active row) | 11.90 | 6.99 |
| Route A ink on card | 5.54 | 7.13 |
| Route B ink on card | 5.83 | 10.87 |
| Traveler initials on traveler fills (lowest of the eight) | 5.14 | 5.14 |
| `--tp-edge` on card (control borders) | 3.74 | 4.17 |
| `--tp-edge` on paper | 3.50 | 4.76 |
| Ink on sunken (ticket stubs, chips) | 11.24 | 11.72 |
| Soft ink on sunken | 5.16 | 6.28 |
| Success on sunken | 4.52 | 6.00 |
| Brand on sunken | 4.61 | 6.95 |
| Route A ink on sunken (the "Added by" name on a stub) | 4.80 | 6.16 |
| Route B ink on sunken | 5.05 | 9.39 |
| `--tp-edge` on sunken (control borders on a stub) | 3.24 | 3.60 |
| `--heat-ink-1` on `--heat-1` | 10.83 | 11.00 |
| `--heat-ink-2` on `--heat-2` | 8.29 | 7.47 |
| `--heat-ink-3` on `--heat-3` | 5.97 | 4.97 |
| `--heat-ink-4` on `--heat-4` | 5.31 | 5.50 |
| `--heat-ink-5` on `--heat-5` | 5.19 | 8.85 |

The heat-ink rows are text on the date-grid steps. The sunken rows were added with the warm surfaces, because tickets carry text and controls on `--tp-sunken` stubs. Every new color pair added later must be checked with the same formula and recorded here. Body text needs 4.5 to 1, large text and control boundaries 3 to 1. The logo's sky `#2AA5FF`, `--tp-route-a` and `--tp-route-b` are decorative fills and never carry text in a color of their own.

### 2.4 Typography

Three bundled families (`@fontsource-variable`, subset to Latin): **Fredoka** (display: rounded and friendly, used only for names, codes and page titles), **Atkinson Hyperlegible Next** (body and labels), **Atkinson Hyperlegible Mono** (numbers and data). Everything that is not a name, a code or a title is Atkinson Hyperlegible Next. The app makes no request to Google Fonts (`googleapis` or `gstatic`); the fonts are the bundled OFL `@fontsource-variable` packages. CSS stacks, each beginning with the bundled variable family:

| Token | Value |
|---|---|
| `--tp-font-display` | `'Fredoka Variable', 'Fredoka', 'Nunito', 'Arial Rounded MT Bold', system-ui, sans-serif` |
| `--tp-font-body` | `'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', 'Atkinson Hyperlegible', system-ui, -apple-system, 'Segoe UI', sans-serif` |
| `--tp-font-mono` | `'Atkinson Hyperlegible Mono Variable', 'Atkinson Hyperlegible Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` |

| Role (Tailwind utility) | Family and axes | Size and line height | Use |
|---|---|---|---|
| `type-display` | Fredoka, weight 700, tracking -0.01em | 40 to 56 px, line 1.0 | Splash, empty hero, paywall headline |
| `type-title` | Fredoka, weight 600, tracking -0.005em | 30 px, line 1.1 | Screen title |
| `type-heading` | Fredoka, weight 600 | 20 px, line 1.2 | Section and card heading |
| `type-code` | Fredoka, weight 700, tracking 0.06em, uppercase | 24 to 48 px | Airport codes like a bag tag (LIS, JFK) (36 to 48 px on tickets and passes) |
| `type-label` | Atkinson Hyperlegible Next, weight 700, tracking 0.08em, uppercase | 11 px | Eyebrows, chip labels, table heads |
| Body large | Atkinson Hyperlegible Next 400 | 17 px, line 1.5 | Lead paragraphs, onboarding |
| Body (default) | Atkinson Hyperlegible Next 400 | 15 px (`0.9375rem`), line 1.55 | Default text |
| Body strong | Atkinson Hyperlegible Next 600 | 15 px | Row titles |
| Small | Atkinson Hyperlegible Next 400 | 13 px, line 1.45 | Captions, disclosure lines, timestamps |
| `type-data` | Atkinson Hyperlegible Mono, tabular figures | 13 to 15 px | Prices, credits, times, counts |
| Figure (hero) | Mono 700, tracking -0.03em | 32 to 48 px | Fare on a fare detail, credit balance |

Rules: sentence case everywhere except `type-label` and `type-code`, which are uppercase by style (the text in the DOM stays sentence case so screen readers do not spell it out). Never set body text below 13 px. Inputs are 16 px on iOS to stop zoom. All sizes are in `rem` so Dynamic Type and browser zoom work (section 9.3). Deck (present mode) uses the `deck-*` container-query utilities already in `index.css`.

### 2.5 Spacing

4 px base. Scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 (Tailwind `1, 2, 3, 4, 5, 6, 8, 10, 12, 16`). Screen gutter 16 px on phones, 24 px from 768 px, content max width 1120 px on web (720 px for reading screens such as notes and settings). Card padding 16 px (12 px when dense). Vertical rhythm between cards 12 px, between sections 24 px. Touch targets are at least 44 by 44 pt with at least 8 px between targets; a visually small control (a 32 px button) gets an invisible hit area to reach 44.

### 2.6 Radii

`--radius` is `0.75rem` (12 px). Derived: `sm` 8 px, `md` 10 px, `lg` 12 px, `xl` 16 px, `2xl` 20 px, `3xl` 24 px, `4xl` 28 px. Buttons are pills (full round). Inputs `lg` (12 px). Cards `xl` (16 px). Bottom sheets `2xl` on the top corners (20 px). Chips and avatars full round. The app icon keeps its own 22% corner.

### 2.7 Elevation

Hermi is flat: hierarchy comes from ground color, hairline rules and the sky band, not shadow.

| Level | Use | Light | Dark |
|---|---|---|---|
| 0 | Page ground | none | none |
| 1 | Cards, tickets, inputs | 1 px `--tp-rule` border (a ticket's outline), no shadow | same |
| 2 | Popovers, menus, toasts, the floating tab bar, the round map buttons | border plus `0 4px 16px rgb(23 50 74 / 12%)` | border plus `0 4px 16px rgb(0 0 0 / 40%)` |
| 3 | Bottom sheets, dialogs, the map sheet | `0 -8px 32px rgb(23 50 74 / 18%)`, scrim `rgb(23 50 74 / 45%)` | lighter surface (`--tp-sunken` top edge 1 px), scrim `rgb(0 0 0 / 60%)` |

### 2.8 Motion

| Token | Value | Use |
|---|---|---|
| `--motion-fast` | 120 ms | Press, hover, pin scale, toggle |
| `--motion-base` | 200 ms | Fades, chip state, section pill |
| `--motion-slow` | 320 ms | Sheets, page transitions |
| `--ease-out` | `cubic-bezier(0.22, 0.61, 0.36, 1)` | Default (same curve as the route draw-on) |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Reorder, layout shifts |
| `--ease-touchdown` (renamed from `--ease-stamp`) | `cubic-bezier(0.2, 0.9, 0.3, 1.2)` | Touchdown only (`touchdown`, 280 ms) |

Signature motions: **touchdown** (a run's outcome ticket stub settles from 1.15 to 1 and fades in, like a plane landing), **route draw-on** (a route's dots appear in order with a 45 ms stagger and the plane glides to the end, at most 1.8 s, on the splash, a new trip and a finished run) and the **nav progress bar** (a 1.1 s sweep that starts after 150 ms so quick loads never flash it). Touchdown and route draw-on are new; they replace the old repo's stamp press and guilloche draw-on with the same timings. Everything else is a short fade or a slide. Reduced motion: touchdown and draw-on render at their final state, sheets fade instead of sliding, the progress bar becomes a static 60% bar, no parallax, no auto-advancing carousels.

### 2.9 Route pattern usage rules

The route pattern (`components/brand/route-pattern.tsx`, new, replacing `guilloche.tsx`; deterministic from a seed) is the signature: two or three dotted routes that start at their own origin dots, curve across the space and meet at a plane, echoing the logo. It is used sparingly and never under text that needs to be read.

1. **Seed** is the trip's UUID, so a trip keeps its pattern on every device. Non-trip uses seed from a fixed string ("hermi-splash", "hermi-paywall"). On a trip, the routes take the colors of its first travelers.
2. **Where it appears:** splash and onboarding hero (full pattern, animated once), the trip card ticket (a short route between the airport codes), trip maps and the plan timeline spine (rule 9), the trip overview header band where a screen has no map, paywall header (static), present-mode title and closing slides, empty states (two routes only, static, 12% opacity), export PDF cover, share-link page.
3. **Where it never appears:** behind body text, inside inputs, on lists of more than three rows, on partner cards, on error states, in the tab bar.
4. **Color:** `--tp-route-a` and `--tp-route-b` (later travelers in their traveler colors); the plane in `--tp-cream` on sky and in `--tp-ink` on paper. On sky surfaces use the `.on-sky` class, which draws at full color; on paper and sheet the pattern sits at 35 to 50% opacity.
5. **Dots:** round, never dashes; 6 to 10 px across at display size with a gap of 1.2 times the dot; at most 80 dots per pattern; each route's start dot is 1.5 times larger, as in the logo.
6. **Decorative:** `aria-hidden="true"`, `focusable="false"`, no title. Never the only carrier of meaning.
7. **Animation:** route draw-on plays once per session per surface and never on scroll. Skipped under reduced motion.
8. **Performance:** dot positions are memoized per seed; at most two animated patterns on screen; static SVG on devices that report low power mode.
9. **Trip maps.** Trip screens on phones open on a calm illustrated map (4.22) that replaces the header band there. The travelers' routes run across it in their colors, drawn at full color like on sky, with numbered pins, price pins on Stays and the plane in a sky disc; the content sits in a bottom sheet over it (4.19). The plan timeline spine is the same twin routes, pink and yellow, drawn between the numbered stops (4.7). The routes stay clear of the place labels, and every pin has a list equivalent.

## 3. Logo usage

Files live in `../brand/` (see [../brand/BRAND.md](../brand/BRAND.md)): `hermi-logo.svg` (mark plus wordmark on light), `hermi-logo-dark.svg`, `hermi-mark.svg` (the app-icon tile), `hermi-wordmark.svg`, `hermi-app-icon.svg` and `hermi-app-icon-1024.png`.

The mark is an H on a sky rounded tile (`#2AA5FF`). Its two posts are dotted routes, pink (`#FF5E7E`) on the left and yellow (`#FFCB2E`) on the right, each with a larger start dot at its foot, and its crossbar is a cream (`#FFF8EC`) plane flying right: two travelers, one trip. The wordmark is "Hermi" in Fredoka SemiBold, ink `#17324A` on light and `#E6F2FF` on dark.

| Context | Use |
|---|---|
| Splash, sign-in, paywall header | Full lockup (mark plus wordmark), centered, mark 72 px |
| Web sidebar (sky) | Mark 32 px and wordmark 17 px in `--tp-sky-ink`; the tile merges into the sky, and the dots and plane carry the mark |
| Web top bar on light | Light lockup, mark 28 px |
| Navigation bar on iOS | No logo; the screen title is used. Trips home may show the 28 px mark (no wordmark) left of the large title |
| Favicon, app icon | `hermi-mark.svg` (also the 16 and 32 px favicon) and the 1024 px PNG, no transparency, no extra rounding (iOS masks it) |
| Email, PDF cover, share page | Full lockup above a sky band with the route pattern |
| Loading | Mark with its route dots appearing from the start dots up and the plane sliding in (route draw-on rule; static under reduced motion) |

Rules:
1. Clear space on every side equals the diameter of a start dot (about 14% of the mark width, minimum 8 px).
2. Minimum sizes: mark 24 px in the UI (the 16 and 32 px favicons use the same file, where the dots merge into a pink and a yellow post), lockup 96 px wide. Below 24 px use the mark only.
3. Never recolor or swap the routes (pink left, yellow right), rotate (the plane points right), stretch, outline, add shadows, or place the mark on busy photography without its tile. On dark grounds use the dark lockup; the tile stays sky.
4. Never use the logo as a button or a bullet. The wordmark is not set in the UI font; always use the file.
5. The app has one name in the UI, "Hermi", in sentence-case copy. No "Hermi AI" or "Hermi Pro" as a product name except "Hermi Plus" and the plan names in the price table.
6. The existing in-repo rosette `BrandMark` and "Trip Planner" text in `logo.tsx` are replaced by the Hermi mark and wordmark, and `guilloche.tsx` is replaced by `route-pattern.tsx` (section 2.9).

## 4. Component library

For how a component looks, `design/hermi.css` and the mockups in `design/screens/` win over the prose of sections 4 and 6; the token values in section 2 still win over both. A component block the kit lacks is added to `hermi.css` and `components.html` by the ticket that needs it, in the same pull request.

Base: shadcn/ui on Radix, already in the Trip Planner's `frontend/src/components/ui/` and carried to `apps/web/src/components/ui/` (button, badge, card, dialog, alert-dialog, dropdown-menu, input, textarea, label, separator, sheet, skeleton, sonner, switch, tabs, tooltip). Additions are named in each entry. Conventions: every component supports light and dark through tokens, has a visible focus ring (`--ring`, a 3 px solid outline with a 2 px offset: `outline: 3px solid var(--ring); outline-offset: 2px`, as in `hermi.css`; a 50 percent ring such as shadcn's `ring/50` failed the 3 to 1 rule of section 9.1 and is not used), has a minimum 44 pt hit area on touch, and never relies on hover for information.

State vocabulary used below: default, hover (web), pressed, focus, disabled (50% opacity, not removed from focus order when it explains itself through a tooltip or helper), loading, error, selected.

### 4.1 Button

| Variant | Look | Use |
|---|---|---|
| Primary (`default`) | `--primary` fill, `--primary-foreground` text | One per screen or sheet |
| Secondary | 1.5 px `--tp-edge` border, `--tp-sheet` fill (`.h-btn--secondary` in `hermi.css`, the kit wins for looks). Maps to the shadcn `outline` variant; the shadcn `secondary` variant is not used for buttons | Supporting action beside a primary |
| Outline | Border `--tp-edge`, transparent fill. The shadcn `outline` variant with a transparent fill; no kit class yet (added to `hermi.css` with the ticket that needs it) | Neutral action, "Not now" on paywalls |
| Ghost | No fill, `--muted` on hover and press | Toolbar and inline |
| Destructive | `--destructive` at 10% fill, danger text | Delete, remove, leave |
| Link | Brand text, underline on hover and always underlined in body copy | Inline navigation |
| Partner | Outline with an external-link icon and the partner name, never brand-filled | Affiliate "Book on <partner>" (see 4.13) |

Sizes: `sm` 28 px, default 32 px on web, `lg` 44 px on touch (all primary actions on phones are 48 px tall, full width in sheets). Icon buttons are square with an `aria-label`. States: pressed translates 1 px down (existing `active:translate-y-px`) and on iOS scales to 0.98; loading replaces the label with a 16 px spinner and keeps the width, sets `aria-busy`, and blocks repeat taps; disabled explains itself ("Add a destination first") in helper text, not only a dimmed button. Labels are plain verbs: Save, Add, Invite, Book, Restore purchases.

### 4.2 Inputs

Text input, textarea, select (Radix), combobox (existing `components/common/combobox.tsx`, used for airports and destinations), date and date-range field, stepper (travelers, nights), switch, checkbox, radio group, segmented control, search field, money field.

| Part | Rule |
|---|---|
| Label | Always visible above the field, `type-label` is not used for form labels (sentence case, 13 px, weight 600) |
| Field | 44 px tall on touch, 16 px text, `--tp-sheet` fill, 1 px `--tp-edge` border, radius `lg` |
| Helper | 13 px soft ink below, for format and limits ("Add the code from your email") |
| Error | Border `--tp-danger`, danger icon plus text below ("That code is not right. Check the email we sent and try again."), `aria-invalid` and `aria-describedby`, focus moves to the first error on submit |
| Disabled | 50% opacity with helper saying why |
| Money field | Mono figures, currency code as a fixed suffix, decimal keyboard, stores minor units |
| Airport combobox | Type to search by city or code; results show the code in `type-code`, the city, and distance from the home airport; "Nearby airports" chip row; results are sorted by distance, never by anything commercial |
| Date range | Sheet calendar on phones, popover on web; "Flexible dates" toggle opens a window picker (earliest departure, latest return, trip length) |
| Switch | 51 by 31 pt on iOS; label on the left, switch on the right, whole row is the hit area |

### 4.3 Cards

`Card` is `--tp-sheet` fill, 1 px `--tp-rule` border, radius `xl`, padding 16 px. Variants: default, interactive (whole card is a link, pressed fills `--tp-sunken`, chevron on the right), selected (2 px `--primary` border plus `--tp-brand-soft` wash), quiet (no border, `--tp-sunken` fill; used for hints and disclosure blocks), and locked (content blurred 6 px with a lock icon and an unlock button, used only where a paywall in 6.27 allows a preview). A card never has more than one primary action.

### 4.4 Trip card

Shown on Trips home. A boarding-pass ticket (4.21): a notched card with a round-dot tear line and a tinted stub. The body has the destination name in `type-heading`, dates in `type-data` ("12 to 19 Mar"), the airport codes in `type-code` with a short route (seeded by trip id, in the first travelers' colors) and a plane between them, and 11 px uppercase labels over mono values for nights, travelers (stacked avatars) and flight or fare. The stub carries a status tag (Planning, Booked, Happening now, Past) and a row of quiet facts: cheapest fare with age ("from $412, 3 h ago"), next item ("Day 1: Alfama walk"), and changes by others since the last visit. Look: [design/components.html](design/components.html). Variants: upcoming, in progress (brand-soft wash, "Day 3 of 7"), past (muted, "Archived on 4 Apr"), shared with me (owner avatar and role chip), locked by limit (read-only chip "Limited", never hidden). States: loading skeleton (ticket body, tear line and stub), offline (shows a "Saved offline" cloud-check icon), pressed, focus. Swipe left reveals Archive; long press opens the context menu (Open, Share, Archive, Delete).

### 4.5 Fare chip

A compact pill that states one fare: price in mono, route code pair in `type-code` at 13 px, and a source tag. Anatomy: `[LIS  $412  Google, 3 h ago]`. Source tags (existing `source-tag.tsx`): Live (teal dot), Cached (amber dot), Agent (violet dot), Google history (rose dot); the dot color always pairs with the word. Trend glyph: arrow down with "Down $42" in success, arrow up with "Up $30" in warning-ink, flat dash glyph replaced by the word "No change". States: default, selected (brand-soft), stale (age over 24 h adds a clock icon and "Check again"), unavailable ("No fare found"). Tapping opens the fare detail. The chip never says "best", "cheapest" or "deal" unless the value is the computed minimum of the shown set, and then it says "Lowest in this list".

### 4.6 Price chart

Recharts line and band chart in a 16:9 card (180 px tall on phones). Series: live, cached, agent and Google history, in the `--viz-*` colors with distinct marker shapes and a legend that doubles as a toggle. The typical-price band uses `--viz-band`. Y axis has currency and no more than five ticks; x axis has dates. Interactions: tap or drag to place a scrubber with a readout ("Tue 14 Oct, $412, cached, seen 6 h ago"); long press pins a point; a "Fare fell $42 since Tuesday" callout sits above. Phones show a sparkline in the list and the full chart on the fare detail. Accessibility: the chart has a text summary ("Lowest $398 on 3 Oct, now $412, up $14 this week"), a visually hidden data table, and arrow keys step the scrubber. States: loading (skeleton with axis), empty ("No fares yet. Checks run daily."), one point ("We need two checks to draw a line"), error ("We could not load this chart. Pull down to try again."), offline ("Showing the last saved data from 3 Oct").

### 4.7 Calendar

Two modes on the Plan section. **Month and range** (`react-day-picker` style grid, used in create trip and flexible dates): 44 pt cells, today ringed, selected range filled `--tp-brand-soft` with `--tp-brand` end caps. **Day timeline** (FullCalendar `timeGridDay` and `listWeek`, themed through the `--fc-classic-*` tokens already in `index.css`): events show as tinted blocks of their activity group color with icon and label, times in mono. The Days view on phones draws the same day as a timeline whose spine is the twin pink and yellow dotted routes (2.9): each stop has a numbered pin in its activity group color (the same number as on the trip map), the time sits in mono at the left, each item is a ticket (4.21) with an "Added by" stub, and the travel time to the next stop is written on the spine ("11 mi, 25 min drive"). Look: [design/components.html](design/components.html). On phones drag-resize is off; long press opens "Move to..." (sheet with day and time). Web allows drag and drop between days, with a 409 conflict toast "Sam changed this just now. Your change was not saved. View their version." States: loading skeleton rows, empty day ("Nothing planned. Add a place or ask for a draft."), offline read-only banner, dragging (lifted with elevation 2).

### 4.8 Day card

One per day in the Plan list. Header: "Day 3", date in mono, a one-line theme the person wrote or accepted ("Sintra by train"), total walking or transit time if known. Body: ordered items with time, icon in the group color, title, optional place photo, and an "Added by" stub on every item when the trip has two or more travelers (a solo trip hides it). The look follows 4.7: the header has a large Fredoka day number with 11 px uppercase labels over mono values (Day, Date), and each item is a ticket on the twin-route spine, with the "Added by" avatar and name on its stub in the person's traveler ink color. Look: [design/components.html](design/components.html). Footer: "Add" and "Draft this day (1 credit)". Variants: collapsed (first two items plus "3 more"), expanded, drop-target (dashed `--tp-edge` border while dragging), today (brand-soft header), empty. Items are ordered by start time, then by `sort_order` (a number on each item, `itinerary_items.sort_order`; untimed items keep the order the person sets). Reorder by drag handle on web, "Move up" and "Move down" actions plus drag on touch (for VoiceOver, custom actions); each reorder or move writes `sort_order` through `POST /trips/{id}/days/{day}/reorder` or `POST /items/{id}/move`. Booked items show a small ticket stub with a check; unbooked bookable items show the "Tickets" partner link only on explicit expand (see 4.13).

### 4.9 Place card

Used in search, saved places, ideas and Discover. Photo 16:10 (or category icon tile when no photo), name, category chip, distance from the trip center, opening-hours status ("Open until 18:00"), rating when a licensed source provides it, a save heart, and an "Add to day" button. Attribution stays visible (Geoapify, Wikipedia). Variants: result row (72 px, thumbnail left), full card, compact pin popup (map). Sorted by relevance and distance only, and a sort label is always shown ("Sorted by distance"). No partner content in the list; "Tickets" or "Book a table" appears on the detail view only, through 4.13. States: loading skeleton, no photo, closed now, saved, added to Day 2.

### 4.10 Lodging card with votes

Photo strip (swipe, up to 6 photos, page dots), name, area, price per night and total for the trip in mono with currency, per-person price for the party, bedrooms, source chip ("Pasted link", "From Stay22 search", "Added by hand"), status chip (Shortlisted, Booked, Rejected), and the vote row. The card is a ticket (4.21): the body has the photo, name, source label with rating, and the price per night in large mono with the total and the per-person price beneath it; below the tear line a stub carries the vote row, with the vote summary on the left and one vote chip per traveler on the right. Look: [design/components.html](design/components.html). **Votes are hearts, nothing else:** one row of vote chips, one per traveler, each an avatar plus a heart (there is no down vote and no "no" mark). Pressed means the heart is filled in that traveler's color and the chip is brand-soft with a brand outline; not pressed means an outline heart. The viewer's own chip is a 44 pt heart toggle ("You love this" with `aria-pressed`) that sends `{ voted: true }` or `{ voted: false }` to `PUT /lodging/{id}/votes/me`. Counts read "3 of 4 like this" (hearts over travelers), names on tap. Variants: shortlist card, compare column (2 to 4 columns, horizontal scroll with a sticky label column), booked (touchdown on the status), rejected (collapsed). Buttons: "Open" always opens the user's saved URL exactly as pasted; "Book via partner" is a separate labeled button only when a program is approved for that host and never for Airbnb (see 4.13). States: no price yet ("Add a price to compare"), price older than 7 days ("Price from 12 Sep, check the site"), locked "later" list on Free after 8 saved (read and export still work), conflict ("Sam also edited this").

### 4.11 Credit cost chip

A pill shown on every button that spends credits. Anatomy: coin glyph, number in mono, the word "credit" or "credits" (for screen readers: "costs 8 credits"). Variants: cost (neutral, `--tp-sunken`), free from cache ("1 credit, from shared cache", success dot), insufficient (warning-ink with "You have 3"), and zero ("Free"). Placement: right side inside the action button, or directly under a button on a sheet. A confirm sheet is required at 6 credits or more (research, agent run), shows the balance before and after, and never auto-confirms. A balance pill ("27 credits") sits in the AI sheet header and Account; tapping it opens Subscription and credits. Wording rules are in 7.3.

### 4.12 Badge and chip set

Badge (status), chip (filter), role chip (Owner, Editor, Viewer), source tag, tier chip (Free, Plus, Pass), fare trend chip, "New" (only for changes by others since last visit, never for marketing). Height 24 px, label in 12 px weight 600, never ALL CAPS except `type-label` badges. Chips that filter are 44 pt tall targets with a 32 px visual.

### 4.13 Affiliate offer card with disclosure line

The only surface for partner links besides the labeled buttons on the lodging and fare screens. Anatomy, top to bottom: an eyebrow `type-label` naming the category and why it is here ("Stays near your Day 2 plan"), the title, a one-line reason grounded in the user's data ("You land in Lisbon at 21:40"), the basis of the price ("From $58 a night, checked 12 Sep, via Stay22"), a row of two equal-weight actions, and the disclosure line.

```
+--------------------------------------------------+
| TRANSFER                                         |
| Airport to your stay                             |
| You land in Lisbon at 21:40 on Fri 12 Mar.       |
| From $24 for 2 people, checked today, via        |
| Welcome Pickups.                                 |
|                                                  |
| [ Book on Welcome Pickups ]  [ I will arrange ]  |
| We earn a commission if you book here.           |
+--------------------------------------------------+
```

Rules, applied to every instance:
1. **Disclosure line** is 13 px `--tp-ink-soft`, always visible directly under the button row, never truncated, never in a tooltip, never below a fold inside the card. Text is exactly: "We earn a commission if you book here." On UK and EU storefronts an "Ad" tag sits in the eyebrow row. Where a partner requires its own line (Booking.com), it is added after ours.
2. **Both routes.** A non-affiliate route is always present: "Search on the airline's site", "Open your saved link", "I will arrange this myself", "Not needed".
3. **Quiet.** Outline buttons, no brand fill, no partner logos larger than 16 px, no badges like "Hot" or "Popular", no timers, no stock counts.
4. **One per screen view**, except lists the user asked for (Stays shortlist, Before you go checklist). Never inside AI output, never beside a paywall, never during present playback, never offline.
5. **Sort statement** on any list of offers ("Sorted by price, lowest first"). Never sorted by commission.
6. **Opens** through `/go/{click_id}` in the in-app Safari view (`SFSafariViewController`, visible address bar, Done button), so the person always sees where they are.
7. **Hide switch.** Settings, How we earn money, "Hide booking links" collapses every card into one plain "Open on partner site" text link. Disclosure still shown.
8. **Flag.** Each partner has a kill switch; a disabled partner renders the non-affiliate route only.

### 4.14 Paywall sheet

**Mockup:** [screens/07-paywall.html](design/screens/07-paywall.html) <img src="design/png/07-paywall.png" width="260" alt="Paywall sheet in light mode: a sky header with a route pattern, two plan tickets with their prices on the stubs, and equal-weight purchase and Not now buttons"> <img src="design/png/07-paywall-dark.png" width="260" alt="The same paywall sheet in dark mode">

A bottom sheet on phones (full height is not used) and a centered 480 px dialog on web. Structure and rules are in section 8. Parts: a header on sky with a static route pattern and the benefit headline for the trigger, a two to three line list of what this gives on this trip, the offer list (up to three options, annual pre-selected where it is a subscription), with each plan drawn as a ticket (4.21): the plan name and what it covers in the body, the price and period on the stub, and the selected plan in the selected card style of 4.3 (look: [design/components.html](design/components.html)), the primary purchase button, the "Not now" button (equal size), a legal row (price, renewal, cancellation, Terms, Privacy), and "Restore purchases". States: loading prices (skeleton rows, buttons disabled, "Not now" enabled), store unavailable ("We cannot reach the App Store. Check your connection and try again. You can keep planning for free."), purchase pending ("Waiting for approval from your family organizer"), success (touchdown on a ticket stub reading "Plus is on", sheet closes, the blocked action resumes), cancelled (no error, sheet stays), error.

### 4.15 Toast

`sonner`, bottom center on web, above the tab bar on iOS (8 px gap), elevation 2, 4 second default, 8 seconds with an action, persistent for errors that need a choice. Variants: success (check icon), info, warning, error (with a "Try again" action), undo ("Day 2 deleted. Undo"), credit ("Used 1 credit. 11 left"). Announced politely to screen readers (`role="status"`), errors with `role="alert"`. Max two visible, newest on top. Never used for paywalls or for anything the person must read before continuing.

### 4.16 Empty state

A centered block: a static route pattern (two routes only, 12% opacity) behind a 48 px line icon, a `type-heading` line saying what lives here, one sentence saying what to do, and one primary button. Optional quiet secondary link. Never a blank screen, never an illustration of people. Copy pattern: "No stays yet" / "Paste a link or search to start a shortlist." / [Add a stay]. Variants per screen are in section 6.

### 4.17 Error state

Inline block (in a card region) or full screen. Anatomy: danger icon, a plain statement of what happened, how to fix it, a primary retry, and a secondary path ("Keep planning offline", "Contact support"). Variants: network ("You are offline. Your trip is saved on this phone. Changes will sync when you reconnect."), server ("Something went wrong on our side. We are looking into it. Try again in a minute."), not found ("This trip is not available. It may have been deleted or you may not have access."), permission ("You can view this trip but not edit it. Ask Sam to make you an editor."), limit ("You have used this month's 12 credits. They renew on 1 Nov."), conflict (409, "Sam changed this while you were editing. Review their version."). Error text includes a request id in small mono ("Reference 7F3A") for support. Full-screen errors never trap the user: Back and Home always work.

### 4.18 Skeletons

`Skeleton` (existing): `--tp-sunken` base with a slow 1.4 s shimmer at 40% contrast (static under reduced motion). Shapes match the final layout exactly (trip card ticket with its stub; fare chip row; chart frame with axes; day card with three rows; lodging card with photo block) so the layout does not jump. Show after 150 ms delay (same rule as the nav progress bar). Never show a spinner on a content area; spinners are for buttons and pull-to-refresh only. After 8 seconds of loading, replace with the error state.

### 4.19 Bottom sheet

`vaul` on phones (Radix `Sheet` and `Dialog` on web). Detents: medium (50% height), large (92% height, leaves the status bar visible). Grabber 36 by 5 px, scrim `rgb(23 50 74 / 45%)`, swipe down or tap scrim to dismiss (disabled while a purchase or a spend confirmation is in progress). Content scrolls inside; the primary button is sticky at the bottom above the safe area. Focus moves to the sheet title on open and back to the trigger on close; `aria-modal`; the page behind is inert. Keyboard: the sheet lifts with the keyboard and the focused field stays visible. Web converts to a 480 px dialog, or a right-hand 420 px panel for add and edit forms.

**Map plus sheet.** On trip screens on phones the sheet is the page itself, not a dialog: the screen opens on the trip map (4.22) and the content sits in a persistent bottom sheet over the map's lower edge (20 px top corners, level 3, grabber), with the section strip at the top of the sheet (5.2). It has no scrim and no focus trap, the modal rules above apply only to sheets opened over it, and the round back and menu buttons on the map stay reachable. Look: [design/components.html](design/components.html).

### 4.20 Tab bar

iOS bottom tab bar, a floating pill: 58 pt tall, inset 12 pt from each side and floating above the home indicator (its bottom edge is 22 pt from the screen edge in the mockups), `--tp-sheet` fill, a 1 px `--tp-rule` border, fully rounded ends and level 2 elevation (2.7); content fades out behind it so lists never run into it. Four tabs: Trips, Discover, Activity, Account. Icons are 22 px lucide line icons (`Luggage`, `Compass`, `Bell`, `CircleUser`), label 11 px weight 600 beneath (labels always shown). Active tab: a `--tp-brand-soft` capsule behind a brand-colored icon and label; inactive `--tp-ink-soft`. Look: [design/components.html](design/components.html). Badge: a 16 px brand dot with a number up to 9, then "9+"; the badge has an accessible name ("Activity, 3 new"). Tapping the active tab scrolls to top, then pops to root. The bar hides while a full-screen sheet or present mode is open and never hides on scroll. Web at 768 px and wider shows the sidebar instead (section 5.3).

### 4.21 Other shared components

| Component | Notes |
|---|---|
| Avatar and avatar stack | 28 px default, initials on the person's traveler color (`--tp-traveler-1` to `-8`, 2.2), each passing 4.5 to 1 with its initials; stack overlaps 8 px and shows "+3" |
| Segmented control | 32 px visual, 44 pt target, iOS style on phones; used for view toggles (List, Map) |
| Progress and run timeline | Steps with a dot, label, elapsed time in mono; current step pulses (static under reduced motion) |
| Ticket and ticket stub | Trip facts that belong together (a trip, a stay, a plan item, a fare, a plan on the paywall) are a boarding-pass ticket: a notched card with a round-dot tear line and a tinted stub that carries the status, the votes or the action. Airport codes are `type-code`, and labels are `type-label` over mono values. The status tag (Done, Stopped, Failed, Booked, Planning) is a small stub itself: notched left edge, round-dot perforation; it lands with `touchdown`; text plus icon, never color only. Look: [design/components.html](design/components.html) |
| Evidence label | One line in small text, "Found on theflightsite.com, checked 12 Sep", on every AI-found fact (fares, findings, notes, slides, share pages, PDF). The whole line is a link to the source. When the source fails to load it reads "Source not checked since 12 Sep"; with several sources it shows the first and "and 2 more". Findings and checked plan items whose date is more than 14 days old add an amber "May be out of date" chip and a "Recheck" button (6.39); fares keep their own age tag instead. Never on Wikipedia text or notes people wrote |
| Verdict chip | Used in Verify this plan (6.38): a 24 px chip with an icon and a word, never color alone. Green check "Confirmed", amber triangle "Differs" or "Partly confirmed", red cross "Could not find it", grey dash "Not checked". Colors use the success, warning, danger and muted ink tokens from 2.1 and meet 4.5 to 1 with their words |
| Sync indicator | One line of text under the destination name in the hero pass on Overview, and a small chip on the map header, centered between the round back and menu buttons, on sections with no hero pass (Flights, Stays, Plan, Group): "Synced 12 s ago", with a small refresh icon. States: Syncing (icon turns, static under reduced motion), Synced N s ago (seconds under a minute, then "3 min", then the time), "Offline, 3 edits waiting", "Could not sync, retrying". Tap runs a sync now. The text updates every 5 seconds; screen readers hear state changes only (polite), never the ticking seconds |
| Status banner | Uses the Banner pattern: "Fares are delayed right now. Saved trips still work." with "Service status" linking to the status page. Shown only when the public status summary says a component is degraded, never for one person's failed request |
| Evidence row | Favicon, page title, the evidence label, one-line quote, "Open source" link |
| Map | MapLibre with the themed pins from `index.css` (`tp-map-pin`, numbered, group colored); attribution stays visible; "Open in Apple Maps" and "Open in Google Maps" actions |
| Banner | Full-width strip under the header for state: offline, limited trip, pending deletion, service degraded. One at a time, most urgent wins |
| Stepper list | Checklist rows with a check, title, reason, three actions (see 6.20) |
| Context menu and action sheet | iOS action sheet on phones, dropdown on web; destructive last, red text plus icon |
| Pull to refresh | A custom route-and-plane spinner is not used; use the native-style spinner with "Updated just now" text |

### 4.22 Trip map header

The top of every trip screen on phones, and of Trips home: a calm illustrated map about 190 px tall that replaces the header band. It carries the travelers' routes (2.9), numbered pins, place labels, price pins on Stays and the plane in a sky disc, with a round 44 px back button and a trip menu button floating on it at level 2 (2.7); the content sheet (4.19) overlaps its lower edge. The map is context: every pin has a list equivalent, no task needs it, and attribution stays visible wherever it shows licensed map data (the Map row in 4.21). Dark mode darkens its land and water (section 12). Look: [design/components.html](design/components.html).

## 5. Navigation and information architecture

### 5.1 Sitemap

```
Hermi
+-- Trips (tab 1, web: sidebar "Trips")
|   +-- Trips home (upcoming, in progress, past, shared with me)
|   +-- Create trip
|   +-- Import a trip  (entries for TripIt, Tripsy, Wanderlog, Google Calendar, Google Maps;
|   |                   calendar file or link, pasted confirmations, Maps list, pasted places)
|   +-- Verify a plan  (paste a plan from ChatGPT, Gemini, Layla or Mindtrip)
|   +-- Trip workspace  /trips/:tripId
|       +-- Overview   (summary, next steps, Before you go, cost so far)
|       +-- Flights    (routes, alerts, booked-fare watch, fare detail, Book this fare)
|       +-- Stays      (shortlist, compare, vote, import)
|       +-- Plan       (day list, calendar, map, add item, ideas)
|       +-- Group      (people: travelers, members, invite)
|       +-- Present    (full screen deck, share)
|       +-- Notes and evidence (reached from Overview; notes also attach to days, items and stays;
|       |                      freshness flag and recheck)
|       +-- Plan checks (Verify this plan results, from the trip menu)
|       +-- Agent runs (from Flights, Plan and the AI sheet; run detail)
|       +-- Trip settings (members, AI on or off, Trip Pass status, calendar feed,
|                          offline download, export, archive)
+-- Discover (tab 2)  destination ideas, cheap fares from your airport
+-- Activity (tab 3)  alerts, changes by others, agent results, invites, referral rewards
+-- Account (tab 4)  profile, subscription and credits (with Cancel subscription), invite friends,
                     import a trip, settings, how we earn, how billing works, service status,
                     install on Android, notifications, export and delete, help

Public web pages (no account, no tab bar, marketing shell)
+-- /samples and /samples/:slug   sample trips
+-- /s/:shareId                   shared-trip page
+-- /vs/:competitor               comparison pages
+-- /r/:code                      friend's code landing
+-- /how-we-earn                  how we earn (partners and rules)
+-- /billing                      how billing works
+-- /install/android              Android install guide
+-- status.hermi.world            public status page (hosted outside the app)
```

Public web pages use the marketing shell described in 6.34 and sit outside the app shell. The trust pages and the Android guide are described in 6.40 and 6.42.

Notes and evidence have no tab of their own. Notes live in Overview (trip notes) and on each day, item and stay; the Evidence list lives on every agent result and in the Notes screen reachable from Overview. Agent runs have no top-level destination at launch (they are an action, not a place); the list of runs for a trip is Overview, "AI activity".

### 5.2 iOS and phone navigation

- Four bottom tabs (4.20) in a floating pill bar, 58 pt tall and inset 12 pt: **Trips, Discover, Activity, Account**. The tab bar shows on every screen except present mode, full-screen sheets and the paywall.
- Inside a trip the tab bar stays (Trips is active). The screen opens on the trip map header (4.22) with the content in a bottom sheet over it (4.19), and a **section strip** sits at the top of the sheet: six scrollable pills, the active one filled with ink, in this order: **Overview, Flights, Stays, Plan, Group, Present**. In Phase 1 Group holds the people list and the invite flow (6.21). The strip is sticky, scrolls horizontally if the text size is large, and keeps the last visited section per trip. "Present" does not open a section page; it opens the full-screen deck.
- Navigation bar: large title on root screens (Trips, Discover, Activity, Account). Inside a trip the map header replaces the inline title bar: a round back button (accessible name "Back to Trips") and a trailing "..." menu (Share, Trip settings, Export) float on the map.
- Swipe from the left edge goes back (native). Modals are bottom sheets; full-screen modals only for create trip, present mode and onboarding.
- Deep links: `https://hermi.world/i/<token>` (invite), `/trips/<uuid>`, `/trips/<uuid>/fares/<route>`, `/s/<shareId>` (read-only), `/r/<code>` (friend's code). Cold start from a link lands on the target with Back going to Trips.
- State restoration: last tab, last trip and section are restored on launch; a scroll position is restored per section.

### 5.3 Web layout

| Width | Layout |
|---|---|
| 1200 px and up | Sky sidebar 248 px (`--tp-sky`; deep sky in dark mode): logo, trip switcher, **Trips, Discover, Activity, Account**, and under the current trip the six sections. Main content max 1120 px. Optional right rail 320 px (AI sheet, evidence, agent run) |
| 768 to 1199 px | Sidebar collapses to a 72 px icon rail with tooltips; right rail opens as an overlay panel |
| Under 768 px | Sidebar is hidden; bottom tab bar and section strip as on iOS. Dialogs become bottom sheets |

The sidebar trip switcher lists the five most recent trips and "All trips". Keyboard shortcuts on web: `g t` Trips, `g p` Plan, `n` new item, `/` search, `?` shortcut list; all are optional and never the only way to act.

### 5.4 Route map

| Route | Screen |
|---|---|
| `/welcome` | Splash and onboarding |
| `/sign-in` | Sign in |
| `/` | Trips home |
| `/trips/new` | Create trip |
| `/import`, `/trips/:tripId/import` | Import a trip |
| `/trips/:tripId/verify`, `/trips/:tripId/verify/:verificationId` | Verify this plan, plan check result |
| `/trips/:tripId` | Overview |
| `/trips/:tripId/flights`, `/flights/:routeId/fare/:fareId` | Flights, fare detail |
| `/trips/:tripId/stays`, `/stays/compare`, `/stays/add` | Stays |
| `/trips/:tripId/plan`, `/plan/:day`, `/plan/map` | Plan |
| `/trips/:tripId/group` | Group (people) |
| `/trips/:tripId/notes` | Notes and evidence |
| `/trips/:tripId/calendar` | Calendar feed (sheet) |
| `/trips/:tripId/runs/:runId` | Agent run |
| `/trips/:tripId/checklist` | Before you go |
| `/trips/:tripId/present` | Present mode (outside the app shell) |
| `/discover`, `/activity` | Discover, Activity |
| `/account`, `/account/subscription`, `/account/invite`, `/account/settings/*` | Account and children |
| `/i/:token` | Invite landing |
| `/s/:shareId` | Shared-trip page (public) |
| `/samples`, `/samples/:slug` | Sample trips (public) |
| `/vs/:competitor` | Comparison page (public) |
| `/r/:code` | Friend's code landing (public) |
| `/how-we-earn`, `/billing` | How we earn, how billing works (public) |
| `/install/android` | Android install guide (public) |
| `/status` | Redirect to the hosted status page |

The current repository routes (`/trips/:tripId/itinerary`, `/lodging`, `/agents`) are renamed to Plan and Stays and folded into the trip workspace.

## 6. Screens

For how a component looks, `design/hermi.css` and the mockups in `design/screens/` win over the prose of sections 4 and 6; the token values in section 2 still win over both. A component block the kit lacks is added to `hermi.css` and `components.html` by the ticket that needs it, in the same pull request.

Every screen follows one template: **Purpose**, **Layout**, **Content**, **Interactions**, **States** (loading, empty, error, offline, no permission, limit reached where they apply), **Copy**, **Events** (analytics names, snake_case, properties in braces; `screen_viewed {screen}` fires on every screen and is not repeated; names and property values are the catalog in 10 section 4), **Accessibility**. Copy follows section 7. Credit prices and limits come from section 1.4 of [01-product-spec.md](01-product-spec.md). Every state listed for a screen is built and has a component test; the offline and error states also have a Playwright test.

### 6.1 Splash and onboarding

**Mockup:** [screens/01-welcome.html](design/screens/01-welcome.html) <img src="design/png/01-welcome.png" width="260" alt="Welcome screen: a calm map with a pink and a yellow dotted route meeting at a plane, and a boarding-pass ticket with the Hermi lockup, the headline Plan together. Know the fare., and Plan a trip and Sign in buttons">

**Purpose.** Show value in one screen and get the person planning in under a minute, with no account.
**Layout.** Full screen, `--tp-paper` ground. Animated route pattern (route draw-on, once) behind the lockup in the upper half. Below: the positioning line in `type-display`, one supporting sentence, and two buttons.

```
+------------------------------+
|        (route pattern)       |
|         [H mark] Hermi       |
|                              |
|  Plan together.              |
|  Know the fare.              |
|                              |
|  Build a trip with the people|
|  you are going with, and see |
|  what flights really cost.   |
|                              |
|  [      Plan a trip       ]  |
|  [        Sign in         ]  |
|                              |
|  By continuing you agree to  |
|  the Terms and Privacy policy|
+------------------------------+
```

**Content.** Three quiet swipeable cards appear only if the person waits or swipes (no auto-advance): "Plan days together", "Watch fares, know what changed", "Every fact links to its source". Dots are optional and labeled.
**Interactions.** "Plan a trip" enters guest mode and opens Create trip (6.6). "Sign in" opens 6.3. Invite links skip this screen. A returning signed-out user sees "Sign in" as primary. Age gate: a one-line confirmation in the sign-in step for storefronts that need it (13 and over, 16 and over for EU and UK locales).
**States.** Loading: the lockup shows instantly, buttons are always active (nothing to load). Offline: same screen, guest planning works offline. Error: not applicable. No permission prompts on this screen, no ATT prompt anywhere.
**Copy.** Title "Plan together. Know the fare." Button "Plan a trip". Legal "By continuing you agree to the Terms and the Privacy policy."
**Events.** `onboarding_started`, `onboarding_choice_made {choice: plan|sign_in|invite}`.
**Accessibility.** The route pattern is hidden from assistive tech; heading order is lockup, headline, body; buttons reachable in order; draw-on skipped under reduced motion.

### 6.2 Guest mode and save your trip

**Purpose.** Let a guest build one trip on the device, then ask for an account only when there is something to keep, share or sync.
**Layout.** A guest sees the normal app with a slim banner under the header: "Guest trip, saved on this phone" and a "Save" button. Tabs: Trips, Discover, Account are live; Activity shows a sign-in prompt.
**Content.** Guest limits: one trip, destinations, plan items, maps, cached fares view, presentation. Anything that needs the server asks for sign-in: invite, sync to a second device, AI beyond the guest allowance, export, alerts, import, purchase.
**Save sheet (bottom sheet, triggered by any of the above).** Title "Save your trip". Body "Create a free account so your trip is safe and you can share it. Nothing you built will be lost." Buttons in this order: Continue with Apple (black, per Apple HIG), Continue with Google, Continue with email, then "Not now" as a text button. After success the guest trip is claimed into the account (merge screen if the identity already has trips: "You already have 2 trips. Add this one too?" with counts).
**Interactions.** The banner "Save" opens the sheet. Dismissing the sheet mutes the prompt for that trigger for 7 days, but the banner remains (it is not a paywall).
**States.** Offline: sign-in buttons disabled with "Connect to the internet to create your account. Your trip stays on this phone." Error on claim: "We could not move your trip into your account. It is still on this phone. Try again." with Retry. Limit: a second guest trip shows "Guests can plan one trip. Create a free account to add more."
**Events.** `guest_trip_created`, `save_prompt_shown {trigger}`, `save_prompt_dismissed {trigger}`, `guest_claimed {trip_count_bucket}`.
**Accessibility.** Sheet focus rules from 4.19; the Apple button meets Apple's contrast and size rules.

### 6.3 Sign in

**Purpose.** Create or restore an account with Sign in with Apple, Google or an email code.
**Layout.** Sheet or full screen: lockup, title "Sign in to Hermi", three buttons stacked (Apple, Google, email), a legal line. Email path: one screen with an email field ("Email") and "Send code"; next screen six digit code field (one field, `autocomplete="one-time-code"`, numeric keyboard), "Resend code in 30 s", and a "Use a different email" link.
**Interactions.** Apple returns the identity token; "Hide My Email" relay is accepted and shown as the email. The code field auto-submits at six digits. Three wrong codes show a gentle warning; five invalidate the code. Passwords do not exist.
**States.** Loading: button spinners. Error (wrong code): "That code is not right. Check the email we sent and try again." Expired: "That code expired. Send a new one." Rate limited: "Too many tries. Wait 10 minutes, then send a new code." Offline: "You are offline. Connect to sign in." Account pending deletion: "Your account is scheduled for deletion on 14 Nov. Restore it to keep your trips." with "Restore account".
**Copy.** Email helper "We will send a six digit code. No password needed." Under the buttons, a text link "Have a friend's code?" opens a one-field sheet (6.37).
**Events.** `signup_started {method}`, `signup_completed {method, from_invite, was_guest}` (new account) or `sign_in_completed {method}` (existing account), `sign_in_failed {method, reason}`.
**Accessibility.** The code field announces "Six digit code"; paste works; error text is linked with `aria-describedby`; the Apple button has a VoiceOver label "Continue with Apple".

### 6.4 Profile setup (skippable)

**Purpose.** Collect the minimum that improves fares: a display name and a home airport.
**Layout.** One sheet: Name, Home airport (combobox with "Use my location" that asks for permission only on tap), Currency (prefilled from locale). "Skip for now" is a full button.
**Interactions.** Saving creates the "Me" traveler. Skipping still creates "Me" with no airport. After this step, onboarding shows the "Coming from TripIt, Tripsy or Wanderlog?" card (6.30).
**States.** Location denied: "Location is off. Type a city or an airport code instead." Offline: fields work, saved locally.
**Events.** `onboarding_step_completed {step: profile|home_airport}`, `onboarding_step_skipped {step}`.
**Accessibility.** The location button states what it does and why ("Use my location to suggest nearby airports").

### 6.5 Trips home

**Mockup:** [screens/02-trips-home.html](design/screens/02-trips-home.html) <img src="design/png/02-trips-home.png" width="260" alt="Trips home: a map with the trips' routes above a sheet with the Trips title and boarding-pass tickets for upcoming and past trips, over the floating tab bar">

**Purpose.** See every trip and start a new one.
**Layout.** Large title "Trips", trailing "+" button (also a primary "New trip" button when empty). Sections: **In progress**, **Upcoming**, **Shared with me**, **Past**. Trip cards (4.4) stacked on phones, a two-column grid from 768 px. A "Trip limit" line under the title on Free: "2 of 2 active trips".
**Content.** Sorted by start date (upcoming ascending, past descending); the sort is fixed and not commission related. A banner appears for pending invites ("Sam invited you to Lisbon in March. View").
**Interactions.** Tap opens the trip at the last section. Swipe left: Archive. Long press: Open, Share, Archive, Delete. Pull to refresh. "+" opens a menu: New trip, Import a trip (6.30), Verify a plan (6.38). Archived trips are under a "Past" section toggle, always readable and exportable.
**States.** Loading: three trip card skeletons. Empty: static route pattern, "No trips yet", "Start with a place and a few dates. You can change everything later.", [New trip], and under it a quiet card "Coming from TripIt, Tripsy or Wanderlog?" with [Import a trip] (6.30). Error: "We could not load your trips. Pull down to try again." Offline: cached trips with "Saved offline" icons and a banner "You are offline. Showing your saved trips." No permission: not applicable. Limit reached: "+" opens the third trip paywall (6.27, trigger `third_trip`) with the free path "Archive a trip" first.
**Copy.** Limit line "You have 2 active trips. Archive one to make room, or upgrade."
**Events.** `trips_home_viewed {trip_count_bucket, active_count}`, `trip_opened {source}`, `trip_archived`.
**Accessibility.** Each card is one link with a combined label ("Lisbon, 12 to 19 March, 2 travelers, planning"); swipe actions have a custom-actions alternative; sections are headings.

### 6.6 Create trip

**Purpose.** Get a trip with a destination, dates and travelers in three taps.
**Layout.** Full-screen modal, three short steps with a progress label ("Step 1 of 3"), one field group per step.

```
+------------------------------+
| x    New trip       Step 1/3 |
|                              |
| Where are you going?         |
| [ Search a city or country ] |
|  Lisbon, Portugal            |
|  Porto, Portugal             |
|                              |
| + Add another destination    |
|                              |
| [          Next           ]  |
+------------------------------+
```

**Content.** Step 1 destination (Geoapify autocomplete, multi-destination allowed), Step 2 dates (range picker, or "I do not have dates yet", or "Flexible" with a window and trip length), Step 3 travelers (you, plus names and home airports for each; "Just me" allowed) and a trip name (prefilled "Lisbon, March"). Template chips on step 1: "Long weekend", "Week abroad", "Road trip", "Blank".
**Interactions.** Create makes the trip, plays the route draw-on once and opens Overview. Dates optional. Back keeps entries. A traveler can be typed or chosen from saved travelers.
**States.** Loading: suggestions skeleton. Empty search: "Try a city, region or country." Error (lookup): "We could not search places right now. Type the name and continue, we will look it up later." Offline: free-text destination accepted, resolved later. Limit reached: Free with 2 active trips shows the third trip paywall on "Create". Guests: one trip limit (6.2).
**Copy.** "Dates are optional. You can add them later."
**Events.** `trip_create_started`, `trip_created {source, destination_count, has_dates}`.
**Accessibility.** Step label is announced; destination results are a listbox with arrow navigation; date picker has a text entry alternative ("12 Mar 2027").

### 6.7 Trip overview

**Mockup:** [screens/03-trip-overview.html](design/screens/03-trip-overview.html) (dark: [#dark](design/screens/03-trip-overview.html#dark)) <img src="design/png/03-trip-overview.png" width="260" alt="Trip overview in light mode: the trip map with numbered pins and the travelers' routes, the section strip as pills, a boarding-pass ticket with airport codes and a Booked stub, next steps and summary cards"> <img src="design/png/03-trip-overview-dark.png" width="260" alt="The same trip overview in dark mode, with a darkened map">

**Purpose.** The trip at a glance and the next sensible step.

```
+------------------------------+
| < Trips     Lisbon       ... |
| Overview Flights Stays Plan  |
|--(underline)-----------------|
| [route pattern band]         |
|  LISBON     12 to 19 Mar     |
|  (SM)(AK)(+1)  Planning      |
|                              |
| Next steps                   |
| [ ] Pick flights       >     |
| [ ] Shortlist 3 stays  >     |
| [ ] Plan day 1         >     |
|                              |
| Fares        from $412       |
|  LIS  [sparkline]  Down $42  |
| Stays        2 of 3 voted    |
| Plan         4 days planned  |
| Before you go   3 to do   >  |
| Cost so far  $1,840 est.     |
| Notes and evidence       >   |
| AI activity              >   |
+------------------------------+
```

The mockup supersedes this wireframe's band layout.

**Layout.** The trip opens on the map header (4.22) with the trip's routes, and the hero pass (destination, dates, airport codes, travelers, status) sits at the top of the sheet. Below: a "Next steps" card (up to three suggestions, derived from missing data: dates, flight, stay, first day), then summary cards for each section, then Before you go, cost so far (from chosen flight and booked stays), Notes and evidence, AI activity (runs and credits used on this trip).
**Content.** A quiet "Places to stay in Lisbon" partner card appears only when dates exist, collapses after the first view, and follows 4.13 (one per screen view). Destination facts (local time, currency, a Wikipedia summary with attribution) are in a collapsed card.
**Interactions.** Every summary card opens its section. "Invite" avatar button opens the invite flow (6.8). The "..." menu: Ask (6.15), Share, Calendar feed (6.31), Import into this trip (6.30), Verify a plan (6.38), Plan checks, Trip settings, Export, Archive, Delete. The hero pass shows the sync indicator (4.21, 6.33) under the destination name. Changes by others show a brand dot on the section and a "Sam updated Stays" line.
**States.** Loading: skeleton header and five cards. Empty (no data yet): only "Next steps". Error: block-level retry per card. Offline: "Saved offline, updated 2 h ago" chip. No permission (viewer): Next steps hidden, summary cards read-only. Limit reached: a limited trip (Plus lapsed, pass expired) shows a banner "This trip is limited. Extra travelers are now viewers. Renew to restore editing." with the free actions visible (read, export).
**Copy.** Empty next step "Pick your dates". Banner as above.
**Events.** `trip_overview_viewed`, `next_step_tapped {step}`, `section_opened {section}`.
**Accessibility.** The header reads as one heading plus a description; cards are links with the state in their name ("Stays, 2 of 3 voted"); the section strip is a `nav` with `aria-current="page"` on the current section.

### 6.8 Invite flow

**Purpose.** Bring the other travelers into the trip; they join free.
**Sender layout.** Group section, "Invite" button, or the Overview avatar plus. A sheet with: role (Editor or Viewer, default Editor), "Share link" (native share sheet, link `hermi.world/i/...`), "Send by email" (email field, up to 20 pending), and the current members list with role chips and "Remove". A line under the role: "They join free. You share your trip's features with them on this trip."
**Free owner.** The first invite is free: a Free owner can invite 1 collaborator per trip, so a couple plans together with no purchase. Asking for a second collaborator is the `invite` paywall trigger (6.27): "Plan together. They join free." with Trip Pass first. The free path: "Keep my one collaborator", and "Share a read-only link" (a viewer link that opens without an account) stays available. Plus owners and owners of a Trip Pass trip can invite up to 6 and see no paywall.
**Recipient flow.** The link opens the app (or the App Store with an "Enter code" fallback, or a web landing page on desktop). Landing: "Sam invited you to Lisbon, 12 to 19 March" with the route pattern band, member avatars, and "Join trip" (primary). No sign-in wall before seeing the trip title and dates. After sign-in a banner "You were added by Sam" and a one-time sheet "Which traveler are you?" listing travelers with a "None of these" option that adds a new one.
**Interactions.** Owner can change role, resend, revoke a pending invite, and remove a member (access ends immediately). Links expire in 7 days (owner can regenerate).
**States.** Loading: member list skeleton. Error: "We could not create the link. Try again." Invite expired: "This invite expired. Ask Sam to send a new one." Invite used or revoked: "This invite is no longer valid." Already a member: opens the trip. Offline: "Connect to send an invite." No permission: editors can invite viewers only if the owner allows it; else the button is hidden and a line reads "Only Sam can invite people." Limit: 20 pending invites, "You have 20 pending invites. Cancel one to send another." Collaborator cap: a Free owner with 1 collaborator sees the `invite` paywall; on Plus and Trip Pass trips the cap is 6, "This trip has 6 collaborators. Remove one to invite someone else."
**Events.** `invite_sheet_opened`, `invite_sent {channel, role}`, `invite_opened {platform_before_install}`, `invite_accepted {role, minutes_to_accept_bucket}`, `traveler_linked`.
**Accessibility.** Role control is a radio group; the share button announces "Share invite link"; the landing page is fully usable without the app.

### 6.9 Flights and alerts

**Purpose.** Find and follow fares for the trip's routes, and set price alerts.
**Layout.** Section header with a "Add route" button. One **route card** per route: codes in `type-code` (NYC to LIS), date window, travelers count, the fare chip row for the cheapest options, price chart (4.6), date grid toggle (Chart, Grid, Options), and an alert switch. "Options" is a list sorted by price by default with a visible sort control (Price, Duration, Stops); every row is a fare chip plus airline, times and stops.

```
+------------------------------+
| Flights               + Route|
| NYC > LIS   12 to 19 Mar     |
| Lowest in this list   $412   |
| [Live $412 3h] [Cached $398] |
| [ price chart 16:9         ] |
| Chart | Grid | Options       |
| Alert me when it drops  [on] |
| Fares at last check. Prices  |
| can change on the booking    |
| site.                        |
| [ Live check  1 credit ]     |
+------------------------------+
```

**Content.** Free: 1 route with cached fares; other routes are visible as "Preview" (locked preview of cached fares, see the `second_route` trigger). Plus: 3 live routes checked daily within 120 days of departure, Trip Pass 2. A flight marked as booked shows the booked-fare watch on its route card (6.32). Source tags, age ("checked 3 h ago"), and a clear line that cached fares come from Aviasales and live from Google Flights. "Live check" (1 credit) refreshes now; a result under 6 hours old is free and says so.
**Interactions.** Add route sheet: origins (up to 2 airports on Free, 4 on paid, per side), destinations, date window or exact dates, trip length, travelers. Tap a fare chip to open fare detail (6.10). Alert switch opens the alert sheet: "Notify me when the lowest fare drops by" (amount or percent) or "below $" with a push permission reason screen the first time ("We will only send alerts for routes you follow"). Edit or delete route in the "..." menu.
**States.** Loading: route card skeleton with chart frame. Empty: "No routes yet", "Add where you fly from and to, and we will track fares for you.", [Add a route]. Error: "We could not load fares. Pull down to try again." Provider down: "Live fares are paused. Cached fares are still here." Offline: last saved fares with their age. No permission: viewers see fares without alert or live check controls. Limit reached: second route on Free opens `second_route`; live check with no credits opens `out_of_credits` with cached fares still shown.
**Copy.** Alert confirmation "Alert on. We will tell you if the lowest fare drops by $30 or more." Stale "Fares may have changed. Check again (1 credit)."
**Events.** `flight_route_added {route_type, days_to_departure_bucket}`, `fare_chip_tapped {source}`, `fare_alert_created {kind}`, `ai_action_started {action: live_search, credits, from_cache}` for a live check (`from_cache: true` when a result under 6 hours old is served free).
**Accessibility.** The chart has the text summary and data table (4.6); the date grid is a real table with row and column headers and heat values also printed as numbers; alert switch has a state label.

### 6.10 Fare detail and Book this fare

**Mockup:** [screens/05-fare-detail.html](design/screens/05-fare-detail.html) <img src="design/png/05-fare-detail.png" width="260" alt="Fare detail: a map with the flight route, a boarding-pass ticket with the airport codes and a fare stub, the price chart, an Explain this fare button, and Book this fare rows as small tickets with their action on the stub">

**Purpose.** Understand one fare and book it on a partner or the airline, honestly.
**Layout.** Large figure (mono 40 px) for the price, "per adult, economy, at last check 3 h ago", trend chip, route and times summary, then the price chart focused on this route, "Why this price" (Explain, 1 credit), then the **Book this fare** compare list.

```
+------------------------------+
| < Flights    NYC > LIS       |
| $412                         |
| per adult, checked 3 h ago   |
| Down $42 since Tuesday       |
| [ chart ]                    |
| [ Explain this fare  1 cr ]  |
|                              |
| Book this fare               |
| Sorted by price, lowest first|
| +--------------------------+ |
| | Aviasales      $412  3h  | |
| | [ Book on Aviasales   ]  | |
| +--------------------------+ |
| | Kiwi.com       $431  3h  | |
| | [ Book on Kiwi.com    ]  | |
| +--------------------------+ |
| Airline site   price varies  |
| [ Search on the airline's  ] |
| [ site                     ] |
| We earn a commission if you  |
| book here. The price can     |
| change on the booking site.  |
| [ Mark as booked ]           |
+------------------------------+
```

**Content.** The compare list shows two or three providers when a live or cached price exists for each, each row with provider name, price, the date and age of the price, and a button. The airline's own site row is always present and equal weight. Sort statement always shown; ties broken alphabetically, never by commission. If the booking page price differs, the copy says so after return ("The price on the partner site can be different. Check it before you pay.").
**Interactions.** Book opens the partner link in the in-app Safari view through `/go/{click_id}`. After return: a sheet "Did you book it?" with "Yes, mark as booked", "Not yet", "I booked somewhere else". "Yes, mark as booked" continues to "What did you pay?" and the booked-fare watch (6.32). "Mark as booked" sets the chosen flight (which can set trip dates after confirmation), puts a Booked ticket stub on the card and offers the soft next step "Plan your days" (no paywall, no partner card). "Explain this fare" (1 credit) gives a short Haiku answer with sources.
**States.** Loading: figure and chart skeletons. Empty providers: only the airline route: "We do not have a partner price for this fare. You can search on the airline's site." Error: "We could not load this fare. Try again." Offline: shows the saved fare; Book buttons are disabled with "Connect to the internet to book." Stale (over 24 h): a warning-ink line "This price is 2 days old. Check again (1 credit)." Limit: Explain with no credits opens `out_of_credits`.
**Copy.** Disclosure as in 4.13. No "best", "deal", "hurry" words.
**Events.** `fare_detail_viewed {age_hours_bucket}`, `partner_link_tapped {program, placement: flight}` (the click id is added server side), `fare_marked_booked`, `ai_action_started {action: explain}`.
**Accessibility.** Price change is announced as text, not color; each provider row is a labeled group ("Aviasales, 412 dollars, checked 3 hours ago, Book on Aviasales, opens in a browser").

### 6.11 Stays: shortlist, compare and vote

**Mockup:** [screens/06-stays-vote.html](design/screens/06-stays-vote.html) <img src="design/png/06-stays-vote.png" width="260" alt="Stays: a map with price pins, an Add a stay button, and lodging tickets with the price per night in the body and the vote summary and heart chips on the stub">

**Purpose.** Collect places to stay, compare them fairly and decide as a group.
**Layout.** Section header with "Add a stay" and a List or Compare segmented control. The list is sorted by a visible control (Hearts, Price, Added, Rating; the API `sort` values `votes`, `price`, `created`, `rating`), default Hearts. Lodging cards (4.10). A sticky bottom bar appears when 2 to 4 are selected: "Compare (3)".
**Add a stay sheet.** Four ways: Paste a link (Airbnb, Vrbo, Booking.com or any URL; the text below says "We never change your links and never load these pages."), Search (partner search results with the sort statement, "Save to shortlist" first and "View" second), Add by hand (name, link, price per night, notes), and "Paste a booking" for a stay you already booked (1 credit, see 6.13). On web, the bookmarklet card imports from a page the user has open.
**Compare.** 2 to 4 columns (Free compares 2): price per night, total, per person, bedrooms, area, cancellation note, votes, notes. Differences are highlighted with a pattern and text, not color alone. Sticky first column on phones with horizontal scroll.
**Voting.** A heart toggle per person (a `lodging_votes` row exists while the heart is on; 03 section 5.8). There is no down vote. Tap the count to see names. Owner and editors can mark a stay "Booked" (ticket stub) or "Rejected".
**Partner surfaces.** A separate "Compare on other sites" link (labeled partner search) and, only for hosts with an approved program, a "Book via partner" button, all using 4.13 wording. Airbnb has plain links only. "Cheaper on <partner>" appears only with real dated price data.
**States.** Loading: three card skeletons. Empty: "No stays yet", "Paste a link or search to start a shortlist.", [Add a stay]. Error: "We could not save this stay. Check the link and try again." Offline: list readable, adding allowed as a queued edit with a "Waiting to sync" chip. No permission: viewers can vote but not add or mark. Limit reached: saving the 9th stay on Free puts it in a locked "Later" list with `ninth_stay` paywall, free path "Keep in Later" and nothing is lost.
**Copy.** Import helper "We never change your links." Vote summary "3 of 4 like this".
**Events.** `lodging_option_added {source}`, `lodging_voted {voted}`, `lodging_compare_opened {count}`, `lodging_booked`, `partner_link_tapped {program, placement: stay}`.
**Accessibility.** Vote buttons use `aria-pressed` and name the person; the compare table is a real table with `th` scope; difference highlights are also announced ("Cheaper than the others by $40").

### 6.12 Plan: calendar and day view

**Mockup:** [screens/04-plan-day.html](design/screens/04-plan-day.html) <img src="design/png/04-plan-day.png" width="260" alt="Plan day view: a map with numbered pins joined by the pink and yellow routes, the Days, Calendar and Map control, a day chip strip, and a timeline whose spine is the twin routes with each stop as a ticket">

**Purpose.** Plan each day together.
**Layout.** Section header with a segmented control (Days, Calendar, Map) and an "Ideas" button. **Days** is the default list of day cards (4.8) with a day chip strip pinned at the top (D1 to D7, today highlighted). Day detail is a push screen with the timeline (4.7) above the ideas tray.
**Content.** Each day: items in order with times, travel time between items when known, and a summary. Ideas tray holds saved places not yet scheduled. "Draft this day" (1 credit) and "Draft the trip" (4 credits) live in the AI sheet (6.15). On the arrival day, a transfer card can appear (4.13, one per view), on a drive day a car card.
**Interactions.** Tap an item to edit. Add with "+" (6.13). Reorder: drag handle (web, and long press on touch) or "Move to..." sheet; the new position is stored in `sort_order`. Swipe left on an item: Delete (undo toast); swipe right: Mark done. Pinch on map. Pull to refresh; polling every 15 to 30 s on shared trips, with a "Sam added Bairro Alto to Day 2" highlight for 6 s and an entry in Activity.
**States.** Loading: day card skeletons. Empty trip: "Nothing planned yet", "Add a place, or ask for a draft to start from.", [Add a place] [Draft the trip, 4 credits]. Empty day: "Free day". Error: "We could not load your plan. Pull down to try again." Offline: readable, edits to notes and checkmarks queue, itinerary structure edits show the read-only banner "Offline. You can read your plan and check things off. Reconnect to rearrange." Conflict: 409 sheet with both versions and "Keep mine" or "Use theirs". No permission: viewers cannot edit. Limit reached: none on the plan itself (the calendar is never gated).
**Copy.** Conflict "Sam changed this while you were editing."
**Events.** `plan_viewed {mode}`, `itinerary_item_moved {method}`, `itinerary_item_deleted`, `edit_conflict_shown {resolution}`.
**Accessibility.** Drag has full keyboard and VoiceOver alternatives (Move up, Move down, Move to day); timeline blocks have text labels with time and duration; the day chip strip is a `tablist` with `aria-selected` on the current day (a real tab widget).

### 6.13 Add item

**Purpose.** Add a place, activity, transport leg, reservation or note to a day or to Ideas.
**Layout.** Bottom sheet, large detent. Top: search field "Search places" with category chips (Sights, Museums, Food, Outdoors, Nightlife, Shopping, Getting around), which are the `item_category` values `sights`, `museum`, `food`, `nature`, `nightlife`, `shopping` and `travel`; an item that fits none is `other`. Results (place cards) sorted by relevance then distance with the sort label. A "Custom item" row at the bottom.
**Content.** A place result opens a detail view (photo, hours, website, Wikipedia summary with attribution, "Explain" 1 credit) with "Add to Day 2" (day picker), "Save to ideas", and optional time. The place detail may carry a "Tickets" or "Book a table" partner chip on the detail view only (4.13). "Paste a booking" (1 credit) takes a confirmation email or text, shows a draft flight, stay or activity for confirmation (names and booking references are replaced with placeholders before anything is sent to the AI provider, and nothing is fetched from any link in the text), and "Add to plan" creates the item or stay. Custom item: title, time, duration, cost, link, note, category (one of the eight above; it chooses the color group and icon) and status (Idea, Planned or Booked, `item_status`).
**Interactions.** Add closes the sheet with a toast "Added to Day 2. Undo" and scrolls to the item. Adding while offline queues the edit.
**States.** Loading: result row skeletons. Empty: "No results. Try a different name, or add it yourself." Error: "Place search is not working right now. Add it by hand and we will match it later." Limit: places search is capped per day on Free (30); at the cap: "You have reached today's 30 place searches. Saved places still work. Searches reset at midnight." with "Add by hand".
**Events.** `itinerary_item_added {category, source}`, `place_searched {result_count_bucket}`.
**Accessibility.** Result list is a listbox; the day picker is a native select on iOS; "Add" buttons include the place name in their label.

### 6.14 Plan map

**Purpose.** See the days spatially and plan walking time.
**Layout.** Full-bleed MapLibre map under the section header, numbered pins in group colors (`tp-map-pin`), a day filter strip (All, D1 to D7), and a half-height list sheet that drags up. A button group: "Open in Apple Maps", "Open in Google Maps".
**Interactions.** Tap a pin to select and highlight the list row; tap a list row to fly to the pin. A route line connects a day's items in order with a walking time label. Location dot only if the person has granted location (asked on tap of "Show me on the map").
**States.** Loading: map tiles with a skeleton frame. Empty: "No places on the map yet. Add a place to a day." Error: "The map did not load. Try again." with a list view fallback. Offline: cached tiles at low zoom for the trip area when downloaded, else "Maps need a connection. Your list is below." No permission: location denied message as in 6.4.
**Events.** `map_opened`, `map_pin_selected`, `maps_handoff {app}`.
**Accessibility.** Every pin has a list equivalent; the map is not required to complete any task; attribution stays visible; pin numbers are also in the list rows.

### 6.15 AI actions: explain, draft, research

**Mockup:** [screens/08-ai-actions.html](design/screens/08-ai-actions.html) <img src="design/png/08-ai-actions.png" width="260" alt="The AI actions sheet: a credit balance, and action rows each with a one-line description and a credit cost chip">

**Purpose.** One sheet for every AI action, with the price up front.
**Layout.** The AI sheet is a bottom sheet that opens from the "Plan with AI" entry on Overview and from an "Ask" button (sparkle glyph replaced by a plain "Ask" label) in the trip menu. Header: title, balance pill ("27 credits"), trip AI toggle state. Body: action rows, each with a one-line description and a credit cost chip:

| Action | Credits | Where else it appears |
|---|---|---|
| Explain (short answer about a fare, place or plan) | 1 | Fare detail, place detail |
| Suggest a packing list (from the weather and your plans) | 1 | Before you go, Packing |
| Paste a booking (turn a confirmation email into a draft) | 1 | Flights, Stays, Add item |
| Verify a plan from another AI (read it: 1, then 1 per place checked, 5 at a time on Free, 12 on Plus and Trip Pass) | 1, then 1 each | Trips home "+", trip menu (6.38) |
| Recheck a finding (older than 14 days) | 1 | Notes and evidence, plan checks (6.39) |
| Live check (flight or rental) | 1 | Flights, Stays |
| Draft this day | 1 | Day card |
| Draft the trip (up to 14 days) | 4 | Plan empty state |
| Research a question (5 searches, 8 fetches) | 8, or 1 from shared cache | Notes, Plan |
| Deep agent run (fare hunt or research) | 40, or 8 from shared cache | Flights, Overview |

**Content and flow.** Choosing an action asks for the minimum input (a question, or which day). A confirm step appears at 6 credits or more: "Research this question? Costs 8 credits. You have 27, so 19 left." with [Start research] and [Cancel]. A shared cache hit is stated before spend: "Someone already researched Lisbon in March this week. Use that for 1 credit?" with [Use it, 1 credit] and [Research fresh, 8 credits].
**Drafts.** Output (including a packing list or a parsed booking) appears as a preview the person edits before anything is added; "Add to plan" is explicit. Drafts carry "Drafted by AI from your dates and places. Check hours and prices." and sources when a web search was used. AI output never contains partner links or partner names.
**First use.** The AI consent screen (once per account): "Hermi sends your destination, dates and what you type to Anthropic to answer. We do not send your name, email or other travelers' names, and it is not used to train models." [Allow] [Not now]. Revoking is in Account, Privacy.
**Interactions.** Cancel works during a wait; a failed or empty action refunds automatically and says so ("No charge. That did not finish."). An agent run is stoppable and billed by turns used (minimum 8 credits) and the sheet says it before stopping.
**States.** Loading: streaming text with a stop button. Empty: n/a. Error: "That did not work, and you were not charged. Try again." Rate limited (10 AI actions a minute): "Slow down a little. Try again in a few seconds." Offline: actions disabled, "AI needs a connection." No permission: viewers cannot run AI; the owner may turn AI off for the trip ("AI is off for this trip. Ask Sam to turn it on."). Limit: out of credits opens `out_of_credits_draft` or `out_of_credits_research` (6.27), monthly provider ceiling reached shows "AI is paused until 1 Nov. Saved data and cached fares still work."
**Events.** `ai_sheet_opened`, `ai_action_started {action, feature, credits, from_cache}` (fired when the person confirms), `ai_action_completed {action, feature, outcome, duration_seconds_bucket}` (a refund is `outcome: refunded`), `ai_consent_shown`, `ai_consent_granted`, `ai_consent_declined`.
**Accessibility.** Cost chips are read as part of the button name; streaming text is in a polite live region updated per sentence, not per token; Stop is always the first focusable control while running.

### 6.16 Agent run: live progress and evidence

**Mockup:** [screens/09-agent-run.html](design/screens/09-agent-run.html) <img src="design/png/09-agent-run.png" width="260" alt="Agent run: the goal, a Running ticket stub with elapsed time and a Stop button, the step timeline, and findings with their evidence labels">

**Purpose.** Watch a deep run, trust what it found, and keep the good parts.
**Layout.** Run screen pushed from the AI sheet. Header: goal ("Find the cheapest way to fly NYC to Lisbon, 10 to 20 March"), a ticket stub status (Running, Done, Stopped, Failed), elapsed time in mono, credits reserved ("40 credits, billed by use"), and a **Stop** button. Body: a **timeline** of steps (Searching, Reading a page, Checking a fare, Saving a finding) with time, and below it **Findings** grouped as Fares and Notes. Each finding is an **evidence row** (4.21): what was found, the evidence label ("Found on theflightsite.com, checked 12 Sep"), the source page title, a quote, "Open source". A finding older than 14 days later shows "May be out of date" and "Recheck" (6.39).

```
+------------------------------+
| < Lisbon      Agent run      |
| Find the cheapest NYC to LIS |
| RUNNING  02:14   Stop        |
| 40 credits, billed by use    |
|                              |
| o Searching flights    00:12 |
| o Reading kayak page   00:41 |
| * Checking a fare...   now   |
|                              |
| Findings (2)                 |
| Fare  $398 TAP, 12 Mar       |
|  Found on theflightsite.com, |
|  checked today [Open source] |
|  [Save to trip] [Dismiss]    |
| Note  Tram 28 is crowded ... |
|  Found on lisbon-guide.org,  |
|  checked 12 Sep [Open]       |
+------------------------------+
```

**Content.** Only findings with a source page and a capture date are shown as findings; rejected items go to a collapsed "Not saved (2)" list with the reason ("No page link", "Page did not show that fare"). Fares are labeled "Seen on a page during this run. Prices can change." The final ticket stub lands with `touchdown` and a summary: "Done. 2 fares and 3 notes saved. 31 credits used."
**Interactions.** The run continues if the app is backgrounded; a push and an Activity item announce completion. "Save to trip" on a finding adds it to fares or notes with its evidence attached; "Dismiss" removes it from view. Stop asks "Stop this run? You will be billed 14 credits for the work done." with [Stop run] and [Keep running].
**States.** Loading (queued): "In the queue. About 1 minute." with Cancel and no charge. Empty result: "Nothing saved. You were not charged." Error: "The run stopped because the price check service is down. You were not charged." Offline: progress is on the server and resumes when online, banner "You are offline. The run keeps going." No permission: only the starter can stop; others can read findings. Limit reached: one run at a time, "A run is already in progress for your account. Wait for it to finish or stop it."
**Events.** `ai_action_started {action: agent_run, feature, credits, from_cache}`, `agent_finding_saved {kind}`, `ai_action_completed {action: agent_run, outcome}` (a run the person stops is `outcome: partial`).
**Accessibility.** Timeline is an ordered list with the current step marked "current"; status changes are polite announcements ("Checking a fare"); the ticket stub carries text, not only color; evidence links say "Open source, theflightsite.com, opens in a browser".

### 6.17 Taster run

**Purpose.** Let a Free person try one deep agent run, once, so they see the best feature before paying.
**Layout.** An entry card on Flights or Overview for accounts whose taster is unused: "Try a deep run, free once", a two-line explainer, and a **Start free run** button with a chip "Free, one time". The confirm step reads the normal confirm copy with "Free taster" in place of the cost.
**Content.** Same run screen as 6.16 with a "Taster" ticket stub. Runs with the same caps (20 turns, 10 searches, 10 fetches, $0.80 hard stop). At the end, a soft card "That was your free run. Runs cost 40 credits (8 when someone already researched it). Plus includes 60 credits a month." with "See plans" and "Done" (equal weight). It is a result-moment offer, not a paywall sheet, and it follows the one-per-session and 7-day mute rules.
**States.** Used: the entry card is replaced by the normal "Deep run, 40 credits" action. Offline: disabled. Error or empty result: the taster is not consumed ("That did not finish, so your free run is still available.").
**Events.** `taster_offered`, `ai_action_started {action: agent_run, taster: true}`, `ai_action_completed {action: agent_run, taster: true, outcome}`, `taster_upsell_shown`.
**Accessibility.** The one-time nature is stated in text, not only a badge.

### 6.18 Notes and evidence

**Purpose.** Keep the trip's knowledge in one place, with where each fact came from.
**Layout.** Reached from Overview. Two tabs in a segmented control: **Notes** (written by people) and **Found by AI** (saved findings). Notes are a reverse-chronological list with author avatar and "private" lock; each note can attach to the trip, a day, an item or a stay. Found by AI lists evidence rows grouped by topic, each with its evidence label ("Found on [site], checked [date]").
**Interactions.** Add a note (plain text, links auto-detected). Mark private (excluded from AI context and from other members). Pin a note to Overview. "Research this" (8 credits) starts research from a selected note. Tap an evidence row to see the quote and open the source. Findings whose date is more than 14 days old show an amber "May be out of date" chip and a "Recheck" button (6.39); the chip text reads "Seen 12 Aug. May be out of date." Nothing is hidden or removed.
**States.** Loading: row skeletons. Empty: "No notes yet", "Write down what you learn. Anything an AI finds is saved here with its source.", [Add a note]. Error: "We could not load notes. Pull down to try again." Offline: notes can be added and ticked (queued); evidence is readable. No permission: viewers can read. Limit: none.
**Events.** `note_added {scope, private}`, `evidence_opened`, `finding_saved_to_notes`, `evidence_stale_shown {age_bucket}`.
**Accessibility.** Private state is text plus icon; evidence links name the domain; long notes are not truncated for screen readers.

### 6.19 Present mode

**Purpose.** Walk the group through the plan on a phone, a TV or AirPlay, and print or share it.
**Layout.** Outside the app shell, full screen, `deck-*` type utilities so text scales by container size. Slides: Title (destination, dates, travelers, route pattern), one per Destination, Flights per route, Stays shortlist, one per Day (map plus items), and Closing "Trip at a glance" (existing slide kinds). An optional last slide "Book the plan" lists partner links with the disclosure line, off by default for the owner to turn on. Chrome (hidden after 3 s of no input): close, slide counter, overview grid, share, print.
**Interactions.** Phones in portrait: swipe up and down between slides in a story layout, tall slides scroll. Web and iPad (later): swipe or arrow keys, tap right or left third. Overview grid shows thumbnails. Screen stays awake (wake lock). Share creates a read-only link with redaction switches (hide addresses, prices, notes and traveler names, which show as "Traveler 1"; all hidden by default; the link expires after 90 days unless the owner picks another length up to a year) and a switch "Let search engines list this page" (off by default, see 6.34). Print or PDF one slide per 16:9 page, links live, checklist without partner buttons. Free shares carry a small "Made with Hermi" footer and the PDF a footer mark; paid tiers do not.
**No partner content during playback.** No cards, no logos, no interstitials on any normal slide.
**States.** Loading: title slide appears first, others stream in. Empty trip: "There is nothing to present yet. Add a day to your plan." Error: "We could not build the presentation. Try again." Offline: works from the offline copy, map slides use the static route plot. No permission: viewers can present. Limit: none (the footer is the only difference).
**Copy.** Footer "Made with Hermi".
**Events.** `present_mode_started {slide_count_bucket}`, `share_link_created {redaction_level}` (sharing from present mode), `present_mode_printed`.
**Accessibility.** Each slide has a heading and is navigable with arrow keys and VoiceOver swipe; auto-advance is never used; slide counter is announced ("Slide 3 of 9"); text stays at least 16 px.

### 6.20 Before you go checklist

**Purpose.** Help the group finish the practical things before leaving. Free on every tier.
**Layout.** Card on Overview (top three open items) and a full screen grouped by **Bookings, Getting around, Connectivity, Safety, Documents, Luggage, Money, Home, Packing**. It appears once there is a chosen flight or a saved stay, or 45 days before departure.
**Packing.** The Packing group starts as one row. "Suggest a packing list" (1 credit, `ai/packing-list`, from the weather numbers and the activity categories of the plan) opens a preview grouped as clothing, toiletries, documents, electronics, health and other; "Add to checklist" saves the lines the person keeps as tick-off rows (`kind` packing, source AI) and "Discard" saves nothing. No product links appear in it.
**Content.** Each row: a check, the title, the reason from the trip's data ("You land in Lisbon at 21:40"), a cost range if known, and three actions: **Get it** (affiliate, where one exists), **I have this**, **Not needed**. At least half the rows have no partner (documents, money, home, packing). Visa and entry rows link to the official government site first. Insurance rows appear only once a flight is booked, use insurer approved wording only, and never include AI advice. eSIM is not shown for domestic trips.
**Interactions.** Done and dismissed persist per trip and sync across members. One optional push seven days before departure. Partner rows follow 4.13 with the disclosure line on each button row. A "Hide booking links" setting collapses them.
**States.** Loading: row skeletons. Empty (nothing applies): "You are all set. Nothing to do before you go." Error: "We could not load your checklist. Try again." Offline: fully usable, partner buttons hidden with "Connect to see booking links." No permission: viewers can tick their own rows only. Limit: none.
**Copy.** Row "eSIM for Portugal. You will be abroad for 7 days. Plans start around $5." [Get it] [I have this] [Not needed]. Disclosure: "We earn a commission if you book here."
**Events.** `checklist_item_shown {kind}`, `partner_link_tapped {program, placement: checklist}` (through `/go`), `checklist_item_updated {kind, status}` (done, skipped, not needed).
**Accessibility.** Checkboxes are real inputs with the title as the label; the three actions are a labeled group per row; progress "4 of 9 done" is text.

### 6.21 Group: people

**Purpose.** See who is on the trip, bring people in and link travelers to accounts. Polls, expenses and settle up are not in Phase 1. Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
**Layout.** The Group section opens on the **People** list (there is no segmented control in Phase 1). Traveler rows show avatar, first name, role chip and home airport (visible to members only). A members block lists accounts with role chips and an "Invite" button (6.8). A line under Invite states the collaborator count: "1 of 1 collaborators" on Free, "3 of 6" on Plus and Trip Pass trips. A "Which traveler are you?" link shows while the person's account is unclaimed.
**Content.** Travelers without accounts are a first name and a traveler color (2.2). A child traveler has no photo or birthdate. A member who left shows as "Former member".
**Interactions.** Add, edit or remove a traveler (first name, color, home airport, adult or child). The owner changes a role, removes a member, or transfers ownership to an editor, who must accept. Any member can leave.
**States.** Loading: skeleton rows. Empty: "Just you so far", "Add your travel partner so plans and fares are shared.", [Invite]. Error: "We could not load people. Pull down to try again." Offline: readable, edits queue. No permission: viewers see the list without edit controls. Limit: the traveler cap (2 on Free, 8 on Plus and Trip Pass) shows an inline message, "Free trips have 2 travelers. Plus or a Trip Pass allows 8.", with a link to Plan and credits and no paywall sheet; the collaborator cap follows 6.8.
**Copy.** Unclaimed link "Which traveler are you?"
**Events.** `traveler_added {type}`, `traveler_linked`, `member_removed`.
**Accessibility.** Each row is one labeled group ("Ana, editor, home airport LIS"); role changes are announced; destructive actions are last and labeled.

### 6.22 Concierge request

Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

### 6.23 Discover

**Purpose.** Ideas and useful numbers for where to go, with no paid placements.
**Layout.** Large title "Discover", a search field, and sections: **Cheap fares from your airport** (cached fares by destination, sorted by price, with source and age), **Destinations** (Wikipedia summary, photo, best months, local currency), **Saved places**. A chip row filters (Beach, City, Mountains, Food).
**Content.** Every list states its sort. Fares are cached (Aviasales) and labeled. No partner cards. A destination page has "Start a trip here" and, when dates exist, the one quiet "Places to stay" card per 4.13.
**States.** Loading: card skeletons. Empty: "Add your home airport to see fares from there.", [Add home airport]. Error: "We could not load ideas. Pull down to try again." Offline: saved destinations only. Limit: none.
**Events.** `discover_viewed`, `destination_opened {country_code}`, `trip_started_from_discover`.
**Accessibility.** Cards are links with price and age in the name; sort control is a labeled menu.

### 6.24 Activity

**Purpose.** One inbox for what changed and what needs an answer.
**Layout.** Large title "Activity", a filter row (All, Alerts, Group, AI), a reverse-chronological list grouped by day. Items: fare alerts ("Fare fell $42 since Tuesday. View fare"), changes by others ("Sam added Bairro Alto to Day 2"), hearts, agent run results, invites, referral rewards, booked-fare drop alerts. Unread items have a brand dot.
**Interactions.** Tap opens the exact place (fare detail, day, flight card). Swipe to mark read. "Mark all as read". Owner can revert an edit within 7 days from the item ("Undo this change").
**States.** Loading: row skeletons. Empty: "Nothing new", "Price alerts, changes from your group and finished AI runs show up here." Error: retry. Offline: cached list. Limit: none. Signed-out guest: "Sign in to get alerts and see changes from your group."
**Events.** `activity_viewed {unread_bucket}`, `activity_item_opened {kind}`.
**Accessibility.** Unread is text ("Unread") plus dot; each row is one link; the tab badge has an accessible count.

### 6.25 Account and settings

**Purpose.** Manage profile, plan, privacy and devices.
**Layout.** Large title "Account". Top: profile card (name, email, tier chip, credit balance). Groups: **Subscription and credits**, **Invite friends** (6.37), **Import a trip** (6.30), **Verify a plan** (6.38), **Profile** (name, home airport, currency, traveler "Me"), **Notifications**, **Appearance** (Light, Dark, System), **Text size** (follows system Dynamic Type, with an in-app override), **Privacy** (AI consent, AI history, analytics choice), **How we earn** (public page, 6.40), **How billing works** (6.40), **Help and support** (with **Install on Android**, 6.42, and **Service status**, 6.41), **Devices** (sign out everywhere), **Export my data**, **Delete account**, **Terms and Privacy**, version.
**How we earn.** The same public page as `/how-we-earn` (6.40): "Hermi is paid for by subscriptions, trip passes, AI credits and commissions from partners when you book. We never show ads, sell your data, or rank anything by commission." Lists every current partner, the disclosure sentence, the ranking rule, and the **Hide booking links** switch.
**States.** Loading: skeleton rows. Error: retry. Offline: profile readable, purchases disabled ("Connect to buy or restore"). Guest: sign-in row replaces the profile card. Limit: n/a.
**Events.** `account_viewed`, `setting_changed {key}`, `booking_links_hidden {value}`.
**Accessibility.** Standard iOS list semantics; switch rows are single hit areas; destructive rows come last and are labeled.

### 6.26 Subscription and credits

**Purpose.** Show what the person has, what it includes and how to change it, with no tricks.
**Layout.**

```
+------------------------------+
| < Account  Plan and credits  |
| Plus (annual)                |
| Renews 14 Mar 2027, $39.99   |
| [ Change plan ]              |
| [ Cancel subscription ]      |
|                              |
| Credits           27 left    |
| 12 monthly, renew 1 Nov      |
| 15 bought, last until Jun    |
| [ Get more credits ]         |
|                              |
| Trip Pass                    |
| Lisbon, ends 4 Dec           |
|                              |
| Compare plans                |
| Restore purchases            |
| How credits work             |
| How billing works            |
+------------------------------+
```

**Content.** Current plan, renewal date and price in the store currency. "Cancel subscription" is a first-level row on the plan card, never inside a menu: one tap opens the App Store's own subscription sheet for this plan, where Apple asks for the final confirm, with no survey or offer before it; once cancelled the row reads "Your plan ends on 14 Mar". "Change plan" opens the same sheet for switching between monthly and annual. On the web app the rows read "Change plan in the iOS app" and "Cancel in the iOS app" and open the App Store's subscription page; nothing can be bought on the web. "How billing works" opens the plain billing page (6.40). Credit balance split into monthly (do not roll over), promo (the taster and referral credits, each with an expiry) and purchased (12 months, spent last) with expiry dates and a ledger link ("History": date, action, credits, refund marks). Trip Pass list with status and binding ("Not applied yet. Choose a trip"); a pass from a first import shows "Included with your first import". **Compare plans** shows the tier table below in plain numbers. Packs: 50, 150, 400 credits at $2.99, $6.99, $14.99 with the per-credit price as a fact and the expiry sentence "Bought credits last 12 months."

| | Free | Plus | Trip Pass |
|---|---|---|---|
| Price | $0 | $5.99 a month or $39.99 a year (about $3.33 a month) | $9.99 once, 90 days |
| Active trips | 2 | Unlimited (fair use 25) | 1 trip |
| Live fare routes | 0 (1 cached route per trip) | 3, checked daily within 120 days of departure | 2 (max 60 checks) |
| Credits | 12 a month | 60 a month | 40 |
| Invite people | 1 per trip, they join free | Up to 6 | Up to 6 |
| Offline reading, calendar feed, import, booked-fare alert, share links | Yes | Yes | Yes |
| Verify this plan, places checked at once | 5 | 12 | 12 |

Later: Phase 2 adds Family, Group Trip Pass and Pro, see [../phase-2-growth/README.md](../phase-2-growth/README.md). The table says "Plans include generous limits, listed above. Live tracking and AI use real services, so they have fair limits."

**Interactions.** Purchases use the native sheet (RevenueCat over StoreKit 2). "Restore purchases" is on this screen and every paywall. Downgrade or lapse never deletes or hides data: a line says so ("Your trips stay yours. If a plan ends, you can still read and export everything.").
**States.** Loading: skeletons. Offline: "Connect to see your plan." Error: "We could not load your plan. Your access has not changed. Try again." Pending purchase: "Your purchase is waiting for approval." Refunded credits: ledger row "Refund, 8 credits returned".
**Events.** `screen_viewed {screen: subscription}`, `restore_tapped {result}`, `purchase_started {product}` for a credit pack tap, `manage_subscription_tapped` (Change plan), `cancel_link_tapped {surface}`, `billing_page_viewed`.
**Accessibility.** The comparison table is a real table; the balance is text with the unit; price lines include period and the true monthly equivalent as plain text.

### 6.27 Paywalls for each trigger

All paywalls use the sheet in 4.14 and the rules in section 8. The trigger id is sent in `paywall_viewed {placement}`.

| Trigger id | When it fires | Headline | What it gives on this trip | Free path (equal weight) | Leading offer |
|---|---|---|---|---|---|
| `third_trip` | Create a third active trip on Free | "Two trips are active" | More active trips, invite people | "Archive a trip" (opens picker) | Plus annual |
| `second_route` | Add a second route on Free | "Watch a second route" | More routes with live checks | "Keep one route" (shows the preview of the second route's cached fares) | Trip Pass |
| `track_live` | Tap Track live or Refresh now without live access | "Live prices for this route" | Daily live checks for this trip, or one check for 1 credit | "Use cached fares" or "Check once, 1 credit" | Trip Pass |
| `alert_limit` | Second alert on Free | "Alerts on live fares" | More alert routes, live fares | "Keep my one alert" | Trip Pass |
| `invite` | Free owner asks for a second collaborator on a trip | "Plan together. They join free." | Up to 6 collaborators on this trip | "Keep my one collaborator" or "Share a read-only link" | Trip Pass |
| `out_of_credits_draft` | Draft with no credits | "Draft this day" | More credits | "Write it myself", plus a blurred preview of day one | Credit pack or Plus |
| `out_of_credits_research` | Research, Ask, Explain or Paste a booking with no credits | "Get 8 credits for one question" | One research question | "Not now" (a file or link import stays free) | Small pack (50 credits, $2.99) |
| `ninth_stay` | Save a ninth stay on Free | "Keep all your stays" | More saved stays per trip | "Keep it in Later" | Trip Pass |
| `export_footer` | Share or export a Free presentation | "Share without the footer" | No footer or watermark | "Share with the footer" | Trip Pass |
| `out_of_credits_verify` | Tap "Check places" (6.38) or "Recheck" (6.39) with fewer credits than it costs | "Check these places" | Credits for the places you picked | "Check fewer places" or "Not now" (the list of places stays free) | Credit pack or Plus |
| `out_of_credits_agent` | Deep agent run or fare hunt with fewer than 40 credits (taster already used) | "Run a deep search" | One deep agent run for 40 credits | "Not now" or use the cached result if one exists | Credit pack (150 credits) or Plus |
| `lifecycle_14d` | Message, not a sheet, 14 days before departure on a Free trip with dates (push or email, at most once per trip) | "Your fares moved this week" | Live checks until you fly | Open the route | Trip Pass |

Paywalls for scheduled routines, group tools, group passes, payment collection and households: Later: Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).

**On the web app** every paywall in this table is the same sheet without prices or a purchase button: the same headline and what it gives, the free path at equal weight, and a primary button "Upgrade in the iOS app" that opens the App Store page. There are no web purchases in Phase 1.

There is **no paywall** after an affiliate booking (only the soft "Plan your days" prompt), at first launch, inside present playback, during an agent run, in the import flow, the calendar feed sheet, the booked-fare alert, the list of places in Verify this plan, on the public web pages, on the taster result (it is a card, not a sheet), or on Account unless the person opens it. Default offer order when the trigger does not decide: Trip Pass first when the trip has dates within 120 days, annual Plus first when the person has two or more active trips.

### 6.28 Export and delete account

**Export.** Account, Export my data. Explains "We will email you a link to a zip with your trips as JSON, plus a readable PDF per trip. The link works for 7 days." Re-authentication (Apple, Google or code), a single [Export my data] button, then a progress row ("Preparing, usually under a day") and a notification when ready. Per-trip export (JSON, ICS, PDF) is also in Trip settings and is free on every tier. Limit: one export a day ("You asked for an export today. The link was sent to a***@gmail.com."). Error: "We could not start your export. Try again." Events: `export_requested`, `export_ready`.
**Delete account.** Account, Delete account (in app, no email or web only path). A full screen with a plain list of effects:

```
+------------------------------+
| < Account   Delete account   |
| This will:                   |
| - Sign you out everywhere    |
| - Delete your profile, AI    |
|   history and saved          |
|   travelers after 30 days    |
| - Delete trips only you are  |
|   in                         |
| - Remove you from shared     |
|   trips. Your edits stay as  |
|   "Deleted user"             |
|                              |
| Trips others are in (1)      |
|  Lisbon: [Transfer] [Delete] |
|                              |
| Your subscription is not     |
| cancelled by this.           |
| [Open subscriptions]         |
|                              |
| [ Export my data first ]     |
| [ Delete my account ]        |
+------------------------------+
```

Flow: list effects, choose what to do with trips others share (transfer to a member, or delete; if unchosen, deleted after 30 days unless a member accepts), re-authenticate, type "delete" or confirm with a destructive button, then a confirmation: "Your account is scheduled for deletion on 14 Nov. Sign in before then to restore it." The Apple Sign in token is revoked. Subscriptions are not cancelled by deletion and the screen links to the system subscriptions page without blocking. States: offline ("Connect to delete your account."), error ("We could not schedule deletion. Nothing was changed. Try again."). Events: `screen_viewed {screen: delete_account}`, `account_deletion_requested {had_subscription}`, `account_deletion_cancelled`. Accessibility: the destructive button is last in order, labeled with the consequence, and never the default focus.

### 6.29 Notifications

**Purpose.** Tell people what matters, never to sell.
**Permission.** Asked only after the first invite or the first price alert, through a reason screen: "Allow notifications so we can tell you when a fare drops or someone joins your trip." [Allow] [Not now]. Declining never blocks the feature; an in-app fallback shows in Activity.
**Types.** Price drop on a followed route (user requested), booked-fare drop (the fare you paid fell by at least 5 percent and $10, at most once a week per flight, 6.32), calendar changes found (6.30), a finished plan check (6.38), someone joined, someone changed the plan (digest, at most one an hour per trip), agent run finished, referral reward earned, trip starts tomorrow, leave for the airport (local notification, works offline), a single optional "7 days before departure" checklist reminder. **Never:** promotions, partner offers, credit sales, re-engagement nags, or any push whose only purpose is a click.
**Settings.** Account, Notifications: a switch per type, a quiet hours control (default 22:00 to 08:00 local), and per-trip mute. Email has its own list with one-click unsubscribe; marketing email is a separate opt-in.
**Copy.** Push titles are facts: "Lisbon: fare fell $42", "Ana joined Lisbon", "Research finished: 3 notes saved". No exclamation marks, no emoji.
**States.** Permission denied: row shows "Notifications are off in Settings" with "Open Settings". Offline: local notifications still fire.
**Events.** `push_prompt_shown {context}`, `push_permission_result {result}`, `notification_opened {type}`.
**Accessibility.** Notification text stands alone without the icon; in-app switches describe the event, not the mechanism.

### 6.30 Import a trip

**Purpose.** Bring a trip from TripIt, Tripsy, Wanderlog, Google Calendar, Google Maps or booking emails into Hermi without retyping it and without sharing a password.
**Layout.** Entry is the onboarding card below (shown once after the profile step, and as a quiet card on an empty Trips home), the "+" menu on Trips home, a trip's "..." menu ("Import into this trip") and Account. The flow is a full-screen modal in three steps with a progress label: **Choose a source**, **Check what we found**, **Done**.

```
+------------------------------+
| Coming from TripIt, Tripsy   |
| or Wanderlog?                |
|                              |
| Bring a trip over from a     |
| calendar file, a calendar    |
| link, booking emails or a    |
| list of places.              |
| No password needed.          |
|                              |
| [  Bring your trips over  ]  |
| [       Start fresh       ]  |
+------------------------------+
```

Step 1, choose a source:

```
+------------------------------+
| x   Import a trip   Step 1/3 |
|                              |
| Where are you coming from?   |
|                              |
| [ TripIt                 ]   |
|   Calendar file or link      |
| [ Tripsy                 ]   |
|   Calendar file or link      |
| [ Wanderlog              ]   |
|   Pasted places or emails    |
| [ Google Calendar        ]   |
|   File or secret address     |
| [ Google Maps list       ]   |
|   Exported file or places    |
| [ Something else         ]   |
|   File, link or booking      |
|   emails (1 credit each)     |
|                              |
| We never ask for a password. |
+------------------------------+
```

Step 2, check what we found:

```
+------------------------------+
| < Back   Check what we found |
| 18 found, 16 will be imported|
|                              |
| Fri 12 Mar                   |
| [x] Flight  JFK to LIS 18:05 |
| [x] Stay  Alfama loft        |
|     Check in 15:00           |
| Sat 13 Mar                   |
| [x] Tour  Sintra day trip    |
| [ ] Other  Dentist 09:00     |
|                              |
| Import to: New trip Lisbon,  |
| March  [Change]              |
|                              |
| [    Import 16 items      ]  |
+------------------------------+
```

Step 3, done:

```
+------------------------------+
| Imported to Lisbon, March    |
|                              |
| 16 items added: 2 flights,   |
| 1 stay, 13 plans.            |
|                              |
| Your first import includes   |
| a Trip Pass for Lisbon:      |
| live fare checks, up to 6    |
| collaborators and 40 credits |
| until 4 Dec.                 |
|                              |
| Keep checking this calendar  |
| every 6 hours          [off] |
| You confirm every change.    |
|                              |
| [       Open trip        ]   |
| [ Turn on calendar feed  ]   |
+------------------------------+
```

**Content.** Step 1 lists entries named for each app (plain text, no logos): TripIt, Tripsy, Wanderlog, Google Calendar, Google Maps list and "Something else". Choosing one opens the matching method with two or three steps for getting the data out of that app, checked against that app's own help pages before launch; where an app has no export we say so. The methods are: "Choose a calendar file" (the file picker for .ics files), "Paste a calendar link" (one field that accepts `webcal://` and `https://` links), "Paste booking emails" (a text area for up to 10 texts, each with a credit cost chip, 4.11, and the balance), "Choose a Maps export" (Takeout CSV, GeoJSON or KML, up to 200 places) and "Paste places" (one per line). The Google Maps entry says "We cannot open a Google Maps list link. Export the list, or paste the place names." A pasted Google Maps list link shows the same line with two export steps and "Keep this link as a note". A line under the rows says "We never ask for a password." Step 2 for places shows the matched place (name, address, small map) with "Not the right place" and untick; places import as ideas with no day.Step 2 lists everything found by day: a tick, a type icon with a text label (Flight, Stay, Activity, Other, never color alone), the title, time and place, and a "Change type" menu on each row. A large calendar adds a date range and type chips with "Select all in range". A destination row reads "Import to: New trip Lisbon, March" with "Change" to pick an existing trip. A sticky primary button reads "Import 16 items". Step 3 shows a Done ticket stub, the counts, the reward card when one was earned (the Trip Pass text below), for a calendar link the switch "Keep checking this calendar every 6 hours" (off by default, never turned on for the person, with the line "You confirm every change. Nothing is applied on its own."), and the buttons "Open trip", "Turn on calendar feed" (6.31) and "Import more". When changes arrive later, a notification and an Activity item open a "Calendar changed" sheet that lists each new, changed (before and after) and removed event with a tick and "Apply 3 changes"; removed events are listed but never deleted for the person, and "Not now" leaves the sheet for later.
**Interactions.** Choosing a file or sending a link or text starts reading at once and moves to step 2. Unticking rows changes the count. Pasted emails are read one at a time, each charged after the confirm; a text with no booking in it is refunded and says so. "Import" saves everything ticked; Back changes nothing. Imported booked flights offer the booked-fare watch (6.32) on the new trip. A guest who taps Import sees the Save your trip sheet first (6.2).
**States.** Loading: skeleton rows under "Reading your file", one row per pasted email as it finishes. Empty: "We did not find any trips or bookings in that file.", "Try another file, or paste a booking email.", [Paste a booking email]. Error: unreadable file "We could not read that file. Check that it is a calendar (.ics) file and try again."; too large "That file is too large. Export a shorter date range and try again."; over 500 events "That calendar has more than 500 events. Choose a date range."; blocked host "We do not open links from Airbnb, Vrbo or Booking.com. Download the calendar and upload the file instead."; link failed "We could not read that link. Check that it is the full link, or upload the file instead." Offline: "Connect to import. Nothing was changed." No permission: viewers cannot import into a trip; editors and owners can. Google Maps link "We cannot open Google Maps links. Export your list, or paste the place names."; more than 200 places "We imported the first 200 places."; polling stopped "We could not reach your calendar three times, so we stopped checking. Turn it back on any time."; Limit: text over 12,000 characters "That is too long. Paste one email at a time."; no credits for a pasted email opens `out_of_credits_research` (6.27) while the file and link routes stay free.
**Copy.** Above the button "Nothing is saved until you tap Import." Reward card "Your first import includes a Trip Pass for Lisbon: live fare checks, up to 6 collaborators and 40 credits until 4 Dec." The card appears only when the pass will be granted (3 or more items including a flight or a stay, a verified email, no active pass on the trip and no active Plus), never for a places-only import, and never as a paywall. No third-party logos are used.
**Events.** `import_started {method: ics_file|ics_feed|pasted|maps_file|places, source_app: tripit|tripsy|wanderlog|google_calendar|google_maps|other|unknown}`, `import_previewed {method, item_count_bucket}`, `import_completed {method, saved_count_bucket, reward_granted}`, `import_failed {method, reason}`, `calendar_polling_enabled`, `calendar_changes_found {change_count_bucket}`, `calendar_changes_applied {applied_count_bucket}`.
**Accessibility.** Each preview row is a checkbox with its full label ("Flight, JFK to LIS, Friday 12 March, 18:05, will be imported"); the count is a polite live region; the step label is announced; the file button, link field and text area have visible labels.

### 6.31 Calendar feed

**Purpose.** Put the trip in the person's own calendar app and keep it up to date.
**Layout.** A sheet from the trip "..." menu and Trip settings (owner only). A "Feed" switch (off by default), the link in mono, "Add to Apple Calendar", "Copy link", a switch "Include stay addresses" (off), the last time a calendar app read the feed ("Last read 2 h ago"), "Make a new link" and "Turn off".

```
+------------------------------+
| < Trip settings              |
| Calendar feed                |
|                              |
| Show this trip in Apple      |
| Calendar, Google Calendar or |
| Outlook.                     |
|                              |
| Feed                    [on] |
| hermi.world/cal/7Kq2...ics   |
| [ Add to Apple Calendar  ]   |
| [ Copy link              ]   |
| Include stay addresses [off] |
|                              |
| Changes show up on your      |
| calendar app's schedule,     |
| often within an hour and     |
| sometimes up to a day.       |
| Anyone with this link can    |
| see your schedule.           |
|                              |
| [ Make a new link ]          |
| Turn off                     |
+------------------------------+
```

**Content.** Turning the feed on creates the link and shows it. Under the buttons a one-line how-to for Google Calendar ("In Google Calendar, choose Other calendars, From URL, and paste the link") and Outlook. The two warnings are fixed copy: "Changes show up on your calendar app's schedule, often within an hour and sometimes up to a day." and "Anyone with this link can see your trip's schedule." No prices, private notes, confirmation numbers, traveler names or partner links are in the feed.
**Interactions.** "Add to Apple Calendar" opens the `webcal://` link. "Copy link" copies and shows a toast. "Make a new link" asks for confirmation ("The old link stops working right away.") and replaces it. "Turn off" revokes the link after a confirm.
**States.** Loading: skeleton switch and link. Empty: the off state. Error: "We could not create the link. Try again." Offline: "Connect to set up a calendar feed." No permission: only the owner sees the row; editors and viewers do not. Limit: none; one feed per trip.
**Copy.** Switch label "Calendar feed", helper "Show this trip in Apple Calendar, Google Calendar or Outlook."
**Events.** `calendar_feed_enabled`, `calendar_feed_link_copied {target: apple|copy}`, `calendar_feed_reset`, `calendar_feed_disabled`.
**Accessibility.** The link is selectable text with a labeled Copy button; switch states are text; confirmations are dialogs with focus rules from 4.19.

### 6.32 Booked-fare alert

**Purpose.** Tell a person who has already booked when the fare they paid drops, and send them to the airline's rules, never to a booking button.
**Layout.** Two parts. First, a sheet that opens after "Yes, mark as booked" on the fare detail (6.10) and after accepting an imported flight: "What did you pay?".

```
+------------------------------+
| What did you pay?            |
|                              |
| Total for 2 travelers        |
| [ $ 480.00          USD ]    |
|                              |
| Tell me if this fare [on]    |
|                              |
| We compare with fares we find|
| for the same airports and    |
| dates. A lower fare may be a |
| different flight. Airlines   |
| have their own change and    |
| credit rules.                |
|                              |
| [         Save          ]    |
| [         Skip          ]    |
+------------------------------+
```

Second, the "Your booked fare" block on the chosen-flight card and the route card:

```
+------------------------------+
| Your booked fare             |
| You paid                 $480|
| Lowest now               $431|
| cached, checked 3 h ago      |
| Down $49 since you booked    |
|                              |
| This is the lowest fare we   |
| found for those dates. It    |
| may be a different flight.   |
|                              |
| Airline change and credit    |
| rules (opens the airline)    |
| Alert me if it drops  [on]   |
+------------------------------+
```

**Content.** The amount is prefilled from the fare and editable; the currency follows the fare. The comparison uses the same airports, dates, cabin and traveler count, from cached fares and, where the trip has a live route, live checks. The block shows the current comparable fare with its source tag and age (4.5), the difference as words and an arrow ("Down $49 since you booked"), and the fixed line "This is the lowest fare we found for those dates. It may be a different flight." The link "Airline change and credit rules" opens the airline's own site, never a partner link. No Book button, partner card or paywall appears in this block or in the alert.
**Interactions.** "Save" stores the amount and the watch; "Skip" stores nothing and the block is not shown. The switch on the block turns the watch on or off. The alert (push and Activity) opens the block. An alert needs the fare to be at least 5 percent and at least $10 (converted) below what was paid, comes at most once a week per flight, and only for a new lower price. It never contains a partner link.
**States.** Loading: skeleton lines. Empty (no watch): a quiet row "Watch the fare you paid" with [Add what you paid]. Stale (comparable data over 48 hours old): "Fares are stale. We will check again soon." and no alert. Error: "We could not save that. Try again." Offline: readable, editing disabled. No permission: viewers see the block without the switch. Limit: none; it does not use the alert counts of 6.9.
**Copy.** Alert "You paid $480. It is now $431 (cached, checked 3 h ago). Check the airline's change and credit rules." Push title "Lisbon: fare fell to $431". The copy never says refund, credit owed, or savings guaranteed.
**Events.** `booked_fare_saved {watch: on|off}`, `booked_fare_watch_changed {value}`, `booked_fare_alert_opened`, `booked_fare_rules_opened`.
**Accessibility.** The price change is announced as text; the money field is labeled with currency ("Amount paid, US dollars"); the switch has a state label.

### 6.33 Offline reading and sync

**Purpose.** Make every trip readable with no signal, on every tier, and show what is saved.
**Layout.** A row in Trip settings, "Available offline", opens the block below. The app also shows the offline banner (4.21), the "Saved offline" chip on trip cards (4.4) and the "Waiting to sync" chip on queued edits.

```
+------------------------------+
| < Trip settings              |
| Available offline            |
|                              |
| Lisbon, March                |
| Downloaded 3 Oct, 18 MB      |
| Saved: plan, flights, stays, |
| checklist, notes, map tiles  |
|                              |
| [ Update download ]          |
| [ Remove download ]          |
|                              |
| Trips you opened in the last |
| 30 days are saved for reading|
| automatically.               |
+------------------------------+
```

**Content.** Trips opened in the last 30 days (up to 10) save their plan, flights and fares with age, stays, checklist, notes, evidence labels and travelers automatically. "Download for offline" adds map tiles for the trip area and shows its size first ("About 18 MB"). Sync state is plain text ("3 edits waiting to sync"), and every trip screen shows the sync indicator (4.21): "Synced 12 s ago" from the last successful sync, "Syncing", "Offline, 3 edits waiting", or "Could not sync, retrying" after three failed polls; tapping it syncs now.
**Interactions.** "Update download" refreshes tiles; "Remove download" frees space after a confirm. Edits made offline queue and send on reconnect, last writer wins per field, and a 409 opens the conflict sheet (6.12). Reading needs no setup.
**States.** Loading: size estimate skeleton. Empty: "Not downloaded yet. Your plan is still saved for reading." Error: "We could not download the map. Your plan is still saved." Offline: the block is readable, Download is disabled ("Connect to download"). No permission: all members can read offline; viewers cannot queue edits. Limit: a trip beyond the 10 most recent shows "Open it once online to save it." Storage full: "Your phone is almost full. Remove a download to save this trip."
**Copy.** Banner `offline_banner` and `saved_offline` (7.5). No partner content is shown offline.
**Events.** `offline_download_started`, `offline_download_completed {size_bucket}`, `offline_download_removed`, `sync_completed {queued_count_bucket}`, `sync_indicator_tapped {state}`.
**Accessibility.** Sync and offline changes are polite announcements; sizes and dates are text; the chip states are words with icons.

### 6.34 Shared-trip page (public)

**Purpose.** Let someone with a link read the trip in a clean page, with no app and no account.
**Layout.** The marketing shell: a light top bar with the light lockup (mark 28 px) and a "Get the app" button, a 720 px reading column, no sidebar and no tab bar, and a footer with Terms, Privacy and How we earn. The page is the route `/s/:shareId`. On phones a sticky bottom bar offers "Plan your own trip"; it is a link, never a paywall or an interstitial, and it can be dismissed for the session.

```
+------------------------------+
| [H] Hermi       Get the app  |
| [route pattern band]         |
| LISBON     12 to 19 Mar      |
| Shared by a Hermi traveler   |
|                              |
| Day 1  Fri 12 Mar            |
|  09:30 Alfama walk           |
|     Found on lisboa.pt,      |
|     checked 12 Sep           |
|  13:00 Lunch, Time Out Market|
|                              |
| [  Plan your own trip  ]     |
| Made with Hermi     Report   |
+------------------------------+
```

**Content.** A route pattern band (seeded by the trip), destination, dates, and the day by day plan with a map. Redaction follows the owner's switches (lodging address, prices, notes and traveler names are hidden by default). Every AI-found item shows its evidence label. Free trips show "Made with Hermi" in the footer. Partner links follow 4.13 and can be turned off by the owner. "Report this page" sits in the footer. The owner sets, in the share sheet in Present (6.19), the expiry, the redaction switches and "Let search engines list this page" (off by default); off pages are not indexed.
**Interactions.** Read, open a day, open the map, "Get the app to edit" (universal link, then App Store), "Plan your own trip" (guest mode). Nothing on the page needs a sign-in.
**States.** Loading: skeleton title and day rows. Empty trip: "There is nothing to show yet." Error: "We could not load this page. Try again." Offline: the browser's own offline page. Expired or revoked: "This link is no longer active. Ask the person who shared it for a new one." No permission: not applicable, the link is the permission. Limit: over the view throttle, "Too many views. Try again in a few minutes."
**Copy.** Footer "Made with Hermi". Redacted traveler names read "Traveler 1".
**Events.** `public_page_viewed {page: shared}`, `public_cta_tapped {page, cta}`, `share_page_reported`.
**Accessibility.** One `h1`, each day a heading, skip link, the map has a list equivalent, text at least 16 px, evidence label links say "Found on lisboa.pt, checked 12 Sep, opens in a browser".

### 6.35 Sample trips (public)

**Purpose.** Show a finished plan so a visitor understands Hermi, with no account.
**Layout.** The marketing shell. `/samples` is a grid of 4 to 6 trip cards (4.4, with a "Sample" chip instead of status) in one or two columns by width, with a line "Trips written by the Hermi team. Prices and facts are dated." `/samples/:slug` is the shared-trip page (6.34) with a "Sample trip" banner, a stay shortlist with hearts, the checklist, a fare chart labeled "Sample data, dated 12 Sep", and a sticky "Copy this trip" button.
**Content.** Every price and fact carries a date, and AI-found facts carry the evidence label. Nothing is presented as a current price. The gallery is a fixed list; there is no search, no feed and no user trips.
**Interactions.** "Copy this trip" duplicates the structure (destinations, plan, stays without votes, checklist) into the visitor's account or a guest trip; a guest lands in the app in guest mode with no sign-in wall. "Plan a trip" opens Create trip.
**States.** Loading: card or page skeletons. Empty: not applicable, the list is fixed. Error: "We could not load this sample. Try again." Offline: browser page. Limit: a guest who already has a guest trip sees "Guests can plan one trip. Create a free account to add more." (6.2).
**Copy.** Banner "Sample trip. Prices and facts are dated and may have changed."
**Events.** `public_page_viewed {page: sample, slug}`, `sample_trip_copied {slug, was_guest}`, `public_cta_tapped {page, cta}`.
**Accessibility.** As 6.34; cards are single links with destination, length and "Sample" in the name.

### 6.36 Comparison pages (public)

**Purpose.** Give an honest side by side with another planner so a person can choose, and make switching easy.
**Layout.** The marketing shell, route `/vs/:competitor` (launch pages `/vs/tripit`, `/vs/wanderlog`, `/vs/tripsy`). Order: title, "Last checked" date, a short summary, two "Choose X if" blocks, the comparison table, "Where <name> is the better choice", "Switching from <name>" with the import link, and "How we wrote this".

```
+------------------------------+
| Hermi and TripIt             |
| Last checked 12 Sep 2026     |
|                              |
| Choose Hermi if you plan     |
| with a partner and want fare |
| tracking. Choose TripIt if   |
| you mostly organize bookings.|
|                              |
| Feature    Hermi     TripIt  |
| <claim>    <fact>    <fact>  |
|            checked   checked |
|            12 Sep    12 Sep  |
|            [Source]  [Source]|
|                              |
| Switching from TripIt?       |
| [ Import your TripIt trips ] |
+------------------------------+
```

**Content.** The table is a real table: each row has the feature, Hermi's value, the other product's value, and under every claim about the other product a "Checked 12 Sep" label with a "Source" link to that product's own page. A claim that cannot be sourced is not in the table. Prices show currency and date. Hermi's own limits are stated (for example, no Android app until Phase 2). No affiliate links, no partner cards, no competitor logos (names are plain text), no "best" or "deal" words. The import button names the source ("Import your TripIt trips") and opens 6.30; for Wanderlog it reads "Bring your trips over". A line at the end states the review date and that pages are re-checked at least every 90 days.
**Interactions.** Read; open sources in a new tab; "Import your TripIt trips" (signs in or starts guest mode first, then 6.30); "Plan a trip".
**States.** Loading: skeleton table. Error and not found: "We could not find that page." with links to the other comparisons. Offline: browser page. Stale review (over 90 days): the page is unpublished until re-checked, it does not show an old date. Limit: none.
**Copy.** Title "Hermi and TripIt". Table note "Each claim about TripIt links to its source and shows when we checked it."
**Events.** `public_page_viewed {page: vs, slug}`, `public_cta_tapped {page, cta}`.
**Accessibility.** The table has column and row headers; source links say "Source for this claim, opens in a browser"; the page reads in the same order visually and in code.

### 6.37 Invite friends and referral code

**Purpose.** Let a person share Hermi and be thanked with credits, plainly and without pressure.
**Layout.** Account, "Invite friends": a card with the rule, the person's link and code, "Share your link" (native share sheet), "Copy code", and a progress block (friends joined, credits earned, the yearly limit).

```
+------------------------------+
| < Account   Invite friends   |
|                              |
| You and a friend each get 20 |
| credits after their first    |
| trip with dates. Credits last|
| 12 months.                   |
|                              |
| Your link                    |
| hermi.world/r/MAYA7K         |
| [ Share your link ]          |
| [ Copy code MAYA7K ]         |
|                              |
| 2 friends joined             |
| 20 credits earned            |
| Up to 5 rewards a month      |
+------------------------------+
```

**Content.** The rule in words: "You and a friend each get 20 credits after their first trip with dates. Credits last 12 months." The limits are stated plainly: "You can earn for up to 5 friends in 30 days and 10 a year." No friend names are shown. No countdowns, no levels, no nags. A friend enters a code from the sign-in screen ("Have a friend's code?", one field) or arrives by the link `hermi.world/r/<code>` (web landing, then the app through the universal link).
**Interactions.** Share opens the native sheet. Applying a code shows "Code applied. You will get 20 credits after you create your first trip with dates." Rewards arrive as promo credits (F-SUB-4) with an Activity item and at most one push.
**States.** Loading: skeleton card. Error: "We could not load your link. Try again." Offline: the code is readable and Share works; applying a code waits ("Connect to apply a code."). Invalid code: "That code is not right. Check it and try again." Own code: "That is your own code." Already used: "You already used a code on this account." Limit: "You have reached the limit for rewards (5 in 30 days, 10 a year). Friends you invite still get theirs." Not eligible (existing account): "Codes are for new accounts."
**Copy.** Button "Share your link". Reward line "Friend joined. 20 credits added."
**Events.** `referral_link_shared {method}`, `referral_code_applied {result}`, `referral_reward_earned {role: referrer|friend}`.
**Accessibility.** The code is selectable text with a labeled Copy button; progress is text ("2 friends joined, 20 credits earned"); errors are linked to the field.

### 6.38 Verify this plan

**Purpose.** Let someone who planned in ChatGPT, Gemini, Layla or Mindtrip paste the plan and see which places, hours and prices hold up, with the source for each, then keep only what checked out.
**Layout.** Entry: Trips home "+" menu, a trip's "..." menu, the import screen and the AI sheet (6.15). A full-screen modal in four steps with a progress label: **Paste the plan**, **Choose what to check**, **Results**, **Add to trip**. It runs inside a trip; from Trips home it offers "Start a trip to check it" (named from the first destination) or "Check it inside one of your trips".

Step 1, paste the plan:

```
+------------------------------+
| x   Verify a plan   Step 1/4 |
|                              |
| Paste a plan from ChatGPT,   |
| Gemini, Layla or Mindtrip.   |
| We check each place, its     |
| hours and its price.         |
|                              |
| [ text area, 8,000 max ]     |
|                              |
| Written by  (o) ChatGPT      |
|             ( ) Gemini ...   |
|                              |
| [ Read the plan   1 credit ] |
|                              |
| We do not open links in the  |
| text and do not save it.     |
+------------------------------+
```

Step 2, choose what to check:

```
+------------------------------+
| < Back    Choose what to     |
|           check   Step 2/4   |
| 9 places found               |
|                              |
| Day 1                        |
| [x] Time Out Market          |
|     Open 10:00 to 00:00      |
| [x] Castelo de S. Jorge      |
|     Ticket 15 EUR            |
| [ ] Miradouro da Graca       |
| Day 2                        |
| [x] Pasteis de Belem         |
|     ...                      |
|                              |
| Free checks up to 5 at a time|
| [ Check 5 places  5 credits ]|
+------------------------------+
```

Step 3, results:

```
+------------------------------+
| < Plan check        Step 3/4 |
| Checked 7 of 9. 5 confirmed, |
| 1 differs, 1 not found.      |
| 2 not checked.               |
|                              |
| [check] Confirmed            |
| Time Out Market              |
|  Found on timeout.com,       |
|  checked today               |
| [warn] Differs               |
| Pasteis de Belem             |
|  Closed Mondays. Your plan   |
|  has Monday at 10:00.        |
|  Found on pasteisdebelem.pt, |
|  checked today               |
| [x] Could not find it        |
| Rooftop Bar Vista Nova       |
|  No place or page matches.   |
| [-] Not checked              |
| Miradouro da Graca           |
|  Over your 5 check limit.    |
+------------------------------+
```

**Content.** Step 1 has a text area (8,000 characters, a counter), an optional "Written by" choice (ChatGPT, Gemini, Layla, Mindtrip, Other; shown, never trusted), and the button "Read the plan" with a credit chip of 1. Step 2 lists up to 25 items grouped by the day in the plan, each with a tick, the place, and the hours or price the plan states. The bottom bar shows the price before anything runs ("Check 5 places, 5 credits") and how many the account can check at once (5 on Free, 12 on Plus and Trip Pass); ticking past the limit is blocked with "Free checks 5 at a time. Check the rest in another run." A confirm sheet appears at 6 credits or more with the balance before and after (4.11). Step 3 shows the result header, then one row per item: a verdict chip (4.21), the place name, a one-line reason in plain words, the evidence label ("Found on [site], checked [date]", a link), and, for differences, what the source says. Red rows say "Could not find it" and what was tried. Items not checked say why (over the limit, cost limit reached, Airbnb, Vrbo or Booking.com page never opened, service error with the credit returned). Step 4 lists the items that can be added: green rows ticked, amber rows unticked until opened, red rows unticked and marked "Not found", with a day picker per item and "Add to Lisbon" (free, nothing is saved until the tap).
**Interactions.** "Read the plan" reads the text and moves to step 2. "Check" starts the run; progress streams row by row (a spinner per row turns into its chip), the person can leave and a push and Activity item announce the finish (F-NOT-1 "plan check finished"), and Stop ends the run and returns the credits for items not yet checked. A second run checks the remaining items. Results stay on the trip under "Plan checks" for 30 days. "Discard" deletes the result and its evidence. The pasted text is never stored.
**States.** Loading: row skeletons under "Reading your plan", then one spinner per row. Empty: "We could not find places in that text. You were not charged." with [Try another text]. Error: "That did not finish. The places we could not check were not charged." with Retry. Offline: "Checking needs a connection." and the text area keeps the paste. No permission: viewers can read results but not start a check. Limit: text over 8,000 characters "That is too long. Paste one trip at a time."; more than 25 places "We read the first 25 places."; too many ticked "Free checks 5 at a time."; no credits opens `out_of_credits_verify` (6.27); AI off for the trip "AI is off for this trip. Ask Sam to turn it on."; the Free owner at the 2 trip limit sees "Check it inside one of your trips." Partial: a row that could not be checked keeps "Not checked" and its credit is returned. Web: identical; the credit paywall says "Upgrade in the iOS app" (6.27).
**Copy.** Step 1 helper "We do not open links in the text and we do not save it." Header `verify_header` (7.5). Never "verified" for the whole plan and never "safe to book". Verdict words are Confirmed, Differs, Partly confirmed, Could not find it, Not checked. No partner link, card or paywall sits on the results.
**Events.** `verify_started {label, text_length_bucket}`, `verify_items_read {item_count_bucket}`, `verify_checked {selected_count_bucket, green, amber, red, unchecked, credits}`, `verify_imported {item_count_bucket}`, `verify_discarded`.
**Accessibility.** Each row is one checkbox or link with its full label ("Confirmed. Time Out Market, Day 1. Found on timeout.com, checked today"); verdicts are words and icons, never color alone; the header count is a polite live region; progress announces "Checked 3 of 5"; the step label is announced.

### 6.39 Evidence freshness and recheck

**Purpose.** Keep the "every fact links to its source" promise honest over time: say when a finding is old, and let the person ask again in one tap.
**Layout.** Not a screen of its own. The evidence label (4.21) and evidence rows on Notes and evidence (6.18), the agent run findings (6.16), plan check results (6.38) and imported plan items gain a second line when the label date is more than 14 days old.

```
+------------------------------+
| Tram 28 is often crowded     |
| after 10:00                  |
| Found on lisbon-guide.org,   |
| checked 12 Sep               |
| [! May be out of date]       |
| [ Recheck   1 credit ]       |
+------------------------------+
```

**Content.** The amber chip "May be out of date" (icon and words) and a "Recheck" button with a credit chip of 1. Nothing is hidden, removed or greyed out. Editors and owners see the button on any finding at any age ("Recheck now"); viewers see the chip only. Fares are not rechecked here: they keep their age tag and "Refresh now" (6.10).
**Interactions.** "Recheck" opens the stored source page once and answers in a small sheet: "Still the same. Checked today." (the label date moves to today), "It now says: {new value}" with the source and [Save as a note] (the old text stays), "The page no longer shows this." or "We could not reach the page. You were not charged." A recheck never searches the web, never opens Airbnb, Vrbo or Booking.com, and never edits the item on its own.
**States.** Loading: the button turns into "Checking" with a spinner. Error: "That did not finish. You were not charged." Offline: "Recheck needs a connection." Limit: no credits opens `out_of_credits_verify` (6.27); AI off for the trip hides the button. Not applicable: fares, Wikipedia text and notes people wrote never show the chip.
**Copy.** Chip `evidence_old`, button `recheck_button` (7.5).
**Events.** `evidence_stale_shown {age_bucket}`, `evidence_rechecked {result: confirmed|changed|not_shown|unreachable, credits}`.
**Accessibility.** The chip is text plus icon; the button name includes the subject ("Recheck: Tram 28 is often crowded"); the result sheet is a polite announcement.

### 6.40 Trust pages: How we earn and How billing works

**Purpose.** Show, in plain words and before anyone asks, how Hermi makes money and how billing works.
**Layout.** Two public pages in the marketing shell (6.34): `/how-we-earn` and `/billing`. The same content opens in the app from Account (6.25) and the paywall legal row. A 720 px reading column, short headings, no affiliate card, no paywall, no banner.

```
+------------------------------+
| How we earn                  |
|                              |
| Hermi is paid for by         |
| subscriptions, Trip Passes,  |
| AI credits and commissions   |
| when you book through a      |
| partner link.                |
|                              |
| What we promise              |
| - Nothing is ranked by       |
|   commission.                |
| - Every partner link is      |
|   labeled.                   |
| - No ads. We never sell your |
|   data.                      |
| - We never fetch Airbnb,     |
|   Vrbo or Booking.com pages. |
|                              |
| Our partners (18 in 7        |
| categories)                  |
| Flights: Aviasales, Kiwi.com |
| Stays: Booking.com, Agoda    |
| ...                          |
+------------------------------+
```

**Content.** How we earn: the sentence above, the four promises, a sample partner button with its label ("We earn a commission if you book here."), the "Hide booking links" setting, the list of every active partner grouped by category with its disclosure line, and live counts of partners and categories, all generated from the same partner list the app uses so a new partner cannot appear without being listed. How billing works (`/billing`): prices and renewal for Plus monthly and annual; the 7-day trial on annual, the reminder 2 days before it converts and what happens on day 8; Trip Pass is one time, 90 days, never renews; credit packs are one time and last 12 months; how to cancel (a button "Cancel subscription" that opens the App Store's subscription sheet on an iPhone, or explains where to find it on the web); what stays after cancelling; refunds go through Apple and what Hermi can do; no card details are stored; purchases are in the iOS app only for now; what stays free. Prices come from the paywall configuration so the page and the paywall cannot disagree.
**Interactions.** Links to the page appear in Account, every paywall's legal row, the plan and credits screen (6.26), every `/vs` page and the App Store listing. Each partner name is plain text, never a link.
**States.** Loading: a text skeleton. Error: "We could not load this page. Try again." Offline: the last loaded copy with its date. Not applicable: empty, permission, limit.
**Copy.** Titles "How we earn" and "How billing works". No em dashes; sentence case.
**Events.** `how_we_earn_viewed {source}`, `billing_page_viewed {source}`, `cancel_link_tapped {surface}`.
**Accessibility.** One `h1`; partner lists are real lists; the cancel button has a visible label; no content lives only in an image.

### 6.41 Service status and sync indicator

**Purpose.** Let a person tell in seconds whether a problem is theirs or ours.
**Layout.** Two parts. The **sync indicator** (4.21) sits on every trip screen: "Synced 12 s ago", with states Syncing, "Offline, 3 edits waiting" and "Could not sync, retrying". The **status page** is hosted outside Hermi's own servers at `status.hermi.world` (opened from Account, Help and support, "Service status", and from the `/status` redirect): five components (web app, API, AI features, fare data, push), each operational, degraded or down, 90 days of uptime, and incidents with times in plain words.
**Content.** The app shows a banner (4.21) only when the public status summary reports a degraded component: "Fares are delayed right now. Saved trips still work." with a "Service status" link. A single person's failed request never produces the banner.
**Interactions.** Tapping the sync indicator runs a sync now and shows the new time. Tapping the banner opens the status page in the in-app browser.
**States.** Loading: the indicator reads "Syncing" after 150 ms. Offline: the banner and the indicator both say so ("Offline, 3 edits waiting"). Error: "Could not sync, retrying" after three failed polls, with "Try now". Not applicable: empty, permission, limit.
**Copy.** `sync_ago`, `sync_offline`, `status_banner` (7.5).
**Events.** `sync_indicator_tapped {state}`, `status_banner_shown {component}`, `status_page_opened {source}`.
**Accessibility.** The indicator is text and an icon, not color alone; it is not a live region for each tick, and a change of state is announced once, politely; the status page is tested with the same checks as the public pages.

### 6.42 Android install guide

**Purpose.** Let Android users use Hermi as an installed app from the browser, and make it clear what works, until a native app exists.
**Layout.** A public page `/install/android` in the marketing shell, reached from Account, Help and support, "Install on Android", and from a dismissible card on Android Chrome. The page shows three short numbered steps with a screenshot each, then two lists.

```
+------------------------------+
| Use Hermi on Android         |
|                              |
| 1 Open hermi.world in Chrome |
| 2 Tap the menu (three dots)  |
| 3 Tap Install app, or Add to |
|   Home screen                |
|                              |
| What works                   |
| - Plan, edit and share trips |
| - Read trips offline         |
| - Plan with friends on       |
|   iPhone                     |
|                              |
| Not yet                      |
| - Push alerts (we email      |
|   price drops instead)       |
| - A Play Store app           |
+------------------------------+
```

**Content.** The steps for Chrome, with a note for Samsung Internet. "What works": full planning and editing, sharing, reading offline, invites. "Not yet": push notifications (price drops and invites arrive by email) and a Play Store app ("A native Android app is planned"). The web app has a manifest (name, icons, theme color, standalone display) and a service worker that keeps opened trips readable offline.
**The card.** On Android Chrome a dismissible card "Add Hermi to your home screen" appears on Trips home after the person has created a trip, never on the first screen, never as a modal, at most once every 30 days. Its button uses the browser's own install prompt where Chrome provides one, and otherwise opens this page.
**Interactions.** "Install" triggers the browser prompt; "Not now" hides the card for 30 days; the page links to Help.
**States.** Loading: static content, no loading state. Already installed: the card does not appear and the page says "Hermi is installed on this phone." Not Chrome: the page shows the steps for Samsung Internet and Firefox, and "Other browsers may differ." Offline: the page is readable from the service worker. Not applicable: empty, error, permission, limit.
**Copy.** Card "Add Hermi to your home screen" with [Install] and [Not now]. No claim of a store app or push that does not exist.
**Events.** `android_install_card_shown`, `android_install_prompted {result: accepted|dismissed}`, `android_install_guide_viewed {source}`, `pwa_installed`.
**Accessibility.** Steps are an ordered list; screenshots have text alternatives that repeat the step; the card is reachable in order and dismissible by keyboard.

## 7. Microcopy rules

### 7.1 Voice and form

1. **Sentence case** for every heading, button, label, tab and toast ("Add a stay", not "Add A Stay"). Proper nouns keep capitals. `type-label` and `type-code` are styled uppercase through CSS only.
2. **Plain verbs.** Save, Add, Invite, Book, Open, Undo, Remove. Not "Utilize", "Leverage", "Initiate", "Submit". Buttons say what happens ("Start research", not "Continue").
3. **No em dashes or en dashes, anywhere.** Use a comma, a period or "to" for ranges ("12 to 19 Mar", "4 to 6 guests"). Hyphens only inside compound words and in technical strings. A lint rule in CI greps UI strings and docs for U+2013 and U+2014 and fails the build.
4. **Short.** Buttons one to three words. Toasts one sentence. Helper text one sentence. Explain the reason, not the feature.
5. **Second person, present tense, calm.** "You are offline", not "Connection lost!". No exclamation marks except in a success ticket stub the person earned (and even then sparingly), no emoji in product copy, no jokes in errors.
6. **Names over pronouns for people:** "Sam added a stay". Dates as "12 Mar" in lists, "Friday 12 March" in headings, times in the person's 12 or 24 hour setting.
7. **Numbers.** Always digits in UI ("3 stays"). Currency with the code when ambiguous ("$412" for the home currency, "EUR 380" for another). Counts agree with the noun ("1 credit", "8 credits").

### 7.2 Errors

An error message has three parts, in order: what happened, why if known, and how to fix it. It never blames the person, never shows a raw code, and always offers a next step. Examples:

| Situation | Copy |
|---|---|
| Network down | "You are offline. Your trip is saved on this phone. Changes will sync when you reconnect." |
| Server error | "Something went wrong on our side. Your work is saved. Try again in a minute." |
| Validation | "Enter an end date after 12 Mar." |
| Not found or no access | "This trip is not available. It may have been deleted, or you may not have access. Ask the person who shared it." |
| Conflict | "Sam changed this while you were editing. Review their version, then save yours if you still want to." |
| Rate limit | "Too many tries. Wait 10 minutes and try again." |
| Out of credits | "You have 3 credits and this costs 8. Get more credits, or ask something smaller." |
| Purchase failed | "The purchase did not go through and you were not charged. Try again, or check your payment method in Settings." |
| Partner link down | "We could not open that booking site. You can search on the airline's site instead." |

### 7.3 Prices, credits and money

1. Prices show currency symbol or code, the period and what they cover ("$39.99 a year, about $3.33 a month"). Subscriptions state the renewal date and how to cancel.
2. Fares always carry age and source ("$412, cached, checked 3 h ago") and "Prices can change on the booking site." No "from" prices in headlines without the date.
3. Credits are always "credits", shown with their cost before the action ("Costs 8 credits. You have 27."). Never dollars for AI. A cached result says "1 credit, from shared cache". Refunds say "No charge" or "Returned 8 credits".
4. Totals and per-person amounts both appear where a group is involved ("$870 each, $3,480 total").
5. Words never used: "free" for anything with a catch (say "Free, one time" or "Included"), "unlimited" (use "fair use 25 trips" or real numbers), "best price", "lowest price guaranteed", "deal", "hurry", "last chance", "only 2 left", "save up to". Comparisons say "Lowest in this list".
6. Trials state the price after the trial and the date it starts ("7 days free, then $39.99 a year from 7 Oct").

### 7.4 Commission disclosure wording

- The sentence, exact and fixed: **"We earn a commission if you book here."** It appears beside every partner button (4.13), in the Before you go rows, in present mode's optional last slide, in printed PDFs, and in email where a partner link appears.
- UK and EU storefronts add an "Ad" tag before the eyebrow. Partner-mandated text (for example Booking.com) is added after our sentence.
- Sort statements: "Sorted by price, lowest first", "Sorted by distance", "Sorted by hearts". Never "recommended" or "top picks" for anything that can carry a commission.
- Neutral links: "We never change your links." on import, and "Open" on a saved item opens the pasted URL unchanged.
- How we earn money (Account) explains the model in four sentences and lists partners.
- AI output never includes partner names, links or disclosure (it has none).

### 7.5 Reusable strings

| Key | Copy |
|---|---|
| `offline_banner` | "You are offline. You can read your trip and check things off." |
| `saved_offline` | "Saved offline, updated 2 h ago" |
| `waiting_to_sync` | "Waiting to sync" |
| `limited_trip` | "This trip is limited. Extra travelers are now viewers. Renew to restore editing. Your data is safe and you can export it any time." |
| `ai_disclaimer` | "Drafted by AI from your dates and places. Check hours and prices." |
| `fare_age` | "Checked 3 h ago" |
| `no_charge` | "No charge. That did not finish." |
| `restore_done` | "Purchases restored." |
| `restore_none` | "We did not find any purchases to restore for this Apple ID." |
| `evidence_label` | "Found on {site}, checked {date}" |
| `evidence_stale` | "Source not checked since {date}" |
| `evidence_old` | "May be out of date" |
| `recheck_button` | "Recheck" |
| `sync_ago` | "Synced {n} s ago" |
| `sync_offline` | "Offline, {n} edits waiting" |
| `verify_header` | "Checked {checked} of {found}. {green} confirmed, {amber} differ, {red} not found. {unchecked} not checked." |
| `web_upgrade` | "Upgrade in the iOS app" |
| `cancel_row` | "Cancel subscription" |
| `status_banner` | "{thing} is delayed right now. Saved trips still work." |
| `import_reward` | "Your first import includes a Trip Pass for {trip}: live fare checks, up to 6 collaborators and 40 credits until {date}." |
| `import_unsaved` | "Nothing is saved until you tap Import." |
| `feed_delay` | "Changes show up on your calendar app's schedule, often within an hour and sometimes up to a day." |
| `feed_public` | "Anyone with this link can see your trip's schedule." |
| `booked_drop` | "You paid {paid}. It is now {now} ({source}, checked {age}). Check the airline's change and credit rules." |
| `booked_caveat` | "This is the lowest fare we found for those dates. It may be a different flight." |
| `referral_rule` | "You and a friend each get 20 credits after their first trip with dates. Credits last 12 months." |

## 8. Paywall design rules

**Mockup:** [screens/07-paywall.html](design/screens/07-paywall.html) <img src="design/png/07-paywall.png" width="260" alt="Paywall sheet in light mode: a sky header with a route pattern, two plan tickets with their prices on the stubs, and equal-weight purchase and Not now buttons"> <img src="design/png/07-paywall-dark.png" width="260" alt="The same paywall sheet in dark mode">

1. **The free path is always visible.** "Not now" (or the specific free action) is a full-size button of equal weight, in the same row or directly under the primary button. It is never a small gray X, a hidden link or a swipe-only dismiss. The scrim tap and swipe down also dismiss.
2. **No paywall before value.** None at first launch, on the splash, in guest mode before a limit, or before the person has built something.
3. **One per session.** At most one paywall sheet is shown per app session. Further triggers in the same session show an inline locked state with the free path, not a sheet.
4. **7-day mute.** Dismissing a paywall mutes that trigger for 7 days (server side, per account and trigger, so it follows across devices). The action the person wanted is either blocked with the free alternative or simply not offered; it does not reappear as a nag. Buying ends the mute.
5. **Say what it gives on this trip.** The first line after the headline names the concrete result for this trip ("Live prices for Lisbon until 4 Dec"), with real numbers from [01-product-spec.md](01-product-spec.md), section 1.4.
6. **Up to three options**, in this order of prominence, chosen by the rules in 6.27: Trip Pass (lead when the trip has dates in the next 120 days), Plus annual (pre-selected where it is the lead subscription), Plus monthly under "More options". Credit packs appear only at credit triggers. Family and Pro arrive in Phase 2, see [../phase-2-growth/README.md](../phase-2-growth/README.md).
7. **Annual is pre-selected with the true monthly equivalent**: "Plus annual, $39.99 a year, about $3.33 a month" next to "Plus monthly, $5.99 a month". The saving is stated as a number ("Save $31.89 a year"), never a percent alone or a crossed-out fake price.
8. **Trials and renewals are plain.** The trial line reads "7 days free, then $39.99 a year from 7 Oct. Cancel any time in Settings." with a link to "How billing works". A reminder with the one-tap cancel link is sent 2 days before conversion. No trial for Trip Pass or credit packs.
9. **Restore purchases** is a visible text button on every paywall and on the Plan and credits screen. It shows a result either way (`restore_done`, `restore_none`).
10. **No countdowns, no invented scarcity, no "limited offer", no pre-checked upsell add-ons, no confirmshaming** ("No thanks, I like paying more"). The free button says "Not now" or names the free action.
11. **Legal row** under the buttons: price and period, renewal, cancellation (with a link to How billing works), Terms, Privacy. 12 px minimum, never hidden. On the web app there is no price or purchase button: the primary button reads "Upgrade in the iOS app".
12. **Never next to affiliate content** and never on the same screen as a partner card. After an affiliate booking there is no paywall.
13. **Confirm credit spends, do not paywall them.** Spending credits is a confirm sheet (6.15), not a paywall; it appears for 6 credits or more and always shows the balance after.
14. **Resume the task.** After a purchase the sheet closes with a ticket stub touchdown, the blocked action resumes (the route is added, the invite sheet opens) and the plan or pass is bound to the trip when it applies ("Apply to Lisbon?" picker for a Trip Pass).
15. **Downgrades never take data.** Copy and behavior follow `limited_trip`. Archived trips stay readable and exportable forever on Free.
16. **Measure without manipulating:** events `paywall_viewed {placement, offer_shown}` (the trigger id from 6.27 is the `placement`), `paywall_dismissed {placement}`, `purchase_started {product, period}` (choosing an option and tapping the purchase button are one event), `purchase_completed {product, period, is_trial}`, `purchase_failed {product, reason}` (a cancelled sheet is `reason: cancelled`), `restore_tapped {result}`.

```
+------------------------------+
|            ------            |
|    (static route pattern)    |
| Plan together. They join     |
| free.                        |
| Invite up to 6 people to     |
| Lisbon, with live fares until|
| 4 Dec.                       |
|                              |
| (o) Trip Pass   $9.99 once   |
|     90 days, this trip       |
| ( ) Plus annual  $39.99 a yr |
|     about $3.33 a month      |
| More options                 |
|                              |
| [ Get Trip Pass  $9.99 ]     |
| [      Not now          ]    |
| Terms  Privacy  Restore      |
| purchases                    |
+------------------------------+
```

## 9. Accessibility

Target: **WCAG 2.2 level AA** on web and iOS, plus Apple's Human Interface accessibility guidance. Accessibility is part of the definition of done for every screen in this file.

### 9.1 Contrast and color

Body text 4.5 to 1, large text and UI boundaries 3 to 1 (measured table in 2.3). Color never carries meaning alone: fare trend uses an arrow and words, votes use an icon and a count, group colors use an icon and a label, traveler colors come with a name or initials, status uses text. Focus indicators are at least 2 px, 3 to 1 against neighbors, and never covered by sticky bars (scroll padding under the tab bar and sticky header). Heat grid cells print their price.

### 9.2 Structure, keyboard and focus

One `h1` per screen. Landmarks: header, nav, main. The section strip is a `nav` element with `aria-current="page"` on the current section, not a `tablist`; `aria-selected` is kept only for true tab widgets such as segmented controls (9.3). Every interactive element is reachable by keyboard on web in a logical order, with visible focus. Sheets trap focus, restore it on close, close on Escape. No keyboard traps, no timing limits except session expiry (with a warning). Drag and drop has non-drag alternatives (WCAG 2.5.7). Targets are at least 24 by 24 CSS px on web (2.5.8) and 44 by 44 pt on touch. Consistent help: a Help link in the same place on every screen's overflow menu (3.2.6). Redundant entry is avoided: trip dates and travelers are prefilled from the trip (3.3.7). Authentication has no cognitive test and supports paste in the code field (3.3.8).

### 9.3 VoiceOver and Dynamic Type

- Every icon button has an `aria-label` that names the action and object ("Remove Bairro Alto from Day 2"). Decorative route patterns and icons are hidden.
- Custom controls expose roles and states (`aria-pressed` for votes, `aria-expanded` for day cards, `aria-selected` for true tab widgets such as segmented controls, `aria-current="step"` in the run timeline).
- Dynamic content uses live regions: toasts (`status` or `alert`), run progress (polite), credit balance changes (polite). Loading states expose `aria-busy`.
- Fixed-height shapes such as ticket stubs use `min-height` and grow with text. Playwright runs the main screens at 310 percent text zoom.
- Rotor and headings: each day card is a heading; each list has an accessible count ("Stays, 4 items").
- Reading order matches visual order. Price, age and source are read in one phrase ("412 dollars, cached, checked 3 hours ago"). Verdict chips are read as a word plus the place ("Confirmed, Time Out Market"); the sync indicator announces state changes only.
- **Dynamic Type:** all text is `rem`. The native shell reads the system size through `@capacitor/text-zoom` and applies it to the root font size, supporting up to Accessibility XXXL (about 310%). Layouts reflow rather than clip: the section strip scrolls, the tab bar labels stay (icons stay 22 px, labels wrap to two lines then truncate only at the largest sizes with the accessible name intact), cards stack their metadata, tables scroll horizontally with a sticky label column, buttons grow in height. Test each screen at default, Large and the largest accessibility size.
- Web supports 200% browser zoom and 400% reflow at 320 px width with no two-dimensional scrolling (except the chart and compare table, which scroll in their own region).

### 9.4 Reduced motion, bold text and other system settings

`prefers-reduced-motion` and iOS Reduce Motion: no draw-on, no touchdown scale, no parallax, no sliding sheets (fade instead), no shimmer, no pulsing. Information previously carried by motion (a new item highlight) is also carried by a static label ("New"). Bold Text raises body weight to 600. Increase Contrast swaps `--tp-rule` and `--tp-edge` to the ink color. Smart Invert and Differentiate Without Color are honored by the rules above. Voice Control: every control has a visible text label or a matching accessible name (WCAG 2.5.3). Captions and transcripts are required for any future video.

### 9.5 Testing

Automated: `@axe-core/playwright` in the e2e suite on every screen in light and dark; lint for missing `aria-label` on icon buttons; contrast unit test over the token pairs in 2.3. Manual before each release: VoiceOver walkthrough of onboarding, create trip, fare detail, stays vote, run and paywall; Dynamic Type at the largest size; Reduce Motion on; keyboard only on web. An accessibility statement is published and the App Store Accessibility Nutrition Labels are declared when true.

## 10. Responsive breakpoints

| Name | Width | Layout |
|---|---|---|
| Phone | 0 to 479 px | One column, bottom tabs, sheets, 16 px gutter, full-width primary buttons |
| Large phone | 480 to 767 px | Same, cards up to 560 px centered, two-up chips |
| Tablet | 768 to 1199 px | Icon rail (72 px), two-column grids (trips, stays), right panel as overlay, dialogs centered |
| Laptop | 1200 to 1439 px | Full sidebar (248 px, starts at 1200 px), content 720 to 1120 px, persistent right rail for AI and evidence |
| Desktop | 1440 px and up | Same as laptop, content capped at 1120 px, presentation and map can go full width |

Rules: design mobile first; navigation switches at 768 px; safe areas through `env(safe-area-inset-*)`; `viewport-fit=cover`; inputs 16 px; the iOS app is locked to portrait on phones in version 1 (set in the Capacitor config), and landscape applies to the web and to iPad later; iPad runs the tablet layout (iPhone only in version 1, iPad later). Container queries drive the deck and dense cards so a component adapts to its container, not the window. Tables become stacked cards under 480 px except the compare table, which scrolls horizontally.

## 11. Haptics

Through `@capacitor/haptics`, used sparingly and never the only feedback.

| Event | Haptic |
|---|---|
| Tab change, segmented control change | Selection (light tick) |
| Toggle a vote, switch, checkbox | Impact light |
| Drag pick up and drop on a day | Impact medium on drop |
| Pull to refresh reaches threshold | Impact light |
| Add item, save stay, mark done | Notification success |
| Purchase success, run finished, trip marked booked | Notification success (paired with the ticket stub) |
| Error, blocked action, conflict | Notification error |
| Limit reached, low credits warning | Notification warning |
| Destructive confirm (delete) | Impact heavy, once |

Rules: off when the system or Low Power Mode disables them, and a Settings switch "Haptics" turns them off; no haptics on scroll, timers or agent progress steps; at most one haptic per action.

## 12. Dark mode

Dark mode follows the system by default with an Appearance setting (Light, Dark, System), applied through the `.dark` class on the root (as today in `theme.tsx`) and `color-scheme` so native controls match. Dark values are the tokens in 2.1 and 2.2 and are validated to the same contrast rules (table in 2.3). In the design kit, `tokens.css` puts the dark values under the `.dark` class (and under `prefers-color-scheme: dark` when no class is set), and trip maps darken their land and water.

Rules: the ground is deep night `#0B1A2A`, cards `#12263A`, not black; shadows give way to lighter surfaces and 1 px rules; brand shifts to the light sky `#6CC4FF` with dark ink text (`#0B1A2A`) on it; sky surfaces (web sidebar, splash, paywall header, trip bands) become deep sky `#0E3F66`; route and traveler fills brighten (`--tp-route-a` `#FF7A93`, `--tp-route-b` `#FFD45C`) and the route pattern sits at 50 to 70% on paper and sheet; chart and heat ramps use the dark sets and invert direction so the most prominent step is still the cheapest; images get a 4% dark overlay only when they sit under text; the logo uses the dark lockup and its tile stays sky `#2AA5FF`; the present deck follows the mode but print always forces light; the app icon is the same in both modes. Test every screen and every paywall in both modes, and with Increase Contrast.

## 13. Analytics conventions

Product analytics uses PostHog with no ad or attribution SDKs and no ATT prompt. Event names are `object_action` in snake_case, past tense (`paywall_viewed`, `lodging_voted`). Properties are coarse and never contain free text, names, emails, addresses, exact dates of trips or note content. Every event carries `platform`, `app_version`, `tier`, `is_guest`, `locale`, `env` and a random session id; user id is the account UUID. Outbound partner clicks are logged server side through `/go/{click_id}`, with a random per-click sub-id that is never the user id. Each screen in section 6 lists its events by the names in the catalog; the full catalog, the property values and retention are in [10-quality-security-launch.md](10-quality-security-launch.md), section 4. A screen that needs an event the catalog lacks gets it added there first.
